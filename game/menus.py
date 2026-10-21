"""The menu scenes: loading, intro (main menu), run start (pick a bag), rewards between rooms and the ending.

All of them are drawn on the UI kit's 320x180 canvas and scaled up to the window.
Keyboard and mouse both work: the mouse hovers/clicks, the keyboard moves the selection.
"""

import os

import pygame

from game import story, ui
from game.backpack import BAGS
from game.combat import CombatScene, quit_run
from game.cutscene import IntroCutscene
from game.enemies import draw_lineup
from game.entities import helper_frame, knight_frame
from game.gear import GEAR, ITEM, TOOL, draw_icon
from game.level import load_level, load_tiles
from game.enemies import ENEMIES
from game.run import ROOMS, SHRINE_HEAL, STARTING_KIT, TRIAL_ROOM, WAVES, RunState
from game.scene import Scene

LEVELS_DIR = "levels"
DIM = 130  # alpha for secondary text
GOLD = (232, 177, 58)
ICON_FONT = ui.IconFont()

UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE)


def layout_feet(x, y):
    """The UI layout places the Knight as a 32x32 frame by its top-left; this is where his feet go."""
    return x + 16, y + 32


class MenuScene(Scene):
    """Shared plumbing: a canvas, mouse hotspots and a clock for animations."""

    def __init__(self, game):
        super().__init__(game)
        self.canvas = pygame.Surface(ui.CANVAS_SIZE)
        self.hotspots = ui.Hotspots()
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def handle_event(self, event):
        result = self.hotspots.handle(event)
        if result:
            kind, key = result
            (self.on_hover if kind == "hover" else self.on_click)(key)
        elif event.type == pygame.KEYDOWN:
            self.on_key(event.key)

    def on_hover(self, key):
        pass

    def on_click(self, key):
        pass

    def on_key(self, key):
        pass

    def draw(self, screen):
        self.hotspots.clear()
        self.draw_canvas(self.canvas)
        ui.present(self.canvas, screen)

    def draw_canvas(self, canvas):
        pass

    def state(self, key, selected):
        """Sprite state for a widget: p(ressed), h(over/selected) or n(ormal)."""
        if self.hotspots.pressed == key:
            return "p"
        return "h" if selected else "n"

    def draw_torches(self, canvas, positions):
        for x, y in positions:
            ui.torch(canvas, (x, y), self.time)


class LoadingScene(MenuScene):
    """Shows "Loading..." for a frame, then loads every level and tileset."""

    def __init__(self, game):
        super().__init__(game)
        self.shown = False

    def update(self, dt):
        if not self.shown:
            return  # draw once before blocking on the loading
        for name in sorted(os.listdir(LEVELS_DIR)):
            if not name.endswith(".tmj"):
                continue
            level = load_level(os.path.join(LEVELS_DIR, name))
            image = level.tileset["image"]
            if image not in self.game.tiles:
                self.game.tiles[image] = load_tiles(level.tileset)
            if name.startswith("trial"):
                self.game.trial_level = level
            else:
                self.game.levels.append(level)
        self.game.change_scene(IntroScene(self.game))

    def draw_canvas(self, canvas):
        canvas.fill(ui.INK)
        ui.draw_text(canvas, "Loading...", (160, 90), scale=2, anchor="center")
        self.shown = True


