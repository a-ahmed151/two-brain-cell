"""The scene manager. Each screen (loading, intro, run start, rewards, combat)
is a Scene; Game runs whichever one is active and holds what lives across them."""

import asyncio

import pygame

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
        self.levels = []  # the arena rooms; each room of a run uses one of them
        self.tiles = {}  # tileset image path -> {gid: tile surface}

        self.current_run = None  # the RunState in progress (game/run.py)

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
