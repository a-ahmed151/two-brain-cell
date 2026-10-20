import asyncio

import pygame

from game.menus import LoadingScene
from game.scene import Game


async def main():
    pygame.init()
    game = Game()
    await game.run(LoadingScene(game))
    pygame.quit()


asyncio.run(main())
