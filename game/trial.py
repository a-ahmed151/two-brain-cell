"""The Trial of the Four Seals: an optional, hard room on the way to room 8.

A sealed door offers a deal. Inside, four waves ("seals") of Trial monsters come one
after another, and each seal is a riddle: only ONE piece of gear hurts its monsters at
all (Enemy.type.only), everything else just bounces off ("immune"). The riddles are
shown before you go in, while you pack a lent bag (the Trial Pack), so the quiz is
answered by doing: pack the bag in the right order, then dig out and hand him the right
thing at the right time. Spike traps in the floor rise and fall in turns.

Win: he's fully healed, the bag gets a slot, and you pick 2 rewards. Lose: the run.
See "The Trial" in GAME_DESIGN.md.
"""

from dataclasses import dataclass
from functools import cache

import pygame

from game import ui
from game.backpack import Backpack, Bag
from game.combat import GOLD, CombatScene, draw_level
from game.enemies import Enemy
from game.gear import GEAR
from game.menus import CONFIRM_KEYS, DIM, LEFT_KEYS, RIGHT_KEYS, MenuScene, RewardScene

TRIAL_KIT = ["pickaxe", "torch", "bomb", "bomb", "potion", "shield"]  # lent for the Trial; the Shield is a red herring
TRIAL_SLOTS = 8  # room for the kit and what he was holding
BREAK_TIME = 3.5  # seconds between seals, to read the next riddle and get ready
RIDDLE_TIME = 4.0  # the riddle stays up this long into each seal
WIN_PICKS = 2

SPIKE_FRAMES = [f"assets/items and trap_animation/peaks/peaks_{i}.png" for i in range(1, 5)]
UP, HALF, DOWN, TIPS = 0, 1, 2, 3  # indices into SPIKE_FRAMES
SPIKE_CYCLE = 3.2  # seconds; the two groups of spikes are half a cycle apart
SPIKE_KNIGHT_DAMAGE = 1  # once per rise; the Helper loses a heart
FLAG_FRAMES = [f"assets/items and trap_animation/flag/flag_{i}.png" for i in range(1, 5)]

NUMERALS = ["I", "II", "III", "IV"]


@dataclass(frozen=True)
class Seal:
    riddle: tuple  # two short lines (41 characters at most together); only hints at the gear
    wave: tuple  # (enemy kind, spawn index, (dx, dy) offset)


SEALS = [
    Seal(("They wear the mountain.", "Break it."),
         (("warden", 0, (0, 0)), ("warden", 3, (0, 0)), ("warden", 4, (0, 0)))),
    Seal(("Born of dark,", "they fear the light."),
         (("shade", 1, (0, 0)), ("shade", 2, (0, 0)), ("shade", 5, (0, 0)), ("shade", 6, (0, 0)),
          ("wisp", 3, (0, 0)), ("wisp", 4, (0, 0)))),
    Seal(("Blades can't wake stone.", "Thunder can."),
         (("gargoyle", 1, (0, 0)), ("gargoyle", 1, (14, -8)), ("gargoyle", 2, (0, 0)), ("gargoyle", 2, (-14, 8)))),
    Seal(("Iron and shadow together.", "Be quick!"),
         (("warden", 3, (0, 0)), ("warden", 4, (0, 0)), ("shade", 5, (0, 0)), ("shade", 6, (0, 0)),
          ("wisp", 1, (0, 0)), ("wisp", 2, (0, 0)))),
]


@cache
def spike_frames():
    return [pygame.image.load(p).convert_alpha() for p in SPIKE_FRAMES]


@cache
def flag_frames():
    return [pygame.image.load(p).convert_alpha() for p in FLAG_FRAMES]


def spike_state(time):
    """Which spike frame shows `time` seconds into a cycle: down, tips poking out as a
    warning, then up (dangerous) and back down."""
    t = time % SPIKE_CYCLE
    if t < 1.5:
        return DOWN
    if t < 2.1:
        return TIPS
    if t < 2.25:
        return HALF
    if t < 3.05:
        return UP
    return HALF


