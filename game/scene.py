"""The scene manager. Each screen (loading, intro, level select, item select, play)
is a Scene; Game runs whichever one is active and holds what lives across them."""

import asyncio

import pygame

from game.backpack import STARTING_BAG

FPS = 60
SCREEN_SIZE = (1280, 720)  # the UI kit's 320x180 canvas at 4x


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

    def next_level(self):
        """The first level not completed yet (or the last one, once all are done)."""
        for i in range(len(self.levels)):
            if i not in self.completed:
                return i
        return len(self.levels) - 1

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
