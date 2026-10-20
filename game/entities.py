import math

import pygame

from game.gear import GEAR, TOOL, draw_icon

KNIGHT_SPEED = 60  # pixels per second
HELPER_SPEED = 130
HELPER_SIZE = 18  # collision box, in pixels
HANDOFF_RANGE = 64  # max distance between Helper and Knight centers for a hand-off


class Knight:
    """Walks the level's path from start to end. Placeholder: a steel square with a red plume."""

    def __init__(self, path):
        self.path = path
        self.pos = pygame.Vector2(path[0])
        self.next_point = 1
        self.walking = False
        self.reached_exit = False
        self.tool = None  # reusable gear, kept until replaced
        self.item = None  # one-use gear

    def receive(self, gear):
        """Put gear in the matching hand. Returns what was in that hand before (it falls on the floor)."""
        if GEAR[gear].hand == TOOL:
            old, self.tool = self.tool, gear
        else:
            old, self.item = self.item, gear
        return old

    def update(self, dt):
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
                self.pos += to_target.normalize() * step
                step = 0
        if self.next_point >= len(self.path):
            self.reached_exit = True

    def draw(self, surface, font):
        body = pygame.Rect(0, 0, 24, 24)
        body.center = self.pos
        pygame.draw.rect(surface, (170, 180, 195), body, border_radius=3)
        pygame.draw.rect(surface, (90, 95, 110), body, 2, border_radius=3)
        plume = pygame.Rect(0, 0, 8, 10)
        plume.midbottom = body.midtop
        pygame.draw.rect(surface, (210, 50, 50), plume)

        # What he's holding, above his head: tool on the left, item on the right.
        for gear, offset in ((self.tool, -11), (self.item, 11)):
            if gear:
                draw_icon(surface, font, gear, (body.centerx + offset, body.top - 20), size=16)


class Helper:
    """Controlled with WASD/arrows. Placeholder: a small round face with a huge backpack."""

    def __init__(self, start, backpack):
        self.rect = pygame.Rect(0, 0, HELPER_SIZE, HELPER_SIZE)
        self.rect.center = start
        self.facing = pygame.Vector2(1, 0)
        self.backpack = backpack
        self.held = None  # gear dug out of the bag, waiting to be handed over
        self.digging = False
        self.dig_left = 0.0  # seconds until the gear is out of the bag

    def in_range(self, knight):
        return pygame.Vector2(self.rect.center).distance_to(knight.pos) <= HANDOFF_RANGE

    def action(self, knight):
        """Action button. Empty-handed: start digging out the next gear (anywhere).
        Holding gear: hand it to the Knight if he's in range.
        Returns the gear the Knight dropped during a hand-off, if any."""
        if self.held:
            if not self.in_range(knight):
                return None
            gear, self.held = self.held, None
            return knight.receive(gear)
        if not self.digging and self.backpack.next is not None:
            self.digging = True
            self.dig_left = self.backpack.bag.extract_time
        return None

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
            return
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

    def pick_up(self, dropped):
        """Walk over dropped gear to put it back at the end of the queue, if the bag has room."""
        for piece in list(dropped):
            if not self.rect.colliderect(piece.rect):
                piece.armed = True
            elif piece.armed and self.backpack.add(piece.gear):
                dropped.remove(piece)

    def draw(self, surface, font):
        center = pygame.Vector2(self.rect.center)
        # The backpack sits behind the Helper, opposite the way they're facing.
        pack = pygame.Rect(0, 0, 22, 24)
        pack.center = center - self.facing * 7
        pygame.draw.rect(surface, (140, 90, 50), pack, border_radius=5)
        pygame.draw.rect(surface, (90, 55, 30), pack, 2, border_radius=5)
        pygame.draw.circle(surface, (250, 215, 170), center, 8)
        pygame.draw.circle(surface, (40, 30, 30), center + self.facing * 3 + pygame.Vector2(-3, -1), 2)
        pygame.draw.circle(surface, (40, 30, 30), center + self.facing * 3 + pygame.Vector2(3, -1), 2)

        if self.digging:
            progress = 1 - self.dig_left / self.backpack.bag.extract_time
            ring = pygame.Rect(0, 0, 34, 34)
            ring.center = center
            pygame.draw.arc(surface, (240, 240, 240), ring, math.pi / 2, math.pi / 2 + progress * math.tau, 3)
        if self.held:
            draw_icon(surface, font, self.held, (center.x, center.y - 20), size=16)