class IntroScene(MenuScene):
    """The title screen / main menu."""

    BUTTONS = ("play", "levels", "quit")  # the kit also has SETTINGS; there's nothing to set
    BUTTON_X, BUTTON_TOP, BUTTON_GAP = 112, 60, 23
    KNIGHT_SPEED = 30

    def __init__(self, game):
        super().__init__(game)
        self.selected = 0

    def on_hover(self, key):
        self.selected = self.BUTTONS.index(key)

    def on_click(self, key):
        self.activate(key)

    def on_key(self, key):
        if key in UP_KEYS:
            self.selected = (self.selected - 1) % len(self.BUTTONS)
        elif key in DOWN_KEYS:
            self.selected = (self.selected + 1) % len(self.BUTTONS)
        elif key in CONFIRM_KEYS:
            self.activate(self.BUTTONS[self.selected])
        elif key == pygame.K_ESCAPE:
            self.game.quit()

    def activate(self, button):
        if button == "play":
            self.game.change_scene(NoticeScene(self.game))
        elif button == "levels":
            self.game.change_scene(RoomSelectScene(self.game))
        elif button == "quit":
            self.game.quit()

    def draw_canvas(self, canvas):
        layout = ui.layout("main")
        canvas.blit(ui.background("main_bg"), (0, 0))
        ui.draw_text(canvas, "Player 2", (160, 18), "gold", scale=2, anchor="center")
        self.draw_torches(canvas, layout["torches"])

        # The Knight paces back and forth along the floor.
        k = layout["knight"]
        span = k["xmax"] - k["xmin"]
        distance = (self.time * self.KNIGHT_SPEED) % (2 * span)
        going_left = distance > span
        x = k["xmin"] + (2 * span - distance if going_left else distance)
        image = knight_frame("walk_left" if going_left else "walk_right", self.time)
        canvas.blit(image, image.get_rect(midbottom=layout_feet(x, k["y"])))

        for i, name in enumerate(self.BUTTONS):
            y = self.BUTTON_TOP + i * self.BUTTON_GAP
            selected = i == self.selected
            image = ui.sprite(f"btn_{name}_{self.state(name, selected)}")
            rect = canvas.blit(image, (self.BUTTON_X, y))
            self.hotspots.add(rect, name)
            if selected:
                canvas.blit(ui.sprite("cursor_sword"), (self.BUTTON_X - 16, y + 6))
        ui.draw_text(canvas, "< > music   M mute", (6, 171), alpha=DIM)


class NoticeScene(MenuScene):
    """The job posting the Helper answered: Player 2 is a job title. Sign to pick a bag."""

    SIGN_RECT = pygame.Rect(120, 151, 80, 17)

    def on_click(self, key):
        self.game.change_scene(RunStartScene(self.game))

    def on_key(self, key):
        if key in CONFIRM_KEYS:
            self.game.change_scene(RunStartScene(self.game))
        elif key == pygame.K_ESCAPE:
            self.game.change_scene(IntroScene(self.game))

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, "Now hiring", (160, 15), "gold", scale=2, anchor="center")
        ui.draw_text(canvas, "Player 2", (160, 42), "gold", scale=2, anchor="midtop")
        for i, (line, color) in enumerate(story.NOTICE):
            ui.draw_text(canvas, line, (160, 68 + i * 12), color, anchor="midtop")
        ui.draw_text(canvas, story.NOTICE_SIGNED, (276, 132), anchor="topright", alpha=DIM + 60)
        ui.button(canvas, self.SIGN_RECT, "Sign", "red", self.state("sign", True))
        self.hotspots.add(self.SIGN_RECT, "sign")
        ui.draw_text(canvas, "ENTER sign   ESC back", (160, 171), anchor="midtop", alpha=DIM)


def room_label(room):
    """'Room 3', 'The boss' or 'The Trial', for a room index (or "trial")."""
    if room == "trial":
        return "The Trial"
    return "The boss" if room == ROOMS - 1 else f"Room {room + 1}"