def lend_trial_pack(run):
    """Swap the run's bag for the Trial Pack; his hands stay as they are. Undo with give_back."""
    bag = run.backpack.bag
    run.lent = (run.backpack, dict(run.hands))
    run.backpack = Backpack(Bag("Trial Pack", TRIAL_SLOTS, bag.extract_time, bag.sprite), TRIAL_KIT)


def give_back(run):
    """The Trial Pack goes back; the run's own bag and his own hands return as they were."""
    if run.lent:
        run.backpack, run.hands = run.lent
        run.lent = None


class TrialOfferScene(MenuScene):
    """The sealed door: go in, or walk past to the normal reward."""

    BUTTONS = ("enter", "pass")
    BUTTON_RECTS = {"enter": pygame.Rect(76, 148, 80, 18), "pass": pygame.Rect(164, 148, 80, 18)}

    def __init__(self, game, shrine=False):
        super().__init__(game)
        self.shrine = shrine  # what would have come next, if you walk past
        self.selected = 0

    def activate(self, button):
        run = self.game.current_run
        if button == "enter":
            lend_trial_pack(run)
            self.game.change_scene(TrialPrepScene(self.game))
        else:
            self.game.change_scene(RewardScene(self.game, shrine=self.shrine))

    def on_hover(self, key):
        self.selected = self.BUTTONS.index(key)

    def on_click(self, key):
        self.activate(key)

    def on_key(self, key):
        if key in LEFT_KEYS or key in RIGHT_KEYS:
            self.selected = 1 - self.selected
        elif key in CONFIRM_KEYS:
            self.activate(self.BUTTONS[self.selected])
        elif key == pygame.K_ESCAPE:
            self.activate("pass")

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        self.draw_torches(canvas, [(24, 60), (284, 60)])
        flags = flag_frames()
        flag = flags[int(self.time * 6) % len(flags)]
        for x in (40, 264):
            canvas.blit(flag, flag.get_rect(midbottom=(x + 8, 34)))
        ui.draw_text(canvas, "A sealed door", (160, 15), "gold", scale=2, anchor="center")
        lines = [
            ("Four seals glow on an old door. A voice:", "cream", 255),
            ("Read my riddles. Pack my bag.", "cream", 255),
            ("Answer each seal with the ONE thing", "cream", 255),
            ("that hurts it... or stay here forever.", "cream", 255),
            ("", "cream", 255),
            ("Win: the Knight fully healed, a bigger", "gold", 255),
            (f"bag, and {WIN_PICKS} rewards to pick.", "gold", 255),
            ("Lose: the run is over. Hearts stay lost.", "cream", DIM + 40),
        ]
        for i, (line, color, alpha) in enumerate(lines):
            ui.draw_text(canvas, line, (160, 34 + i * 12), color, anchor="midtop", alpha=alpha)
        for i, name in enumerate(self.BUTTONS):
            rect = self.BUTTON_RECTS[name]
            selected = i == self.selected
            ui.button(canvas, rect, "Enter" if name == "enter" else "Walk past",
                      "red" if name == "enter" else "stone", self.state(name, selected))
            if selected:
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, name)
        ui.draw_text(canvas, "A/D choose   ENTER go", (160, 172), anchor="midtop", alpha=DIM)


