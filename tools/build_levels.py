"""Builds the arena rooms (levels/arena_*.tmj) from the ASCII layouts below.

Each arena is one screen (20x15 tiles) and is drawn one character per 16 px tile:
  #   wall or void (autotiled: wall faces, caps, pillars and corners next to floor; dark void elsewhere)
  .   floor
  K   the Knight's start    H   the Helper's start    X   the exit door (where he leaves the room)
  E   an enemy spawn point  C   the chest (a Key opens it)
Decor (drawn on the decor layer, never solid):
  ^   wall torch    =   banner   (on a wall cell)
  %   bones    &   cobweb    $   chest    +   box    !   candle stand   (on a floor cell)

The output is a normal Tiled map, so it can be opened and polished in Tiled afterwards,
but running this script again overwrites those files. Run from the project root:
    python tools/build_levels.py
"""

import json

TILE = 16
TILESET = {
    "columns": 10, "firstgid": 1, "image": "../assets/character and tileset/Dungeon_Tileset.png",
    "imageheight": 160, "imagewidth": 160, "margin": 0, "name": "dungeon", "spacing": 0,
    "tilecount": 100, "tileheight": 16, "tilewidth": 16,
}

# Tileset gids (see assets/character and tileset/Dungeon_Tileset.png).
TOP_FACES = [2, 3, 4, 5]  # wall seen from the room below it
BOTTOM_CAPS = [42, 43, 44, 45]  # wall with the room above it
LEFT_WALL, RIGHT_WALL = 11, 16  # room to the right / to the left
CORNER = {"se": 1, "sw": 6, "ne": 41, "nw": 46}  # which diagonal the room is on
VOID = 79
FLOORS = [7, 7, 8, 7, 9, 7, 17, 19]
DECOR = {"^": 91, "=": 75, "%": 78, "&": 65, "$": 84, "+": 82, "!": 94}
WALL_DECOR = "^="
MARKERS = {"K": "knight_start", "H": "helper_start", "X": "exit", "E": "spawn", "C": "chest"}

ARENAS = {
    "arena_1.tmj": dict(name="Crypt", layout="""
####################
####################
###^####=##=####^###
##&......X.......%##
##................##
##..E..........E..##
##................##
##.......##.......##
##.K.H...##.....E.##
##................##
##..E.........C...##
##................##
##%..............!##
####################
####################
"""),
    "arena_2.tmj": dict(name="Pillar Hall", layout="""
####################
####################
###^#####==#####^###
##.......X........##
##..E..........E..##
##...##......##...##
##...##......##...##
##.K.............E##
##.H..............##
##...##......##...##
##...##......##...##
##..E....C.....E..##
##&..............%##
####################
####################
"""),
    "arena_3.tmj": dict(name="Cross Vault", layout="""
####################
####################
####^####=#####^####
###......X.......###
###..E........E..###
#####..........#####
##..............E.##
##.K.H............##
##................##
#####..........#####
###..E.......C...###
###..............###
###&............%###
####################
####################
"""),
}



def parse(layout):
    rows = [r for r in layout.strip("\n").split("\n")]
    width = max(len(r) for r in rows)
    return [r.ljust(width, "#") for r in rows]


def is_floor(ch):
    return ch != "#" and ch not in WALL_DECOR


def autotile(grid):
    h, w = len(grid), len(grid[0])

    def open_at(x, y):
        return 0 <= x < w and 0 <= y < h and is_floor(grid[y][x])

    floor = [[0] * w for _ in range(h)]
    walls = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if open_at(x, y):
                floor[y][x] = FLOORS[(x * 3 + y * 5) % len(FLOORS)]
                continue
            if open_at(x, y + 1):
                walls[y][x] = TOP_FACES[x % 4]
            elif open_at(x, y - 1):
                walls[y][x] = BOTTOM_CAPS[x % 4]
            elif open_at(x + 1, y):
                walls[y][x] = LEFT_WALL
            elif open_at(x - 1, y):
                walls[y][x] = RIGHT_WALL
            elif open_at(x + 1, y + 1):
                walls[y][x] = CORNER["se"]
            elif open_at(x - 1, y + 1):
                walls[y][x] = CORNER["sw"]
            elif open_at(x + 1, y - 1):
                walls[y][x] = CORNER["ne"]
            elif open_at(x - 1, y - 1):
                walls[y][x] = CORNER["nw"]
            else:
                walls[y][x] = VOID
    return floor, walls


def center(x, y):
    return x * TILE + TILE // 2, y * TILE + TILE // 2


def point(oid, kind, x, y):
    px, py = center(x, y)
    return {"height": 0, "id": oid, "name": kind, "point": True, "rotation": 0, "type": kind,
            "visible": True, "width": 0, "x": px, "y": py}


def build(spec):
    grid = parse(spec["layout"])
    h, w = len(grid), len(grid[0])
    floor, walls = autotile(grid)
    decor = [[DECOR.get(grid[y][x], 0) for x in range(w)] for y in range(h)]

    marks = {}
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            marks.setdefault(ch, []).append((x, y))
    objects = []
    for ch, kind in MARKERS.items():
        for x, y in marks.get(ch, []):
            objects.append(point(len(objects) + 1, kind, x, y))

    def tile_layer(lid, name, cells):
        return {"data": [g for row in cells for g in row], "height": h, "id": lid, "name": name,
                "opacity": 1, "type": "tilelayer", "visible": True, "width": w, "x": 0, "y": 0}

    props = [("name", spec["name"])]
    return {
        "type": "map", "version": "1.10", "tiledversion": "1.11.0", "orientation": "orthogonal",
        "renderorder": "right-down", "infinite": False, "width": w, "height": h,
        "tilewidth": TILE, "tileheight": TILE, "compressionlevel": -1,
        "nextlayerid": 5, "nextobjectid": len(objects) + 1,
        "properties": [{"name": n, "type": "string", "value": v} for n, v in props],
        "tilesets": [TILESET],
        "layers": [
            tile_layer(1, "floor", floor),
            tile_layer(2, "walls", walls),
            tile_layer(3, "decor", decor),
            {"draworder": "topdown", "id": 4, "name": "objects", "opacity": 1, "type": "objectgroup",
             "visible": True, "x": 0, "y": 0, "objects": objects},
        ],
    }


def main():
    for filename, spec in ARENAS.items():
        with open(f"levels/{filename}", "w") as f:
            json.dump(build(spec), f, indent=1)
            f.write("\n")
        print(f"wrote levels/{filename}")


if __name__ == "__main__":
    main()