class RoomSelectScene(MenuScene):
    """Levels: start a run at any room, the boss, or straight into the Trial. You still
    pick a bag first; from there the run carries on as normal."""

    ROOMS_PER_ROW = 5
    CHOICES = list(range(ROOMS)) + ["trial"]

    def __init__(self, game, selected=0):
        super().__init__(game)
        self.selected = self.CHOICES.index(selected)
        self.doors = [(w["x"], w["y"]) for w in ui.layout("levels")["widgets"] if w["type"] == "level"]

    def choose(self, index):
        self.game.change_scene(RunStartScene(self.game, self.CHOICES[index]))

    def on_hover(self, key):
        if key != "back":
            self.selected = key

    def on_click(self, key):
        if key == "back":
            self.game.change_scene(IntroScene(self.game))
        else:
            self.choose(key)

    def on_key(self, key):
        count, row = len(self.CHOICES), self.ROOMS_PER_ROW
        if key in LEFT_KEYS:
            self.selected = (self.selected - 1) % count
        elif key in RIGHT_KEYS:
            self.selected = (self.selected + 1) % count
        elif key in UP_KEYS or key in DOWN_KEYS:
            self.selected = (self.selected + row) % count
        elif key in CONFIRM_KEYS:
            self.choose(self.selected)
        elif key == pygame.K_ESCAPE:
            self.game.change_scene(IntroScene(self.game))

    @staticmethod
    def describe(choice):
        if choice == "trial":
            return "Four seals. Only the right gear hurts."
        if choice == ROOMS - 1:
            return "The Count, and his skulls."
        kinds = dict.fromkeys(kind for wave in WAVES[choice] for kind in wave)
        names = [ENEMIES[k].name + ("" if ENEMIES[k].name.endswith(("s", "ed")) else "s") for k in kinds]
        return ", ".join(names)

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, "Pick a room", (160, 15), "gold", scale=2, anchor="center")
        back = canvas.blit(ui.sprite(f"icon_back_{self.state('back', False)}"), (6, 6))
        self.hotspots.add(back, "back")
        self.draw_torches(canvas, [(12, 104), (300, 104)])
        ui.draw_text(canvas, "Start a run anywhere", (160, 38), anchor="midtop", alpha=DIM)

        for i, choice in enumerate(self.CHOICES):
            x, y = self.doors[i]
            selected = i == self.selected
            if choice == "trial":
                name, plate = "level_done", "T"
            elif choice == ROOMS - 1:
                name, plate = "level_current", str(ROOMS)  # the gold door
            else:
                name, plate = "level_open", str(choice + 1)
            rect = canvas.blit(ui.sprite(f"{name}_hover" if selected else name), (x, y))
            ui.draw_text(canvas, plate, (rect.centerx + 1, rect.y + 5), "dark", anchor="center")
            if selected:
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, i)

        choice = self.CHOICES[self.selected]
        ui.draw_text(canvas, room_label(choice), (160, 131), "gold", anchor="midtop")
        ui.draw_text(canvas, self.describe(choice), (160, 141), anchor="midtop")
        ui.draw_text(canvas, "You start with just your bag's kit.", (160, 158), anchor="midtop", alpha=DIM)
        ui.draw_text(canvas, "WASD choose   ENTER go   ESC back", (160, 170), anchor="midtop", alpha=DIM)