class TrialPrepScene(RewardScene):
    """Read the four riddles and pack the lent bag (same controls as "Get ready")."""

    def __init__(self, game):
        super().__init__(game, picks=0)

    def go(self):
        self.game.change_scene(TrialScene(self.game))

    def quit_button(self):
        # Back out to the door: the Trial Pack is given back.
        give_back(self.run)
        self.game.change_scene(TrialOfferScene(self.game))

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, "The riddles", (160, 13), "gold", scale=2, anchor="center")
        back = canvas.blit(ui.sprite(f"icon_back_{self.state(('quit', 0), False)}"), (6, 6))
        self.hotspots.add(back, ("quit", 0))
        for i, seal in enumerate(SEALS):
            y = 27 + i * 11
            ui.draw_text(canvas, NUMERALS[i], (14, y), "gold")
            ui.draw_text(canvas, " ".join(seal.riddle), (38, y))
        ui.draw_text(canvas, "Only the right gear hurts each seal.", (160, 74), anchor="midtop")
        ui.draw_text(canvas, "Pack it in order: the front is dug first.", (160, 84), anchor="midtop", alpha=DIM)
        self.draw_slots(canvas)
        ui.draw_text(canvas, "Lent for the Trial. Your bag waits.", (160, 131), anchor="midtop", alpha=DIM)

        if self.notice_left:
            message = self.notice
        elif self.grabbed is not None:
            message = "Now pick where it goes."
        else:
            message = "Pick a slot, then where it goes."
        ui.draw_text(canvas, message, (160, 143), anchor="midtop")
        ui.button(canvas, self.GO_RECT, "Enter", "red", self.state(("go", 0), self.section == "go"))
        self.hotspots.add(self.GO_RECT, ("go", 0))
        if self.section == "go":
            pygame.draw.rect(canvas, GOLD, self.GO_RECT.inflate(4, 4), 1)
        ui.draw_text(canvas, "WASD move   ENTER choose   ESC back", (160, 173), anchor="midtop", alpha=DIM)


