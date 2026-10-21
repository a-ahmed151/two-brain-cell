"""Monsters in the arena rooms. They chase their prey and hit it on a cooldown.
See "Enemies" in GAME_DESIGN.md."""

from dataclasses import dataclass
from functools import cache

import pygame

MONSTERS = "assets/Character_animation/monsters_idle/{folder}/v2/{prefix}_v2_{i}.png"
FPS = 6
HIT_FLASH = 0.12  # seconds an enemy flashes white after a hit
ATTACK_RANGE = 13  # centre to centre, in pixels
SIZE = 8  # collision box


@dataclass(frozen=True)
class EnemyType:
    name: str
    folder: str
    prefix: str
    hp: int
    speed: float  # pixels per second
    damage: int
    cooldown: float  # seconds between hits
    tags: tuple = ()  # matched against GearType.bonus
    hunts: str = "knight"  # or "helper"
    lifesteal: bool = False  # heals by half the damage it deals
    scale: int = 1
    tint: tuple | None = None
    summons: str | None = None  # boss: calls one of these every SUMMON_TIME


SUMMON_TIME = 7.0

ENEMIES = {
    "skeleton": EnemyType("Skeleton", "skeleton1", "skeleton", hp=6, speed=22, damage=2, cooldown=1.0),
    "armored": EnemyType("Armored", "skeleton2", "skeleton2", hp=15, speed=16, damage=3, cooldown=1.3,
                         tags=("armored",), tint=(150, 175, 230)),
    "skull": EnemyType("Skull", "skull", "skull", hp=4, speed=34, damage=1, cooldown=1.3, tags=("burns",),
                       hunts="helper"),
    "vampire": EnemyType("Vampire", "vampire", "vampire", hp=12, speed=24, damage=3, cooldown=1.1,
                         tags=("burns",), lifesteal=True),
    "count": EnemyType("The Count", "vampire", "vampire", hp=50, speed=18, damage=4, cooldown=1.5,
                       tags=("burns",), lifesteal=True, scale=2, tint=(255, 150, 150), summons="skull"),
}


@cache
def enemy_frames(kind):
    """Right-facing and left-facing idle frames, scaled and tinted. Needs the display to exist."""
    t = ENEMIES[kind]
    right = []
    for i in range(1, 5):
        image = pygame.image.load(MONSTERS.format(folder=t.folder, prefix=t.prefix, i=i)).convert_alpha()
        if t.scale != 1:
            image = pygame.transform.scale_by(image, t.scale)
        if t.tint:
            image.fill((*t.tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
        right.append(image)
    left = [pygame.transform.flip(image, True, False) for image in right]
    white = [_flash(image) for image in right], [_flash(image) for image in left]
    return (right, left), white


def _flash(image):
    mask = pygame.mask.from_surface(image)
    return mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))


def move_body(pos, step, size, level):
    """Move a square body centred on `pos` by `step`, one axis at a time so it slides
    along walls. Returns the new position."""
    pos = pygame.Vector2(pos)
    for axis in (0, 1):
        moved = pygame.Vector2(pos)
        moved[axis] += step[axis]
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (round(moved.x), round(moved.y))
        if not level.rect_hits_wall(rect):
            pos = moved
    return pos


class Enemy:
    def __init__(self, kind, pos):
        self.kind = kind
        self.type = ENEMIES[kind]
        self.pos = pygame.Vector2(pos)
        self.hp = self.max_hp = self.type.hp
        self.cooldown = self.type.cooldown * 0.6  # a beat before the first swing
        self.flash = 0.0
        self.time = 0.0
        self.facing_left = False
        self.summon_left = SUMMON_TIME

    @property
    def dead(self):
        return self.hp <= 0

    @property
    def reach(self):
        return ATTACK_RANGE * self.type.scale

    def hurt(self, amount):
        self.hp -= amount
        self.flash = HIT_FLASH

    def update(self, dt, knight, helper, level, others):
        """Chase the prey and hit it when close. Returns a new enemy kind to summon, or None."""
        self.time += dt
        self.flash = max(0.0, self.flash - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        prey = helper if self.type.hunts == "helper" and helper.alive else knight
        target = pygame.Vector2(prey.rect.center) if prey is helper else knight.pos
        to_prey = target - self.pos
        distance = to_prey.length()
        if distance > 0.5:
            self.facing_left = to_prey.x < 0
        if distance > self.reach * 0.8:
            heading = level.route(self.pos, target, SIZE * self.type.scale) - self.pos
            if heading.length_squared() == 0:
                heading = to_prey
            step = heading.normalize() * self.type.speed * dt
            # Don't stack on top of each other.
            for other in others:
                if other is not self and not other.dead:
                    away = self.pos - other.pos
                    if 0 < away.length() < 10:
                        step += away.normalize() * 12 * dt
            self.pos = move_body(self.pos, step, SIZE * self.type.scale, level)
        if distance <= self.reach and self.cooldown == 0:
            self.cooldown = self.type.cooldown
            dealt = prey.hurt(self.type.damage)
            if self.type.lifesteal and dealt:
                self.hp = min(self.max_hp, self.hp + (dealt + 1) // 2)
        if self.type.summons:
            self.summon_left -= dt
            if self.summon_left <= 0:
                self.summon_left = SUMMON_TIME
                return self.type.summons
        return None

    @property
    def feet(self):
        return self.pos.y + 7 * self.type.scale

    def draw(self, surface):
        (right, left), (white_right, white_left) = enemy_frames(self.kind)
        frames = (white_left if self.facing_left else white_right) if self.flash else \
            (left if self.facing_left else right)
        image = frames[int(self.time * FPS) % len(frames)]
        rect = image.get_rect(midbottom=(self.pos.x, self.feet + 1))
        surface.blit(image, rect)
        if self.hp < self.max_hp:
            bar = pygame.Rect(0, 0, 10 * self.type.scale, 2)
            bar.midbottom = (rect.centerx, rect.top - 1)
            pygame.draw.rect(surface, (40, 20, 30), bar)
            pygame.draw.rect(surface, (210, 60, 70), (bar.x, bar.y, round(bar.w * self.hp / self.max_hp), 2))
