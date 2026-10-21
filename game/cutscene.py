"""The intro cutscene, played before room 1 of every run.

The Helper waits in an empty room. The Knight bursts in through the entrance,
they have a short (one-sided) chat, and both walk out through the exit into room 1.
The lines show in a dialogue panel at the top that slides in and types itself out.

ENTER/SPACE/click: finish the line, or go to the next one. ESC/TAB or the Skip button: skip it all.
"""

from functools import cache

import pygame

from game import ui
from game.combat import draw_level, draw_open_door
from game.entities import helper_animations, helper_frame, knight_frame
from game.scene import Scene

WORLD_SCALE = 3  # the 320x240 room, drawn 960x720 in the middle of the window
VIEW = (320, 240)
WORLD_X = 40  # where the room sits on the 320x180 UI canvas (the sides are dark, with torches)

KNIGHT_SPEED = 42  # px/s; a little brisker than in a fight, he's excited
HELPER_SPEED = 34  # and the Helper is carrying everything
FADE_TIME = 0.6
TYPE_SPEED = 38  # characters per second
PANEL_SLIDE = 0.25  # seconds for the dialogue panel to slide in or out
PANEL = pygame.Rect(46, 4, 228, 44)  # on the UI canvas, over the top wall
TEXT_CHARS = 31  # characters per line inside the panel
SKIP_RECT = pygame.Rect(284, 4, 32, 14)
ARROW_FRAMES = [f"assets/interface/arrow_{i}.png" for i in range(1, 5)]  # point down
ARROW_FPS = 8
SOUNDS = "assets/sounds/{}.wav"

KNIGHT, HELPER = "knight", "helper"
NAMES = {KNIGHT: "Sir Knight", HELPER: "Helper"}

# (speaker, line, animation while it's on screen). The Helper never speaks (see
# GAME_DESIGN.md), so his "lines" are what he does, in dashes.
SCRIPT = [
    (KNIGHT, "THERE you are! I've been looking everywhere for you.", "idle_right"),
    (KNIGHT, "Sword? Check. Potions? Check. My lucky comb?", "idle_right"),
    (HELPER, "- pats the bulging bag -", "dig"),
    (KNIGHT, "Splendid! Today, this dungeon learns my name.", "victory"),
    (KNIGHT, "And yours, too! It's... uh...", "idle_right"),
    (HELPER, "- waits -", "idle_left"),
    (KNIGHT, "...", "idle_down"),
    (KNIGHT, "Let's start... Helper.", "idle_right"),
    (HELPER, "- sighs, and heaves the bag onto his back -", "hold_up"),
    (KNIGHT, "Onward! Try to keep up!", "idle_up"),
]


@cache
def arrow_frames():
    return [pygame.image.load(p).convert_alpha() for p in ARROW_FRAMES]


@cache
def sound(name):
    """A sound effect, or None if there's no audio (some browsers, headless runs)."""
    try:
        effect = pygame.mixer.Sound(SOUNDS.format(name))
        effect.set_volume(0.5)
        return effect
    except (pygame.error, FileNotFoundError):
        return None


def play(name):
    effect = sound(name)
    if effect:
        effect.play()


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def direction(vector):
    if abs(vector.x) > abs(vector.y):
        return "left" if vector.x < 0 else "right"
    return "up" if vector.y < 0 else "down"


class Walker:
    """Someone in the cutscene, walking a list of points. `pos` is the middle of their feet box."""

    BODY = 9  # feet box, for steering around walls

    def __init__(self, pos, speed, level, facing="down"):
        self.pos = pygame.Vector2(pos)
        self.level = level
        self.speed = speed
        self.facing = facing
        self.points = []
        self.moving = False
        self.visible = True

    def walk(self, *points):
        self.points += [pygame.Vector2(p) for p in points]

    @property
    def arrived(self):
        return not self.points

    def update(self, dt):
        self.moving = False
        if not self.points:
            return
        target = self.points[0]
        to_point = target - self.pos
        box = pygame.Rect(0, 0, self.BODY, self.BODY)
        box.center = target
        if not self.level.rect_hits_wall(box):  # doorways are in the wall: walk straight in
            heading = self.level.route(self.pos, target, self.BODY) - self.pos
            if heading.length_squared() and heading.length() < to_point.length():
                to_point = heading
        step = self.speed * dt
        if (target - self.pos).length() <= step:
            self.pos = self.points.pop(0)
        else:
            self.pos += to_point.normalize() * min(step, to_point.length())
        if to_point.length_squared():
            self.facing = direction(to_point)
        self.moving = True


