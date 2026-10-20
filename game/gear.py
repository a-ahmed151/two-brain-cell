"""Gear the Knight can hold, and gear lying on the floor. See "Gear" in GAME_DESIGN.md."""

from dataclasses import dataclass

import pygame

TOOL = "tool"  # reusable; stays in the Knight's tool hand until replaced
ITEM = "item"  # consumed on use; goes in his item hand

ICON_SIZE = 18


@dataclass(frozen=True)
class GearType:
    name: str
    hand: str  # TOOL or ITEM
    color: tuple


# Gear is referred to everywhere by these ids (also used in the maps' gear_pool).
GEAR = {
    "sword": GearType("Sword", TOOL, (200, 205, 215)),
    "pickaxe": GearType("Pickaxe", TOOL, (150, 110, 70)),
    "torch": GearType("Torch", TOOL, (240, 160, 40)),
    "shield": GearType("Shield", TOOL, (70, 110, 190)),
    "key": GearType("Key", ITEM, (230, 200, 60)),
    "plank": GearType("Plank", ITEM, (170, 120, 60)),
    "bomb": GearType("Bomb", ITEM, (75, 75, 85)),
    "potion": GearType("Potion", ITEM, (210, 60, 90)),
}


def draw_icon(surface, font, gear, center, size=ICON_SIZE):
    """Placeholder: a colored square with the gear's first letter. Tools are square, items rounded."""
    gear_type = GEAR[gear]
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    radius = size // 2 if gear_type.hand == ITEM else 2
    pygame.draw.rect(surface, gear_type.color, rect, border_radius=radius)
    pygame.draw.rect(surface, (20, 20, 25), rect, 1, border_radius=radius)
    letter = font.render(gear_type.name[0], True, (20, 20, 25))
    surface.blit(letter, letter.get_rect(center=rect.center))


class DroppedGear:
    """Gear the Knight dropped. The Helper walks over it to put it back in the bag."""

    def __init__(self, gear, pos):
        self.gear = gear
        self.rect = pygame.Rect(0, 0, ICON_SIZE, ICON_SIZE)
        self.rect.center = pos
        # Not collectable until the Helper has stepped off it, so gear dropped
        # right next to them doesn't jump straight back into the bag.
        self.armed = False

    def draw(self, surface, font):
        draw_icon(surface, font, self.gear, self.rect.center)
