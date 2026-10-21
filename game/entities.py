import json
import math
import os
from functools import cache

import pygame

from game.enemies import move_body
from game.gear import FIST_DAMAGE, GEAR, TOOL, draw_icon

KNIGHT_SPEED = 30  # pixels per second
KNIGHT_SIZE = 9  # collision box
KNIGHT_MAX_HP = 40
KNIGHT_REACH = 15  # centre to centre, for his swings
ATTACK_TIME = 0.8  # seconds between swings
LUNGE_TIME = 0.15  # he leans into each swing for this long
HURT_FLASH = 0.15
POTION_HEAL = 15
POTION_AT = 0.4  # he drinks a held Potion once he's below this much of his HP
BOMB_DAMAGE = 8
BOMB_RADIUS = 36
BOMB_CROWD = 2  # he throws a held Bomb once this many enemies are in range (or the boss is)

HELPER_SPEED = 65
HELPER_SIZE = 9  # collision box, in pixels
HELPER_HP = 4  # hearts; every hit takes one
HELPER_INVULNERABLE = 1.0  # seconds after a hit
HANDOFF_RANGE = 32  # max distance between Helper and Knight centers for a hand-off

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


class Popup:
    """A short line of text floating up from where something happened (damage, heals)."""

    LIFE = 0.8

    def __init__(self, pos, text, color):
        self.pos = pygame.Vector2(pos)
        self.text = text
        self.color = color
        self.age = 0.0


