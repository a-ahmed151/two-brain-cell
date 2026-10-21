"""The scenes before a run: loading, intro (main menu), level select and item select (the Pack screen).

All of them are drawn on the UI kit's 320x180 canvas and scaled up to the window.
Keyboard and mouse both work: the mouse hovers/clicks, the keyboard moves the selection.
"""

import os

import pygame

from game import ui
from game.backpack import BAGS
from game.entities import helper_frame, knight_frame
from game.gear import GEAR, draw_icon
from game.level import load_level, load_tiles
from game.play import PlayScene
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
        # File names start with the level number, so sorting gives the play order.
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

    BUTTONS = ("play", "levels", "quit")  # the kit also has SETTINGS; there are no settings yet
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
            self.game.change_scene(ItemSelectScene(self.game, self.game.next_level()))
        elif button == "levels":
            self.game.change_scene(LevelSelectScene(self.game, self.game.next_level()))
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


class LevelSelectScene(MenuScene):
    """Doors for each level: done, current (the next one to beat), open or locked."""

    ROW = 5  # doors per row

    def __init__(self, game, selected=0):
        super().__init__(game)
        self.selected = selected

    def door_state(self, index):
        if index in self.game.completed:
            return "done"
        if not self.game.level_available(index):
            return "locked"
        return "current" if index == self.game.next_level() else "open"

    def on_hover(self, key):
        if isinstance(key, int):
            self.selected = key

    def on_click(self, key):
        if key == "back":
            self.game.change_scene(IntroScene(self.game))
        else:
            self.start(key)

    def on_key(self, key):
        count = len(self.game.levels)
        moves = {**dict.fromkeys(LEFT_KEYS, -1), **dict.fromkeys(RIGHT_KEYS, 1),
                 **dict.fromkeys(UP_KEYS, -self.ROW), **dict.fromkeys(DOWN_KEYS, self.ROW)}
        if key in moves:
            self.selected = min(max(self.selected + moves[key], 0), count - 1)
        elif key in CONFIRM_KEYS:
            self.start(self.selected)
        elif key == pygame.K_ESCAPE:
            self.game.change_scene(IntroScene(self.game))

    def start(self, index):
        if self.game.level_available(index):
            self.game.change_scene(ItemSelectScene(self.game, index))

    def draw_canvas(self, canvas):
        layout = ui.layout("levels")
        canvas.blit(ui.background("levels_bg"), (0, 0))
        title = ui.sprite(layout["title"]["name"])
        canvas.blit(title, title.get_rect(midtop=(160, layout["title"]["y"])))
        self.draw_torches(canvas, layout["torches"])
        k = layout["knight"]
        image = knight_frame("idle_down", self.time)
        canvas.blit(image, image.get_rect(midbottom=layout_feet(k["x"], k["y"])))

        back = canvas.blit(ui.sprite(f"icon_back_{self.state('back', False)}"), (6, 6))
        self.hotspots.add(back, "back")

        doors = [w for w in layout["widgets"] if w["type"] == "level"]
        for i, level in enumerate(self.game.levels[:len(doors)]):
            door = doors[i]
            state = self.door_state(i)
            hover = "_hover" if i == self.selected else ""
            rect = canvas.blit(ui.sprite(f"level_{state}{hover}"), (door["x"], door["y"]))
            self.hotspots.add(rect, i)
            if state != "locked":
                ui.draw_text(canvas, str(i + 1), (rect.centerx, rect.y + 2), "dark", anchor="midtop")

        level = self.game.levels[self.selected]
        info = layout["info"]
        if self.game.level_available(self.selected):
            ui.draw_text(canvas, f"Level {self.selected + 1}: {level.name}", (info["x"], 158), anchor="midtop")
            ui.draw_text(canvas, "Click a door to start", (info["x"], 169), anchor="midtop", alpha=DIM)
        else:
            ui.draw_text(canvas, f"Level {self.selected + 1}: locked", (info["x"], 158), anchor="midtop")
            ui.draw_text(canvas, "Beat the level before it first", (info["x"], 169), anchor="midtop", alpha=DIM)


