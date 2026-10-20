"""The scene manager. Each screen (loading, intro, level select, item select, play)
is a Scene; Game runs whichever one is active and holds what lives across them."""

import asyncio

import pygame

from game.backpack import STARTING_BAG

FPS = 60
SCREEN_SIZE = (960, 720)  # 20x15 tiles of 16 px, scaled up 3x
TEXT_COLOR = (235, 235, 235)
DIM_COLOR = (130, 125, 140)
HIGHLIGHT_COLOR = (120, 220, 255)
BACKGROUND_COLOR = (25, 22, 30)


def draw_text(surface, font, text, pos, anchor="topleft", color=TEXT_COLOR):
    image = font.render(text, True, color)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


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
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Player 2")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 40)
        self.title_font = pygame.font.Font(None, 96)
        self.icon_font = pygame.font.Font(None, 18)
        self.scene = None
        self.running = True

        # Filled in by the loading scene.
        self.levels = []  # in play order
        self.tiles = {}  # tileset image path -> {gid: tile surface}

        # Progress for this session.
        self.completed = set()  # indices into self.levels
        self.unlocked_bags = [STARTING_BAG]

    def level_available(self, index):
        return index == 0 or index - 1 in self.completed

    def change_scene(self, scene):
        self.scene = scene

    def quit(self):
        self.running = False

    async def run(self, first_scene):
        self.scene = first_scene
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                else:
                    self.scene.handle_event(event)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()

            await asyncio.sleep(0)  # required by pygbag for the web build
