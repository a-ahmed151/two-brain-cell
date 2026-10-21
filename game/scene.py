"""The scene manager. Each screen (loading, intro, run start, rewards, combat)
is a Scene; Game runs whichever one is active and holds what lives across them."""

import asyncio

import pygame

from game.music import Music

FPS = 60
SCREEN_SIZE = (1280, 720)  # the UI kit's 320x180 canvas at 4x
ICON = "assets/icon.png"  # the window/taskbar icon: the Helper under his bag
ICON_SIZE = 64


class Scene:
    """One screen of the game. Override the hooks you need; switch screens with game.change_scene()."""

    def __init__(self, game):
        self.game = game

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass


class Game:
    def __init__(self):
        # Before set_mode: some platforms only pick up the icon when the window is created.
        pygame.display.set_icon(pygame.transform.smoothscale(pygame.image.load(ICON), (ICON_SIZE, ICON_SIZE)))
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Player 2")
        self.clock = pygame.time.Clock()
        self.scene = None
        self.running = True
        self.closing = None  # seconds left of the music fading out before the window closes
        self.music = Music()
        self.shade = pygame.Surface(SCREEN_SIZE)  # the picture fades to black with the music

        # Filled in by the loading scene.
        self.levels = []  # the arena rooms; each room of a run uses one of them
        self.trial_level = None  # the Trial's own room (levels/trial.tmj), never used for normal rooms
        self.tiles = {}  # tileset image path -> {gid: tile surface}

        self.current_run = None  # the RunState in progress (game/run.py)

    def change_scene(self, scene):
        self.scene = scene

    def quit(self):
        """Fade the music out, then close."""
        if self.closing is None:
            self.closing = self.music.fade_out()

    async def run(self, first_scene):
        self.scene = first_scene
        self.music.start()
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif self.closing is None and not self.music.handle_event(event):
                    self.scene.handle_event(event)
            if self.closing is not None:
                self.closing -= dt
                if self.closing <= 0:
                    self.running = False
            self.scene.update(dt)
            self.music.update(dt)
            self.scene.draw(self.screen)
            self.music.draw(self.screen)
            if self.closing is not None and self.music.fade_time:
                self.shade.set_alpha(round(255 * (1 - max(0.0, self.closing) / self.music.fade_time)))
                self.screen.blit(self.shade, (0, 0))
            pygame.display.flip()

            await asyncio.sleep(0)  # required by pygbag for the web build
