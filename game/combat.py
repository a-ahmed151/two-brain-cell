"""A room of the run: the Knight fights whatever's in it while the Helper digs gear
out of the bag and hands it over. Clear the room to move on."""

from collections import defaultdict
from functools import cache

import pygame

from game import ui
from game.enemies import ENEMIES, Enemy, draw_lineup
from game.entities import HELPER_HP, Helper, Knight, Popup
from game.gear import GEAR, ITEM, TOOL, draw_icon
from game.run import ROOM_REST, ROOMS
from game.scene import Scene

WORLD_SCALE = 3  # the world is drawn at native pixel-art size, then scaled up
VIEW = (320, 240)  # one arena; 960x720 on screen
HUD_SIZE = (80, 180)  # side panel on the UI canvas scale (4x), right of the world
CHEST_FRAMES = "assets/items and trap_animation/chest/chest_{}1.png"

HIGHLIGHT_COLOR = (120, 220, 255)
GOLD = (232, 177, 58)
SLOT_COLOR = (107, 78, 99)
HP_COLOR = (210, 60, 70)
DIM = 130
GLOAT_TIME = 2.5  # boss room: he poses this long before heading for the exit
DOORSTEP_REACH = 10  # how close the Helper must get to the open exit's doorstep to leave
OPEN_DOOR = (79, 47, 48)  # tileset gids: dark doorway, left door leaf, right door leaf (drawn flipped)
ARROW_FRAMES = [f"assets/interface/arrow_{i}.png" for i in range(1, 5)]  # point down
ARROW_FPS = 8
BETRAYAL_DELAY = 2.5  # seconds of the Knight lying there before the ending
DEATH_DELAY = 1.0  # seconds before the "he's dead" banner, so you see what got him
ICON_FONT = ui.IconFont()

# Shown before the fight, for each kind of enemy in the room.
ADVICE = {
    "armored": "Armor: the Sword is weak. Pickaxe!",
    "skull": "Skulls hunt YOU. Stay near him.",
    "vampire": "Vampires heal. Torch stops it!",
    "count": "The Count calls skulls. Torch!",
}


PAUSE_OPTIONS = ("Resume", "Quit run")


def quit_run(game):
    """Give up on the run and go back to the main menu."""
    from game.menus import IntroScene  # menus imports this module too
    game.current_run = None
    game.change_scene(IntroScene(game))


def draw_level(surface, level, tiles):
    ts = level.tile_size
    surface.fill((0, 0, 0))
    for layer in (level.floor, level.wall_tiles, level.decor):
        for row in range(level.height):
            for col in range(level.width):
                gid = layer[row][col]
                if gid:
                    surface.blit(tiles[gid], (col * ts, row * ts))


@cache
def arrow_frames():
    """The bobbing arrow under the open exit, turned to point up at it."""
    return [pygame.transform.rotate(pygame.image.load(p).convert_alpha(), 180) for p in ARROW_FRAMES]


def draw_open_door(surface, tiles, center):
    """Draw the two-tile exit door, opened, centred on `center` (the door's middle)."""
    void, left, right = (tiles[g] for g in OPEN_DOOR)
    for i, leaf in ((0, left), (1, pygame.transform.flip(right, True, False))):
        pos = (center.x - 16 + i * 16, center.y - 8)
        surface.blit(void, pos)
        surface.blit(leaf, pos)


@cache
def chest_image(opened):
    return pygame.image.load(CHEST_FRAMES.format("open_" if opened else "")).convert_alpha()


def draw_slot(surface, gear, center, size=12, marked=False):
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if gear:
        draw_icon(surface, ICON_FONT, gear, center, size=size)
    else:
        pygame.draw.rect(surface, SLOT_COLOR, rect, 1)
    if marked:
        pygame.draw.rect(surface, GOLD, rect.inflate(4, 4), 1)


def enemy_summary(kinds):
    counts = {}
    for kind in kinds:
        counts[kind] = counts.get(kind, 0) + 1
    return ", ".join(f"{n} {ENEMIES[k].name}" for k, n in counts.items())


class CombatScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        run = self.run = game.current_run
        self.level = game.levels[run.arena_index]
        self.tiles = game.tiles[self.level.tileset["image"]]
        self.background = pygame.Surface(VIEW)
        draw_level(self.background, self.level, self.tiles)
        self.world = pygame.Surface(VIEW)
        self.world_font = pygame.font.Font(None, 12)
        self.hud = pygame.Surface(HUD_SIZE)
        view_on_screen = (VIEW[0] * WORLD_SCALE, VIEW[1] * WORLD_SCALE)
        self.overlay = pygame.Surface((view_on_screen[0] // ui.UI_SCALE, view_on_screen[1] // ui.UI_SCALE),
                                      pygame.SRCALPHA)
        self.time = 0.0

        self.knight = Knight(self.level.knight_start, run.knight_hp, run.knight_max_hp, run.knight_gear)
        self.helper = Helper(self.level.helper_start, run.backpack)
        spawns = self.level.spawns
        self.enemies = [Enemy(kind, spawns[i % len(spawns)]) for i, kind in enumerate(run.enemies)]
        self.started = False  # everything waits for SPACE
        self.chest_opened = False  # the Helper opens it with a Key
        self.cleared = False
        self.gloat = 0.0  # boss room, after the fight
        # None while playing; otherwise "won" or "lost", shown as a banner: (title, lines).
        self.outcome = None
        self.banner = ("", [])
        self.death_time = 0.0
        self.paused = False
        self.pause_choice = 0
        self.overlay_hotspots = ui.Hotspots()  # the pause menu, on the overlay
        self.hud_hotspots = ui.Hotspots(offset=(VIEW[0] * WORLD_SCALE, 0))

    # --- flow ---

    def handle_event(self, event):
        if self.paused:
            self.pause_event(event)
            return
        result = self.hud_hotspots.handle(event)
        if result and result[0] == "click" and result[1] == "pause" and not self.outcome:
            self.paused = True
            return
        confirm = (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)) or \
            (event.type == pygame.MOUSEBUTTONUP and event.button == 1)
        if self.outcome:
            if confirm:
                self.leave()
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.paused, self.pause_choice = True, 0
        elif self.knight.dead:
            return
        elif not self.started:
            if event.key == pygame.K_SPACE:
                self.started = True
                self.knight.fighting = True
                self.knight.popup("TO GLORY!", GOLD)
        elif event.key == pygame.K_e:
            if self.helper.action(self.knight, self.closed_chest()) == "chest":
                self.open_chest()

    def open_chest(self):
        """A random item, to the end of the bag. It always fits: the Key's slot is free."""
        self.chest_opened = True
        loot = self.run.roll_chest()
        self.run.backpack.put_back(loot)
        self.knight.popup(f"{GEAR[loot].name}!", GOLD, self.level.chest + (0, -12))

    def pause_event(self, event):
        result = self.overlay_hotspots.handle(event)
        if result:
            kind, choice = result
            self.pause_choice = choice
            if kind == "click":
                self.choose_pause()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.paused = False
            elif event.key in (pygame.K_w, pygame.K_UP, pygame.K_s, pygame.K_DOWN):
                self.pause_choice = 1 - self.pause_choice
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.choose_pause()

    def choose_pause(self):
        if PAUSE_OPTIONS[self.pause_choice] == "Resume":
            self.paused = False
        else:
            quit_run(self.game)

    def closed_chest(self):
        return None if self.chest_opened else self.level.chest

    def leave(self):
        from game.menus import RewardScene, RunStartScene
        if self.outcome == "lost":
            self.game.current_run = None
            self.game.change_scene(RunStartScene(self.game))
            return
        run = self.run
        shrine = run.shrine_next()
        run.room += 1
        self.game.change_scene(RewardScene(self.game, shrine=shrine))

    def end(self, outcome, title, *lines):
        self.outcome = outcome
        self.banner = (title, lines)

    def room_clear(self):
        """The Helper walked out of the open exit. Carry the Knight and the bag over into
        the next room: gear the Helper is still holding, and his unused item, go to the
        back of the bag; he keeps his tool."""
        knight, helper, run = self.knight, self.helper, self.run
        if helper.held:
            run.backpack.put_back(helper.held)
            helper.held = None
        helper.digging = False
        if knight.item and not run.backpack.full:
            run.backpack.put_back(knight.item)
            knight.item = None
        run.knight_hp = min(knight.max_hp, knight.hp + ROOM_REST)  # he catches his breath
        run.hands = {TOOL: knight.tool, ITEM: knight.item}
        self.outcome = "won"  # nothing more happens in this room
        self.leave()

    def update(self, dt):
        if self.paused:
            return
        knight, helper = self.knight, self.helper
        self.time += dt
        if self.outcome:
            knight.update(dt, self.level)  # keeps his victory/death animation going
            return
        if not self.started:
            # Frozen until SPACE; only the idle animations play.
            helper.update(dt, defaultdict(bool), self.level)
            knight.update(dt, self.level)
            for enemy in self.enemies:
                enemy.time += dt
            return
        helper.update(dt, pygame.key.get_pressed(), self.level)
        knight.update(dt, self.level, self.enemies)
        for enemy in list(self.enemies):
            summon = enemy.update(dt, knight, helper, self.level, self.enemies)
            if summon:
                self.enemies.append(Enemy(summon, enemy.pos + (0, 10)))
        for enemy in self.enemies:
            if enemy.dead:
                knight.popups.append(Popup(enemy.pos + (0, -6), "X", (200, 200, 200)))
        self.enemies = [e for e in self.enemies if not e.dead]

        if knight.dead:
            self.death_time += dt
            poisoned = knight.death_cause == "poison"
            if self.death_time < (BETRAYAL_DELAY if poisoned else DEATH_DELAY):
                return
            if poisoned:
                from game.menus import EndingScene
                self.game.current_run = None
                self.game.change_scene(EndingScene(self.game))
            else:
                self.end("lost", "He's dead.", f"The run ends in room {self.run.room + 1}.", "ENTER: new run")
            return
        if not helper.alive:
            self.end("lost", "You're dead.", "Who carries his stuff now?", "ENTER: new run")
            return
        if self.enemies:
            return

        if not self.cleared:
            # The exit opens. There's time to open the chest before walking out.
            self.cleared = True
            knight.fighting = False
            if self.run.boss_room:
                knight.popup("Hah! My skill is unmatched.", GOLD)
                helper.backpack.queue.insert(0, "poison")
            else:
                knight.popup("Hah! Too easy.", GOLD)
        if not self.run.boss_room:
            if pygame.Vector2(helper.rect.center).distance_to(self.level.doorstep) <= DOORSTEP_REACH:
                self.room_clear()
            return
        # The boss is dead. He'll take all the credit again... unless he never gets out.
        self.gloat += dt
        if self.gloat >= GLOAT_TIME and knight.leaving is None:
            knight.leaving = pygame.Vector2(self.level.doorstep)
        if knight.reached_exit:
            self.game.current_run = None
            self.end("lost", "Too late!", "He took the gold and the credit.", "Again.", "ENTER: new run")

    # --- drawing ---

    def draw(self, screen):
        knight, helper = self.knight, self.helper
        world = self.world
        world.blit(self.background, (0, 0))
        if self.level.chest is not None:
            image = chest_image(self.chest_opened)
            world.blit(image, image.get_rect(center=self.level.chest))
        if self.cleared:
            draw_open_door(world, self.tiles, self.level.exit_pos)
            if not self.run.boss_room:
                frames = arrow_frames()
                arrow = frames[int(self.time * ARROW_FPS) % len(frames)]
                world.blit(arrow, arrow.get_rect(midtop=self.level.doorstep + (0, 6)))
        if helper.held and GEAR[helper.held].helper_only:
            chest = self.closed_chest()
            if chest is not None and helper.near(chest):
                pygame.draw.circle(world, HIGHLIGHT_COLOR, chest, 10, 1)
        elif helper.held and helper.in_range(knight) and not knight.dead:
            pygame.draw.circle(world, HIGHLIGHT_COLOR, knight.pos, 10, 1)

        # Draw whoever's feet are lower on screen last, so they overlap correctly.
        actors = [(knight.feet, knight.draw), (helper.rect.bottom + 1, helper.draw)]
        actors += [(e.feet, lambda s, f, e=e: e.draw(s)) for e in self.enemies]
        for _, draw in sorted(actors, key=lambda a: a[0]):
            draw(world, ICON_FONT)
        for popup in knight.popups:
            text = self.world_font.render(popup.text, False, popup.color)
            text.set_alpha(round(255 * (1 - popup.age / Popup.LIFE)))
            world.blit(text, text.get_rect(center=popup.pos))

        view_on_screen = (VIEW[0] * WORLD_SCALE, VIEW[1] * WORLD_SCALE)
        pygame.transform.scale(world, view_on_screen, screen.subsurface((0, 0, *view_on_screen)))

        self.draw_hud(self.hud)
        hud_x = view_on_screen[0]
        screen.blit(pygame.transform.scale(self.hud, (screen.get_width() - hud_x, screen.get_height())), (hud_x, 0))

        tip = self.current_tip()
        if self.outcome or tip or not self.started or self.paused:
            self.overlay.fill((0, 0, 0, 0))
            self.overlay_hotspots.clear()
            if self.paused:
                self.draw_pause(self.overlay)
            elif self.outcome:
                self.draw_banner(self.overlay)
            elif not self.started:
                self.draw_start(self.overlay)
            else:
                self.draw_tip(self.overlay, tip, bottom=True)
            screen.blit(pygame.transform.scale_by(self.overlay, ui.UI_SCALE), (0, 0))

    def draw_pause(self, overlay):
        overlay.fill((0, 0, 0, 150))
        rect = pygame.Rect(0, 0, 120, 82)
        rect.center = overlay.get_rect().center
        ui.nine_slice(overlay, "panel9", rect)
        ui.draw_text(overlay, "Paused", (rect.centerx, rect.y + 10), "gold", scale=2, anchor="midtop")
        for i, label in enumerate(PAUSE_OPTIONS):
            button = pygame.Rect(0, rect.y + 34 + i * 20, 84, 16)
            button.centerx = rect.centerx
            selected = i == self.pause_choice
            state = "p" if self.overlay_hotspots.pressed == i else ("h" if selected else "n")
            ui.button(overlay, button, label, "red" if i else "stone", state)
            if selected:
                pygame.draw.rect(overlay, GOLD, button.inflate(4, 4), 1)
            self.overlay_hotspots.add(button, i)

    def current_tip(self):
        if not self.cleared or self.knight.dead:
            return None
        # One line, so it sits on the bottom wall and keeps the room (and the chest) in view.
        if self.run.boss_room:
            return ["Credit again? There's Poison in the bag."]
        if self.closed_chest() is not None and "key" in self.helper.backpack.queue + [self.helper.held]:
            return ["Clear! Open the chest, then exit."]
        return ["Clear! Walk out the open door."]

    def draw_start(self, overlay):
        """Before the fight: what's in the room, over a dimmed view, until SPACE."""
        overlay.fill((0, 0, 0, 120))
        kinds = self.run.enemies
        title = "Boss" if self.run.boss_room else f"Room {self.run.room + 1}"
        lines = [enemy_summary(kinds)] + [ADVICE[k] for k in dict.fromkeys(kinds) if k in ADVICE]
        width = max(len(line) for line in lines) * ui.GLYPH_ADVANCE + 20
        rect = pygame.Rect(0, 0, max(width, 140), 80 + 10 * len(lines))
        rect.center = overlay.get_rect().center
        ui.nine_slice(overlay, "panel9", rect)
        ui.draw_text(overlay, title, (rect.centerx, rect.y + 10), "gold", scale=2, anchor="midtop")
        draw_lineup(overlay, kinds, (rect.centerx, rect.y + 39))
        for i, line in enumerate(lines):
            ui.draw_text(overlay, line, (rect.centerx, rect.y + 54 + i * 10), anchor="midtop")
        pulse = 255 if int(self.time * 2) % 2 == 0 else 140
        ui.draw_text(overlay, "Press SPACE to start", (rect.centerx, rect.bottom - 16), "gold", anchor="midtop",
                     alpha=pulse)

    def draw_hud(self, hud):
        knight, helper = self.knight, self.helper
        backpack = helper.backpack
        w = hud.get_width()
        ui.nine_slice(hud, "panel9", hud.get_rect())
        room = "Boss" if self.run.boss_room else f"Room {self.run.room + 1}/{ROOMS}"
        ui.draw_text(hud, room, (w // 2, 8), "gold", anchor="midtop")

        ui.draw_text(hud, "Knight", (w // 2, 20), anchor="midtop", alpha=DIM)
        bar = pygame.Rect(w // 2 - 25, 30, 50, 4)
        pygame.draw.rect(hud, SLOT_COLOR, bar)
        pygame.draw.rect(hud, HP_COLOR, (bar.x, bar.y, round(bar.w * knight.hp / knight.max_hp), bar.h))
        ui.draw_text(hud, f"{knight.hp}/{knight.max_hp}", (w // 2, 36), anchor="midtop")
        draw_slot(hud, knight.tool, (w // 2 - 9, 53))
        draw_slot(hud, knight.item, (w // 2 + 9, 53))

        ui.draw_text(hud, "Helper", (w // 2, 64), anchor="midtop", alpha=DIM)
        for i in range(HELPER_HP):
            heart = pygame.Rect(w // 2 - 3 - 5 * (HELPER_HP - 1) + i * 10, 74, 6, 6)
            pygame.draw.rect(hud, HP_COLOR if i < helper.hp else SLOT_COLOR, heart, border_radius=2)
        draw_slot(hud, helper.held, (w // 2, 90))
        if helper.digging:
            progress = 1 - helper.dig_left / backpack.bag.extract_time
            bar = pygame.Rect(w // 2 - 15, 99, 30, 3)
            pygame.draw.rect(hud, SLOT_COLOR, bar)
            pygame.draw.rect(hud, GOLD, (bar.x, bar.y, round(bar.w * progress), bar.h))

        bag = backpack.bag
        ui.draw_text(hud, bag.name, (w // 2, 106), "gold", anchor="midtop")
        ui.draw_text(hud, f"{len(backpack.queue)}/{bag.slots} dig {bag.extract_time}", (w // 2, 115), anchor="midtop")
        for slot in range(max(bag.slots, len(backpack.queue))):
            col, row = slot % 4, slot // 4
            gear = backpack.queue[slot] if slot < len(backpack.queue) else None
            draw_slot(hud, gear, (w // 2 - 24 + col * 16, 130 + row * 15), marked=slot == 0 and gear is not None)

        hints = ["E dig/give", "ESC pause"]
        if helper.held and GEAR[helper.held].helper_only:
            chest = self.closed_chest()
            hints[0] = "E chest" if chest is not None and helper.near(chest) else "E to bag"
        if not self.started and not self.outcome:
            hints = ["SPACE start"] + hints
        self.hud_hotspots.clear()
        for i, hint in enumerate(hints):
            ready = hint == "SPACE start"
            rect = ui.draw_text(hud, hint, (w // 2, 155 + i * 8), "gold" if ready else "cream", anchor="midtop",
                                alpha=255 if ready else DIM)
            if hint == "ESC pause":
                self.hud_hotspots.add(rect.inflate(4, 2), "pause")  # click it to pause, too

    def draw_tip(self, overlay, lines, bottom=False):
        width = max(len(line) for line in lines) * ui.GLYPH_ADVANCE + 20
        rect = pygame.Rect(0, 4, max(width, 100), 12 + 10 * len(lines))
        rect.centerx = overlay.get_width() // 2
        if bottom:
            rect.bottom = overlay.get_height() - 4  # keeps the doors in the top wall in view
        ui.nine_slice(overlay, "panel9", rect)
        for i, line in enumerate(lines):
            ui.draw_text(overlay, line, (rect.centerx, rect.y + 7 + i * 10), "gold" if i == 0 else "cream",
                         anchor="midtop")

    def draw_banner(self, overlay):
        title, lines = self.banner
        rect = pygame.Rect(0, 0, 200, 40 + 10 * len(lines))
        rect.center = overlay.get_rect().center
        ui.nine_slice(overlay, "panel9", rect)
        ui.draw_text(overlay, title, (rect.centerx, rect.y + 12), "gold", scale=2, anchor="midtop")
        for i, line in enumerate(lines):
            ui.draw_text(overlay, line, (rect.centerx, rect.y + 32 + i * 10), anchor="midtop")