class IntroCutscene(Scene):
    def __init__(self, game, next_scene):
        super().__init__(game)
        self.next_scene = next_scene  # built lazily: called when the cutscene ends
        run = game.current_run
        self.bag = run.backpack.bag.sprite
        # Not the room the fight is in: they walk out of this one into it.
        others = [i for i in range(len(game.levels)) if i != run.arena_index] or [run.arena_index]
        self.level = level = game.levels[others[0]]
        self.tiles = game.tiles[level.tileset["image"]]
        self.background = pygame.Surface(VIEW)
        draw_level(self.background, level, self.tiles)
        self.world = pygame.Surface(VIEW)
        self.canvas = pygame.Surface(ui.CANVAS_SIZE, pygame.SRCALPHA)
        self.hotspots = ui.Hotspots()

        ts = level.tile_size
        entrance = level.entrance if level.entrance is not None else level.knight_start - (0, 32)
        self.entrance = pygame.Vector2(entrance)
        self.exit = pygame.Vector2(level.exit_pos)
        # They meet just below the top wall, halfway between the doors.
        meet_y = self.entrance.y + 3 * ts
        mid_x = (self.entrance.x + self.exit.x) / 2
        # ...where the Helper has room to step aside (down) to let him by later.
        for dx in (0, -8, 8, -16, 16, -24, 24, -32, 32, -40, 40, -48, 48):
            box = pygame.Rect(0, 0, Walker.BODY + 4, Walker.BODY + 4)
            box.center = (mid_x + 12 + dx, meet_y + 16)
            if not level.rect_hits_wall(box):
                mid_x += dx
                break
        self.helper = Walker((mid_x + 12, meet_y), HELPER_SPEED, level, "up")
        self.knight = Walker(self.entrance, KNIGHT_SPEED, level, "down")
        self.knight.walk(self.entrance + (0, ts * 1.5), (mid_x - 12, meet_y))

        self.time = 0.0
        self.phase = "fade_in"  # fade_in, enter, talk, leave, fade_out
        self.phase_time = 0.0
        self.entrance_open = True
        self.exit_open = False
        self.line = -1  # index into SCRIPT while talking
        self.line_time = 0.0
        self.panel_time = 0.0  # how far the panel has slid in (0 hidden .. PANEL_SLIDE shown)
        self.surprise = 0.0  # the "!" over the Knight's head when he spots the Helper
        self.done = False
        play("door_open")

    # --- flow ---

    def set_phase(self, phase):
        self.phase, self.phase_time = phase, 0.0

    def finish(self):
        if not self.done:
            self.done = True
            self.game.change_scene(self.next_scene())

    def skip(self):
        play("choose_level")
        self.finish()

    def advance(self):
        """ENTER/click: show the whole line, or go to the next one."""
        if self.phase != "talk":
            return
        if self.typed() < len(SCRIPT[self.line][1]):
            self.line_time = 99.0
            return
        self.next_line()

    def next_line(self):
        self.line += 1
        self.line_time = 0.0
        if self.line >= len(SCRIPT):
            self.line = len(SCRIPT) - 1
            self.start_leaving()

    def start_leaving(self):
        self.set_phase("leave")
        self.exit_open = True
        play("door_open")
        doorstep = self.exit + (0, self.level.tile_size)
        # The Helper steps aside to let him stride past, then trudges after him.
        self.knight.walk(doorstep + (0, 6), doorstep, self.exit)
        for side in ((0, 16), (0, -16), (-14, 14)):  # down if there's room, else up
            box = pygame.Rect(0, 0, Walker.BODY + 4, Walker.BODY + 4)
            box.center = self.helper.pos + side
            if not self.level.rect_hits_wall(box):
                break
        self.helper.walk(self.helper.pos + side)
        self.helper_following = False

    def typed(self):
        return int(self.line_time * TYPE_SPEED)

    def handle_event(self, event):
        result = self.hotspots.handle(event)
        if result and result[0] == "click" and result[1] == "skip":
            self.skip()
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                self.skip()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                self.advance()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and not result:
            self.advance()

    def update(self, dt):
        self.time += dt
        self.phase_time += dt
        self.line_time += dt
        self.surprise = max(0.0, self.surprise - dt)
        knight, helper = self.knight, self.helper
        talking = self.phase == "talk"
        self.panel_time = min(PANEL_SLIDE, self.panel_time + dt) if talking else max(0.0, self.panel_time - dt)

        if self.phase == "fade_in":
            if self.phase_time >= FADE_TIME:
                self.set_phase("enter")
        elif self.phase == "enter":
            if knight.pos.y > self.entrance.y + self.level.tile_size and self.entrance_open:
                self.entrance_open = False  # it swings shut behind him
            if knight.facing == "right" and helper.facing == "up":
                helper.facing = "left"  # turns at the footsteps
                self.surprise = 0.8
            if knight.arrived:
                knight.facing = "right"
                self.set_phase("talk")
                self.next_line()
        elif self.phase == "leave":
            if not self.helper_following and helper.arrived and knight.pos.x > helper.pos.x + 12:
                self.helper_following = True
                doorstep = self.exit + (0, self.level.tile_size)
                helper.walk(doorstep + (0, 6), doorstep, self.exit)
            for walker, delay in ((knight, 0.3), (helper, 0.0)):
                if self.phase_time >= delay:
                    walker.update(dt)
                if walker.arrived and (walker is knight or self.helper_following):
                    walker.visible = False  # through the door
            if not knight.visible and not helper.visible:
                self.set_phase("fade_out")
                play("enter_level")
            return
        elif self.phase == "fade_out":
            if self.phase_time >= FADE_TIME:
                self.finish()
            return
        knight.update(dt)
        helper.update(dt)

    # --- drawing ---

    def knight_animation(self):
        k = self.knight
        if k.moving:
            return f"walk_{k.facing}"
        if self.phase == "talk" and SCRIPT[self.line][0] == KNIGHT:
            return SCRIPT[self.line][2]
        return f"idle_{k.facing}"

    def helper_image(self):
        h = self.helper
        if h.moving:
            name, time = f"walk_{h.facing}", self.time
        elif self.phase == "talk" and SCRIPT[self.line][0] == HELPER:
            name, time = SCRIPT[self.line][2], self.line_time
        else:
            name, time = f"idle_{h.facing}", self.time
        frames, fps, loop = helper_animations(self.bag)[name]
        if not loop:
            time %= len(frames) / fps + 0.5  # replay one-shot animations, with a beat between
        return helper_frame(self.bag, name, time)

    def draw(self, screen):
        world = self.world
        world.blit(self.background, (0, 0))
        if self.entrance_open:
            draw_open_door(world, self.tiles, self.entrance)
        if self.exit_open:
            draw_open_door(world, self.tiles, self.exit)

        knight, helper = self.knight, self.helper
        actors = []
        if knight.visible:
            actors.append((knight.pos.y + 7, knight, knight_frame(self.knight_animation(), self.time)))
        if helper.visible:
            actors.append((helper.pos.y + 5, helper, self.helper_image()))
        for feet, walker, image in sorted(actors, key=lambda a: a[0]):
            rect = image.get_rect(midbottom=(walker.pos.x, feet))
            world.blit(image, rect)
            # In a doorway they're half in the wall: hide what's above the door's top.
            if walker.pos.y < self.exit.y + 8 and self.phase == "leave":
                cover = pygame.Rect(rect.x, rect.y, rect.w, max(0, int(self.exit.y - 8 - rect.y)))
                world.blit(self.background, cover, cover)

        # The speaker gets a bobbing arrow over their head.
        if self.phase == "talk" and self.panel_time >= PANEL_SLIDE:
            speaker = knight if SCRIPT[self.line][0] == KNIGHT else helper
            frames = arrow_frames()
            arrow = frames[int(self.time * ARROW_FPS) % len(frames)]
            top = speaker.pos.y - (24 if speaker is knight else 20)
            world.blit(arrow, arrow.get_rect(midbottom=(speaker.pos.x, top)))
        if self.surprise:
            pop = ui.render_text("!", "gold")
            lift = 3 * ease_out((0.8 - self.surprise) / 0.15)
            world.blit(pop, pop.get_rect(midbottom=(knight.pos.x, knight.pos.y - 20 - lift)))

        screen.fill(ui.INK)
        x = WORLD_X * ui.UI_SCALE
        pygame.transform.scale(world, (VIEW[0] * WORLD_SCALE, VIEW[1] * WORLD_SCALE),
                               screen.subsurface((x, 0, VIEW[0] * WORLD_SCALE, VIEW[1] * WORLD_SCALE)))

        canvas = self.canvas
        canvas.fill((0, 0, 0, 0))
        self.hotspots.clear()
        for pos in ((14, 70), (290, 70)):
            ui.torch(canvas, pos, self.time)
        self.draw_panel(canvas)
        state = "p" if self.hotspots.pressed == "skip" else "n"
        ui.button(canvas, SKIP_RECT, "Skip", "stone", state)
        self.hotspots.add(SKIP_RECT, "skip")
        if self.phase == "talk":
            ui.draw_text(canvas, "ENTER next    ESC skip", (160, 171), anchor="midtop", alpha=150)

        # Fades to and from black.
        if self.phase == "fade_in":
            fade = 1 - self.phase_time / FADE_TIME
        elif self.phase == "fade_out":
            fade = self.phase_time / FADE_TIME
        else:
            fade = 0
        if fade > 0:
            shade = pygame.Surface(ui.CANVAS_SIZE, pygame.SRCALPHA)
            shade.fill((*ui.INK, round(255 * min(1, fade))))
            canvas.blit(shade, (0, 0))
        screen.blit(pygame.transform.scale_by(canvas, ui.UI_SCALE), (0, 0))

    def draw_panel(self, canvas):
        if self.panel_time <= 0 or self.line < 0:
            return
        slide = ease_out(self.panel_time / PANEL_SLIDE)
        rect = PANEL.move(0, round((1 - slide) * -(PANEL.bottom + 2)))
        ui.nine_slice(canvas, "panel9", rect)

        speaker, text, _ = SCRIPT[self.line]
        # Portrait in a little stone frame on the left.
        frame = pygame.Rect(rect.x + 7, rect.y + 7, 30, 30)
        ui.nine_slice(canvas, "button9_stone_n", frame)
        if speaker == KNIGHT:
            face = knight_frame("idle_down", self.time)
        else:
            face = helper_frame(self.bag, "idle_down", self.time)
        clip = canvas.get_clip()
        canvas.set_clip(frame.inflate(-4, -4))
        canvas.blit(face, face.get_rect(midbottom=(frame.centerx, frame.bottom - 1)))
        canvas.set_clip(clip)

        left = frame.right + 6
        ui.draw_text(canvas, NAMES[speaker], (left, rect.y + 7), "gold")
        acting = speaker == HELPER
        shown = self.typed()
        y = rect.y + 18
        for line in ui.wrap(text, TEXT_CHARS)[:3]:
            visible = line[:max(0, shown)]
            shown -= len(line) + 1
            if visible:
                ui.draw_text(canvas, visible, (left, y), alpha=170 if acting else 255)
            y += 9
        # A bouncing "more" arrow once the line has finished typing.
        if self.typed() >= len(text):
            frames = arrow_frames()
            arrow = frames[int(self.time * ARROW_FPS) % len(frames)]
            canvas.blit(arrow, arrow.get_rect(bottomright=(rect.right - 6, rect.bottom - 4)))
