"""The gameplay scene: the Knight walks his path while the Helper digs and hands over gear."""

import pygame

from game.backpack import BAGS, Backpack
from game.entities import Helper, Knight
from game.gear import draw_icon
from game.scene import HIGHLIGHT_COLOR, Scene, draw_text

SCALE = 3  # the world is drawn at native pixel-art size, then scaled up for the window

GRID_COLOR = (52, 49, 58)
PATH_COLOR = (200, 170, 60)
EXIT_COLOR = (60, 170, 90)


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


def draw_backpack(surface, font, icon_font, backpack, topright):
    """HUD: bag name and fill, then the queue from front (next hand-off) to back."""
    bag = backpack.bag
    label = draw_text(surface, font, f"{bag.name} {len(backpack.queue)}/{bag.slots}  ({bag.extract_time}s)",
                      topright, "topright")
    x = label.right - 11
    for i in reversed(range(bag.slots)):
        center = (x - (bag.slots - 1 - i) * 24, label.bottom + 14)
        if i < len(backpack.queue):
            draw_icon(surface, icon_font, backpack.queue[i], center)
        else:
            empty = pygame.Rect(0, 0, 18, 18)
            empty.center = center
            pygame.draw.rect(surface, GRID_COLOR, empty, 1)
        if i == 0:
            marker = pygame.Rect(0, 0, 24, 24)
            marker.center = center
            pygame.draw.rect(surface, HIGHLIGHT_COLOR, marker, 2, border_radius=3)


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

        gear = [self.level.gear_pool[i] for i in picked]
        self.knight = Knight(self.level.path, self.level.knight_gear)
        self.helper = Helper(self.level.helper_start, Backpack(BAGS[bag_id], gear))
        self.won = False

    def back_to_item_select(self):
        from game.menus import ItemSelectScene  # menus imports this module too
        self.game.change_scene(ItemSelectScene(self.game, self.level_index, self.bag_id, self.picked))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.won:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.next_level()
        elif event.key == pygame.K_ESCAPE:
            self.back_to_item_select()
        elif event.key == pygame.K_r:
            self.game.change_scene(PlayScene(self.game, self.level_index, self.bag_id, self.picked))
        elif event.key == pygame.K_SPACE:
            self.knight.walking = True
        elif event.key == pygame.K_e:
            self.helper.action(self.knight)

    def next_level(self):
        from game.menus import ItemSelectScene, LevelSelectScene
        if self.level_index + 1 < len(self.game.levels):
            self.game.change_scene(ItemSelectScene(self.game, self.level_index + 1))
        else:
            self.game.change_scene(LevelSelectScene(self.game, self.level_index))

    def update(self, dt):
        if self.won:
            return
        self.helper.update(dt, pygame.key.get_pressed(), self.level)
        self.knight.update(dt)
        if self.knight.reached_exit:
            self.won = True
            self.game.completed.add(self.level_index)

    def draw(self, screen):
        game, knight, helper = self.game, self.knight, self.helper
        draw_level(self.world, self.level, self.tiles)
        if helper.held and helper.in_range(knight):
            pygame.draw.circle(self.world, HIGHLIGHT_COLOR, knight.pos, 10, 1)
        knight.draw(self.world, self.world_icon_font)
        helper.draw(self.world, self.world_icon_font)
        pygame.transform.scale(self.world, (self.level.pixel_width * SCALE, self.level.pixel_height * SCALE), screen)

        # The HUD is drawn at window resolution so text stays sharp.
        draw_text(screen, game.font, self.level.name, (8, 6))
        draw_backpack(screen, game.font, game.icon_font, helper.backpack, (screen.get_width() - 8, 6))
        bottom = (screen.get_width() // 2, screen.get_height() - 8)
        if self.won:
            draw_text(screen, game.font, "The Knight has completed the dungeon!  (ENTER: continue)", bottom, "midbottom")
        elif not knight.walking:
            draw_text(screen, game.font, "SPACE: GO    WASD: move    E: dig    R: restart    ESC: back to packing",
                      bottom, "midbottom")
        else:
            draw_text(screen, game.font, "WASD: move    E: dig out gear (stand still) / give it to the Knight    R: restart",
                      bottom, "midbottom")
