"""The gameplay scene: the Knight walks his path while the Helper digs and hands over gear."""

import pygame

from game import ui
from game.backpack import BAGS, Backpack
from game.entities import Helper, Knight
from game.gear import draw_icon
from game.scene import Scene

WORLD_SCALE = 3  # the world is drawn at native pixel-art size, then scaled up; 320x240 -> 960x720
HUD_SIZE = (80, 180)  # side panel on the UI canvas scale (4x), right of the world

PATH_COLOR = (200, 170, 60)
EXIT_COLOR = (60, 170, 90)
HIGHLIGHT_COLOR = (120, 220, 255)
GOLD = (232, 177, 58)
SLOT_COLOR = (107, 78, 99)
DIM = 130
BETRAYAL_DELAY = 2.5  # seconds of the Knight lying there before the ending
ICON_FONT = ui.IconFont()


def draw_level(surface, level, tiles):
    ts = level.tile_size
    surface.fill((0, 0, 0))
    for layer in (level.floor, level.wall_tiles):
        for row in range(level.height):
            for col in range(level.width):
                gid = layer[row][col]
                if gid:
                    surface.blit(tiles[gid], (col * ts, row * ts))

    # The Knight's path, shown so you can plan around it.
    for a, b in zip(level.path, level.path[1:]):
        segment = b - a
        for i in range(0, int(segment.length()), 6):
            pygame.draw.circle(surface, PATH_COLOR, a + segment.normalize() * i, 1)

    exit_rect = pygame.Rect(0, 0, ts - 3, ts - 3)
    exit_rect.center = level.exit_pos
    pygame.draw.rect(surface, EXIT_COLOR, exit_rect, 2)


def draw_slot(surface, gear, center, size=12, marked=False):
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if gear:
        draw_icon(surface, ICON_FONT, gear, center, size=size)
    else:
        pygame.draw.rect(surface, SLOT_COLOR, rect, 1)
    if marked:
        pygame.draw.rect(surface, GOLD, rect.inflate(4, 4), 1)