def draw_card(canvas, rect, state, selected, title, blurb, icon=None, image=None, dim=False):
    """A reward card: icon (or sprite), name and a short wrapped description."""
    ui.nine_slice(canvas, f"button9_{'red' if selected else 'stone'}_{state}", rect)
    if image:
        canvas.blit(image, image.get_rect(center=(rect.centerx, rect.y + 11)))
    elif icon:
        draw_icon(canvas, ICON_FONT, icon, (rect.centerx, rect.y + 11), size=14)
    alpha = DIM if dim else 255
    ui.draw_text(canvas, title, (rect.centerx, rect.y + 21), "gold", anchor="midtop", alpha=alpha)
    for i, line in enumerate(ui.wrap(blurb, rect.w // ui.GLYPH_ADVANCE - 1)[:3]):
        ui.draw_text(canvas, line, (rect.centerx, rect.y + 31 + i * 9), anchor="midtop", alpha=alpha)


class RunStartScene(MenuScene):
    """Pick the bag for this run. Every bag comes with its own starting kit."""

    CARD_W, CARD_H, CARD_GAP, CARD_Y = 92, 84, 8, 36
    START_RECT = pygame.Rect(120, 144, 80, 18)
    BLURBS = {
        "satchel": "The all-rounder.",
        "hauler": "Holds lots. Slow dig.",
        "pouch": "Fast dig. Tiny.",
    }

    def __init__(self, game, start_room=0):
        super().__init__(game)
        self.bags = list(BAGS)
        self.selected = 0
        self.start_room = start_room  # from the Levels screen: a room index, or "trial"

    def start(self):
        bag_id = self.bags[self.selected]
        run = self.game.current_run = RunState(bag_id, self.game.levels)
        if self.start_room == "trial":
            from game.trial import TrialPrepScene, lend_trial_pack  # trial imports this module
            run.room = TRIAL_ROOM
            run.trial_offered = True
            lend_trial_pack(run)
            self.game.change_scene(TrialPrepScene(self.game))
            return
        run.room = self.start_room
        run.trial_offered = self.start_room >= TRIAL_ROOM  # it's offered on the way to room 8
        self.game.change_scene(RewardScene(self.game, picks=0))

    def back(self):
        if self.start_room:
            self.game.change_scene(RoomSelectScene(self.game, self.start_room))
        else:
            self.game.change_scene(IntroScene(self.game))

    def on_hover(self, key):
        if key != "start" and key != "back":
            self.selected = key

    def on_click(self, key):
        if key == "back":
            self.back()
        elif key == "start":
            self.start()
        else:
            self.selected = key

    def on_key(self, key):
        if key in LEFT_KEYS:
            self.selected = (self.selected - 1) % len(self.bags)
        elif key in RIGHT_KEYS:
            self.selected = (self.selected + 1) % len(self.bags)
        elif key in CONFIRM_KEYS:
            self.start()
        elif key == pygame.K_ESCAPE:
            self.back()

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, "Pick a bag", (160, 15), "gold", scale=2, anchor="center")
        back = canvas.blit(ui.sprite(f"icon_back_{self.state('back', False)}"), (6, 6))
        self.hotspots.add(back, "back")
        if self.start_room:
            where = room_label(self.start_room)
            ui.draw_text(canvas, f"Starting at: {where}", (160, 27), "gold", anchor="midtop")
        else:
            ui.draw_text(canvas, f"{ROOMS - 1} rooms, then the boss. One life.", (160, 27), anchor="midtop",
                         alpha=DIM)
        x = 160 - (3 * self.CARD_W + 2 * self.CARD_GAP) // 2
        for i, bag_id in enumerate(self.bags):
            bag = BAGS[bag_id]
            rect = pygame.Rect(x + i * (self.CARD_W + self.CARD_GAP), self.CARD_Y, self.CARD_W, self.CARD_H)
            selected = i == self.selected
            ui.nine_slice(canvas, f"button9_{'red' if selected else 'stone'}_{self.state(i, False)}", rect)
            helper = helper_frame(bag.sprite, "idle_down", self.time)
            canvas.blit(helper, helper.get_rect(midbottom=(rect.centerx, rect.y + 22)))
            ui.draw_text(canvas, bag.name, (rect.centerx, rect.y + 24), "gold", anchor="midtop")
            ui.draw_text(canvas, f"{bag.slots} slots", (rect.centerx, rect.y + 33), anchor="midtop")
            ui.draw_text(canvas, f"dig {bag.extract_time} sec", (rect.centerx, rect.y + 42), anchor="midtop")
            for j, line in enumerate(ui.wrap(self.BLURBS[bag_id], 14)[:2]):
                ui.draw_text(canvas, line, (rect.centerx, rect.y + 53 + j * 9), anchor="midtop", alpha=DIM + 60)
            kit = STARTING_KIT[bag_id]
            for j, gear in enumerate(kit):
                draw_icon(canvas, ICON_FONT, gear, (rect.centerx - (len(kit) - 1) * 6 + j * 12, rect.bottom - 9),
                          size=10)
            if selected:
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, i)
        ui.draw_text(canvas, "The Knight starts with his Sword.", (160, 124), anchor="midtop")
        ui.draw_text(canvas, "Bag order is dig order.", (160, 133), anchor="midtop", alpha=DIM)
        ui.button(canvas, self.START_RECT, "Start", "red", self.state("start", True))
        self.hotspots.add(self.START_RECT, "start")
        ui.draw_text(canvas, "A/D choose   ENTER start", (160, 168), anchor="midtop", alpha=DIM)


