"""The menu scenes: loading, intro (main menu), run start (pick a bag), rewards between rooms and the ending.

All of them are drawn on the UI kit's 320x180 canvas and scaled up to the window.
Keyboard and mouse both work: the mouse hovers/clicks, the keyboard moves the selection.
"""

import os

import pygame

from game import ui
from game.backpack import BAGS
from game.combat import CombatScene
from game.enemies import draw_lineup
from game.entities import helper_frame, knight_frame
from game.gear import GEAR, draw_icon
from game.level import load_level, load_tiles
from game.run import ROOMS, SHRINE_HEAL, STARTING_KIT, RunState
from game.scene import Scene

LEVELS_DIR = "levels"
DIM = 130  # alpha for secondary text
GOLD = (232, 177, 58)
ICON_FONT = ui.IconFont()

UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE)


def layout_feet(x, y):
    """The UI layout places the Knight as a 32x32 frame by its top-left; this is where his feet go."""
    return x + 16, y + 32


class MenuScene(Scene):
    """Shared plumbing: a canvas, mouse hotspots and a clock for animations."""

    def __init__(self, game):
        super().__init__(game)
        self.canvas = pygame.Surface(ui.CANVAS_SIZE)
        self.hotspots = ui.Hotspots()
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def handle_event(self, event):
        result = self.hotspots.handle(event)
        if result:
            kind, key = result
            (self.on_hover if kind == "hover" else self.on_click)(key)
        elif event.type == pygame.KEYDOWN:
            self.on_key(event.key)

    def on_hover(self, key):
        pass

    def on_click(self, key):
        pass

    def on_key(self, key):
        pass

    def draw(self, screen):
        self.hotspots.clear()
        self.draw_canvas(self.canvas)
        ui.present(self.canvas, screen)

    def draw_canvas(self, canvas):
        pass

    def state(self, key, selected):
        """Sprite state for a widget: p(ressed), h(over/selected) or n(ormal)."""
        if self.hotspots.pressed == key:
            return "p"
        return "h" if selected else "n"

    def draw_torches(self, canvas, positions):
        for x, y in positions:
            ui.torch(canvas, (x, y), self.time)


class LoadingScene(MenuScene):
    """Shows "Loading..." for a frame, then loads every level and tileset."""

    def __init__(self, game):
        super().__init__(game)
        self.shown = False

    def update(self, dt):
        if not self.shown:
            return  # draw once before blocking on the loading
        for name in sorted(os.listdir(LEVELS_DIR)):
            if not name.endswith(".tmj"):
                continue
            level = load_level(os.path.join(LEVELS_DIR, name))
            image = level.tileset["image"]
            if image not in self.game.tiles:
                self.game.tiles[image] = load_tiles(level.tileset)
            self.game.levels.append(level)
        self.game.change_scene(IntroScene(self.game))

    def draw_canvas(self, canvas):
        canvas.fill(ui.INK)
        ui.draw_text(canvas, "Loading...", (160, 90), scale=2, anchor="center")
        self.shown = True


