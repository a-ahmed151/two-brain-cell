"""A room of the run: the Knight fights whatever's in it while the Helper digs gear
out of the bag and hands it over. Clear the room to move on."""

from functools import cache

import pygame

from game import ui
from game.enemies import ENEMIES, Enemy
from game.entities import HELPER_HP, Helper, Knight, Popup
from game.gear import draw_icon
from game.run import ROOM_REST, ROOMS
from game.scene import Scene

WORLD_SCALE = 3  # the world is drawn at native pixel-art size, then scaled up
VIEW = (320, 240)  # one arena; 960x720 on screen
HUD_SIZE = (80, 180)  # side panel on the UI canvas scale (4x), right of the world
CHEST_FRAMES = "assets/items and trap_animation/chest/chest_{}1.png"

EXIT_COLOR = (60, 170, 90)
HIGHLIGHT_COLOR = (120, 220, 255)
GOLD = (232, 177, 58)
SLOT_COLOR = (107, 78, 99)
HP_COLOR = (210, 60, 70)
DIM = 130
GLOAT_TIME = 2.5  # boss room: he poses this long before heading for the exit
BETRAYAL_DELAY = 2.5  # seconds of the Knight lying there before the ending
DEATH_DELAY = 1.0  # seconds before the "he's dead" banner, so you see what got him
ICON_FONT = ui.IconFont()

# Shown before the fight, for each kind of enemy in the room.
ADVICE = {
    "armored": "Armor: the Sword is weak. Pickaxe!",
    "skull": "Skulls hunt YOU. Stay near him.",
    "vampire": "Vampires heal on bite. Torch!",
    "count": "The Count calls skulls. Torch!",
}


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
        self.cleared = False
        self.gloat = 0.0  # boss room, after the fight
        # None while playing; otherwise "won" or "lost", shown as a banner: (title, lines).
        self.outcome = None
        self.banner = ("", [])
        self.death_time = 0.0

    # --- flow ---

    def handle_event(self, event):
        confirm = (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)) or \
            (event.type == pygame.MOUSEBUTTONUP and event.button == 1)
        if self.outcome:
            if confirm:
                self.leave()
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            from game.menus import IntroScene  # menus imports this module too
            self.game.change_scene(IntroScene(self.game))
        elif self.knight.dead:
            return
        elif event.key == pygame.K_SPACE and not self.knight.fighting and not self.cleared:
            self.knight.fighting = True
            self.knight.popup("TO GLORY!", GOLD)
        elif event.key == pygame.K_e:
            self.helper.action(self.knight)

    def leave(self):
        from game.menus import RewardScene, RunStartScene
        if self.outcome == "lost":
            self.game.current_run = None
            self.game.change_scene(RunStartScene(self.game))
            return
        run = self.run
        shrine = run.shrine_next()
        run.room += 1
        picks = 2 if self.knight.chest_opened else 1
        self.game.change_scene(RewardScene(self.game, picks=picks, shrine=shrine))

    def end(self, outcome, title, *lines):
        self.outcome = outcome
        self.banner = (title, lines)

    def room_clear(self):
        """Carry the Knight and the bag over into the next room."""
        knight, helper, run = self.knight, self.helper, self.run
        if helper.held:
            run.backpack.queue.insert(0, helper.held)  # back on top of the bag
            helper.held = None
        helper.digging = False
        run.knight_hp = min(knight.max_hp, knight.hp + ROOM_REST)  # he catches his breath
        run.knight_gear = [g for g in (knight.tool, knight.item) if g]
        title = "Room clear!"
        lines = [f"He rests: {run.knight_hp}/{knight.max_hp} HP"]
        if knight.chest_opened:
            lines.append("Chest! Two rewards this time.")
        lines.append("ENTER: continue")
        self.end("won", title, *lines)

    def update(self, dt):
        knight, helper = self.knight, self.helper
        self.time += dt
        chest = self.level.chest
        if self.outcome:
            knight.update(dt, self.level)  # keeps his victory/death animation going
            return
        helper.update(dt, pygame.key.get_pressed(), self.level)
        knight.update(dt, self.level, self.enemies, chest)
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
        if self.enemies or not knight.fighting:
            return

        if not self.run.boss_room:
            self.room_clear()
            return
        # The boss is dead. He'll take all the credit again... unless he never gets out.
        if not self.cleared:
            self.cleared = True
            knight.fighting = False
            knight.popup("Hah! My skill is unmatched.", GOLD)
            helper.backpack.queue.insert(0, "poison")
        self.gloat += dt
        if self.gloat >= GLOAT_TIME and knight.leaving is None:
            knight.leaving = pygame.Vector2(self.level.exit_pos)
        if knight.reached_exit:
            self.game.current_run = None
            self.end("lost", "Too late!", "He took the gold and the credit.", "Again.", "ENTER: new run")

    # --- drawing ---

    def draw(self, screen):
        knight, helper = self.knight, self.helper
        world = self.world
        world.blit(self.background, (0, 0))
        if self.level.chest is not None:
            image = chest_image(knight.chest_opened)
            world.blit(image, image.get_rect(center=self.level.chest))
        if self.cleared:
            door = pygame.Rect(0, 0, 13, 13)
            door.center = self.level.exit_pos
            pygame.draw.rect(world, EXIT_COLOR, door, 2)
        if helper.held and helper.in_range(knight) and not knight.dead:
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
        if self.outcome or tip:
            self.overlay.fill((0, 0, 0, 0))
            if self.outcome:
                self.draw_banner(self.overlay)
            else:
                self.draw_tip(self.overlay, tip)
            screen.blit(pygame.transform.scale_by(self.overlay, ui.UI_SCALE), (0, 0))

    def current_tip(self):
        if self.cleared and not self.knight.dead:
            return ["He'll take the credit again...", "There's Poison on top of the bag."]
        if self.knight.fighting:
            return None
        kinds = self.run.enemies
        lines = [f"Room {self.run.room + 1}: {enemy_summary(kinds)}"]
        lines += [ADVICE[k] for k in dict.fromkeys(kinds) if k in ADVICE]
        lines.append("Gear him up, then SPACE to fight.")
        return lines

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
        ui.draw_text(hud, f"{len(backpack.queue)}/{bag.slots}  dig {bag.extract_time}", (w // 2, 115), anchor="midtop")
        for slot in range(max(bag.slots, len(backpack.queue))):
            col, row = slot % 4, slot // 4
            gear = backpack.queue[slot] if slot < len(backpack.queue) else None
            draw_slot(hud, gear, (w // 2 - 24 + col * 16, 130 + row * 15), marked=slot == 0 and gear is not None)

        hints = ["E dig/give", "ESC quit"]
        if not knight.fighting and not self.cleared and not self.outcome:
            hints = ["SPACE fight!"] + hints
        for i, hint in enumerate(hints):
            ready = hint == "SPACE fight!"
            ui.draw_text(hud, hint, (w // 2, 155 + i * 8), "gold" if ready else "cream", anchor="midtop",
                         alpha=255 if ready else DIM)

    def draw_tip(self, overlay, lines):
        width = max(len(line) for line in lines) * ui.GLYPH_ADVANCE + 20
        rect = pygame.Rect(0, 4, max(width, 100), 12 + 10 * len(lines))
        rect.centerx = overlay.get_width() // 2
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