class RewardScene(MenuScene):
    """Between rooms: pick gear for the bag (or a priest's blessing), then get ready for
    the next room by sorting the bag and choosing what the Knight holds.

    Sections, top to bottom: the cards, the slots (bag, then his two hands), the Go
    button. W/S moves between them. Choosing two slots swaps them; tools only go in his
    tool hand and items in his item hand. Choosing a taken card gives it back, and
    choosing another card once you've picked swaps your pick for it. With the bag full,
    a picked card asks which gear to throw out for it.

    With no picks and no blessing it's just the "get ready" screen (before room 1).
    """

    CARD_W, CARD_H, CARD_GAP, CARD_Y = 92, 58, 8, 30
    BAG_Y = 104
    GO_RECT = pygame.Rect(120, 156, 80, 15)
    HAND_X = {TOOL: 250, ITEM: 276}
    NOTICE_TIME = 2.0
    BLESSINGS = [
        ("heal", "Prayer", f"Heals the Knight {SHRINE_HEAL} HP."),
        ("slot", "Bigger bag", "One more slot."),
        ("dig", "Quick hands", "Dig 25% faster."),
    ]
    PRIEST = "assets/Character_animation/priests_idle/priest{}/v1/priest{}_v1_1.png"

    def __init__(self, game, picks=1, shrine=False):
        super().__init__(game)
        self.run = game.current_run
        self.shrine = shrine
        self.picks = picks
        if shrine:
            self.cards = [b[0] for b in self.BLESSINGS]
        else:
            self.cards = self.run.roll_rewards() if picks else []
        # Taken card -> how to undo it: for gear, what it replaced in a full bag (or
        # None); for a blessing, the run's HP and bag before it.
        self.taken = {}
        self.section = "cards" if self.cards else "slots"
        self.cursor = 0  # in the cards or the slots, whichever is focused
        self.grabbed = None  # slot waiting for a second slot to swap with
        self.pending = None  # a card waiting for a bag slot to replace
        self.notice = ""
        self.notice_left = 0.0
        self.quitting = False  # the quit button was clicked once; a second click quits
        self.priests = [pygame.image.load(self.PRIEST.format(i, i)).convert_alpha() for i in (1, 2, 3)]

    @property
    def queue(self):
        return self.run.backpack.queue

    @property
    def slots(self):
        """Every place gear can sit: the bag's slots in order, then his tool and item hands."""
        return [("bag", i) for i in range(self.run.backpack.bag.slots)] + [("hand", TOOL), ("hand", ITEM)]

    def say(self, text):
        self.notice, self.notice_left = text, self.NOTICE_TIME

    def update(self, dt):
        super().update(dt)
        self.notice_left = max(0.0, self.notice_left - dt)

    # --- cards ---

    def choose_card(self, index):
        if index in self.taken:
            self.give_back(index)
        elif self.picks > 0:
            self.take(index)
        elif self.taken:
            # Change your mind: swap the latest pick for this one.
            if self.give_back(list(self.taken)[-1]):
                self.take(index)

    def take(self, index):
        card = self.cards[index]
        if self.shrine:
            self.taken[index] = (self.run.knight_hp, self.run.backpack.bag)
            {"heal": self.run.heal, "slot": self.run.bigger_bag, "dig": self.run.faster_digging}[card]()
        elif self.run.backpack.full:
            self.pending = index
            self.section, self.cursor = "slots", 0
            return
        else:
            self.run.backpack.add(card)
            self.taken[index] = None
        self.picks -= 1
        if self.picks == 0:
            self.section, self.cursor = "go", 0

    def give_back(self, index):
        """Undo a taken card. Returns False if it can't be undone."""
        card, record = self.cards[index], self.taken[index]
        if self.shrine:
            hp, bag = record
            if len(self.queue) > bag.slots:
                self.say("Empty a bag slot first.")
                return False
            self.run.knight_hp, self.run.backpack.bag = hp, bag
        elif card in self.queue:
            spot = len(self.queue) - 1 - self.queue[::-1].index(card)  # the copy added last
            if record:
                self.queue[spot] = record  # put back what it replaced
            else:
                del self.queue[spot]
        elif self.run.hands[GEAR[card].hand] == card:
            self.run.hands[GEAR[card].hand] = None
            if record:
                self.queue.append(record)
        else:
            return False
        del self.taken[index]
        self.picks += 1
        self.grabbed = None
        return True

    # --- slots ---

    def gear_at(self, slot):
        kind, where = slot
        if kind == "hand":
            return self.run.hands[where]
        return self.queue[where] if where < len(self.queue) else None

    def choose_slot(self, index):
        slot = self.slots[index]
        if self.pending is not None:
            if slot[0] == "bag" and self.gear_at(slot):
                record = self.queue[slot[1]]
                self.queue[slot[1]] = self.cards[self.pending]
                self.taken[self.pending] = record
                self.pending = None
                self.picks -= 1
                self.section, self.cursor = ("cards", 0) if self.picks > 0 else ("go", 0)
            return
        if self.grabbed is None:
            self.grabbed = index
        elif self.grabbed == index:
            self.grabbed = None
        else:
            self.swap(self.slots[self.grabbed], slot)
            self.grabbed = None

    def swap(self, a, b):
        first, second = self.gear_at(a), self.gear_at(b)
        for slot, gear in ((a, second), (b, first)):
            if slot[0] == "hand" and gear and GEAR[gear].helper_only:
                self.say(f"The {GEAR[gear].name} is for you, not him.")
                return
            if slot[0] == "hand" and gear and GEAR[gear].hand != slot[1]:
                self.say(f"Only {slot[1]}s go in his {slot[1]} hand.")
                return
        # Lay the bag out slot by slot, swap, then close up the gaps.
        bag = self.queue + [None] * max(0, self.run.backpack.bag.slots - len(self.queue))
        for slot, gear in ((a, second), (b, first)):
            if slot[0] == "hand":
                self.run.hands[slot[1]] = gear
            else:
                bag[slot[1]] = gear
        self.queue[:] = [g for g in bag if g]

    # --- input ---

    def go(self):
        if self.run.room == 0:
            # Before room 1: the Knight and the Helper meet up, then walk into it together.
            self.game.change_scene(IntroCutscene(self.game, lambda: CombatScene(self.game)))
            return
        self.game.change_scene(CombatScene(self.game))

    def sections(self):
        return (["cards"] if self.cards else []) + ["slots", "go"]

    def on_hover(self, key):
        kind, value = key
        if kind in ("cards", "slots"):
            self.section, self.cursor = kind, value
        elif kind == "go":
            self.section = "go"

    def quit_button(self):
        if self.quitting:
            quit_run(self.game)
        else:
            self.quitting = True
            self.say("Again to quit the run (ESC/click).")

    def on_click(self, key):
        kind, value = key
        if kind != "quit":
            self.quitting = False
        if kind == "quit":
            self.quit_button()
        elif kind == "cards":
            self.choose_card(value)
        elif kind == "slots":
            self.choose_slot(value)
        elif kind == "go":
            self.go()

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            if self.pending is None and self.grabbed is None:
                self.quit_button()  # twice to quit the run
            self.pending = self.grabbed = None
            return
        self.quitting = False
        sections = self.sections()
        index = sections.index(self.section)
        if key in UP_KEYS and index > 0:
            self.section, self.cursor = sections[index - 1], 0
        elif key in DOWN_KEYS and index < len(sections) - 1:
            self.section, self.cursor = sections[index + 1], 0
        elif key in LEFT_KEYS:
            self.cursor = max(0, self.cursor - 1)
        elif key in RIGHT_KEYS:
            count = len(self.cards) if self.section == "cards" else len(self.slots)
            self.cursor = min(count - 1, self.cursor + 1)
        elif key in CONFIRM_KEYS:
            if self.section == "cards":
                self.choose_card(self.cursor)
            elif self.section == "slots":
                self.choose_slot(self.cursor)
            else:
                self.go()

    # --- drawing ---

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        if self.shrine:
            title = "Blessing"
        elif not self.cards:
            title = "Get ready"
        else:
            title = "Pick a reward"
        if self.shrine and self.run.room in story.PRIEST:
            # The middle priest speaks from his card.
            ui.speech_bubble(canvas, story.PRIEST[self.run.room], (160, self.CARD_Y + 2), width=30)
        else:
            ui.draw_text(canvas, title, (160, 14), "gold", scale=2, anchor="center")
        self.draw_scores(canvas)
        quit_rect = canvas.blit(ui.sprite(f"icon_exit_{self.state(('quit', 0), self.quitting)}"), (6, 6))
        self.hotspots.add(quit_rect, ("quit", 0))
        ui.draw_text(canvas, "Quit run", (3, quit_rect.bottom + 1), alpha=255 if self.quitting else DIM)
        if self.cards:
            self.draw_cards(canvas)
        else:
            ui.draw_text(canvas, "Sort the bag and choose what he holds.", (160, 50), anchor="midtop")
            ui.draw_text(canvas, "The front of the bag is dug out first.", (160, 62), anchor="midtop", alpha=DIM)
        self.draw_slots(canvas)

        label = "Next: the boss" if self.run.boss_room else f"Next: room {self.run.room + 1}"
        ui.draw_text(canvas, label, (30, 130), "gold")
        draw_lineup(canvas, self.run.enemies, (190, 134))
        if self.quitting and not self.notice_left:
            self.quitting = False  # the confirm window ran out
        if self.notice_left:
            message = self.notice
        elif self.pending is not None:
            message = "Bag full! Pick gear to throw out."
        elif self.grabbed is not None:
            message = "Now pick where it goes."
        elif self.picks > 0:
            message = "Choose a card, or skip with Go."
        elif self.taken:
            message = "Click another card to change it."
        else:
            message = "Pick a slot, then where it goes."
        ui.draw_text(canvas, message, (160, 146), anchor="midtop")

        label = "Fight the boss" if self.run.boss_room else ("Next room" if self.run.room else "Start")
        ui.button(canvas, self.GO_RECT, label, "red", self.state(("go", 0), self.section == "go"))
        self.hotspots.add(self.GO_RECT, ("go", 0))
        if self.section == "go":
            pygame.draw.rect(canvas, GOLD, self.GO_RECT.inflate(4, 4), 1)
        ui.draw_text(canvas, "WASD move   ENTER choose", (160, 173), anchor="midtop", alpha=DIM)

    def draw_scores(self, canvas):
        ui.draw_text(canvas, f"P1 {story.p1_score(self.run.p1_score)}", (314, 4), "gold", anchor="topright")
        ui.draw_text(canvas, f"P2 {story.p2_score(self.run.room)}", (314, 13), anchor="topright", alpha=DIM)

    def draw_cards(self, canvas):
        x = 160 - (3 * self.CARD_W + 2 * self.CARD_GAP) // 2
        for i, card in enumerate(self.cards):
            rect = pygame.Rect(x + i * (self.CARD_W + self.CARD_GAP), self.CARD_Y, self.CARD_W, self.CARD_H)
            key = ("cards", i)
            focused = self.section == "cards" and self.cursor == i
            taken = i in self.taken
            dim = not taken and self.picks <= 0
            if self.shrine:
                _, name, blurb = self.BLESSINGS[i]
                draw_card(canvas, rect, self.state(key, False), taken, name, blurb, image=self.priests[i], dim=dim)
            else:
                gear = GEAR[card]
                draw_card(canvas, rect, self.state(key, False), taken, gear.name, gear.blurb, icon=card, dim=dim)
            if focused or self.pending == i:
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, key)

    def slot_rect(self, slot):
        kind, where = slot
        x = self.HAND_X[where] if kind == "hand" else 30 + where * 16
        return pygame.Rect(x, self.BAG_Y, 13, 13)

    def draw_slots(self, canvas):
        bag = self.run.backpack.bag
        ui.draw_text(canvas, f"{bag.name}: {bag.slots} slots, dig {bag.extract_time}", (30, self.BAG_Y - 10),
                     alpha=DIM + 60)
        ui.draw_text(canvas, "1st", (30, self.BAG_Y + 15), alpha=DIM)
        ui.draw_text(canvas, f"Knight {self.run.knight_hp}/{self.run.knight_max_hp}", (293, self.BAG_Y - 10),
                     anchor="topright", alpha=DIM + 60)
        for hand, x in self.HAND_X.items():
            ui.draw_text(canvas, hand, (x + 6, self.BAG_Y + 15), anchor="midtop", alpha=DIM)
        for i, slot in enumerate(self.slots):
            rect = self.slot_rect(slot)
            gear = self.gear_at(slot)
            if gear:
                draw_icon(canvas, ICON_FONT, gear, rect.center, size=13)
            else:
                pygame.draw.rect(canvas, (107, 78, 99), rect, 1)
            if i == self.grabbed:
                pygame.draw.rect(canvas, (120, 220, 255), rect.inflate(4, 4), 1)
            elif self.section == "slots" and self.cursor == i:
                pygame.draw.rect(canvas, GOLD, rect.inflate(4, 4), 1)
            self.hotspots.add(rect, ("slots", i))


