import asyncio

import pygame

from game.backpack import BAGS, STARTING_BAG, Backpack
from game.entities import Helper, Knight
from game.gear import DroppedGear, draw_icon
from game.level import load_level

FPS = 60
LEVEL_FILE = "levels/01_empty_room.tmj"

FLOOR_COLOR = (45, 42, 50)
WALL_COLOR = (95, 90, 100)
GRID_COLOR = (52, 49, 58)
PATH_COLOR = (200, 170, 60)
EXIT_COLOR = (60, 170, 90)
TEXT_COLOR = (235, 235, 235)
RANGE_COLOR = (120, 220, 255)

# Stand-in for the Pack screen: number keys pick a bag before the run starts.
BAG_KEYS = {pygame.K_1: "satchel", pygame.K_2: "hauler", pygame.K_3: "pouch"}


def draw_level(surface, level):
    ts = level.tile_size
    surface.fill((0, 0, 0))
    for row in range(level.height):
        for col in range(level.width):
            rect = pygame.Rect(col * ts, row * ts, ts, ts)
            if level.walls[row][col]:
                pygame.draw.rect(surface, WALL_COLOR, rect)
            elif level.floor[row][col]:
                pygame.draw.rect(surface, FLOOR_COLOR, rect)
                pygame.draw.rect(surface, GRID_COLOR, rect, 1)

    # The Knight's path, shown so you can plan around it.
    for a, b in zip(level.path, level.path[1:]):
        segment = b - a
        for i in range(0, int(segment.length()), 12):
            pygame.draw.circle(surface, PATH_COLOR, a + segment.normalize() * i, 2)

    exit_rect = pygame.Rect(0, 0, ts - 6, ts - 6)
    exit_rect.center = level.exit_pos
    pygame.draw.rect(surface, EXIT_COLOR, exit_rect, 3)


def draw_text(surface, font, text, pos, anchor="topleft"):
    image = font.render(text, True, TEXT_COLOR)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


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
            pygame.draw.rect(surface, RANGE_COLOR, marker, 2, border_radius=3)


async def main():
    pygame.init()
    level = load_level(LEVEL_FILE)
    screen = pygame.display.set_mode((level.pixel_width, level.pixel_height))
    pygame.display.set_caption("Player 2")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    icon_font = pygame.font.Font(None, 18)

    bag_id = STARTING_BAG

    def reset():
        # Until the Pack screen exists, the bag is filled from the front of the level's gear pool.
        bag = BAGS[bag_id]
        backpack = Backpack(bag, level.gear_pool[:bag.slots])
        return Knight(level.path), Helper(level.helper_start, backpack), []

    knight, helper, dropped = reset()
    running = True
    while running:
        dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    knight.walking = True
                elif event.key == pygame.K_e:
                    fallen = helper.action(knight)
                    if fallen:
                        dropped.append(DroppedGear(fallen, knight.pos))
                elif event.key == pygame.K_r:
                    knight, helper, dropped = reset()
                elif event.key in BAG_KEYS and not knight.walking:
                    bag_id = BAG_KEYS[event.key]
                    knight, helper, dropped = reset()

        helper.update(dt, pygame.key.get_pressed(), level)
        helper.pick_up(dropped)
        knight.update(dt)

        draw_level(screen, level)
        for piece in dropped:
            piece.draw(screen, icon_font)
        if helper.held and helper.in_range(knight):
            pygame.draw.circle(screen, RANGE_COLOR, knight.pos, 20, 2)
        knight.draw(screen, icon_font)
        helper.draw(screen, icon_font)
        draw_text(screen, font, level.name, (8, 6))
        draw_backpack(screen, font, icon_font, helper.backpack, (level.pixel_width - 8, 6))
        if knight.reached_exit:
            draw_text(screen, font, "The Knight has completed the dungeon!  (R to restart)",
                      (level.pixel_width // 2, level.pixel_height - 8), "midbottom")
        elif not knight.walking:
            draw_text(screen, font, "1/2/3: bag    SPACE: GO    WASD: move    E: dig    R: restart",
                      (level.pixel_width // 2, level.pixel_height - 8), "midbottom")
        else:
            draw_text(screen, font, "WASD: move    E: dig out gear (stand still) / give it to the Knight    R: restart",
                      (level.pixel_width // 2, level.pixel_height - 8), "midbottom")
        pygame.display.flip()

        await asyncio.sleep(0)  # required by pygbag for the web build

    pygame.quit()


asyncio.run(main())