class IntroScene(MenuScene):
    """The title screen / main menu."""

    BUTTONS = ("play", "quit")  # the kit also has LEVELS and SETTINGS; a run has neither
    BUTTON_X, BUTTON_TOP, BUTTON_GAP = 112, 68, 23
    KNIGHT_SPEED = 30

    def __init__(self, game):
        super().__init__(game)
        self.selected = 0

    def on_hover(self, key):
        self.selected = self.BUTTONS.index(key)

    def on_click(self, key):
        self.activate(key)

    def on_key(self, key):
        if key in UP_KEYS:
            self.selected = (self.selected - 1) % len(self.BUTTONS)
        elif key in DOWN_KEYS:
            self.selected = (self.selected + 1) % len(self.BUTTONS)
        elif key in CONFIRM_KEYS:
            self.activate(self.BUTTONS[self.selected])
        elif key == pygame.K_ESCAPE:
            self.game.quit()

    def activate(self, button):
        if button == "play":
            self.game.change_scene(RunStartScene(self.game))
        elif button == "quit":
            self.game.quit()

    def draw_canvas(self, canvas):
        layout = ui.layout("main")
        canvas.blit(ui.background("main_bg"), (0, 0))
        ui.draw_text(canvas, "Player 2", (160, 18), "gold", scale=2, anchor="center")
        self.draw_torches(canvas, layout["torches"])

        # The Knight paces back and forth along the floor.
        k = layout["knight"]
        span = k["xmax"] - k["xmin"]
        distance = (self.time * self.KNIGHT_SPEED) % (2 * span)
        going_left = distance > span
        x = k["xmin"] + (2 * span - distance if going_left else distance)
        image = knight_frame("walk_left" if going_left else "walk_right", self.time)
        canvas.blit(image, image.get_rect(midbottom=layout_feet(x, k["y"])))

        for i, name in enumerate(self.BUTTONS):
            y = self.BUTTON_TOP + i * self.BUTTON_GAP
            selected = i == self.selected
            image = ui.sprite(f"btn_{name}_{self.state(name, selected)}")
            rect = canvas.blit(image, (self.BUTTON_X, y))
            self.hotspots.add(rect, name)
            if selected:
                canvas.blit(ui.sprite("cursor_sword"), (self.BUTTON_X - 16, y + 6))


