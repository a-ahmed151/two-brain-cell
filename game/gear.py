"""Gear the Knight can hold, and the buffs it gives him. See "Gear" in GAME_DESIGN.md."""

from dataclasses import dataclass, field
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
    blurb: str = ""  # one line for the reward screen
    # Tools: what he hits for while holding it, and how it changes vs enemy tags.
    damage: int = 0
    bonus: dict = field(default_factory=dict)  # enemy tag -> damage multiplier
    guard: float = 1.0  # multiplier on damage he takes while holding it
    fire: bool = False  # its hits burn: a burned vampire can't heal any more
    helper_only: bool = False  # the Helper uses it; it can't go in the Knight's hands


FIST_DAMAGE = 1  # empty tool hand

# Gear is referred to everywhere by these ids. Items sit in his item hand until he
# uses them by himself (see Knight.use_item in game/entities.py), except the Key,
# which the Helper uses on the chest (Helper.action).
GEAR = {
    "sword": GearType("Sword", TOOL, (200, 205, 215), "Good hits. Weak vs armor.", damage=3,
                      bonus={"armored": 0.67}),
    "pickaxe": GearType("Pickaxe", TOOL, (150, 110, 70), "Cracks armor. Clumsy.", damage=1,
                        bonus={"armored": 5}),
    "torch": GearType("Torch", TOOL, (240, 160, 40), "Burns undead. Stops healing.", damage=1,
                      bonus={"burns": 4, "vampire": 2}, fire=True),
    "shield": GearType("Shield", TOOL, (70, 110, 190), "Halves damage taken.", damage=1, guard=0.5),
    "key": GearType("Key", ITEM, (230, 200, 60), "You open the room's chest.", helper_only=True),
    "bomb": GearType("Bomb", ITEM, (75, 75, 85), "Blasts enemies near him."),
    "potion": GearType("Potion", ITEM, (210, 60, 90), "Drunk when he's hurt."),
    "poison": GearType("Poison", ITEM, (120, 200, 70), "Not a health potion."),  # the betrayal
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

