import json
import math
from functools import cache

import pygame

from game.gear import GEAR, TOOL, draw_icon

KNIGHT_SPEED = 30  # pixels per second
HELPER_SPEED = 65
HELPER_SIZE = 9  # collision box, in pixels
HANDOFF_RANGE = 32  # max distance between Helper and Knight centers for a hand-off

HELPER_SHEET = "assets/helper_full_gear.png"  # 4x4 grid of 24x24 frames; rows face down, up, left, right
HELPER_FRAME = 24
HELPER_ANIM_FPS = 8
_helper_frames = None


def helper_frames():
    """Frames as [direction][frame], loaded on first use (needs the display to exist)."""
    global _helper_frames
    if _helper_frames is None:
        sheet = pygame.image.load(HELPER_SHEET).convert_alpha()
        size = HELPER_FRAME
        _helper_frames = [[sheet.subsurface((col * size, row * size, size, size)) for col in range(4)]
                          for row in range(4)]
    return _helper_frames


KNIGHT_SHEET = "assets/knight/chibi_knight.json"  # one row per animation; cols 0-6 face right, 7-13 face left
KNIGHT_FACING_LEFT_COL = 7


@cache
def knight_animations():
    """{name: (right frames, left frames, fps, loop)}, loaded on first use (needs the display to exist)."""
    with open(KNIGHT_SHEET) as f:
        data = json.load(f)
    sheet = pygame.image.load(f"assets/knight/{data['image']}").convert_alpha()
    w, h = data["frameWidth"], data["frameHeight"]
    animations = {}
    for name, anim in data["animations"].items():
        y = anim["row"] * h
        right = [sheet.subsurface((col * w, y, w, h)) for col in range(anim["frames"])]
        left = [sheet.subsurface(((KNIGHT_FACING_LEFT_COL + col) * w, y, w, h)) for col in range(anim["frames"])]
        animations[name] = (right, left, anim["fps"], anim["loop"])
    return animations


def knight_frame(name, time, facing_left=False):
    """The frame of a knight animation `time` seconds after it started."""
    right, left, fps, loop = knight_animations()[name]
    index = int(time * fps)
    index = index % len(right) if loop else min(index, len(right) - 1)
    return (left if facing_left else right)[index]


class Knight:
    """Walks the level's path from start to end. Drawn from the chibi knight sprite sheet."""

    def __init__(self, path, gear=()):
        self.path = path
        self.pos = pygame.Vector2(path[0])
        self.next_point = 1
        self.walking = False
        self.reached_exit = False
        self.tool = None  # reusable gear, kept until replaced
        self.item = None  # one-use gear
        self.facing = (path[1] - path[0]).normalize()
        self.animation = None
        self.anim_time = 0.0
        for piece in gear:
            self.receive(piece)

    def receive(self, gear):
        """Put gear in the matching hand. Returns what was in that hand before."""
        if GEAR[gear].hand == TOOL:
            old, self.tool = self.tool, gear
        else:
            old, self.item = self.item, gear
        return old

    def update(self, dt):
        self.anim_time += dt
        if not self.walking or self.reached_exit:
            return
        step = KNIGHT_SPEED * dt
        while step > 0 and self.next_point < len(self.path):
            target = self.path[self.next_point]
            to_target = target - self.pos
            if to_target.length() <= step:
                self.pos = pygame.Vector2(target)
                step -= to_target.length()
                self.next_point += 1
            else:
                self.facing = to_target.normalize()
                self.pos += self.facing * step
                step = 0
        if self.next_point >= len(self.path):
            self.reached_exit = True

    def current_animation(self):
        if self.reached_exit:
            return "victory"
        if abs(self.facing.x) > abs(self.facing.y):
            return "walk_side" if self.walking else "idle_side"
        if self.facing.y < 0:
            return "walk_up" if self.walking else "idle_up"
        return "walk_down" if self.walking else "idle"

    def draw(self, surface, font):
        name = self.current_animation()
        if name != self.animation:
            self.animation, self.anim_time = name, 0.0
        image = knight_frame(name, self.anim_time, facing_left=self.facing.x < 0)
        # He walks the path with his feet a little below it, so he looks centered on the tile.
        sprite = image.get_rect(midbottom=(self.pos.x, self.pos.y + 7))
        surface.blit(image, sprite)

        # What he's holding, above his head: tool on the left, item on the right.
        for gear, offset in ((self.tool, -5), (self.item, 5)):
            if gear:
                draw_icon(surface, font, gear, (self.pos.x + offset, sprite.top - 3), size=8)


class Helper:
    """Controlled with WASD/arrows. Drawn from the full-gear backpack sprite sheet."""

    def __init__(self, start, backpack):
        self.rect = pygame.Rect(0, 0, HELPER_SIZE, HELPER_SIZE)
        self.rect.center = start
        self.facing = pygame.Vector2(1, 0)
        self.backpack = backpack
        self.held = None  # gear dug out of the bag, waiting to be handed over
        self.digging = False
        self.dig_left = 0.0  # seconds until the gear is out of the bag
        self.walk_time = 0.0  # drives the walk animation; 0 while standing still

    def in_range(self, knight):
        return pygame.Vector2(self.rect.center).distance_to(knight.pos) <= HANDOFF_RANGE

    def action(self, knight):
        """Action button. Empty-handed: start digging out the next gear (anywhere).
        Holding gear: hand it to the Knight if he's in range. Whatever he was
        holding in that hand goes back to the end of the queue."""
        if self.held:
            if self.in_range(knight):
                gear, self.held = self.held, None
                old = knight.receive(gear)
                if old:
                    # Always fits: the gear just handed over freed its slot.
                    self.backpack.add(old)
        elif not self.digging and self.backpack.next is not None:
            self.digging = True
            self.dig_left = self.backpack.bag.extract_time

    def update(self, dt, keys, level):
        move = pygame.Vector2(
            (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
            (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if self.digging:
            if move.length_squared() == 0:
                self._dig(dt)
                return
            self.digging = False  # moving cancels the dig; the gear stays in the bag

        if move.length_squared() == 0:
            self.walk_time = 0.0
            return
        self.walk_time += dt
        move = move.normalize()
        self.facing = move
        distance = move * HELPER_SPEED * dt

        # Move one axis at a time so the Helper slides along walls.
        for axis in (0, 1):
            old = self.rect.copy()
            if axis == 0:
                self.rect.x += round(distance.x)
            else:
                self.rect.y += round(distance.y)
            if level.rect_hits_wall(self.rect):
                self.rect = old

    def _dig(self, dt):
        self.dig_left -= dt
        if self.dig_left <= 0:
            self.digging = False
            self.held = self.backpack.take_next()

    def draw(self, surface, font):
        center = pygame.Vector2(self.rect.center)
        if abs(self.facing.x) > abs(self.facing.y):
            direction = 2 if self.facing.x < 0 else 3
        else:
            direction = 1 if self.facing.y < 0 else 0
        frame = int(self.walk_time * HELPER_ANIM_FPS) % 4
        image = helper_frames()[direction][frame]
        # The collision box is the Helper's feet; the sprite stands on it.
        sprite = image.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + 1))
        surface.blit(image, sprite)

        if self.digging:
            progress = 1 - self.dig_left / self.backpack.bag.extract_time
            ring = pygame.Rect(0, 0, 17, 17)
            ring.center = center
            pygame.draw.arc(surface, (240, 240, 240), ring, math.pi / 2, math.pi / 2 + progress * math.tau, 2)
        if self.held:
            draw_icon(surface, font, self.held, (center.x, sprite.top - 4), size=8)