class Knight:
    """Fights whatever is nearest with whatever he's holding, and uses his item by himself
    when the moment comes. Drawn from assets/knight.png."""

    def __init__(self, pos, hp=KNIGHT_MAX_HP, max_hp=KNIGHT_MAX_HP, gear=()):
        self.pos = pygame.Vector2(pos)
        self.hp = hp
        self.max_hp = max_hp
        self.fighting = False  # SPACE sends him in
        self.leaving = None  # once the room is clear: where he walks to (the boss room's exit)
        self.reached_exit = False
        self.dead = False
        self.death_cause = None  # "enemy" or "poison"
        self.tool = None  # reusable gear, kept until replaced
        self.item = None  # one-use gear, used by himself when the moment comes
        self.swing = 0.0  # cooldown until his next swing
        self.lunge = 0.0
        self.lunge_dir = pygame.Vector2()
        self.flash = 0.0
        self.facing = pygame.Vector2(1, 0)
        self.moving = False
        self.popups = []  # read and drawn by the scene
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
        self.fighting = False

    def popup(self, text, color, pos=None):
        self.popups.append(Popup(pos if pos is not None else self.pos + (0, -16), text, color))

    def hurt(self, amount):
        """Take a hit (softened by a Shield). Returns the damage actually dealt."""
        if self.dead:
            return 0
        guard = GEAR[self.tool].guard if self.tool else 1.0
        dealt = max(1, round(amount * guard))
        self.hp -= dealt
        self.flash = HURT_FLASH
        self.popup(f"-{dealt}", (240, 90, 90))
        if self.hp <= 0:
            self.hp = 0
            self.die("enemy")
            self.popup("Tell my mother... I was right...", (230, 230, 230), self.pos + (0, -26))
        return dealt

    def heal(self, amount):
        healed = min(amount, self.max_hp - self.hp)
        self.hp += healed
        self.popup(f"+{healed}", (110, 220, 120))

    def damage_against(self, enemy):
        if not self.tool:
            return FIST_DAMAGE
        gear = GEAR[self.tool]
        multiplier = 1.0
        for tag in enemy.type.tags:
            multiplier *= gear.bonus.get(tag, 1.0)
        return max(1, round(gear.damage * multiplier))

    def use_item(self, enemies):
        """The Knight uses his item when it makes sense, all by himself."""
        item = self.item
        if item == "potion" and self.hp <= self.max_hp * POTION_AT:
            self.item = None
            self.heal(POTION_HEAL)
        elif item == "bomb" and self.fighting:
            near = [e for e in enemies if not e.dead and e.pos.distance_to(self.pos) <= BOMB_RADIUS * e.type.scale]
            if len(near) >= BOMB_CROWD or any(e.type.scale > 1 for e in near):
                self.item = None
                self.popup("BOOM!", (255, 200, 80))
                for enemy in near:
                    enemy.hurt(BOMB_DAMAGE)

    def update(self, dt, level, enemies=()):
        """Fight the nearest enemy, or once the room's clear, walk out if told to."""
        self.anim_time += dt
        self.flash = max(0.0, self.flash - dt)
        self.lunge = max(0.0, self.lunge - dt)
        self.swing = max(0.0, self.swing - dt)
        for popup in self.popups:
            popup.age += dt
            popup.pos.y -= 14 * dt
        self.popups = [p for p in self.popups if p.age < Popup.LIFE]
        self.moving = False
        if self.dead or self.reached_exit:
            return
        self.use_item(enemies)
        if self.leaving is not None:
            if self._walk_to(self.leaving, dt, 2, level):
                self.reached_exit = True
            return
        if not self.fighting:
            return
        alive = [e for e in enemies if not e.dead]
        if not alive:
            return
        target = min(alive, key=lambda e: e.pos.distance_squared_to(self.pos))
        reach = KNIGHT_REACH + 4 * (target.type.scale - 1)
        if self.pos.distance_to(target.pos) > reach * 0.8:
            self._walk_to(target.pos, dt, reach * 0.8, level)
        if self.pos.distance_to(target.pos) <= reach and self.swing == 0:
            self.swing = ATTACK_TIME
            self.lunge = LUNGE_TIME
            to_target = target.pos - self.pos
            self.lunge_dir = to_target.normalize() if to_target.length_squared() else pygame.Vector2()
            if to_target.length_squared():
                self.facing = self.lunge_dir
            damage = self.damage_against(target)
            target.hurt(damage)
            self.popup(str(damage), (255, 255, 255), target.pos + (0, -12 * target.type.scale))

    def _walk_to(self, point, dt, stop, level=None):
        """Step toward `point`; True once within `stop` pixels of it."""
        to_point = point - self.pos
        if to_point.length() <= stop:
            return True
        self.moving = True
        if level:
            heading = level.route(self.pos, point, KNIGHT_SIZE) - self.pos
            if heading.length_squared():
                to_point = heading
        self.facing = to_point.normalize()
        step = self.facing * min(KNIGHT_SPEED * dt, to_point.length())
        self.pos = move_body(self.pos, step, KNIGHT_SIZE, level) if level else self.pos + step
        return False

    def current_animation(self):
        if self.dead:
            return "death"
        if self.reached_exit:
            return "victory"
        if abs(self.facing.x) > abs(self.facing.y):
            direction = "left" if self.facing.x < 0 else "right"
        else:
            direction = "up" if self.facing.y < 0 else "down"
        return f"{'walk' if self.moving else 'idle'}_{direction}"

    @property
    def feet(self):
        return self.pos.y + 7

    def draw(self, surface, font):
        name = self.current_animation()
        if name != self.animation:
            self.animation, self.anim_time = name, 0.0
        image = knight_frame(name, self.anim_time)
        if self.flash and not self.dead:
            image = image.copy()
            image.fill((255, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
        lean = self.lunge_dir * 4 * (self.lunge / LUNGE_TIME) if self.lunge else pygame.Vector2()
        sprite = image.get_rect(midbottom=(self.pos.x + lean.x, self.feet + lean.y))
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
        self.pos = pygame.Vector2(start)  # exact position; the rect is it rounded to pixels
        self.rect = pygame.Rect(0, 0, HELPER_SIZE, HELPER_SIZE)
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.facing = pygame.Vector2(1, 0)
        self.backpack = backpack
        self.held = None  # gear dug out of the bag, waiting to be handed over
        self.digging = False
        self.dig_left = 0.0  # seconds until the gear is out of the bag
        self.walk_time = 0.0  # drives the walk animation; 0 while standing still
        self.give_time = 0.0  # time left on the hand-over animation
        self.give_side = "right"
        self.hurt_time = 0.0
        self.handed = []  # every piece of gear given to the Knight this run, in order
        self.hp = HELPER_HP
        self.invulnerable = 0.0
        self.animation = None
        self.anim_time = 0.0

    @property
    def alive(self):
        return self.hp > 0

    def hurt(self, amount):
        """Every hit takes one heart, then a moment of safety. Returns the damage dealt."""
        if not self.alive or self.invulnerable > 0:
            return 0
        self.hp -= 1
        self.invulnerable = HELPER_INVULNERABLE
        self.digging = False  # getting hit knocks the gear back into the bag
        self.hurt_time = self.animation_length("hurt")
        return 1

    def in_range(self, knight):
        return pygame.Vector2(self.rect.center).distance_to(knight.pos) <= HANDOFF_RANGE

    def near(self, point):
        return pygame.Vector2(self.rect.center).distance_to(point) <= HANDOFF_RANGE

    def action(self, knight, chest=None):
        """Action button. Empty-handed: start digging out the next gear (anywhere).
        Holding gear: hand it to the Knight if he's in range. Whatever he was
        holding in that hand goes back to the end of the queue. Holding the Key
        next to the (closed) chest at `chest`: open it, and return "chest";
        anywhere else, put it back at the end of the queue."""
        if not self.alive:
            return None
        if self.held and GEAR[self.held].helper_only:
            if chest is not None and self.near(chest):
                self.held = None
                self.give_side = "left" if chest.x < self.rect.centerx else "right"
                self.give_time = self.animation_length(f"give_{self.give_side}")
                return "chest"
            self.backpack.put_back(self.held)
            self.held = None
        elif self.held:
            if self.in_range(knight) and not knight.dead:
                gear, self.held = self.held, None
                self.give_side = "left" if knight.pos.x < self.rect.centerx else "right"
                self.give_time = self.animation_length(f"give_{self.give_side}")
                self.handed.append(gear)
                old = knight.receive(gear)
                if old:
                    self.backpack.put_back(old)  # to the end of the queue
        elif not self.digging and self.backpack.next is not None:
            self.digging = True
            self.dig_left = self.backpack.bag.extract_time
        return None

    def animation_length(self, name):
        frames, fps, _ = helper_animations(self.backpack.bag.sprite)[name]
        return len(frames) / fps

    def update(self, dt, keys, level, blockers=()):
        """Move and dig. `blockers` are rects the Helper can't walk into."""
        self.anim_time += dt
        self.give_time = max(0.0, self.give_time - dt)
        self.hurt_time = max(0.0, self.hurt_time - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        if not self.alive:
            return
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

        # Move one axis at a time so the Helper slides along walls. The position is kept
        # exact and only rounded for the rect; rounding each step instead would make a
        # diagonal step (0.7 per axis) count as a full pixel on both axes, and run fast.
        for axis in (0, 1):
            moved = pygame.Vector2(self.pos)
            moved[axis] += distance[axis]
            rect = self.rect.copy()
            rect.center = round(moved.x), round(moved.y)
            if not level.rect_hits_wall(rect) and rect.collidelist(blockers) == -1:
                self.pos, self.rect = moved, rect

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
        if not self.alive:
            return "death"
        if self.hurt_time > 0:
            return "hurt"
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
        if self.invulnerable and self.alive and int(self.invulnerable * 12) % 2:
            image = image.copy()
            image.set_alpha(110)  # blinking while safe after a hit
        # Sprites are anchored at the feet (bottom-centre); the collision box is the feet.
        sprite = image.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + 1))
        surface.blit(image, sprite)

        if self.digging:
            ring = pygame.Rect(0, 0, 17, 17)
            ring.center = self.rect.center
            pygame.draw.arc(surface, (240, 240, 240), ring, math.pi / 2, math.pi / 2 + progress * math.tau, 2)
        if self.held:
            draw_icon(surface, font, self.held, (sprite.centerx, sprite.top + 1), size=8)
