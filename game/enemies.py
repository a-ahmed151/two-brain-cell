"""Monsters in the arena rooms. They chase their prey and hit it on a cooldown.
See "Enemies" in GAME_DESIGN.md."""

from dataclasses import dataclass
from functools import cache

import pygame

from game import ui
from game.gear import draw_icon

MONSTERS = "assets/Character_animation/monsters_idle/{folder}/v2/{prefix}_v2_{i}.png"
FPS = 6
HIT_FLASH = 0.12  # seconds an enemy flashes white after a hit
ATTACK_RANGE = 13  # centre to centre, in pixels
# Any enemy turns on the Helper who comes this close (centre to centre)...
AGGRO_RANGE = 24
# ...and keeps after him until he gets this far away. He's faster than all of them: running is the only way out.
GIVE_UP_RANGE = 56
ALERT_TIME = 0.7  # how long the "!" (spotted) or "?" (lost him) shows over its head
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
    lifesteal: bool = False  # heals by a third of the damage it deals (at least 1)
    scale: int = 1
    tint: tuple | None = None
    summons: str | None = None  # boss: calls one of these every SUMMON_TIME
    counter: str = "sword"  # the gear that beats it, shown when the room is announced
    only: str | None = None  # Trial monsters: nothing but this gear hurts them at all


SUMMON_TIME = 7.0

ENEMIES = {
    "skeleton": EnemyType("Skeleton", "skeleton1", "skeleton", hp=6, speed=22, damage=2, cooldown=1.0),
    "armored": EnemyType("Armored", "skeleton2", "skeleton2", hp=15, speed=16, damage=3, cooldown=1.3,
                         tags=("armored",), tint=(150, 175, 230), counter="pickaxe"),
    "skull": EnemyType("Skull", "skull", "skull", hp=4, speed=34, damage=1, cooldown=1.3, tags=("burns",),
                       hunts="helper", counter="torch"),
    "vampire": EnemyType("Vampire", "vampire", "vampire", hp=12, speed=24, damage=3, cooldown=1.1,
                         tags=("burns", "vampire"), lifesteal=True, counter="torch"),
    "count": EnemyType("The Count", "vampire", "vampire", hp=50, speed=18, damage=4, cooldown=1.5,
                       tags=("burns", "vampire"), lifesteal=True, scale=2, tint=(255, 150, 150), summons="skull",
                       counter="torch"),
    # The Trial's monsters (game/trial.py). Each is a riddle: only one piece of gear hurts it.
    "warden": EnemyType("Iron Warden", "skeleton2", "skeleton2", hp=10, speed=14, damage=2, cooldown=1.5,
                        tags=("armored",), tint=(240, 200, 90), only="pickaxe", counter="pickaxe"),
    "shade": EnemyType("Shade", "vampire", "vampire", hp=4, speed=26, damage=2, cooldown=1.3, tags=("burns",),
                       tint=(105, 115, 230), only="torch", counter="torch"),
    "wisp": EnemyType("Wisp", "skull", "skull", hp=3, speed=36, damage=1, cooldown=1.2, tags=("burns",),
                      hunts="helper", tint=(120, 235, 255), only="torch", counter="torch"),
    "gargoyle": EnemyType("Gargoyle", "skeleton1", "skeleton", hp=8, speed=9, damage=4, cooldown=1.6,
                          tint=(150, 150, 160), only="bomb", counter="bomb"),
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


@cache
def enemy_icon(kind):
    """A 16 px tall picture of the enemy for menus and room announcements."""
    image = enemy_frames(kind)[0][0][0]
    return pygame.transform.scale_by(image, 16 / image.get_height())


def draw_lineup(surface, kinds, center):
    """The enemies in a room as a row of pictures on the UI canvas: each kind once, with
    how many there are and the gear that beats it. Returns the row's rect."""
    counts = {}
    for kind in kinds:
        counts[kind] = counts.get(kind, 0) + 1
    cell = 44
    rect = pygame.Rect(0, 0, cell * len(counts), 18)
    rect.center = center
    for i, (kind, count) in enumerate(counts.items()):
        x = rect.x + i * cell
        icon = enemy_icon(kind)
        surface.blit(icon, icon.get_rect(midleft=(x + 2, rect.centery)))
        ui.draw_text(surface, f"x{count}", (x + 20, rect.y))
        draw_icon(surface, ui.IconFont(), ENEMIES[kind].counter, (x + 25, rect.bottom - 3), size=9)
    return rect


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
        self.burned = False  # hit by fire: no more lifesteal
        self.after_helper = False  # a Knight-hunter that got distracted by the Helper
        self.alert = ""  # "!" or "?", shown over its head
        self.alert_left = 0.0

    @property
    def dead(self):
        return self.hp <= 0

    @property
    def reach(self):
        return ATTACK_RANGE * self.type.scale

    def hurt(self, amount, fire=False, gear=None):
        """Take a hit from `gear` (None: bare fists). Returns the damage actually dealt:
        0 if this is a Trial monster and that isn't the one gear that hurts it."""
        self.flash = HIT_FLASH
        if self.type.only and gear != self.type.only:
            return 0
        self.hp -= amount
        if fire:
            self.burned = True
        return amount

    def update(self, dt, knight, helper, level, others):
        """Chase the prey and hit it when close. Returns a new enemy kind to summon, or None."""
        self.time += dt
        self.flash = max(0.0, self.flash - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.alert_left = max(0.0, self.alert_left - dt)
        self.notice(helper, knight)
        prey = helper if (self.type.hunts == "helper" or self.after_helper) and helper.alive else knight
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
            if self.type.lifesteal and dealt and not self.burned:
                self.hp = min(self.max_hp, self.hp + max(1, dealt // 3))
        if self.type.summons:
            self.summon_left -= dt
            if self.summon_left <= 0:
                self.summon_left = SUMMON_TIME
                return self.type.summons
        return None

    def notice(self, helper, knight):
        """Knight-hunters turn on a Helper who wanders too close, and lose him once he runs."""
        if self.type.hunts == "helper":
            return
        if not helper.alive or knight.dead:
            self.after_helper = False
            return
        distance = self.pos.distance_to(helper.rect.center)
        if not self.after_helper and distance <= AGGRO_RANGE + self.reach - ATTACK_RANGE:
            self.after_helper = True
            self.alert, self.alert_left = "!", ALERT_TIME
        elif self.after_helper and distance > GIVE_UP_RANGE:
            self.after_helper = False
            self.alert, self.alert_left = "?", ALERT_TIME

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
        if self.alert_left:
            mark = ui.render_text(self.alert, "gold")
            surface.blit(mark, mark.get_rect(midbottom=(rect.centerx, rect.top - 3)))
        if self.burned and self.type.lifesteal:
            # A little flame by its health bar: it can't heal any more.
            draw_icon(surface, ui.IconFont(), "torch", (rect.right, rect.top + 1), size=7)
