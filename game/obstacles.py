"""Obstacles on the Knight's path. He stops at each one and uses the matching gear by
himself; without it, he dies. See "The Knight" in GAME_DESIGN.md."""

from dataclasses import dataclass
from functools import cache

import pygame

from game.gear import GEAR, draw_icon

SKELETON_FRAMES = [f"assets/Character_animation/monsters_idle/skeleton1/v2/skeleton_v2_{i}.png" for i in range(1, 5)]
SKELETON_FPS = 6
CLEAR_TIME = 0.4  # seconds an obstacle takes to fade out once handled


@dataclass(frozen=True)
class Rule:
    gear: str  # what the Knight needs in a hand
    consumed: bool  # items are used up; tools are kept
    death: str  # banner line when he arrives without the gear
    tile: int = 0  # tileset gid to draw; 0 = animated sprite (the skeleton)


RULES = {
    "skeleton": Rule("sword", False, "A skeleton got him."),
    "locked_door": Rule("key", True, "The door was locked.", tile=39),
    "rock": Rule("pickaxe", False, "He walked into the rubble.", tile=50),
}


@cache
def skeleton_frames():
    return [pygame.image.load(path).convert_alpha() for path in SKELETON_FRAMES]


def project_onto_path(path, point):
    """The closest point on the path to `point`, and how far along the path it is."""
    point = pygame.Vector2(point)
    best = (float("inf"), pygame.Vector2(path[0]), 0.0)
    walked = 0.0
    for a, b in zip(path, path[1:]):
        segment = b - a
        length = segment.length()
        t = 0.0 if length == 0 else max(0.0, min(1.0, (point - a).dot(segment) / (length * length)))
        closest = a + segment * t
        distance = point.distance_to(closest)
        if distance < best[0]:
            best = (distance, closest, walked + length * t)
        walked += length
    return best[1], best[2]


class Obstacle:
    def __init__(self, kind, pos, at):
        self.kind = kind
        self.rule = RULES[kind]
        self.pos = pygame.Vector2(pos)  # on the path
        self.at = at  # distance along the path
        self.cleared = False
        self.fade = 0.0  # counts down after clearing
        self.time = 0.0

    @classmethod
    def on_path(cls, kind, point, path):
        pos, at = project_onto_path(path, point)
        return cls(kind, pos, at)

    def fresh(self):
        """A new, uncleared copy for another run of the level."""
        return Obstacle(self.kind, self.pos, self.at)

    def clear(self):
        self.cleared = True
        self.fade = CLEAR_TIME

    def update(self, dt):
        self.time += dt
        self.fade = max(0.0, self.fade - dt)

    def draw(self, surface, tiles, font):
        if self.cleared and self.fade <= 0:
            return
        if self.rule.tile:
            image = tiles[self.rule.tile]
        else:
            frames = skeleton_frames()
            image = frames[int(self.time * SKELETON_FPS) % len(frames)]
        if self.cleared:
            image = image.copy()
            image.set_alpha(round(255 * self.fade / CLEAR_TIME))
        rect = image.get_rect(center=self.pos)
        surface.blit(image, rect)
        if not self.cleared:
            # What it takes to get past, so the map explains the plan.
            draw_icon(surface, font, self.rule.gear, (self.pos.x, rect.top - 5), size=8)

    @property
    def rect(self):
        """The tile it fills. Solid for the Helper until it's cleared."""
        rect = pygame.Rect(0, 0, 16, 16)
        rect.center = self.pos
        return rect

    @property
    def gear_name(self):
        return GEAR[self.rule.gear].name