class PlayScene(Scene):
    """One run of a level with the bag and gear chosen on the item select screen."""

    def __init__(self, game, level_index, bag_id, picked):
        super().__init__(game)
        self.level_index = level_index
        self.level = game.levels[level_index]
        self.tiles = game.tiles[self.level.tileset["image"]]
        self.bag_id = bag_id
        self.picked = picked  # indices into the level's gear pool, in queue order
        self.world = pygame.Surface((self.level.pixel_width, self.level.pixel_height))
        self.world_icon_font = pygame.font.Font(None, 10)
        self.hud = pygame.Surface(HUD_SIZE)
        world_w = self.level.pixel_width * WORLD_SCALE
        # The win banner is drawn on a UI-scale overlay covering the world.
        self.overlay = pygame.Surface((world_w // ui.UI_SCALE, game.screen.get_height() // ui.UI_SCALE),
                                      pygame.SRCALPHA)

        gear = [self.level.gear_pool[i] for i in picked]
        self.knight = Knight(self.level.path, self.level.knight_gear)
        self.helper = Helper(self.level.helper_start, Backpack(BAGS[bag_id], gear))
        # None while playing; otherwise "won" or "lost", shown as a banner: (title, lines).
        self.outcome = None
        self.banner = ("", [])
        self.death_time = 0.0

    def back_to_item_select(self):
        from game.menus import ItemSelectScene  # menus imports this module too
        self.game.change_scene(ItemSelectScene(self.game, self.level_index, self.bag_id, self.picked))

    def handle_event(self, event):
        confirm = (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)) or \
            (event.type == pygame.MOUSEBUTTONUP and event.button == 1)
        if self.outcome == "won":
            if confirm:
                self.next_level()
            return
        if self.outcome == "lost" and confirm:
            self.restart()
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.back_to_item_select()
        elif event.key == pygame.K_r:
            self.restart()
        elif self.outcome or self.knight.dead:
            return
        elif event.key == pygame.K_SPACE:
            self.knight.walking = True
        elif event.key == pygame.K_e:
            self.helper.action(self.knight)

    def restart(self):
        self.game.change_scene(PlayScene(self.game, self.level_index, self.bag_id, self.picked))

    def next_level(self):
        from game.menus import ItemSelectScene, LevelSelectScene
        if self.level_index + 1 < len(self.game.levels):
            self.game.change_scene(ItemSelectScene(self.game, self.level_index + 1))
        else:
            self.game.change_scene(LevelSelectScene(self.game, self.level_index))

    def update(self, dt):
        knight = self.knight
        if self.outcome:
            knight.update(dt)  # keeps his victory/death animation going
            return
        self.helper.update(dt, pygame.key.get_pressed(), self.level)
        knight.update(dt)
        if knight.dead:
            self.death_time += dt
            if self.death_time < BETRAYAL_DELAY:
                return
            if self.level.betrayal:
                from game.menus import EndingScene
                self.game.completed.add(self.level_index)
                self.game.change_scene(EndingScene(self.game))
            else:
                self.end("lost", "He's dead.", "That wasn't a health potion.", "ENTER: retry")
        elif knight.reached_exit:
            if self.level.betrayal:
                self.end("lost", "Too late!", "He took the credit again.", "ENTER: retry")
            else:
                self.game.completed.add(self.level_index)
                self.end("won", "Level clear!", "ENTER: continue")

    def end(self, outcome, title, *lines):
        self.outcome = outcome
        self.banner = (title, lines)

    def draw(self, screen):
        knight, helper = self.knight, self.helper
        draw_level(self.world, self.level, self.tiles)
        if helper.held and helper.in_range(knight):
            pygame.draw.circle(self.world, HIGHLIGHT_COLOR, knight.pos, 10, 1)
        # Draw whoever's feet are lower on screen last, so they overlap correctly.
        feet = {knight: knight.pos.y + 7, helper: helper.rect.bottom + 1}
        for actor in sorted(feet, key=feet.get):
            actor.draw(self.world, self.world_icon_font)
        world_size = (self.level.pixel_width * WORLD_SCALE, self.level.pixel_height * WORLD_SCALE)
        screen.blit(pygame.transform.scale(self.world, world_size), (0, 0))

        self.draw_hud(self.hud)
        hud_x = world_size[0]
        screen.blit(pygame.transform.scale(self.hud, (screen.get_width() - hud_x, screen.get_height())), (hud_x, 0))

        if self.outcome:
            self.overlay.fill((0, 0, 0, 0))
            self.draw_banner(self.overlay)
            screen.blit(pygame.transform.scale_by(self.overlay, ui.UI_SCALE), (0, 0))

    def draw_hud(self, hud):
        knight, helper = self.knight, self.helper
        backpack = helper.backpack
        w = hud.get_width()
        ui.nine_slice(hud, "panel9", hud.get_rect())
        ui.draw_text(hud, self.level.name[:12], (w // 2, 8), "gold", anchor="midtop")

        ui.draw_text(hud, "Knight", (w // 2, 22), anchor="midtop", alpha=DIM)
        draw_slot(hud, knight.tool, (w // 2 - 9, 39))
        draw_slot(hud, knight.item, (w // 2 + 9, 39))

        ui.draw_text(hud, "Helper", (w // 2, 52), anchor="midtop", alpha=DIM)
        draw_slot(hud, helper.held, (w // 2, 69))
        if helper.digging:
            progress = 1 - helper.dig_left / backpack.bag.extract_time
            bar = pygame.Rect(w // 2 - 15, 78, 30, 3)
            pygame.draw.rect(hud, SLOT_COLOR, bar)
            pygame.draw.rect(hud, GOLD, (bar.x, bar.y, round(bar.w * progress), bar.h))

        bag = backpack.bag
        ui.draw_text(hud, bag.name, (w // 2, 86), "gold", anchor="midtop")
        ui.draw_text(hud, f"{len(backpack.queue)}/{bag.slots}  {bag.extract_time}s", (w // 2, 95), anchor="midtop")
        for slot in range(bag.slots):
            col, row = slot % 3, slot // 3
            gear = backpack.queue[slot] if slot < len(backpack.queue) else None
            draw_slot(hud, gear, (w // 2 - 18 + col * 18, 114 + row * 18), marked=slot == 0 and gear is not None)

        hints = ["E dig/give", "R restart", "ESC pack"]
        if not knight.walking and not knight.dead and not self.outcome:
            ui.draw_text(hud, "SPACE go!", (w // 2, 140), "gold", anchor="midtop")
        for i, hint in enumerate(hints):
            ui.draw_text(hud, hint, (w // 2, 150 + i * 9), anchor="midtop", alpha=DIM)

    def draw_banner(self, overlay):
        title, lines = self.banner
        rect = pygame.Rect(0, 0, 172, 40 + 10 * len(lines))
        rect.center = overlay.get_rect().center
        ui.nine_slice(overlay, "panel9", rect)
        ui.draw_text(overlay, title, (rect.centerx, rect.y + 12), "gold", scale=2, anchor="midtop")
        for i, line in enumerate(lines):
            ui.draw_text(overlay, line, (rect.centerx, rect.y + 32 + i * 10), anchor="midtop")