class StoryEndScene(MenuScene):
    """An ending: a title, a tableau of the two of them, then lines that appear one by
    one. ENTER skips to the end, then goes on."""

    TITLE = "The End"
    CONTINUE = "ENTER: main menu"
    FIRST_LINE, LINE_DELAY = 2.0, 1.4
    LINES_Y = 86

    def __init__(self, game, lines):
        super().__init__(game)
        self.lines = lines

    def lines_shown(self):
        if self.time < self.FIRST_LINE:
            return 0
        return min(len(self.lines), int((self.time - self.FIRST_LINE) / self.LINE_DELAY) + 1)

    def advance(self):
        if self.lines_shown() < len(self.lines):
            self.time = self.FIRST_LINE + self.LINE_DELAY * len(self.lines)  # skip to the end
        else:
            self.game.change_scene(self.next_scene())

    def next_scene(self):
        return IntroScene(self.game)

    def on_click(self, key):
        self.advance()

    def on_key(self, key):
        if key in CONFIRM_KEYS or key == pygame.K_ESCAPE:
            self.advance()

    def draw_canvas(self, canvas):
        canvas.blit(ui.background("levels_bg"), (0, 0))
        ui.draw_text(canvas, self.TITLE, (160, 15), "gold", scale=2, anchor="center")
        # Click anywhere to continue.
        self.hotspots.add(canvas.get_rect(), "continue")
        self.draw_tableau(canvas)
        for i, (line, color) in enumerate(self.lines[:self.lines_shown()]):
            ui.draw_text(canvas, line, (160, self.LINES_Y + i * 12), color, anchor="midtop")
        if self.lines_shown() == len(self.lines):
            ui.draw_text(canvas, self.CONTINUE, (160, 160), anchor="midtop", alpha=DIM)

    def draw_tableau(self, canvas):
        pass


