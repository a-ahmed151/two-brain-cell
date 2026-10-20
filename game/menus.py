"""The scenes before a run: loading, intro, level select and item select (the Pack screen)."""

import os

import pygame

from game.backpack import BAGS, Backpack
from game.gear import GEAR, draw_icon
from game.level import load_level, load_tiles
from game.play import PlayScene
from game.scene import BACKGROUND_COLOR, DIM_COLOR, HIGHLIGHT_COLOR, TEXT_COLOR, Scene, draw_text

LEVELS_DIR = "levels"


class LoadingScene(Scene):
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

    def draw(self, screen):
        screen.fill(BACKGROUND_COLOR)
        draw_text(screen, self.game.big_font, "Loading...", screen.get_rect().center, "center")
        self.shown = True


class IntroScene(Scene):
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.game.quit()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.game.change_scene(LevelSelectScene(self.game))

    def draw(self, screen):
        game = self.game
        screen.fill(BACKGROUND_COLOR)
        cx, cy = screen.get_rect().center
        draw_text(screen, game.title_font, "Player 2", (cx, cy - 60), "center")
        draw_text(screen, game.font, "Every hero needs someone to carry the stuff.", (cx, cy), "center", DIM_COLOR)
        draw_text(screen, game.big_font, "Press ENTER", (cx, cy + 100), "center", HIGHLIGHT_COLOR)


class LevelSelectScene(Scene):
    def __init__(self, game, selected=0):
        super().__init__(game)
        self.selected = selected

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        count = len(self.game.levels)
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % count
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % count
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.game.level_available(self.selected):
                self.game.change_scene(ItemSelectScene(self.game, self.selected))
        elif event.key == pygame.K_ESCAPE:
            self.game.change_scene(IntroScene(self.game))

    def draw(self, screen):
        game = self.game
        screen.fill(BACKGROUND_COLOR)
        draw_text(screen, game.big_font, "Choose a dungeon", (screen.get_width() // 2, 60), "midtop")
        for i, level in enumerate(game.levels):
            y = 140 + i * 40
            available = game.level_available(i)
            label = f"{i + 1}. {level.name}" if available else f"{i + 1}. (locked)"
            if i in game.completed:
                label += "   done"
            color = HIGHLIGHT_COLOR if i == self.selected else TEXT_COLOR if available else DIM_COLOR
            draw_text(screen, game.big_font, label, (200, y), color=color)
            if i == self.selected:
                draw_text(screen, game.big_font, ">", (170, y), color=color)
        draw_text(screen, game.font, "W/S: choose    ENTER: pack your bag    ESC: back",
                  (screen.get_width() // 2, screen.get_height() - 8), "midbottom")


class ItemSelectScene(Scene):
    """The Pack screen: pick a bag, then which gear goes in it and in what order."""

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
        self.cursor = 0

    @property
    def bag(self):
        return BAGS[self.bag_id]

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        pool = self.level.gear_pool
        if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            bags = self.game.unlocked_bags
            step = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
            new_id = bags[(bags.index(self.bag_id) + step) % len(bags)]
            if new_id != self.bag_id:
                self.bag_id = new_id
                self.picked = []  # switching bags empties it
        elif event.key in (pygame.K_UP, pygame.K_w) and pool:
            self.cursor = (self.cursor - 1) % len(pool)
        elif event.key in (pygame.K_DOWN, pygame.K_s) and pool:
            self.cursor = (self.cursor + 1) % len(pool)
        elif event.key == pygame.K_SPACE and pool:
            if self.cursor in self.picked:
                self.picked.remove(self.cursor)
            elif len(self.picked) < self.bag.slots:
                self.picked.append(self.cursor)
        elif event.key == pygame.K_RETURN:
            self.game.change_scene(PlayScene(self.game, self.level_index, self.bag_id, self.picked))
        elif event.key == pygame.K_ESCAPE:
            self.game.change_scene(LevelSelectScene(self.game, self.level_index))

    def draw(self, screen):
        game = self.game
        screen.fill(BACKGROUND_COLOR)
        width = screen.get_width()
        draw_text(screen, game.big_font, f"{self.level_index + 1}. {self.level.name}", (width // 2, 24), "midtop")
        if self.new_bag:
            new = BAGS[self.new_bag]
            draw_text(screen, game.font, f"New bag: {new.name}! Holds {new.slots}, {new.extract_time}s to dig.",
                      (width // 2, 64), "midtop", HIGHLIGHT_COLOR)

        # Bags, left to right.
        draw_text(screen, game.font, "Bag  (A/D)", (60, 100), color=DIM_COLOR)
        for i, bag_id in enumerate(game.unlocked_bags):
            bag = BAGS[bag_id]
            box = pygame.Rect(60 + i * 220, 126, 200, 70)
            selected = bag_id == self.bag_id
            pygame.draw.rect(screen, HIGHLIGHT_COLOR if selected else DIM_COLOR, box, 3 if selected else 1,
                             border_radius=6)
            draw_text(screen, game.big_font, bag.name, (box.x + 12, box.y + 8))
            draw_text(screen, game.font, f"{bag.slots} slots, {bag.extract_time}s dig", (box.x + 12, box.y + 42),
                      color=DIM_COLOR)

        # The level's gear pool; a number shows where a piece sits in the queue.
        draw_text(screen, game.font, "Gear  (W/S, SPACE to pack)", (60, 230), color=DIM_COLOR)
        for i, gear in enumerate(self.level.gear_pool):
            y = 262 + i * 30
            selected = i == self.cursor
            if selected:
                pygame.draw.rect(screen, HIGHLIGHT_COLOR, (54, y - 4, 300, 28), 2, border_radius=4)
            draw_icon(screen, game.icon_font, gear, (74, y + 10))
            draw_text(screen, game.font, f"{GEAR[gear].name}  ({GEAR[gear].hand})", (92, y + 2))
            if i in self.picked:
                draw_text(screen, game.font, f"#{self.picked.index(i) + 1}", (300, y + 2), color=HIGHLIGHT_COLOR)

        # The queue as it will be in the bag, and what the Knight already holds.
        right = 520
        draw_text(screen, game.font, "Queue (first handed over first)", (right, 230), color=DIM_COLOR)
        queue = Backpack(self.bag, [self.level.gear_pool[i] for i in self.picked]).queue
        for slot in range(self.bag.slots):
            center = (right + 14 + slot * 30, 276)
            if slot < len(queue):
                draw_icon(screen, game.icon_font, queue[slot], center, size=22)
            else:
                empty = pygame.Rect(0, 0, 22, 22)
                empty.center = center
                pygame.draw.rect(screen, DIM_COLOR, empty, 1)
        draw_text(screen, game.font, "The Knight starts with", (right, 320), color=DIM_COLOR)
        for slot, gear in enumerate(self.level.knight_gear):
            draw_icon(screen, game.icon_font, gear, (right + 14 + slot * 30, 362), size=22)

        draw_text(screen, game.font, "ENTER: start    ESC: back to dungeons",
                  (width // 2, screen.get_height() - 8), "midbottom")
