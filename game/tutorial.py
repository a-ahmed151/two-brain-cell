"""The tour: a practice room that teaches the game one step at a time, then a few pages
on what can't be practised in one room (rewards, bags, who beats who, the road ahead).

Each step says what to do in a box and waits until it's done: it checks what happened,
not which key was pressed, so doing something early still counts. Nobody dies in the
tour. See "Tutorial" in GAME_DESIGN.md.
"""

from dataclasses import dataclass
from typing import Callable

import pygame

from game import audio, ui
from game.backpack import BAGS
from game.combat import GOLD, CombatScene
from game.enemies import ENEMIES, Enemy, enemy_icon
from game.entities import HELPER_HP, helper_frame
from game.gear import GEAR, draw_icon
from game.menus import CONFIRM_KEYS, DIM, LEFT_KEYS, RIGHT_KEYS, IntroScene, MenuScene, NoticeScene, RunStartScene
from game.run import ROOMS, RunState

ARENA = "Crypt"  # the practice room: it has a chest
BAG = "satchel"
KIT = ["pickaxe", "potion", "key"]  # in dig order; he starts with his Sword as usual
BEAT = 0.9  # seconds of "Nice!" between steps
WALK_DISTANCE = 30  # pixels the Helper must walk to pass the first step
HURT_HP = 14  # step "Items": he's hurt, below where he drinks a Potion
LOST_TIME = 3.0  # seconds the "that was the end" message stays up
ICON_FONT = ui.IconFont()


@dataclass
class Step:
    title: str
    lines: list
    done: Callable  # scene -> bool
    start: Callable | None = None  # scene -> None, when the step begins
    highlight: str | None = None  # a part of the side panel to point at: "bag", "hands" or "hearts"
    bottom: bool = False  # the box at the bottom of the room, to keep the top in view
    footer: str | None = None


def spawn(scene, *kinds, away_from_helper=False):
    """Monsters at the room's spawn points farthest from the Knight (or from the Helper),
    so there's a moment to see them coming."""
    who = pygame.Vector2(scene.helper.rect.center) if away_from_helper else scene.knight.pos
    spots = sorted(scene.level.spawns, key=lambda p: -p.distance_to(who))
    scene.enemies += [Enemy(kind, spots[i % len(spots)]) for i, kind in enumerate(kinds)]


def freeze_for_fight(scene):
    """The real "before the fight" screen: what's coming, then SPACE sends him in."""
    scene.run.rooms[0] = (scene.run.rooms[0][0], ["skeleton", "skeleton"])
    scene.started = False
    spawn(scene, "skeleton", "skeleton")


def hurt_knight(scene):
    knight = scene.knight
    if knight.hp > HURT_HP:
        knight.hp = HURT_HP
        knight.popup("Ouch!", (240, 90, 90))


def has(scene, gear):
    return scene.helper.held == gear or scene.knight.tool == gear or scene.knight.item == gear


STEPS = [
    Step("You are Player 2", ["Sir Knight fights. You carry the bag", "and hand him the right gear."],
         lambda s: s.read, footer="ENTER ok"),
    Step("Walk", ["WASD or the arrow keys."],
         lambda s: s.helper.pos.distance_to(s.level.helper_start) >= WALK_DISTANCE),
    Step("Send him in", ["He picks targets and swings himself.", "You never attack."],
         lambda s: s.started and not s.enemies, start=freeze_for_fight),
    Step("Dig", ["Armor! His Sword barely scratches it.", "E digs out the gold slot. Hold still."],
         lambda s: has(s, "pickaxe"), start=lambda s: spawn(s, "armored"), highlight="bag"),
    Step("Hand it over", ["Walk up to him and press E.", "His old Sword goes back in the bag."],
         lambda s: s.knight.tool == "pickaxe", highlight="hands"),
    Step("Right tool, right foe", ["The Pickaxe smashes armor.", "Each room shows what beats who."],
         lambda s: not s.enemies),
    Step("Run!", ["Skulls hunt YOU. You can't fight:", "run, you're faster. Lead it to him.",
                  "4 hearts per run. They never heal."],
         lambda s: not s.enemies, start=lambda s: spawn(s, "skull", away_from_helper=True), highlight="hearts"),
    Step("Items", ["He uses items by himself: a Potion", "when hurt, a Bomb when foes are near.",
                   "Hand him the Potion."],
         lambda s: "potion" in s.helper.handed and s.knight.item != "potion", start=hurt_knight,
         highlight="hands"),
    Step("The Key", ["The Key is YOURS. Dig it out, then", "press E at the chest for loot."],
         lambda s: s.chest_opened),
    Step("Way out", ["Room clear! Walk out the open door.", "He follows you."],
         lambda s: False, bottom=True),  # room_clear() ends the tour
]
HUD_HIGHLIGHT = {"hands": (-17, 45, 34, 17), "hearts": (-22, 70, 44, 12), "bag": (-34, 104, 68, 48)}


