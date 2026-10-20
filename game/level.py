"""Loads levels made in Tiled and exported as JSON (.tmj).

See the "Level format (Tiled)" section in GAME_DESIGN.md for the layer and
object conventions.
"""

import json
import os
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
    walls: list[list[bool]]
    tileset: dict  # first embedded Tiled tileset; "image" is resolved to a path from the project root
    path: list[pygame.Vector2]  # Knight's route in pixels; path[0] is his start
    helper_start: pygame.Vector2
    exit_pos: pygame.Vector2
    unlocks_bag: str | None  # bag the player gets when this level starts
    betrayal: bool  # the final level: poison the Knight before he reaches the exit
    gear_pool: list[str]
    knight_gear: list[str]  # what the Knight holds at the start, outside the bag
    obstacles: list[dict]  # everything else on the objects layer

    @property
    def pixel_width(self):
        return self.width * self.tile_size

    @property
    def pixel_height(self):
        return self.height * self.tile_size

    def rect_hits_wall(self, rect):
        ts = self.tile_size
        for row in range(rect.top // ts, (rect.bottom - 1) // ts + 1):
            for col in range(rect.left // ts, (rect.right - 1) // ts + 1):
                if not (0 <= row < self.height and 0 <= col < self.width):
                    return True
                if self.walls[row][col]:
                    return True
        return False


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
    walls = [[gid != 0 for gid in row] for row in wall_tiles]

    tileset = dict(data["tilesets"][0])
    tileset["image"] = os.path.normpath(os.path.join(os.path.dirname(filename), tileset["image"]))

    path = []
    for obj in layers["path"]["objects"]:
        if "polyline" in obj:
            path = [pygame.Vector2(obj["x"] + p["x"], obj["y"] + p["y"]) for p in obj["polyline"]]
            break
    if len(path) < 2:
        raise ValueError(f"{filename}: the 'path' layer needs a polyline with at least 2 points")

    helper_start = exit_pos = None
    obstacles = []
    for obj in layers["objects"]["objects"]:
        # Tiled 1.9 saved the Class field as "class"; other versions use "type".
        kind = obj.get("type") or obj.get("class", "")
        pos = pygame.Vector2(obj["x"], obj["y"])
        if kind == "helper_start":
            helper_start = pos
        elif kind == "exit":
            exit_pos = pos
        else:
            obstacles.append({"kind": kind, "rect": pygame.Rect(obj["x"], obj["y"], obj["width"], obj["height"])})

    def gear_list(prop):
        return [g.strip() for g in props.get(prop, "").split(",") if g.strip()]

    return Level(
        name=props.get("name", "Untitled"),
        width=width,
        height=height,
        tile_size=data["tilewidth"],
        floor=floor,
        wall_tiles=wall_tiles,
        walls=walls,
        tileset=tileset,
        path=path,
        helper_start=helper_start or pygame.Vector2(path[0]),
        exit_pos=exit_pos or pygame.Vector2(path[-1]),
        unlocks_bag=props.get("unlocks_bag") or None,
        betrayal=bool(props.get("betrayal", False)),
        gear_pool=gear_list("gear_pool"),
        knight_gear=gear_list("knight_gear"),
        obstacles=obstacles,
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