def wrap(text, width):
    """Split text into lines of at most `width` characters, at spaces."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return lines + [line] if line else lines


def draw_card(canvas, rect, state, selected, title, blurb, icon=None, image=None, dim=False):
    """A reward card: icon (or sprite), name and a short wrapped description."""
    ui.nine_slice(canvas, f"button9_{'red' if selected else 'stone'}_{state}", rect)
    if image:
        canvas.blit(image, image.get_rect(center=(rect.centerx, rect.y + 11)))
    elif icon:
        draw_icon(canvas, ICON_FONT, icon, (rect.centerx, rect.y + 11), size=14)
    alpha = DIM if dim else 255
    ui.draw_text(canvas, title, (rect.centerx, rect.y + 21), "gold", anchor="midtop", alpha=alpha)
    for i, line in enumerate(wrap(blurb, rect.w // ui.GLYPH_ADVANCE - 1)[:3]):
        ui.draw_text(canvas, line, (rect.centerx, rect.y + 31 + i * 9), anchor="midtop", alpha=alpha)


class RunStartScene(MenuScene):
    """Pick the bag for this run. Every bag comes with its own starting kit."""

    CARD_W, CARD_H, CARD_GAP, CARD_Y = 92, 84, 8, 36
    START_RECT = pygame.Rect(120, 144, 80, 18)
    BLURBS = {
        "satchel": "The all-rounder.",
        "hauler": "Holds lots. Slow dig.",
        "pouch": "Fast dig. Tiny.",
    }

    def __init__(self, game):
        super().__init__(game)
        self.bags = list(BAGS)
        self.selected = 0

    def start(self):
        bag_id = self.bags[self.selected]
        self.game.current_run = RunState(bag_id, self.game.levels)
        self.game.change_scene(CombatScene(self.game))

    def on_hover(self, key):
        if key != "start" and key != "back":
            self.selected = key

    def on_click(self, key):
        if key == "back":
            self.game.change_scene(IntroScene(self.game))
        elif key == "start":
            self.start()
        else:
            self.selected = key

    def on_key(self, key):
        if key in LEFT_KEYS:
            self.selected = (self.selected - 1) % len(self.bags)
        elif key in RIGHT_KEYS:
            self.selected = (self.selected + 1) % len(self.bags)
        elif key in CONFIRM_KEYS:
            self.start()
        elif key == pygame.K_ESCAPE:
            self.game.change_scene(IntroScene(self.game))

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, "Pick a bag", (160, 15), "gold", scale=2, anchor="center")
        back = canvas.blit(ui.sprite(f"icon_back_{self.state('back', False)}"), (6, 6))
        self.hotspots.add(back, "back")
        ui.draw_text(canvas, f"{ROOMS - 1} rooms, then the boss. One life.", (160, 27), anchor="midtop",
                     alpha=DIM)
        x = 160 - (3 * self.CARD_W + 2 * self.CARD_GAP) // 2
        for i, bag_id in enumerate(self.bags):
            bag = BAGS[bag_id]
            rect = pygame.Rect(x + i * (self.CARD_W + self.CARD_GAP), self.CARD_Y, self.CARD_W, self.CARD_H)
            selected = i == self.selected
            ui.nine_slice(canvas, f"button9_{'red' if selected else 'stone'}_{self.state(i, False)}", rect)
            helper = helper_frame(bag.sprite, "idle_down", self.time)
            canvas.blit(helper, helper.get_rect(midbottom=(rect.centerx, rect.y + 22)))
            ui.draw_text(canvas, bag.name, (rect.centerx, rect.y + 24), "gold", anchor="midtop")
            ui.draw_text(canvas, f"{bag.slots} slots", (rect.centerx, rect.y + 33), anchor="midtop")
            ui.draw_text(canvas, f"dig {bag.extract_time} sec", (rect.centerx, rect.y + 42), anchor="midtop")
            for j, line in enumerate(wrap(self.BLURBS[bag_id], 14)[:2]):
                ui.draw_text(canvas, line, (rect.centerx, rect.y + 53 + j * 9), anchor="midtop", alpha=DIM + 60)
            kit = STARTING_KIT[bag_id]
            for j, gear in enumerate(kit):
                draw_icon(canvas, ICON_FONT, gear, (rect.centerx - (len(kit) - 1) * 6 + j * 12, rect.bottom - 9),
                          size=10)
            if selected:
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, i)
        ui.draw_text(canvas, "The Knight starts with his Sword.", (160, 124), anchor="midtop")
        ui.draw_text(canvas, "Bag order is dig order.", (160, 133), anchor="midtop", alpha=DIM)
        ui.button(canvas, self.START_RECT, "Start", "red", self.state("start", True))
        self.hotspots.add(self.START_RECT, "start")
        ui.draw_text(canvas, "A/D choose   ENTER start", (160, 168), anchor="midtop", alpha=DIM)


class RewardScene(MenuScene):
    """Between rooms: pick gear for the bag (or a priest's blessing), then sort the bag.

    Sections, top to bottom: the cards, the bag, the Go button. W/S moves between them.
    In the bag, choosing two slots swaps them; with the bag full, a picked card
    asks which gear to throw out for it.
    """

    CARD_W, CARD_H, CARD_GAP, CARD_Y = 92, 58, 8, 30
    BAG_Y = 104
    GO_RECT = pygame.Rect(120, 156, 80, 15)
    BLESSINGS = [
        ("heal", "Prayer", f"Heals the Knight {SHRINE_HEAL} HP."),
        ("slot", "Bigger bag", "One more slot."),
        ("dig", "Quick hands", "Dig 25% faster."),
    ]
    PRIEST = "assets/Character_animation/priests_idle/priest{}/v1/priest{}_v1_1.png"

    def __init__(self, game, picks=1, shrine=False):
        super().__init__(game)
        self.run = game.current_run
        self.shrine = shrine
        self.picks = picks
        self.cards = [b[0] for b in self.BLESSINGS] if shrine else self.run.roll_rewards()
        self.taken = set()
        self.section = "cards"
        self.cursor = 0  # in the cards or the bag, whichever is focused
        self.grabbed = None  # bag slot waiting for a second slot to swap with
        self.pending = None  # a card waiting for a bag slot to replace
        self.priests = [pygame.image.load(self.PRIEST.format(i, i)).convert_alpha() for i in (1, 2, 3)]

    @property
    def queue(self):
        return self.run.backpack.queue

    def take(self, index):
        if self.picks <= 0 or index in self.taken:
            return
        card = self.cards[index]
        if self.shrine:
            {"heal": self.run.heal, "slot": self.run.bigger_bag, "dig": self.run.faster_digging}[card]()
        elif self.run.backpack.full:
            self.pending = index
            self.section, self.cursor = "bag", 0
            return
        else:
            self.run.backpack.add(card)
        self.taken.add(index)
        self.picks -= 1
        if self.picks == 0:
            self.section, self.cursor = "go", 0

    def choose_slot(self, slot):
        if self.pending is not None:
            if slot < len(self.queue):
                self.queue[slot] = self.cards[self.pending]
                self.taken.add(self.pending)
                self.pending = None
                self.picks -= 1
                if self.picks > 0:
                    self.section, self.cursor = "cards", 0
            return
        if slot >= len(self.queue):
            return
        if self.grabbed is None:
            self.grabbed = slot
        else:
            a, b = self.grabbed, slot
            self.queue[a], self.queue[b] = self.queue[b], self.queue[a]
            self.grabbed = None

    def go(self):
        self.game.change_scene(CombatScene(self.game))

    def on_hover(self, key):
        kind, value = key
        if kind in ("cards", "bag"):
            self.section, self.cursor = kind, value
        elif kind == "go":
            self.section = "go"

    def on_click(self, key):
        kind, value = key
        if kind == "cards":
            self.take(value)
        elif kind == "bag":
            self.choose_slot(value)
        elif kind == "go":
            self.go()

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            self.pending = self.grabbed = None
            return
        sections = ["cards", "bag", "go"]
        index = sections.index(self.section)
        if key in UP_KEYS and index > 0:
            self.section, self.cursor = sections[index - 1], 0
        elif key in DOWN_KEYS and index < 2:
            self.section, self.cursor = sections[index + 1], 0
        elif key in LEFT_KEYS:
            self.cursor = max(0, self.cursor - 1)
        elif key in RIGHT_KEYS:
            count = len(self.cards) if self.section == "cards" else self.run.backpack.bag.slots
            self.cursor = min(count - 1, self.cursor + 1)
        elif key in CONFIRM_KEYS:
            if self.section == "cards":
                self.take(self.cursor)
            elif self.section == "bag":
                self.choose_slot(self.cursor)
            else:
                self.go()

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        title = "Blessing" if self.shrine else ("Pick a reward" if self.picks < 2 else "Pick two")
        ui.draw_text(canvas, title, (160, 14), "gold", scale=2, anchor="center")
        self.draw_cards(canvas)
        self.draw_bag(canvas)

        label = "Next: the boss" if self.run.boss_room else f"Next: room {self.run.room + 1}"
        ui.draw_text(canvas, label, (30, 130), "gold")
        draw_lineup(canvas, self.run.enemies, (190, 134))
        if self.pending is not None:
            message = "Bag full! Pick gear to throw out."
        elif self.grabbed is not None:
            message = "Now pick the slot to swap with."
        elif self.picks > 0:
            message = "Choose a card, or skip with Go."
        else:
            message = "Pick two bag slots to swap them."
        ui.draw_text(canvas, message, (160, 146), anchor="midtop")

        label = "Fight the boss" if self.run.boss_room else "Next room"
        ui.button(canvas, self.GO_RECT, label, "red", self.state(("go", 0), self.section == "go"))
        self.hotspots.add(self.GO_RECT, ("go", 0))
        if self.section == "go":
            pygame.draw.rect(canvas, GOLD, self.GO_RECT.inflate(4, 4), 1)
        ui.draw_text(canvas, "WASD move   ENTER choose", (160, 173), anchor="midtop", alpha=DIM)

    def draw_cards(self, canvas):
        x = 160 - (3 * self.CARD_W + 2 * self.CARD_GAP) // 2
        for i, card in enumerate(self.cards):
            rect = pygame.Rect(x + i * (self.CARD_W + self.CARD_GAP), self.CARD_Y, self.CARD_W, self.CARD_H)
            key = ("cards", i)
            focused = self.section == "cards" and self.cursor == i
            dim = i in self.taken or self.picks <= 0
            if self.shrine:
                _, name, blurb = self.BLESSINGS[i]
                draw_card(canvas, rect, self.state(key, False), i in self.taken, name, blurb,
                          image=self.priests[i], dim=dim and i not in self.taken)
            else:
                gear = GEAR[card]
                draw_card(canvas, rect, self.state(key, False), i in self.taken, gear.name, gear.blurb,
                          icon=card, dim=dim and i not in self.taken)
            if focused or self.pending == i:
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, key)

    def draw_bag(self, canvas):
        backpack = self.run.backpack
        bag = backpack.bag
        ui.draw_text(canvas, f"{bag.name}: {bag.slots} slots, dig {bag.extract_time}", (30, self.BAG_Y - 10),
                     alpha=DIM + 60)
        for slot in range(bag.slots):
            rect = pygame.Rect(30 + slot * 16, self.BAG_Y, 13, 13)
            gear = self.queue[slot] if slot < len(self.queue) else None
            if gear:
                draw_icon(canvas, ICON_FONT, gear, rect.center, size=13)
            else:
                pygame.draw.rect(canvas, (107, 78, 99), rect, 1)
            if slot == self.grabbed:
                pygame.draw.rect(canvas, (120, 220, 255), rect.inflate(4, 4), 1)
            elif self.section == "bag" and self.cursor == slot:
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, ("bag", slot))
        ui.draw_text(canvas, "1st", (30, self.BAG_Y + 15), alpha=DIM)

        ui.draw_text(canvas, f"Knight {self.run.knight_hp}/{self.run.knight_max_hp}", (290, self.BAG_Y - 10),
                     anchor="topright", alpha=DIM + 60)
        for i, gear in enumerate(self.run.knight_gear):
            draw_icon(canvas, ICON_FONT, gear, (284 - i * 16, self.BAG_Y + 6), size=13)


class EndingScene(MenuScene):
    """After the betrayal: the Knight's last words, then the Helper finally gets paid."""

    LINES = [
        ("Tell my mother... I was right...", "cream"),
        ("The Knight never saw it coming.", "cream"),
        ("This time, the Helper keeps the gold.", "cream"),
        ("And the Knight gets the stale bread.", "cream"),
        ("Player 2 wins.", "gold"),
    ]
    FIRST_LINE, LINE_DELAY = 1.0, 1.6

    def lines_shown(self):
        return max(0, min(len(self.LINES), int((self.time - self.FIRST_LINE) / self.LINE_DELAY) + 1))

    def advance(self):
        if self.lines_shown() < len(self.LINES):
            self.time = self.FIRST_LINE + self.LINE_DELAY * len(self.LINES)  # skip to the end
        else:
            self.game.change_scene(IntroScene(self.game))

    def on_click(self, key):
        self.advance()

    def on_key(self, key):
        if key in CONFIRM_KEYS or key == pygame.K_ESCAPE:
            self.advance()

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, "The End", (160, 15), "gold", scale=2, anchor="center")
        # Click anywhere to continue.
        self.hotspots.add(canvas.get_rect(), "continue")

        knight = knight_frame("death", self.time)
        canvas.blit(knight, knight.get_rect(midbottom=(144, 76)))
        helper = helper_frame("large", "idle_left", self.time)  # facing the Knight, bag full of gold
        canvas.blit(helper, helper.get_rect(midbottom=(176, 76)))

        for i, (line, color) in enumerate(self.LINES[:self.lines_shown()]):
            ui.draw_text(canvas, line, (160, 86 + i * 12), color, anchor="midtop")
        if self.lines_shown() == len(self.LINES):
            ui.draw_text(canvas, "ENTER: main menu", (160, 160), anchor="midtop", alpha=DIM)