class EndingScene(StoryEndScene):
    """After the betrayal: the Knight's last words, the scoreboard flips, and the Helper
    finally gets paid."""

    def __init__(self, game, score):
        # Player 1's score finally goes to Player 2.
        super().__init__(game, [("P1  GAME OVER", "cream"), (f"P2  {story.p1_score(score)}", "gold")]
                         + story.ENDING)

    def draw_tableau(self, canvas):
        knight = knight_frame("death", self.time)
        canvas.blit(knight, knight.get_rect(midbottom=(144, 76)))
        helper = helper_frame("large", "idle_left", self.time)  # facing the Knight, bag full of gold
        canvas.blit(helper, helper.get_rect(midbottom=(176, 76)))
        ui.speech_bubble(canvas, story.LAST_WORDS, (140, 60), width=18)


class RenewedScene(StoryEndScene):
    """He made it out with the gold: Player 1 takes all the glory, his score rolls up,
    and Player 2 goes back to work."""

    TITLE = "Victory!"
    CONTINUE = "ENTER: sign again"
    TALLY_TIME = 1.5  # his score counts up this long
    COINS = [(-34, 0.0), (-22, 0.55), (-10, 0.25), (8, 0.8), (20, 0.4), (32, 0.1)]  # x offset, phase
    COIN_FALL = 46  # pixels a coin drops before it lands
    KNIGHT = (150, 96)  # his feet; scaled up, in the middle of it all
    LINES_Y = 108

    def __init__(self, game, score, bag):
        super().__init__(game, story.RENEWED_ENDING)
        self.score = score
        self.bag = bag  # the Helper's sprite size

    def next_scene(self):
        return NoticeScene(self.game)  # the job's still open

    def draw_tableau(self, canvas):
        x, feet = self.KNIGHT
        for dx, phase in self.COINS:
            fall = ((self.time * 0.9 + phase) % 1.0) * self.COIN_FALL
            coin = ui.sprite("coin")
            canvas.blit(coin, coin.get_rect(center=(x + dx, feet - self.COIN_FALL + fall)))
        knight = pygame.transform.scale_by(knight_frame("victory", self.time), 2)
        canvas.blit(knight, knight.get_rect(midbottom=(x, feet + 4)))
        helper = helper_frame(self.bag, "dig", self.time)  # still digging in the bag
        canvas.blit(helper, helper.get_rect(midbottom=(x + 46, feet)))
        ui.speech_bubble(canvas, story.GLORY, (x - 4, feet - 44), width=26)

        rolled = round(self.score * min(1.0, self.time / self.TALLY_TIME))
        ui.draw_text(canvas, f"P1 {story.p1_score(rolled)}", (38, 56), "gold")
        ui.draw_text(canvas, f"P2 {story.P2_BLANK}", (38, 66), alpha=DIM)
        if self.time >= self.TALLY_TIME and int(self.time * 3) % 2 == 0:
            ui.draw_text(canvas, "High score!", (38, 76), "gold")
