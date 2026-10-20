"""Pixel-art UI from assets/UI: atlas sprites, the bitmap font, nine-slice panels and mouse hotspots.

Menus are laid out on a 320x180 canvas (the size the UI kit was drawn at) and
scaled up 4x to fill the window.
"""

import json
from functools import cache

import pygame

ATLAS = "assets/UI/ui_atlas.json"
LAYOUT = "assets/UI/ui_layout.json"
TORCH_FRAMES = [f"assets/items and trap_animation/torch/torch_{i}.png" for i in range(1, 5)]
TORCH_FPS = 8

CANVAS_SIZE = (320, 180)
UI_SCALE = 4
GLYPH_ADVANCE = 6  # the font is 5x7 glyphs plus a 1px shadow
GLYPH_HEIGHT = 8
INK = (26, 18, 32)  # the darkest color in the UI palette


@cache
def _atlas():
    with open(ATLAS) as f:
        data = json.load(f)
    image = pygame.image.load(f"assets/UI/{data['image']}").convert_alpha()
    return image, data["frames"], data["nine_slice"]


@cache
def sprite(name):
    image, frames, _ = _atlas()
    f = frames[name]
    return image.subsurface((f["x"], f["y"], f["w"], f["h"]))


def has_sprite(name):
    return name in _atlas()[1]


@cache
def background(name):
    """A 320x180 screen background from assets/UI/screens, e.g. 'main_bg'."""
    return pygame.image.load(f"assets/UI/screens/{name}.png").convert()


@cache
def layout(screen):
    """Widget positions from the UI kit's layout file, e.g. layout('main')."""
    with open(LAYOUT) as f:
        return json.load(f)[screen]


@cache
def torch_frames():
    return [pygame.image.load(path).convert_alpha() for path in TORCH_FRAMES]


def torch(surface, pos, time):
    frames = torch_frames()
    surface.blit(frames[int(time * TORCH_FPS) % len(frames)], pos)


@cache
def render_text(text, color="cream", scale=1):
    """Text in the bitmap font. Colors: cream, gold, dark. Uppercase only; unknown characters show as '?'."""
    text = text.upper()
    surf = pygame.Surface((max(1, len(text) * GLYPH_ADVANCE), GLYPH_HEIGHT), pygame.SRCALPHA)
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        name = f"font_{color}_{ord(ch)}"
        surf.blit(sprite(name if has_sprite(name) else f"font_{color}_63"), (i * GLYPH_ADVANCE, 0))
    if scale > 1:
        surf = pygame.transform.scale_by(surf, scale)
    return surf


def draw_text(surface, text, pos, color="cream", scale=1, anchor="topleft", alpha=255):
    image = render_text(text, color, scale)
    if alpha < 255:
        image = image.copy()
        image.set_alpha(alpha)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


class IconFont:
    """Stands in for a pygame font so gear.draw_icon letters its icons in the bitmap font."""

    def render(self, text, antialias=False, color=None):
        return render_text(text, "dark")


def _tile(surface, image, area, dest):
    """Fill dest with copies of image's area (keeps pixel patterns crisp instead of stretching them)."""
    piece = image.subsurface(area)
    clip = surface.get_clip()
    surface.set_clip(dest.clip(clip) if clip else dest)
    for y in range(dest.top, dest.bottom, piece.get_height()):
        for x in range(dest.left, dest.right, piece.get_width()):
            surface.blit(piece, (x, y))
    surface.set_clip(clip)


def nine_slice(surface, name, rect):
    """Draw a panel or button sprite stretched to rect, keeping its corners. name like 'panel9' or 'button9_red_h'."""
    rect = pygame.Rect(rect)
    image = sprite(name)
    border = _atlas()[2].get(name) or _atlas()[2][name.rsplit("_", 1)[0] + "_*"]
    w, h = image.get_size()
    b = min(border, rect.w // 2, rect.h // 2)
    mid_w, mid_h = w - 2 * border, h - 2 * border
    inner = pygame.Rect(rect.x + b, rect.y + b, rect.w - 2 * b, rect.h - 2 * b)
    # corners
    surface.blit(image, rect.topleft, (0, 0, b, b))
    surface.blit(image, (rect.right - b, rect.y), (w - b, 0, b, b))
    surface.blit(image, (rect.x, rect.bottom - b), (0, h - b, b, b))
    surface.blit(image, (rect.right - b, rect.bottom - b), (w - b, h - b, b, b))
    # edges and middle
    _tile(surface, image, (border, 0, mid_w, b), pygame.Rect(inner.x, rect.y, inner.w, b))
    _tile(surface, image, (border, h - b, mid_w, b), pygame.Rect(inner.x, rect.bottom - b, inner.w, b))
    _tile(surface, image, (0, border, b, mid_h), pygame.Rect(rect.x, inner.y, b, inner.h))
    _tile(surface, image, (w - b, border, b, mid_h), pygame.Rect(rect.right - b, inner.y, b, inner.h))
    _tile(surface, image, (border, border, mid_w, mid_h), inner)


def button(surface, rect, label, variant="stone", state="n"):
    """A text button built from the nine-slice button sprite. state: n(ormal), h(over), p(ressed)."""
    rect = pygame.Rect(rect)
    nine_slice(surface, f"button9_{variant}_{state}", rect)
    color = "gold" if state == "h" or variant == "red" else "cream"
    face_y = rect.centery - (0 if state == "p" else 1)
    draw_text(surface, label, (rect.centerx, face_y), color, anchor="center")


def present(canvas, screen):
    """Scale a UI canvas up to the whole window."""
    pygame.transform.scale(canvas, screen.get_size(), screen)


class Hotspots:
    """Clickable areas, registered while drawing and hit-tested against the mouse (in canvas pixels)."""

    def __init__(self, scale=UI_SCALE, offset=(0, 0)):
        self.scale = scale
        self.offset = offset  # where the canvas sits in the window
        self.areas = []
        self.pressed = None

    def clear(self):
        self.areas = []

    def add(self, rect, key):
        self.areas.append((pygame.Rect(rect), key))

    def at(self, window_pos):
        pos = ((window_pos[0] - self.offset[0]) // self.scale, (window_pos[1] - self.offset[1]) // self.scale)
        for rect, key in reversed(self.areas):
            if rect.collidepoint(pos):
                return key
        return None

    def handle(self, event):
        """Returns ("hover", key) on mouse movement over a hotspot, ("click", key) on a full click, else None."""
        if event.type == pygame.MOUSEMOTION:
            key = self.at(event.pos)
            return ("hover", key) if key is not None else None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pressed = self.at(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            key, pressed, self.pressed = self.at(event.pos), self.pressed, None
            if key is not None and key == pressed:
                return ("click", key)
        return None
