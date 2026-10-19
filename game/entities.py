import pygame

KNIGHT_SPEED = 60  # pixels per second
HELPER_SPEED = 130
HELPER_SIZE = 18  # collision box, in pixels


class Knight:
    """Walks the level's path from start to end. Placeholder: a steel square with a red plume."""

    def __init__(self, path):
        self.path = path
        self.pos = pygame.Vector2(path[0])
        self.next_point = 1
        self.walking = False
        self.reached_exit = False

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

    def draw(self, surface):
        body = pygame.Rect(0, 0, 24, 24)
        body.center = self.pos
        pygame.draw.rect(surface, (170, 180, 195), body, border_radius=3)
        pygame.draw.rect(surface, (90, 95, 110), body, 2, border_radius=3)
        plume = pygame.Rect(0, 0, 8, 10)
        plume.midbottom = body.midtop
        pygame.draw.rect(surface, (210, 50, 50), plume)


class Helper:
    """Controlled with WASD/arrows. Placeholder: a small round face with a huge backpack."""

    def __init__(self, start):
        self.rect = pygame.Rect(0, 0, HELPER_SIZE, HELPER_SIZE)
        self.rect.center = start
        self.facing = pygame.Vector2(1, 0)

    def update(self, dt, keys, level):
        move = pygame.Vector2(
            (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
            (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
        )
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

    def draw(self, surface):
        center = pygame.Vector2(self.rect.center)
        # The backpack sits behind the Helper, opposite the way they're facing.
        pack = pygame.Rect(0, 0, 22, 24)
        pack.center = center - self.facing * 7
        pygame.draw.rect(surface, (140, 90, 50), pack, border_radius=5)
        pygame.draw.rect(surface, (90, 55, 30), pack, 2, border_radius=5)
        pygame.draw.circle(surface, (250, 215, 170), center, 8)
        pygame.draw.circle(surface, (40, 30, 30), center + self.facing * 3 + pygame.Vector2(-3, -1), 2)
        pygame.draw.circle(surface, (40, 30, 30), center + self.facing * 3 + pygame.Vector2(3, -1), 2)