class ItemSelectScene(MenuScene):
    """The Pack screen: pick a bag, then which gear goes in it and in what order.

    The keyboard works on one section at a time, top to bottom: bags, gear, start.
    W/S at a section's edge moves to the next one; ENTER/SPACE acts on what's focused.
    """

    PANEL_LEFT, PANEL_RIGHT = 40, 280
    CARD_W, CARD_H, CARD_GAP, CARD_Y = 80, 26, 6, 47
    GEAR_X, GEAR_Y, GEAR_COL_W, GEAR_ROW_H, GEAR_COLS = 40, 88, 76, 10, 2
    RIGHT_X = 196
    START_RECT = pygame.Rect(200, 128, 80, 18)

    def __init__(self, game, level_index, bag_id=None, picked=None):
        super().__init__(game)
        self.level_index = level_index
        self.level = game.levels[level_index]
        self.new_bag = None
        bag = self.level.unlocks_bag
        if bag and bag not in game.unlocked_bags:
            game.unlocked_bags.append(bag)
            self.new_bag = bag
        self.bag_id = bag_id or self.new_bag or game.unlocked_bags[0]
        self.picked = list(picked or [])  # indices into the gear pool, in queue order
        self.cursor = 0  # focused gear, when the gear section is focused
        self.section = "bags"  # "bags", "gear" or "start"

    @property
    def bag(self):
        return BAGS[self.bag_id]

    def choose_bag(self, bag_id):
        if bag_id != self.bag_id:
            self.bag_id = bag_id
            self.picked = []  # switching bags empties it

    def toggle(self, index):
        if index in self.picked:
            self.picked.remove(index)
        elif len(self.picked) < self.bag.slots:
            self.picked.append(index)

    def start(self):
        self.game.change_scene(PlayScene(self.game, self.level_index, self.bag_id, self.picked))

    def back(self):
        self.game.change_scene(LevelSelectScene(self.game, self.level_index))

    def on_hover(self, key):
        kind, value = key
        if kind == "bag":
            self.section = "bags"
        elif kind == "gear":
            self.section, self.cursor = "gear", value
        elif kind == "start":
            self.section = "start"

    def on_click(self, key):
        kind, value = key
        if kind == "bag":
            self.choose_bag(value)
        elif kind == "gear":
            self.toggle(value)
        elif kind == "start":
            self.start()
        elif kind == "back":
            self.back()

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            self.back()
        elif self.section == "bags":
            self.bags_key(key)
        elif self.section == "gear":
            self.gear_key(key)
        elif key in UP_KEYS:
            self.section = "gear" if self.level.gear_pool else "bags"
        elif key in CONFIRM_KEYS:
            self.start()

    def bags_key(self, key):
        bags = self.game.unlocked_bags
        if key in LEFT_KEYS or key in RIGHT_KEYS:
            step = -1 if key in LEFT_KEYS else 1
            self.choose_bag(bags[(bags.index(self.bag_id) + step) % len(bags)])
        elif key in DOWN_KEYS or key in CONFIRM_KEYS:
            self.section = "gear" if self.level.gear_pool else "start"

    def gear_key(self, key):
        count, cols = len(self.level.gear_pool), self.GEAR_COLS
        row, col = divmod(self.cursor, cols)
        if key in LEFT_KEYS and col > 0:
            self.cursor -= 1
        elif key in RIGHT_KEYS and col < cols - 1 and self.cursor + 1 < count:
            self.cursor += 1
        elif key in UP_KEYS:
            if row == 0:
                self.section = "bags"
            else:
                self.cursor -= cols
        elif key in DOWN_KEYS:
            if (row + 1) * cols >= count:
                self.section = "start"  # already on the last row
            else:
                self.cursor = min(self.cursor + cols, count - 1)
        elif key in CONFIRM_KEYS:
            self.toggle(self.cursor)

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, "Pack your bag", (160, 15), "gold", scale=2, anchor="center")
        back = canvas.blit(ui.sprite(f"icon_back_{self.state(('back', None), False)}"), (6, 6))
        self.hotspots.add(back, ("back", None))
        ui.draw_text(canvas, f"{self.level_index + 1}. {self.level.name}", (160, 37), "gold", anchor="midtop")

        self.draw_bags(canvas)
        self.draw_gear(canvas)
        self.draw_queue(canvas)

        start = ("start", None)
        ui.button(canvas, self.START_RECT, "Start", "red", self.state(start, self.section == "start"))
        self.hotspots.add(self.START_RECT, start)

        if self.new_bag:
            new = BAGS[self.new_bag]
            ui.draw_text(canvas, f"New bag unlocked: {new.name} - {new.slots} slots, {new.extract_time}s dig",
                         (160, 152), "gold", anchor="midtop")
        elif self.level.pack_tip:
            ui.draw_text(canvas, self.level.pack_tip, (160, 152), "gold", anchor="midtop")
        ui.draw_text(canvas, "WASD move   ENTER choose   ESC back", (160, 166), anchor="midtop", alpha=DIM)

    def draw_bags(self, canvas):
        bags = self.game.unlocked_bags
        total = len(bags) * self.CARD_W + (len(bags) - 1) * self.CARD_GAP
        x = 160 - total // 2
        for bag_id in bags:
            bag = BAGS[bag_id]
            rect = pygame.Rect(x, self.CARD_Y, self.CARD_W, self.CARD_H)
            selected = bag_id == self.bag_id
            key = ("bag", bag_id)
            ui.nine_slice(canvas, f"button9_{'red' if selected else 'stone'}_{self.state(key, False)}", rect)
            ui.draw_text(canvas, bag.name, (rect.centerx, rect.y + 4), "gold" if selected else "cream",
                         anchor="midtop")
            ui.draw_text(canvas, f"{bag.slots} slots {bag.extract_time}s", (rect.centerx, rect.y + 13),
                         anchor="midtop")
            if selected and self.section == "bags":
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, key)
            x += self.CARD_W + self.CARD_GAP

    def draw_gear(self, canvas):
        ui.draw_text(canvas, "Gear", (self.GEAR_X, 78), alpha=DIM)
        for i, gear in enumerate(self.level.gear_pool):
            col, row = i % self.GEAR_COLS, i // self.GEAR_COLS
            rect = pygame.Rect(self.GEAR_X + col * self.GEAR_COL_W, self.GEAR_Y + row * self.GEAR_ROW_H,
                               self.GEAR_COL_W - 4, self.GEAR_ROW_H)
            if i == self.cursor and self.section == "gear":
                pygame.draw.rect(canvas, GOLD, rect.inflate(2, 0), 1)
            draw_icon(canvas, ICON_FONT, gear, (rect.x + 6, rect.centery), size=10)
            packed = i in self.picked
            ui.draw_text(canvas, GEAR[gear].name, (rect.x + 13, rect.y + 1), alpha=255 if packed else DIM + 60)
            if packed:
                ui.draw_text(canvas, str(self.picked.index(i) + 1), (rect.right - 2, rect.y + 1), "gold",
                             anchor="topright")
            self.hotspots.add(rect, ("gear", i))

    def draw_queue(self, canvas):
        x = self.RIGHT_X
        ui.draw_text(canvas, "Queue", (x, 78), alpha=DIM)
        for slot in range(self.bag.slots):
            rect = pygame.Rect(x + slot * 14, 88, 12, 12)
            if slot < len(self.picked):
                draw_icon(canvas, ICON_FONT, self.level.gear_pool[self.picked[slot]], rect.center, size=12)
            else:
                pygame.draw.rect(canvas, (107, 78, 99), rect, 1)
        ui.draw_text(canvas, "Knight holds", (x, 104), alpha=DIM)
        for slot, gear in enumerate(self.level.knight_gear):
            draw_icon(canvas, ICON_FONT, gear, (x + 6 + slot * 14, 120), size=12)


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
