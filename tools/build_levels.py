"""Builds the teaching levels (levels/01-03) from the ASCII layouts below.

Each layout is drawn one character per 16 px tile:
  #   wall or void (autotiled: wall faces, caps, pillars and corners next to floor; dark void elsewhere)
  .   floor
  K   the Knight's start (first point of his path)    H   the Helper's start
  a-z the Knight's path, in order, after K             E   the exit (last point of his path)
  S   skeleton    D   locked door    R   rock (obstacles; they sit on the path)
Decor (drawn on the decor layer, never solid):
  ^   wall torch    =   banner   (on a wall cell)
  %   bones    &   cobweb    $   chest    +   box    !   candle stand   (on a floor cell)

The output is a normal Tiled map, so it can be opened and polished in Tiled afterwards,
but running this script again overwrites those three files. Run from the project root:
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
OBSTACLES = {"S": "skeleton", "D": "locked_door", "R": "rock"}

LEVELS = {
    "01_first_blood.tmj": dict(
        name="First Blood", gear_pool="sword", knight_gear="", tutorial="first_blood",
        pack_tip="Pack the Sword, then START.",
        layout="""
################################
################################
################################
#####^###########^###^#####=####
##&......#####.........###..$..#
##.......#####.........###.....#
##.......#####.................#
##.K.......S.......a...###.....#
##.......#####.........###.....#
##..H....#####%........#########
##############.........#########
##############.........#########
###################.############
###################.############
###################S############
###############!..........######
###############...........######
###############....b..E..+######
###############&..........######
################################
"""),
    "02_locked_in.tmj": dict(
        name="Locked In", gear_pool="key,pickaxe,key", knight_gear="sword", tutorial="locked_in",
        pack_tip="Queue order is dig order. Doors eat Keys.",
        layout="""
############################################
############################################
############################################
#####^##^#######^##^########################
##&.......####.......#######################
##........####.......#######################
##.K.......S......a..#######################
##........####.......#######################
##..H.....####...%...#######################
##################D#########################
##################.#########################
########^#####^###.#####^###^###############
####..............................##########
####.....%........................##########
####..............b...........c...##########
####&.............................##########
######.#######################S#############
######.#######################.#########=###
######.#####################^#.##^####.....#
###........###############.........###.!..+#
###........###############.........###.....#
###....$...###############....d....D....E..#
###........###############.........###...$.#
###&.......###############.........###.....#
############################################
############################################
"""),
    "03_rubble.tmj": dict(
        name="Rubble", gear_pool="pickaxe", knight_gear="sword", tutorial="rubble",
        pack_tip="One Pickaxe. The Sword comes back to you.",
        layout="""
########################################
########################################
########################################
#####^##########^###############^###^###
##&......####........#######..........&#
##.......####........#######...........#
##.K......S......a...#######..E...d....#
##.......####........#######...........#
##..H....####........#######........$..#
#################.################.#####
#################R################R#####
#################.################.#####
##############^##.######^#########.#^###
############.................###......##
############........%......!.###......##
############.................###......##
############.................###......##
############.....b...........S....c...##
############.................###......##
############&................###.....+##
########################################
########################################
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
    waypoints = [marks["K"][0]] + [marks[c][0] for c in "abcdefghijklmnopqrstuvwxyz" if c in marks] + [marks["E"][0]]
    path = [center(x, y) for x, y in waypoints]

    objects = [point(2, "helper_start", *marks["H"][0]), point(3, "exit", *marks["E"][0])]
    for ch, kind in OBSTACLES.items():
        for x, y in marks.get(ch, []):
            objects.append(point(len(objects) + 2, kind, x, y))

    def tile_layer(lid, name, cells):
        return {"data": [g for row in cells for g in row], "height": h, "id": lid, "name": name,
                "opacity": 1, "type": "tilelayer", "visible": True, "width": w, "x": 0, "y": 0}

    x0, y0 = path[0]
    props = [("name", spec["name"]), ("unlocks_bag", ""), ("gear_pool", spec["gear_pool"]),
             ("knight_gear", spec["knight_gear"]), ("tutorial", spec["tutorial"]), ("pack_tip", spec["pack_tip"])]
    return {
        "type": "map", "version": "1.10", "tiledversion": "1.11.0", "orientation": "orthogonal",
        "renderorder": "right-down", "infinite": False, "width": w, "height": h,
        "tilewidth": TILE, "tileheight": TILE, "compressionlevel": -1,
        "nextlayerid": 6, "nextobjectid": len(objects) + 2,
        "properties": [{"name": n, "type": "string", "value": v} for n, v in props],
        "tilesets": [TILESET],
        "layers": [
            tile_layer(1, "floor", floor),
            tile_layer(2, "walls", walls),
            tile_layer(3, "decor", decor),
            {"draworder": "topdown", "id": 4, "name": "path", "opacity": 1, "type": "objectgroup",
             "visible": True, "x": 0, "y": 0, "objects": [{
                 "height": 0, "id": 1, "name": "knight_path", "rotation": 0, "type": "", "visible": True,
                 "width": 0, "x": x0, "y": y0, "polyline": [{"x": x - x0, "y": y - y0} for x, y in path]}]},
            {"draworder": "topdown", "id": 5, "name": "objects", "opacity": 1, "type": "objectgroup",
             "visible": True, "x": 0, "y": 0, "objects": objects},
        ],
    }


def main():
    for filename, spec in LEVELS.items():
        with open(f"levels/{filename}", "w") as f:
            json.dump(build(spec), f, indent=1)
            f.write("\n")
        print(f"wrote levels/{filename}")


if __name__ == "__main__":
    main()
