import json
import math
import os
from functools import cache

import pygame

from game.gear import GEAR, TOOL, draw_icon

KNIGHT_SPEED = 30  # pixels per second
HELPER_SPEED = 65
HELPER_SIZE = 9  # collision box, in pixels
HANDOFF_RANGE = 32  # max distance between Helper and Knight centers for a hand-off
OBSTACLE_GAP = 12  # the Knight stops this far before an obstacle to deal with it
USE_TIME = 0.4  # seconds he spends using gear on an obstacle

HELPER_SHEETS = "assets/helper/{size}/helper_{size}.json"  # one sheet per backpack size (Bag.sprite)


@cache
def helper_animations(size):
    """{name: (frames, fps, loop)} for one Helper sheet, loaded on first use (needs the display to exist)."""
    path = HELPER_SHEETS.format(size=size)
    with open(path) as f:
        data = json.load(f)
    sheet = pygame.image.load(os.path.join(os.path.dirname(path), data["image"])).convert_alpha()
    w, h = data["frameWidth"], data["frameHeight"]
    return {name: ([sheet.subsurface((col * w, anim["row"] * h, w, h)) for col in range(anim["frames"])],
                   anim["fps"], anim["loop"])
            for name, anim in data["animations"].items()}


def helper_frame(size, name, time):
    """The frame of a Helper animation `time` seconds after it started."""
    frames, fps, loop = helper_animations(size)[name]
    index = int(time * fps)
    return frames[index % len(frames) if loop else min(index, len(frames) - 1)]


KNIGHT_SHEET = "assets/knight.png"  # 4x4 grid of 32x32 walk frames; rows face down, up, left, right
KNIGHT_FRAME = 32
KNIGHT_DIRECTIONS = ("down", "up", "left", "right")
KNIGHT_WALK_FPS = 8


