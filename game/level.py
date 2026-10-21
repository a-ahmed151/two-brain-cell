"""Loads arena rooms made in Tiled and exported as JSON (.tmj).

The arenas are built by tools/build_levels.py; see its docstring for the markers.
"""

import json
import os
from collections import deque
from dataclasses import dataclass

import pygame


@dataclass
class Level:
    name: str
    width: int  # in tiles
    height: int
    tile_size: int
    floor: list[list[int]]  # [row][col] tile gids, 0 = empty
    wall_tiles: list[list[int]]
    decor: list[list[int]]  # props drawn over floor and walls; never solid
    walls: list[list[bool]]
    tileset: dict  # first embedded Tiled tileset; "image" is resolved to a path from the project root
    knight_start: pygame.Vector2
    helper_start: pygame.Vector2
    exit_pos: pygame.Vector2  # middle of the exit door, in the top wall; it opens once the room is clear
    spawns: list[pygame.Vector2]  # where enemies appear
    chest: pygame.Vector2 | None  # opened with a Key for an extra reward

    @property
    def pixel_width(self):
        return self.width * self.tile_size

    @property
    def pixel_height(self):
        return self.height * self.tile_size

    @property
    def doorstep(self):
        """The floor just inside the exit door: walk here to leave the room."""
        return self.exit_pos + (0, self.tile_size)

    def rect_hits_wall(self, rect):
        ts = self.tile_size
        for row in range(rect.top // ts, (rect.bottom - 1) // ts + 1):
            for col in range(rect.left // ts, (rect.right - 1) // ts + 1):
                if not (0 <= row < self.height and 0 <= col < self.width):
                    return True
                if self.walls[row][col]:
                    return True
        return False

    def clear_line(self, a, b, size):
        """Can a square body of `size` slide straight from a to b without touching a wall?"""
        a, b = pygame.Vector2(a), pygame.Vector2(b)
        steps = max(1, int(a.distance_to(b) // 4))
        rect = pygame.Rect(0, 0, size, size)
        for i in range(steps + 1):
            rect.center = a.lerp(b, i / steps)
            if self.rect_hits_wall(rect):
                return False
        return True

    def route(self, start, goal, size):
        """Where to head next to get from start to goal around the walls: the goal itself
        when the way is clear, otherwise the next tile on a shortest path over the floor."""
        if self.clear_line(start, goal, size):
            return pygame.Vector2(goal)
        ts = self.tile_size
        first = (int(start[0] // ts), int(start[1] // ts))
        last = (int(goal[0] // ts), int(goal[1] // ts))
        came_from = {last: None}  # searched backwards from the goal, so each cell knows its next step
        frontier = deque([last])
        while frontier:
            x, y = frontier.popleft()
            if (x, y) == first:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) in came_from or not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                # No cutting corners past a wall.
                if self.walls[ny][nx] or self.walls[y][nx] or self.walls[ny][x]:
                    continue
                came_from[(nx, ny)] = (x, y)
                frontier.append((nx, ny))
        step = came_from.get(first)
        if step is None:
            return pygame.Vector2(goal)  # no way round; push on and slide
        return pygame.Vector2(step[0] * ts + ts / 2, step[1] * ts + ts / 2)


def load_level(filename):
    with open(filename) as f:
        data = json.load(f)

    width, height = data["width"], data["height"]
    props = {p["name"]: p["value"] for p in data.get("properties", [])}
    layers = {layer["name"]: layer for layer in data["layers"]}

    def grid(layer_name):
        layer = layers.get(layer_name)
        if layer is None:
            return [[0] * width for _ in range(height)]
        # The top bits of a gid are Tiled's flip flags; we don't draw flipped tiles.
        cells = [gid & 0x0FFFFFFF for gid in layer["data"]]
        return [cells[row * width:(row + 1) * width] for row in range(height)]

    floor = grid("floor")
    wall_tiles = grid("walls")
    decor = grid("decor")
    walls = [[gid != 0 for gid in row] for row in wall_tiles]

    tileset = dict(data["tilesets"][0])
    tileset["image"] = os.path.normpath(os.path.join(os.path.dirname(filename), tileset["image"]))

    points = {}
    for obj in layers["objects"]["objects"]:
        # Tiled 1.9 saved the Class field as "class"; other versions use "type".
        kind = obj.get("type") or obj.get("class", "")
        points.setdefault(kind, []).append(pygame.Vector2(obj["x"], obj["y"]))
    for required in ("knight_start", "helper_start", "exit", "spawn"):
        if required not in points:
            raise ValueError(f"{filename}: needs a '{required}' object")

    return Level(
        name=props.get("name", "Untitled"),
        width=width,
        height=height,
        tile_size=data["tilewidth"],
        floor=floor,
        wall_tiles=wall_tiles,
        decor=decor,
        walls=walls,
        tileset=tileset,
        knight_start=points["knight_start"][0],
        helper_start=points["helper_start"][0],
        exit_pos=points["exit"][0],
        spawns=points["spawn"],
        chest=points.get("chest", [None])[0],
    )


def load_tiles(tileset):
    """Cut a Tiled tileset image into tiles, keyed by gid. Needs the display to exist."""
    image = pygame.image.load(tileset["image"]).convert_alpha()
    tw, th = tileset["tilewidth"], tileset["tileheight"]
    margin, spacing = tileset.get("margin", 0), tileset.get("spacing", 0)
    tiles = {}
    for i in range(tileset["tilecount"]):
        col, row = i % tileset["columns"], i // tileset["columns"]
        rect = (margin + col * (tw + spacing), margin + row * (th + spacing), tw, th)
        tiles[tileset["firstgid"] + i] = image.subsurface(rect)
    return tiles
