"""The gameplay scene: the Knight walks his path while the Helper digs and hands over gear."""

import math
from functools import cache

import pygame

from game import ui
from game.backpack import BAGS, Backpack
from game.entities import Helper, Knight
from game.gear import GEAR, draw_icon
from game.obstacles import RULES
from game.scene import Scene
from game.tutorial import current_tip

WORLD_SCALE = 3  # the world is drawn at native pixel-art size, then scaled up
VIEW = (320, 240)  # world pixels the camera shows; 960x720 on screen
CAMERA_EASE = 8  # how quickly the camera catches up with the Helper
LOCATOR_FRAMES = [f"assets/interface/arrow_{i}.png" for i in range(1, 5)]  # points down
LOCATOR_FPS = 8
LOCATOR_MARGIN = 12
HUD_SIZE = (80, 180)  # side panel on the UI canvas scale (4x), right of the world

PATH_COLOR = (200, 170, 60)
EXIT_COLOR = (60, 170, 90)
HIGHLIGHT_COLOR = (120, 220, 255)
GOLD = (232, 177, 58)
SLOT_COLOR = (107, 78, 99)
DIM = 130
RETRY = "ENTER: retry   ESC: repack"
BETRAYAL_DELAY = 2.5  # seconds of the Knight lying there before the ending
DEATH_DELAY = 1.0  # seconds before the "he's dead" banner, so you see what got him
ICON_FONT = ui.IconFont()


def draw_level(surface, level, tiles):
    ts = level.tile_size
    surface.fill((0, 0, 0))
    for layer in (level.floor, level.wall_tiles, level.decor):
        for row in range(level.height):
            for col in range(level.width):
                gid = layer[row][col]
                if gid:
                    surface.blit(tiles[gid], (col * ts, row * ts))

    # The Knight's path, shown so you can plan around it.
    for a, b in zip(level.path, level.path[1:]):
        segment = b - a
        for i in range(0, int(segment.length()), 6):
            pygame.draw.circle(surface, PATH_COLOR, a + segment.normalize() * i, 1)

    exit_rect = pygame.Rect(0, 0, ts - 3, ts - 3)
    exit_rect.center = level.exit_pos
    pygame.draw.rect(surface, EXIT_COLOR, exit_rect, 2)


@cache
def locator_frames():
    return [pygame.image.load(path).convert_alpha() for path in LOCATOR_FRAMES]


def draw_slot(surface, gear, center, size=12, marked=False):
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if gear:
        draw_icon(surface, ICON_FONT, gear, center, size=size)
    else:
        pygame.draw.rect(surface, SLOT_COLOR, rect, 1)
    if marked:
        pygame.draw.rect(surface, GOLD, rect.inflate(4, 4), 1)