@cache
def knight_animations():
    """{name: (frames, fps)}, loaded on first use (needs the display to exist).

    The sheet only has walk cycles, so standing still is the first walk frame,
    victory is standing facing down, and death is that frame tipped over."""
    sheet = pygame.image.load(KNIGHT_SHEET).convert_alpha()
    size = KNIGHT_FRAME
    animations = {}
    for row, direction in enumerate(KNIGHT_DIRECTIONS):
        walk = [sheet.subsurface((col * size, row * size, size, size)) for col in range(4)]
        animations[f"walk_{direction}"] = (walk, KNIGHT_WALK_FPS)
        animations[f"idle_{direction}"] = (walk[:1], 1)
    animations["victory"] = animations["idle_down"]
    fallen = pygame.transform.rotate(animations["idle_down"][0][0], 90)
    lying = pygame.Surface((size, size), pygame.SRCALPHA)  # same anchor as the others: on the floor
    body = fallen.subsurface(fallen.get_bounding_rect())
    lying.blit(body, body.get_rect(midbottom=(size // 2, size)))
    animations["death"] = ([lying], 1)
    return animations


def knight_frame(name, time):
    """The frame of a knight animation `time` seconds after it started."""
    frames, fps = knight_animations()[name]
    return frames[int(time * fps) % len(frames)]


class Knight:
    """Walks the level's path from start to end. Drawn from assets/knight.png."""

    def __init__(self, path, gear=()):
        self.path = path
        self.pos = pygame.Vector2(path[0])
        self.next_point = 1
        self.walking = False
        self.reached_exit = False
        self.dead = False
        self.death_cause = None  # obstacle kind, or "poison"
        self.distance = 0.0  # how far along the path he is
        self.using = None  # the obstacle he's busy with
        self.use_left = 0.0
        self.tool = None  # reusable gear, kept until replaced
        self.item = None  # one-use gear
        self.facing = (path[1] - path[0]).normalize()
        self.animation = None
        self.anim_time = 0.0
        for piece in gear:
            self.receive(piece)

    def receive(self, gear):
        """Put gear in the matching hand. Returns what was in that hand before."""
        if gear == "poison":
            # He trusts the Helper completely and drinks it at once.
            self.die("poison")
            return None
        if GEAR[gear].hand == TOOL:
            old, self.tool = self.tool, gear
        else:
            old, self.item = self.item, gear
        return old

    def die(self, cause):
        self.dead = True
        self.death_cause = cause
        self.walking = False

    def holds(self, gear):
        return gear in (self.tool, self.item)

    def update(self, dt, obstacles=()):
        """Walk on, stopping at each obstacle to use the right gear on it (or die trying)."""
        self.anim_time += dt
        if not self.walking or self.reached_exit or self.dead:
            return
        if self.using:
            self.use_left -= dt
            if self.use_left > 0:
                return
            self.using.clear()
            self.using = None
        step = KNIGHT_SPEED * dt
        ahead = next((o for o in obstacles if not o.cleared), None)
        if ahead:
            room = ahead.at - OBSTACLE_GAP - self.distance
            if room <= step:
                self._walk(max(0.0, room))
                self._meet(ahead)
                return
        self._walk(step)

    def _meet(self, obstacle):
        rule = obstacle.rule
        if not self.holds(rule.gear):
            self.die(obstacle.kind)
            return
        if rule.consumed:
            self.item = None
        self.using = obstacle
        self.use_left = USE_TIME

    def _walk(self, step):
        self.distance += step
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
        if self.dead:
            return "death"
        if self.reached_exit:
            return "victory"
        if abs(self.facing.x) > abs(self.facing.y):
            direction = "left" if self.facing.x < 0 else "right"
        else:
            direction = "up" if self.facing.y < 0 else "down"
        moving = self.walking and not self.using
        return f"{'walk' if moving else 'idle'}_{direction}"

    def draw(self, surface, font):
        name = self.current_animation()
        if name != self.animation:
            self.animation, self.anim_time = name, 0.0
        image = knight_frame(name, self.anim_time)
        # He walks the path with his feet a little below it, so he looks centered on the tile.
        sprite = image.get_rect(midbottom=(self.pos.x, self.pos.y + 7))
        surface.blit(image, sprite)

        if self.dead:
            return
        # What he's holding, above his head: tool on the left, item on the right.
        for gear, offset in ((self.tool, -5), (self.item, 5)):
            if gear:
                draw_icon(surface, font, gear, (self.pos.x + offset, sprite.top - 3), size=8)


class Helper:
    """Controlled with WASD/arrows. Drawn from the sheet matching the bag's size."""

    def __init__(self, start, backpack):
        self.rect = pygame.Rect(0, 0, HELPER_SIZE, HELPER_SIZE)
        self.rect.center = start
        self.facing = pygame.Vector2(1, 0)
        self.backpack = backpack
        self.held = None  # gear dug out of the bag, waiting to be handed over
        self.digging = False
        self.dig_left = 0.0  # seconds until the gear is out of the bag
        self.walk_time = 0.0  # drives the walk animation; 0 while standing still
        self.give_time = 0.0  # time left on the hand-over animation
        self.give_side = "right"
        self.handed = []  # every piece of gear given to the Knight this run, in order
        self.animation = None
        self.anim_time = 0.0

    def in_range(self, knight):
        return pygame.Vector2(self.rect.center).distance_to(knight.pos) <= HANDOFF_RANGE

    def action(self, knight):
        """Action button. Empty-handed: start digging out the next gear (anywhere).
        Holding gear: hand it to the Knight if he's in range. Whatever he was
        holding in that hand goes back to the end of the queue."""
        if self.held:
            if self.in_range(knight):
                gear, self.held = self.held, None
                self.give_side = "left" if knight.pos.x < self.rect.centerx else "right"
                self.give_time = self.animation_length(f"give_{self.give_side}")
                self.handed.append(gear)
                old = knight.receive(gear)
                if old:
                    # Always fits: the gear just handed over freed its slot.
                    self.backpack.add(old)
        elif not self.digging and self.backpack.next is not None:
            self.digging = True
            self.dig_left = self.backpack.bag.extract_time

    def animation_length(self, name):
        frames, fps, _ = helper_animations(self.backpack.bag.sprite)[name]
        return len(frames) / fps

    def update(self, dt, keys, level, blockers=()):
        """Move and dig. `blockers` are rects the Helper can't walk into (uncleared obstacles)."""
        self.anim_time += dt
        self.give_time = max(0.0, self.give_time - dt)
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
            if level.rect_hits_wall(self.rect) or self.rect.collidelist(blockers) != -1:
                self.rect = old

    def _dig(self, dt):
        self.dig_left -= dt
        if self.dig_left <= 0:
            self.digging = False
            self.held = self.backpack.take_next()

    def facing_name(self):
        if abs(self.facing.x) > abs(self.facing.y):
            return "left" if self.facing.x < 0 else "right"
        return "up" if self.facing.y < 0 else "down"

    def current_animation(self):
        if self.digging:
            return "dig"
        if self.walk_time > 0:
            return f"walk_{self.facing_name()}"
        if self.give_time > 0:
            return f"give_{self.give_side}"
        if self.held:
            return "hold_up"  # hands raised; the gear is drawn above his head
        return f"idle_{self.facing_name()}"

    def draw(self, surface, font):
        size = self.backpack.bag.sprite
        name = self.current_animation()
        if name != self.animation:
            self.animation, self.anim_time = name, 0.0
        if name == "dig":
            # Stretch the rummage over the bag's extract time, so the glint lands as the gear comes out.
            progress = 1 - self.dig_left / self.backpack.bag.extract_time
            time = progress * self.animation_length("dig") * 0.999
        else:
            time = self.anim_time
        image = helper_frame(size, name, time)
        # Sprites are anchored at the feet (bottom-centre); the collision box is the feet.
        sprite = image.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + 1))
        surface.blit(image, sprite)

        if self.digging:
            ring = pygame.Rect(0, 0, 17, 17)
            ring.center = self.rect.center
            pygame.draw.arc(surface, (240, 240, 240), ring, math.pi / 2, math.pi / 2 + progress * math.tau, 2)
        if self.held:
            draw_icon(surface, font, self.held, (sprite.centerx, sprite.top + 1), size=8)