class TrialScene(CombatScene):
    """The fight: four seals in a row in the Hall of Seals, with spike traps."""

    def __init__(self, game):
        super().__init__(game)
        level = self.level = game.trial_level
        self.tiles = game.tiles[level.tileset["image"]]
        draw_level(self.background, level, self.tiles)
        self.knight.pos = pygame.Vector2(level.knight_start)
        self.helper.pos = pygame.Vector2(level.helper_start)
        self.helper.rect.center = round(self.helper.pos.x), round(self.helper.pos.y)
        self.seal = 0
        self.enemies = self.spawn(0)
        self.seal_time = 0.0  # seconds since this seal's monsters appeared
        self.break_time = 0.0  # seconds since the last seal broke
        self.spike_time = 0.0
        self.spiked = set()  # (spike index, rise number): the Knight's been hit by that rise already
        # Two groups that take turns, half a cycle apart: spikes in up-down lanes, and the rest.
        ts = level.tile_size
        tiles = {(int(x // ts), int(y // ts)) for x, y in level.spikes}
        self.spike_offset = []
        for x, y in level.spikes:
            col, row = int(x // ts), int(y // ts)
            upright = (col, row - 1) in tiles or (col, row + 1) in tiles
            self.spike_offset.append(0.0 if upright else SPIKE_CYCLE / 2)

    def spawn(self, index):
        spawns = self.level.spawns
        wave = []
        for kind, at, offset in SEALS[index].wave:
            enemy = Enemy(kind, spawns[at] + offset)
            enemy.flash = 0.4  # they burst out of the seal
            wave.append(enemy)
        return wave

    @property
    def last_seal(self):
        return self.seal == len(SEALS) - 1

    def hud_title(self):
        return f"Seal {NUMERALS[self.seal]}/{NUMERALS[-1]}"

    # --- the waves ---

    def room_won(self, dt):
        if self.last_seal:
            return True
        if self.break_time == 0.0:
            self.knight.popup(f"Seal {NUMERALS[self.seal]} broken!", GOLD)
        self.break_time += dt
        if self.break_time >= BREAK_TIME:
            self.seal += 1
            self.enemies = self.spawn(self.seal)
            self.break_time = self.seal_time = 0.0
        return False

    def update(self, dt):
        super().update(dt)
        if self.paused or not self.started or self.outcome or self.exiting:
            return
        self.seal_time += dt
        self.spike_time += dt
        self.spring_spikes()
        self.resupply()

    def spike_up(self, index):
        return spike_state(self.spike_time + self.spike_offset[index]) == UP

    def spring_spikes(self):
        """Raised spikes cost the Helper a heart (then his usual moment of safety), and
        hurt the Knight once per rise. They don't bother the monsters."""
        knight, helper = self.knight, self.helper
        feet = pygame.Rect(0, 0, 9, 5)
        feet.center = (knight.pos.x, knight.pos.y + 4)
        for i, spike in enumerate(self.level.spikes):
            if not self.spike_up(i):
                continue
            rect = pygame.Rect(0, 0, 12, 12)
            rect.center = spike
            if helper.alive and rect.colliderect(helper.rect):
                helper.hurt(1)
            rise = int((self.spike_time + self.spike_offset[i]) // SPIKE_CYCLE)
            if not knight.dead and rect.colliderect(feet) and (i, rise) not in self.spiked:
                self.spiked.add((i, rise))
                knight.hurt(SPIKE_KNIGHT_DAMAGE)

    def resupply(self):
        """Bombs get used up. If a seal still needs gear that's gone (in the bag, in your
        hands, in his), the seal grants another, so the Trial can't be stuck for good."""
        helper, knight = self.helper, self.knight
        have = set(helper.backpack.queue) | {helper.held, knight.tool, knight.item}
        needed = {e.type.only for e in self.enemies if e.type.only} - have
        for gear in needed:
            if not helper.backpack.full:
                helper.backpack.put_back(gear)
                knight.popup(f"The seal grants a {GEAR[gear].name}.", GOLD, self.level.exit_pos + (0, 24))

    def room_clear(self):
        """Through the door: give the Trial Pack back and collect the reward."""
        run = self.run
        run.helper_hp = self.helper.hp
        give_back(run)
        run.knight_hp = run.knight_max_hp  # fully healed
        run.bigger_bag()
        run.trial_won = True
        self.outcome = "won"
        self.game.change_scene(RewardScene(self.game, picks=WIN_PICKS))

    def leave(self):
        if self.outcome == "lost":
            give_back(self.run)
        super().leave()

    # --- drawing ---

    def draw_floor(self, world):
        frames = spike_frames()
        for i, spike in enumerate(self.level.spikes):
            image = frames[spike_state(self.spike_time + self.spike_offset[i])]
            world.blit(image, image.get_rect(center=spike))

    def current_tip(self):
        if self.knight.dead or self.exiting or self.outcome:
            return None
        if self.last_seal and not self.enemies:
            return ["The last seal breaks! Walk out the door."]
        upcoming = self.seal + 1 if not self.enemies else self.seal
        if self.enemies and self.seal_time > RIDDLE_TIME:
            return None
        riddle = SEALS[upcoming].riddle
        return [f"Seal {NUMERALS[upcoming]}", *riddle]

    def draw_start(self, overlay):
        overlay.fill((0, 0, 0, 140))
        lines = [
            ("Four seals. Each one: only ONE", "cream"),
            ("piece of gear can hurt it.", "cream"),
            ("", "cream"),
            (f"Seal {NUMERALS[0]}:", "gold"),
            *[(line, "cream") for line in SEALS[0].riddle],
            ("", "cream"),
            ("Spikes rise in turns. Watch them!", "cream"),
        ]
        width = max(len(line) for line, _ in lines) * ui.GLYPH_ADVANCE + 24
        rect = pygame.Rect(0, 0, max(width, 160), 62 + 10 * len(lines))
        rect.center = overlay.get_rect().center
        ui.nine_slice(overlay, "panel9", rect)
        ui.draw_text(overlay, "The Trial", (rect.centerx, rect.y + 10), "gold", scale=2, anchor="midtop")
        for i, (line, color) in enumerate(lines):
            ui.draw_text(overlay, line, (rect.centerx, rect.y + 32 + i * 10), color, anchor="midtop")
        pulse = 255 if int(self.time * 2) % 2 == 0 else 140
        ui.draw_text(overlay, "Press SPACE to start", (rect.centerx, rect.bottom - 16), "gold", anchor="midtop",
                     alpha=pulse)
