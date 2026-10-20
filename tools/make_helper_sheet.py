"""Builds assets/helper_full_gear.png from the artist's reference sheet (assets/image.png).

The reference sheet has labels, an opaque background and frames at ~5x scale, and
two of its rows don't face the way they're labelled: "Up" only shows the back in
its last two frames, and "Right" faces left. So:
  down  = Down row
  up    = Up frames 3, 4, 3, 4
  left  = Left row
  right = Left row, mirrored

Output: 4x4 grid of 24x24 frames, rows down/up/left/right (what game/entities.py
and assets/helper_full_gear.tsj expect). Run from the project root:
    python tools/make_helper_sheet.py
"""

import pygame

SOURCE = "assets/image.png"
OUTPUT = "assets/helper_full_gear.png"
BACKGROUND = (28, 16, 24)
# Frame bounds in the source, found by scanning for non-background pixels.
COLS = [(140, 258), (295, 413), (454, 575), (615, 735)]
ROWS = [(90, 220), (255, 381), (408, 533), (565, 694)]
DOWN, UP, LEFT = 0, 1, 2
CELL = 24
TARGET_HEIGHT = 23


def cut(img, row, col):
    (x0, x1), (y0, y1) = COLS[col], ROWS[row]
    frame = img.subsurface((x0 - 4, y0 - 4, x1 - x0 + 9, y1 - y0 + 9)).copy()
    for y in range(frame.get_height()):
        for x in range(frame.get_width()):
            c = frame.get_at((x, y))
            if sum(abs(c[i] - BACKGROUND[i]) for i in range(3)) < 45:
                frame.set_at((x, y), (0, 0, 0, 0))
    return frame.subsurface(frame.get_bounding_rect()).copy()


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


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    img = pygame.image.load(SOURCE).convert_alpha()

    down = [cut(img, DOWN, c) for c in range(4)]
    back = [cut(img, UP, c) for c in (2, 3)]
    up = back + back
    left = [cut(img, LEFT, c) for c in range(4)]
    right = [pygame.transform.flip(f, True, False) for f in left]
    rows = [down, up, left, right]

    # One scale for every frame so the Helper doesn't change size between them.
    scale = TARGET_HEIGHT / max(f.get_height() for row in rows for f in row)
    sheet = pygame.Surface((CELL * 4, CELL * 4), pygame.SRCALPHA)
    for r, row in enumerate(rows):
        for c, frame in enumerate(row):
            small = shrink(frame, scale)
            sheet.blit(small, small.get_rect(midbottom=(c * CELL + CELL // 2, (r + 1) * CELL - 1)))
    remove_specks(sheet)
    pygame.image.save(sheet, OUTPUT)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
