"""Gear the Knight can hold. See "Gear" in GAME_DESIGN.md."""

from dataclasses import dataclass
from functools import cache

import pygame

TOOL = "tool"  # reusable; stays in the Knight's tool hand until replaced
ITEM = "item"  # consumed on use; goes in his item hand

ICON_SIZE = 18
ICON_SHEET = "assets/gear_icons.png"  # one row of 16x16 icons, built by tools/make_knight_sheet.py
ICON_SHEET_ORDER = ["sword", "pickaxe", "torch", "shield", "key", "bomb", "potion"]
ICON_SHEET_SIZE = 16


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
    "poison": GearType("Poison", ITEM, (120, 200, 70)),  # the betrayal: he drinks it on the spot
}


@cache
def _icon(gear, size):
    """The gear's icon scaled to `size`, or None if the sheet has no art for it. Loaded on
    first use (needs the display to exist)."""
    if gear not in ICON_SHEET_ORDER:
        return None
    sheet = _icon_sheet()
    n = ICON_SHEET_ORDER.index(gear)
    icon = sheet.subsurface((n * ICON_SHEET_SIZE, 0, ICON_SHEET_SIZE, ICON_SHEET_SIZE))
    return pygame.transform.scale(icon, (size, size))


@cache
def _icon_sheet():
    return pygame.image.load(ICON_SHEET).convert_alpha()


def draw_icon(surface, font, gear, center, size=ICON_SIZE):
    """The gear's icon from the icon sheet. Gear without art (Plank, Poison) falls back to
    a colored square with its first letter; tools are square, items rounded."""
    icon = _icon(gear, size)
    if icon:
        surface.blit(icon, icon.get_rect(center=center))
        return
    gear_type = GEAR[gear]
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    radius = size // 2 if gear_type.hand == ITEM else 2
    pygame.draw.rect(surface, gear_type.color, rect, border_radius=radius)
    pygame.draw.rect(surface, (20, 20, 25), rect, 1, border_radius=radius)
    letter = font.render(gear_type.name[0], True, (20, 20, 25))
    surface.blit(letter, letter.get_rect(center=rect.center))

