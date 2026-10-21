"""Builds assets/knight.png and assets/gear_icons.png from the artist's reference
sheet (assets/knight_and_items.png).

The reference sheet has labels, an opaque background and frames at ~4x scale, and
its Knight rows don't face the way they're labelled: "Up" shows his face (turned
right), "Right" faces left, and there's no back view at all. So, from the
"Knight (Walking)" block:
  down  = Down row, frames 1, 2, 3, 2 (frame 4 turns sideways)
  up    = down, with the helmet and face repainted as a plain helmet back (a stand-in)
  left  = Left row, frames 1, 2, 1, 2 (frames 3-4 turn the wrong way)
  right = left, mirrored

Outputs:
  assets/knight.png     4x4 grid of 32x32 frames, rows down/up/left/right
  assets/gear_icons.png one row of 16x16 icons, in GEAR_ICONS order (game/gear.py reads it)
Run from the project root:
    python tools/make_knight_sheet.py
"""

import pygame

SOURCE = "assets/knight_and_items.png"
KNIGHT_OUTPUT = "assets/knight.png"
ICONS_OUTPUT = "assets/gear_icons.png"

# "Knight (Walking)" frame bounds, found by scanning for non-background pixels.
WALK_COLS = [(665, 721), (771, 828), (867, 931), (969, 1035)]
WALK_ROWS = [(71, 150), (169, 244), (266, 336), (357, 431)]
DOWN, LEFT = 0, 2
CELL = 32
TARGET_HEIGHT = 27

# Gear id -> (center x, icon row) in the "Item Icons" block. Plank isn't on the sheet.
# Keep this order in sync with ICON_SHEET_ORDER in game/gear.py.
ICON_ROWS = [(515, 570), (612, 666)]
GEAR_ICONS = {
    "sword": (80, 0),
    "pickaxe": (1102, 0),
    "torch": (882, 0),
    "shield": (681, 0),
    "key": (1214, 0),
    "bomb": (384, 1),
    "potion": (80, 1),
}
ICON = 16
ICON_TARGET = 18

HELMET = (150, 156, 170)
HELMET_SHADE = (115, 120, 135)
OUTLINE = (40, 26, 34)


def is_background(c):
    # The sheet's background is a near-black purple that varies a little by panel.
    return c.r < 45 and c.g < 30 and c.b < 35


def cut(img, rect, flood=True):
    """Copy a frame and clear its background. With flood, only background reachable from
    the edges is cleared, so dark pixels inside a sprite (visor slots) are kept; without
    it, every background-coloured pixel goes, which opens up holes like the key's ring."""
    frame = img.subsurface(rect).copy()
    w, h = frame.get_size()
    if not flood:
        for y in range(h):
            for x in range(w):
                if is_background(frame.get_at((x, y))):
                    frame.set_at((x, y), (0, 0, 0, 0))
        return frame.subsurface(frame.get_bounding_rect()).copy()
    todo = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    seen = set()
    while todo:
        x, y = todo.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        seen.add((x, y))
        if is_background(frame.get_at((x, y))):
            frame.set_at((x, y), (0, 0, 0, 0))
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return frame.subsurface(frame.get_bounding_rect()).copy()


def cut_walk(img, row, col):
    (x0, x1), (y0, y1) = WALK_COLS[col], WALK_ROWS[row]
    return cut(img, (x0 - 4, y0 - 4, x1 - x0 + 9, y1 - y0 + 9))


def shrink(frame, scale):
    size = (max(1, round(frame.get_width() * scale)), max(1, round(frame.get_height() * scale)))
    small = pygame.transform.smoothscale(frame, size)
    # Hard alpha edges, like hand-made pixel art.
    for y in range(small.get_height()):
        for x in range(small.get_width()):
            p = small.get_at((x, y))
            small.set_at((x, y), (p.r, p.g, p.b, 255) if p.a >= 128 else (0, 0, 0, 0))
    return small


def remove_specks(sheet, passes=2):
    w, h = sheet.get_size()
    for _ in range(passes):
        solid = [[sheet.get_at((x, y)).a > 0 for x in range(w)] for y in range(h)]
        for y in range(h):
            for x in range(w):
                if solid[y][x]:
                    neighbours = sum(solid[y + dy][x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                                     if (dx or dy) and 0 <= x + dx < w and 0 <= y + dy < h)
                    if neighbours <= 2:
                        sheet.set_at((x, y), (0, 0, 0, 0))


def back_view(frame):
    """Repaint the helmet and face of a front-facing frame as a plain helmet back.
    The plume, body and legs are kept."""
    back = frame.copy()
    w, h = back.get_size()
    # Helmet and face run from below the plume down to the chin.
    top, bottom = int(h * 0.22), int(h * 0.74)
    for y in range(top, bottom):
        for x in range(w):
            c = frame.get_at((x, y))
            if c.a == 0 or (c.r > 120 and c.g < 70):  # transparent or plume
                continue
            edge = any(not (0 <= x + dx < w and 0 <= y + dy < h) or frame.get_at((x + dx, y + dy)).a == 0
                       for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)))
            if edge:
                back.set_at((x, y), OUTLINE)
            elif y > top + (bottom - top) * 0.7 or abs(x - w // 2) <= 1:
                # Shade the lower rim and a rear seam down the middle.
                back.set_at((x, y), HELMET_SHADE)
            else:
                back.set_at((x, y), HELMET)
    return back


def build_knight(img):
    down = [cut_walk(img, DOWN, c) for c in (0, 1, 2, 1)]
    up = [back_view(f) for f in down]
    left = [cut_walk(img, LEFT, c) for c in (0, 1, 0, 1)]
    right = [pygame.transform.flip(f, True, False) for f in left]
    rows = [down, up, left, right]

    # One scale for every frame so the Knight doesn't change size between them.
    scale = TARGET_HEIGHT / max(f.get_height() for row in rows for f in row)
    sheet = pygame.Surface((CELL * 4, CELL * 4), pygame.SRCALPHA)
    for r, row in enumerate(rows):
        for c, frame in enumerate(row):
            small = shrink(frame, scale)
            sheet.blit(small, small.get_rect(midbottom=(c * CELL + CELL // 2, (r + 1) * CELL - 1)))
    remove_specks(sheet)
    pygame.image.save(sheet, KNIGHT_OUTPUT)
    print(f"wrote {KNIGHT_OUTPUT}")


def build_icons(img):
    icons = []
    for cx, row in GEAR_ICONS.values():
        y0, y1 = ICON_ROWS[row]
        icons.append(cut(img, (cx - 48, y0, 96, y1 - y0), flood=False))

    # One scale for every icon so they match in the HUD.
    scale = ICON_TARGET / max(max(i.get_size()) for i in icons)
    sheet = pygame.Surface((ICON * len(icons), ICON), pygame.SRCALPHA)
    for n, icon in enumerate(icons):
        small = shrink(icon, scale)
        sheet.blit(small, small.get_rect(center=(n * ICON + ICON // 2, ICON // 2)))
    remove_specks(sheet, passes=1)
    pygame.image.save(sheet, ICONS_OUTPUT)
    print(f"wrote {ICONS_OUTPUT}")


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    img = pygame.image.load(SOURCE).convert_alpha()
    build_knight(img)
    build_icons(img)


if __name__ == "__main__":
    main()