class PlayScene(Scene):
    """One run of a level with the bag and gear chosen on the item select screen."""

    def __init__(self, game, level_index, bag_id, picked):
        super().__init__(game)
        self.level_index = level_index
        self.level = game.levels[level_index]
        self.tiles = game.tiles[self.level.tileset["image"]]
        self.bag_id = bag_id
        self.picked = picked  # indices into the level's gear pool, in queue order
        map_size = (self.level.pixel_width, self.level.pixel_height)
        # The map's tiles and path never change, so they're drawn once.
        self.background = pygame.Surface(map_size)
        draw_level(self.background, self.level, self.tiles)
        self.world = pygame.Surface(map_size)
        self.view = pygame.Surface(VIEW)
        self.world_icon_font = pygame.font.Font(None, 10)
        self.hud = pygame.Surface(HUD_SIZE)
        # Banners and coach prompts are drawn on a UI-scale overlay covering the view.
        view_on_screen = (VIEW[0] * WORLD_SCALE, VIEW[1] * WORLD_SCALE)
        self.overlay = pygame.Surface((view_on_screen[0] // ui.UI_SCALE, view_on_screen[1] // ui.UI_SCALE),
                                      pygame.SRCALPHA)
        self.time = 0.0
        self.map_viewed = False  # has the player looked at the whole map (TAB) yet

        gear = [self.level.gear_pool[i] for i in picked]
        self.obstacles = [o.fresh() for o in self.level.obstacles]
        self.knight = Knight(self.level.path, self.level.knight_gear)
        self.helper = Helper(self.level.helper_start, Backpack(BAGS[bag_id], gear))
        # None while playing; otherwise "won" or "lost", shown as a banner: (title, lines).
        self.outcome = None
        self.banner = ("", [])
        self.death_time = 0.0
        self.camera = self.camera_target()

    def camera_target(self):
        """Top-left of the view: centred on the Helper, kept inside the map (or centring a small map)."""
        target = pygame.Vector2(self.helper.rect.center) - pygame.Vector2(VIEW) / 2
        for axis, size in enumerate((self.level.pixel_width, self.level.pixel_height)):
            if size <= VIEW[axis]:
                target[axis] = (size - VIEW[axis]) / 2
            else:
                target[axis] = max(0, min(target[axis], size - VIEW[axis]))
        return target

    def showing_map(self):
        return pygame.key.get_pressed()[pygame.K_TAB]

    def back_to_item_select(self):
        from game.menus import ItemSelectScene  # menus imports this module too
        self.game.change_scene(ItemSelectScene(self.game, self.level_index, self.bag_id, self.picked))

    def handle_event(self, event):
        confirm = (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)) or \
            (event.type == pygame.MOUSEBUTTONUP and event.button == 1)
        if self.outcome == "won":
            if confirm:
                self.next_level()
            return
        if self.outcome == "lost" and confirm:
            self.restart()
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.back_to_item_select()
        elif event.key == pygame.K_r:
            self.restart()
        elif self.outcome or self.knight.dead:
            return
        elif event.key == pygame.K_SPACE:
            self.knight.walking = True
        elif event.key == pygame.K_e:
            self.helper.action(self.knight)

    def restart(self):
        self.game.change_scene(PlayScene(self.game, self.level_index, self.bag_id, self.picked))

    def next_level(self):
        from game.menus import ItemSelectScene, LevelSelectScene
        if self.level_index + 1 < len(self.game.levels):
            self.game.change_scene(ItemSelectScene(self.game, self.level_index + 1))
        else:
            self.game.change_scene(LevelSelectScene(self.game, self.level_index))

    def update(self, dt):
        knight = self.knight
        self.time += dt
        self.camera += (self.camera_target() - self.camera) * min(1.0, dt * CAMERA_EASE)
        if self.showing_map():
            self.map_viewed = True
        for obstacle in self.obstacles:
            obstacle.update(dt)
        if self.outcome:
            knight.update(dt)  # keeps his victory/death animation going
            return
        blockers = [o.rect for o in self.obstacles if not o.cleared]
        self.helper.update(dt, pygame.key.get_pressed(), self.level, blockers)
        knight.update(dt, self.obstacles)
        if knight.dead:
            self.death_time += dt
            poisoned = knight.death_cause == "poison"
            if self.death_time < (BETRAYAL_DELAY if poisoned else DEATH_DELAY):
                return
            if poisoned and self.level.betrayal:
                from game.menus import EndingScene
                self.game.completed.add(self.level_index)
                self.game.change_scene(EndingScene(self.game))
            elif poisoned:
                self.end("lost", "He's dead.", "That wasn't a health potion.", RETRY)
            else:
                rule = RULES[knight.death_cause]
                self.end("lost", "He's dead.", rule.death, f"He needed the {GEAR[rule.gear].name}.", RETRY)
        elif knight.reached_exit:
            if self.level.betrayal:
                self.end("lost", "Too late!", "He took the credit again.", RETRY)
            else:
                self.game.completed.add(self.level_index)
                self.end("won", "Level clear!", "ENTER: continue")

    def end(self, outcome, title, *lines):
        self.outcome = outcome
        self.banner = (title, lines)

    def draw(self, screen):
        knight, helper = self.knight, self.helper
        self.world.blit(self.background, (0, 0))
        for obstacle in self.obstacles:
            obstacle.draw(self.world, self.tiles, self.world_icon_font)
        if helper.held and helper.in_range(knight):
            pygame.draw.circle(self.world, HIGHLIGHT_COLOR, knight.pos, 10, 1)
        # Draw whoever's feet are lower on screen last, so they overlap correctly.
        feet = {knight: knight.pos.y + 7, helper: helper.rect.bottom + 1}
        for actor in sorted(feet, key=feet.get):
            actor.draw(self.world, self.world_icon_font)
        view_on_screen = (VIEW[0] * WORLD_SCALE, VIEW[1] * WORLD_SCALE)
        showing_map = self.showing_map()
        if showing_map:
            self.draw_map(screen.subsurface((0, 0, *view_on_screen)))
        else:
            self.view.fill((0, 0, 0))
            self.view.blit(self.world, (-round(self.camera.x), -round(self.camera.y)))
            self.draw_locator(self.view)
            pygame.transform.scale(self.view, view_on_screen, screen.subsurface((0, 0, *view_on_screen)))

        self.draw_hud(self.hud)
        hud_x = view_on_screen[0]
        screen.blit(pygame.transform.scale(self.hud, (screen.get_width() - hud_x, screen.get_height())), (hud_x, 0))

        tip = None if showing_map else current_tip(self)
        if self.outcome or tip:
            self.overlay.fill((0, 0, 0, 0))
            if self.outcome:
                self.draw_banner(self.overlay)
            else:
                self.draw_tip(self.overlay, tip)
            screen.blit(pygame.transform.scale_by(self.overlay, ui.UI_SCALE), (0, 0))

    def draw_map(self, area):
        """TAB: the whole map, scaled to fit, for planning on maps bigger than the screen."""
        area.fill((0, 0, 0))
        w, h = self.world.get_size()
        scale = min(area.get_width() / w, area.get_height() / h)
        size = (round(w * scale), round(h * scale))
        rect = pygame.Rect((0, 0), size)
        rect.center = area.get_rect().center
        area.blit(pygame.transform.scale(self.world, size), rect)

    def draw_locator(self, view):
        """When the Knight is off screen, an arrow at the edge of the view points to him."""
        on_view = self.knight.pos - self.camera
        if pygame.Rect((0, 0), VIEW).inflate(-8, -8).collidepoint(on_view):
            return
        centre = pygame.Vector2(VIEW) / 2
        direction = on_view - centre
        if direction.length_squared() == 0:
            return
        # Walk from the centre toward him until we hit the margin box.
        half = pygame.Vector2(VIEW[0] / 2 - LOCATOR_MARGIN, VIEW[1] / 2 - LOCATOR_MARGIN)
        reach = min(half.x / abs(direction.x) if direction.x else math.inf,
                    half.y / abs(direction.y) if direction.y else math.inf)
        spot = centre + direction * reach
        frames = locator_frames()
        arrow = frames[int(self.time * LOCATOR_FPS) % len(frames)]
        arrow = pygame.transform.rotate(arrow, math.degrees(math.atan2(direction.x, direction.y)))
        view.blit(arrow, arrow.get_rect(center=spot))

    def draw_hud(self, hud):
        knight, helper = self.knight, self.helper
        backpack = helper.backpack
        w = hud.get_width()
        ui.nine_slice(hud, "panel9", hud.get_rect())
        ui.draw_text(hud, self.level.name[:12], (w // 2, 8), "gold", anchor="midtop")

        ui.draw_text(hud, "Knight", (w // 2, 22), anchor="midtop", alpha=DIM)
        draw_slot(hud, knight.tool, (w // 2 - 9, 39))
        draw_slot(hud, knight.item, (w // 2 + 9, 39))

        ui.draw_text(hud, "Helper", (w // 2, 52), anchor="midtop", alpha=DIM)
        draw_slot(hud, helper.held, (w // 2, 69))
        if helper.digging:
            progress = 1 - helper.dig_left / backpack.bag.extract_time
            bar = pygame.Rect(w // 2 - 15, 78, 30, 3)
            pygame.draw.rect(hud, SLOT_COLOR, bar)
            pygame.draw.rect(hud, GOLD, (bar.x, bar.y, round(bar.w * progress), bar.h))

        bag = backpack.bag
        ui.draw_text(hud, bag.name, (w // 2, 86), "gold", anchor="midtop")
        ui.draw_text(hud, f"{len(backpack.queue)}/{bag.slots}  {bag.extract_time}s", (w // 2, 95), anchor="midtop")
        for slot in range(bag.slots):
            col, row = slot % 3, slot // 3
            gear = backpack.queue[slot] if slot < len(backpack.queue) else None
            draw_slot(hud, gear, (w // 2 - 18 + col * 18, 114 + row * 18), marked=slot == 0 and gear is not None)

        hints = ["E dig/give", "TAB map", "R restart", "ESC pack"]
        if not knight.walking and not knight.dead and not self.outcome:
            hints = ["SPACE go!"] + hints[:-1]  # the one that matters before the run
        for i, hint in enumerate(hints):
            ready = hint == "SPACE go!"
            ui.draw_text(hud, hint, (w // 2, 143 + i * 9), "gold" if ready else "cream", anchor="midtop",
                         alpha=255 if ready else DIM)

    def draw_tip(self, overlay, lines):
        """A coach prompt at the top of the map."""
        width = max(len(line) for line in lines) * ui.GLYPH_ADVANCE + 20
        rect = pygame.Rect(0, 4, max(width, 100), 12 + 10 * len(lines))
        rect.centerx = overlay.get_width() // 2
        ui.nine_slice(overlay, "panel9", rect)
        for i, line in enumerate(lines):
            ui.draw_text(overlay, line, (rect.centerx, rect.y + 7 + i * 10), "gold" if i == 0 else "cream",
                         anchor="midtop")

    def draw_banner(self, overlay):
        title, lines = self.banner
        rect = pygame.Rect(0, 0, 172, 40 + 10 * len(lines))
        rect.center = overlay.get_rect().center
        ui.nine_slice(overlay, "panel9", rect)
        ui.draw_text(overlay, title, (rect.centerx, rect.y + 12), "gold", scale=2, anchor="midtop")
        for i, line in enumerate(lines):
            ui.draw_text(overlay, line, (rect.centerx, rect.y + 32 + i * 10), anchor="midtop")
