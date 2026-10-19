import asyncio

import pygame

from game.entities import Helper, Knight
from game.level import load_level

FPS = 60
LEVEL_FILE = "levels/01_empty_room.tmj"

FLOOR_COLOR = (45, 42, 50)
WALL_COLOR = (95, 90, 100)
GRID_COLOR = (52, 49, 58)
PATH_COLOR = (200, 170, 60)
EXIT_COLOR = (60, 170, 90)
TEXT_COLOR = (235, 235, 235)


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


async def main():
    pygame.init()
    level = load_level(LEVEL_FILE)
    screen = pygame.display.set_mode((level.pixel_width, level.pixel_height))
    pygame.display.set_caption("Player 2")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    def reset():
        return Knight(level.path), Helper(level.helper_start)

    knight, helper = reset()
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
                elif event.key == pygame.K_r:
                    knight, helper = reset()

        helper.update(dt, pygame.key.get_pressed(), level)
        knight.update(dt)

        draw_level(screen, level)
        knight.draw(screen)
        helper.draw(screen)
        draw_text(screen, font, level.name, (8, 6))
        if knight.reached_exit:
            draw_text(screen, font, "The Knight has completed the dungeon!  (R to restart)",
                      (level.pixel_width // 2, level.pixel_height - 8), "midbottom")
        elif not knight.walking:
            draw_text(screen, font, "SPACE: GO    WASD: move    R: restart",
                      (level.pixel_width // 2, level.pixel_height - 8), "midbottom")
        pygame.display.flip()

        await asyncio.sleep(0)  # required by pygbag for the web build

    pygame.quit()


asyncio.run(main())
