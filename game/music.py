"""Background music: assets/sounds/bg.mp3 on a loop, faded in when the game starts and
faded out when it closes.

The volume is adjustable from anywhere in the game: < and > (or - and +) turn it down
and up in steps of 10%, M mutes. A small panel shows the level for a moment. The level is kept
in settings.json, so it's the same next time.
"""

import sys

import pygame

from game import settings, ui

TRACK = "assets/sounds/bg.mp3"
WEB_TRACK = "assets/sounds/bg.ogg"  # browsers (the pygbag web build) play Ogg, not MP3
FADE_IN_MS = 3000
FADE_OUT_MS = 1500
STEPS = 10  # the volume goes 0..STEPS
DEFAULT_LEVEL = 4  # 40%: quiet enough to sit under the sound effects
MAX_VOLUME = 0.5  # the mixer volume at 100%; the track is mastered loud
TOAST_TIME = 1.5  # seconds the volume panel stays up after a change

DOWN_KEYS = (pygame.K_COMMA, pygame.K_LESS, pygame.K_MINUS, pygame.K_KP_MINUS)
UP_KEYS = (pygame.K_PERIOD, pygame.K_GREATER, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS)
MUTE_KEYS = (pygame.K_m,)


def _load_level():
    try:
        level = int(settings.load().get("music", DEFAULT_LEVEL))
        return max(0, min(STEPS, level))
    except (ValueError, TypeError):
        return DEFAULT_LEVEL


class Music:
    def __init__(self):
        self.level = _load_level()
        self.muted = False
        self.playing = False
        self.toast = 0.0
        self.canvas = pygame.Surface((80, 20), pygame.SRCALPHA)

    @property
    def volume(self):
        """What the mixer is set to (0..MAX_VOLUME)."""
        if self.muted:
            return 0.0
        return MAX_VOLUME * self.level / STEPS

    def start(self):
        """Start the track, fading in. Does nothing if there's no audio device or file."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(WEB_TRACK if sys.platform == "emscripten" else TRACK)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(loops=-1, fade_ms=FADE_IN_MS)
            self.playing = True
        except (pygame.error, FileNotFoundError):
            self.playing = False

    fade_time = FADE_OUT_MS / 1000

    def fade_out(self):
        """Start fading out; returns how many seconds that takes. With no music the game
        still fades the picture out, just as long."""
        if self.playing:
            pygame.mixer.music.fadeout(FADE_OUT_MS)
            self.playing = False
        return self.fade_time

    def handle_event(self, event):
        """< > (- +) and M, from any screen. Returns True if the key was a volume key."""
        if event.type != pygame.KEYDOWN:
            return False
        if event.key in DOWN_KEYS:
            self.level, self.muted = max(0, self.level - 1), False
        elif event.key in UP_KEYS:
            self.level, self.muted = min(STEPS, self.level + 1), False
        elif event.key in MUTE_KEYS:
            self.muted = not self.muted
        else:
            return False
        if self.playing:
            pygame.mixer.music.set_volume(self.volume)
        self.toast = TOAST_TIME
        self.save()
        return True

    def save(self):
        settings.set("music", self.level)

    def update(self, dt):
        self.toast = max(0.0, self.toast - dt)

    def draw(self, screen):
        """The volume panel, top centre, for a moment after a change."""
        if not self.toast:
            return
        canvas = self.canvas
        canvas.fill((0, 0, 0, 0))
        rect = canvas.get_rect()
        pygame.draw.rect(canvas, ui.INK, rect, border_radius=3)
        pygame.draw.rect(canvas, (107, 78, 99), rect, 1, border_radius=3)
        label = "Music off" if self.muted or self.level == 0 else f"Music {self.level * 10}%"
        ui.draw_text(canvas, label, (rect.centerx, 3), "gold", anchor="midtop")
        for i in range(STEPS):
            on = i < self.level and not self.muted
            pygame.draw.rect(canvas, (232, 177, 58) if on else (70, 52, 70), (6 + i * 7, 13, 5, 3))
        image = pygame.transform.scale_by(canvas, ui.UI_SCALE)
        image.set_alpha(round(255 * min(1.0, self.toast / 0.3)))  # fades away at the end
        screen.blit(image, image.get_rect(midtop=(screen.get_width() // 2, 8)))