class TutorialScene(CombatScene):
    pause_options = ("Resume", "Leave tour")
    first_run_hints = False

    def __init__(self, game):
        run = game.current_run = RunState(BAG, game.levels, seed=0)
        arena = next((i for i, level in enumerate(game.levels) if level.name == ARENA), 0)
        run.rooms[0] = (arena, [])
        run.backpack.queue = list(KIT)
        super().__init__(game)
        self.started = True  # the Helper walks around from the start; SPACE comes later
        self.step = 0
        self.read = False  # the first step: ENTER
        self.passed = None  # seconds since this step was done
        self.lost_left = 0.0

    # --- flow ---

    @property
    def current(self):
        return STEPS[self.step]

    def handle_event(self, event):
        if self.step == 0 and not self.paused and event.type == pygame.KEYDOWN and event.key in CONFIRM_KEYS:
            self.read = True
            return
        super().handle_event(event)

    def update(self, dt):
        super().update(dt)
        self.lost_left = max(0.0, self.lost_left - dt)
        if self.paused or self.outcome:
            return
        if self.passed is None:
            if self.current.done(self):
                self.passed = 0.0
                audio.play("choose_level")
                self.knight.popup("Nice!", GOLD, pygame.Vector2(self.helper.rect.center) + (0, -14))
            return
        self.passed += dt
        if self.passed >= BEAT and self.step < len(STEPS) - 1:
            self.step += 1
            self.passed = None
            if self.current.start:
                self.current.start(self)

    def room_won(self, dt):
        return self.step == len(STEPS) - 1  # the door stays shut until the last step

    def room_clear(self):
        self.game.current_run = None
        self.game.change_scene(TutorialEndScene(self.game))

    def end(self, outcome, title, *lines):
        """Nobody dies in the tour: patch them up and carry on."""
        knight, helper = self.knight, self.helper
        helper.hp = HELPER_HP
        if knight.dead:
            knight.dead = False
            knight.hp = knight.max_hp
            knight.fighting = bool(self.enemies)
            knight.speech = None
        self.death_time = 0.0
        self.lost_left = LOST_TIME

    def hud_title(self):
        return "Tutorial"

    def clear_line(self):
        return "I taught you well."

    # --- drawing ---

    def current_tip(self):
        return [self.current.title]  # draw_tip draws the whole step

    def draw_tip(self, overlay, lines, bottom=False):
        step = self.current
        if self.lost_left:
            ui.hint_panel(overlay, "In a real run, that's the end!", ["The tour patched you up."])
            return
        title = "Nice!" if self.passed is not None else f"{self.step + 1}/{len(STEPS)}  {step.title}"
        ui.hint_panel(overlay, title, step.lines, step.footer, top=not step.bottom, width=37,
                      alpha=DIM if self.passed is not None else 255)

    def draw_floor(self, world):
        if self.current.title == "The Key" and not self.chest_opened and self.pulse:
            pygame.draw.circle(world, GOLD, self.level.chest, 12, 1)

    @property
    def pulse(self):
        return int(self.time * 3) % 2 == 0

    def draw_hud(self, hud):
        super().draw_hud(hud)
        area = HUD_HIGHLIGHT.get(self.current.highlight)
        if area and self.passed is None and self.pulse:
            x, y, w, h = area
            pygame.draw.rect(hud, GOLD, (hud.get_width() // 2 + x, y, w, h), 1)


class TutorialEndScene(MenuScene):
    """What the practice room can't show, a page at a time."""

    PAGES = ["Between rooms", "Pick your bag", "Who beats who", "The road ahead"]
    BACK_RECT = pygame.Rect(76, 152, 80, 16)
    NEXT_RECT = pygame.Rect(164, 152, 80, 16)
    WHO = [  # enemy, what it's about
        ("skeleton", "Basic."),
        ("armored", "Sword is weak."),
        ("skull", "Hunts YOU."),
        ("vampire", "Heals itself."),
        ("count", "Calls skulls."),
    ]

    def __init__(self, game):
        super().__init__(game)
        self.page = 0

    @property
    def last(self):
        return self.page == len(self.PAGES) - 1

    def turn(self, step):
        if self.last and step > 0:
            self.game.change_scene(NoticeScene(self.game))  # start a run
            return
        self.page = max(0, self.page + step)

    def on_click(self, key):
        self.turn(-1 if key == "back" else 1)

    def on_key(self, key):
        if key in LEFT_KEYS:
            self.turn(-1)
        elif key in RIGHT_KEYS or key in CONFIRM_KEYS:
            self.turn(1)
        elif key == pygame.K_ESCAPE:
            self.game.change_scene(IntroScene(self.game))

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, self.PAGES[self.page], (160, 15), "gold", scale=2, anchor="center")
        ui.draw_text(canvas, f"{self.page + 1}/{len(self.PAGES)}", (314, 6), anchor="topright", alpha=DIM)
        getattr(self, f"draw_page_{self.page}")(canvas)
        if self.page:
            ui.button(canvas, self.BACK_RECT, "Back", "stone", self.state("back", False))
            self.hotspots.add(self.BACK_RECT, "back")
        ui.button(canvas, self.NEXT_RECT, "Start a run" if self.last else "Next", "red", self.state("next", True))
        self.hotspots.add(self.NEXT_RECT, "next")
        ui.draw_text(canvas, "A/D page   ENTER next   ESC menu", (160, 171), anchor="midtop", alpha=DIM)

    def lines(self, canvas, lines, top):
        for i, (line, color) in enumerate(lines):
            ui.draw_text(canvas, line, (160, top + i * 12), color, anchor="midtop")

    def draw_page_0(self, canvas):
        self.lines(canvas, [
            ("After each room, pick 1 of 3 gear.", "cream"),
            ("Then sort: click two slots to swap.", "cream"),
            ("Bag order is dig order: gold slot first.", "gold"),
            ("The last two slots are his hands:", "cream"),
            ("his tool, and his item.", "cream"),
            ("He keeps his tool, and rests 5 HP.", "cream"),
            ("Your hearts never come back.", "gold"),
        ], 40)

    def draw_page_1(self, canvas):
        blurbs = RunStartScene.BLURBS
        for i, (bag_id, bag) in enumerate(BAGS.items()):
            rect = pygame.Rect(18 + i * 98, 30, 90, 80)
            ui.nine_slice(canvas, "button9_stone_n", rect)
            helper = helper_frame(bag.sprite, "idle_down", self.time)
            canvas.blit(helper, helper.get_rect(midbottom=(rect.centerx, rect.y + 24)))
            ui.draw_text(canvas, bag.name, (rect.centerx, rect.y + 26), "gold", anchor="midtop")
            ui.draw_text(canvas, f"{bag.slots} slots", (rect.centerx, rect.y + 36), anchor="midtop")
            ui.draw_text(canvas, f"dig {bag.extract_time} sec", (rect.centerx, rect.y + 45), anchor="midtop")
            for j, line in enumerate(ui.wrap(blurbs[bag_id], 14)[:2]):
                ui.draw_text(canvas, line, (rect.centerx, rect.y + 56 + j * 9), anchor="midtop", alpha=DIM + 60)
        self.lines(canvas, [
            ("Big bag: ready for anything, slow dig.", "cream"),
            ("Small bag: fast, but guess what's next.", "cream"),
        ], 118)

    def draw_page_2(self, canvas):
        for i, (kind, note) in enumerate(self.WHO):
            y = 34 + i * 17
            enemy = ENEMIES[kind]
            icon = enemy_icon(kind)
            canvas.blit(icon, icon.get_rect(center=(48, y + 4)))
            ui.draw_text(canvas, enemy.name, (60, y), "gold")
            draw_icon(canvas, ICON_FONT, enemy.counter, (132, y + 3), size=12)
            ui.draw_text(canvas, GEAR[enemy.counter].name, (141, y))
            ui.draw_text(canvas, note, (196, y), alpha=DIM + 60)
        self.lines(canvas, [
            ("Shield: hits all near. He takes only 1.", "cream"),
            ("Bomb: thrown when foes get close.", "cream"),
        ], 122)

    def draw_page_3(self, canvas):
        self.lines(canvas, [
            (f"{ROOMS - 1} rooms, then the boss: the Count.", "cream"),
            ("Rooms 3 and 6 end with a blessing.", "cream"),
            ("Before room 8, a sealed door: the Trial.", "cream"),
            ("Optional. Big risk, big reward.", "cream"),
            ("If he dies, or you do, the run is over.", "gold"),
            ("", "cream"),
            ("He'll take the gold and the glory...", "cream"),
            ("unless you check the bag at the end.", "gold"),
        ], 40)
