"""One roguelike run: the rooms ahead, and what carries over between them (the bag,
the Knight's HP and the gear in his hands). See "A run" in GAME_DESIGN.md."""

import dataclasses
import random

from game.backpack import BAGS, Backpack
from game.entities import KNIGHT_MAX_HP
from game.gear import ITEM, TOOL

ROOMS = 9  # the last one is the boss
SHRINE_AFTER = (2, 5)  # room indices followed by a priest instead of a reward
REWARD_CHOICES = 3
REWARD_POOL = ["sword", "pickaxe", "torch", "shield", "potion", "potion", "bomb", "bomb", "key"]
SHRINE_HEAL = 15
ROOM_REST = 5  # HP he gets back after every room
DIG_SPEEDUP = 0.75  # the shrine's "faster digging" multiplies the extract time by this

# Each bag starts with a different kit; the Knight always starts holding the Sword.
STARTING_KIT = {
    "satchel": ["potion", "pickaxe"],
    "hauler": ["potion", "pickaxe", "torch", "bomb"],
    "pouch": ["potion"],
}
KNIGHT_TOOL = "sword"

# Enemy mixes by stage; each room draws one at random. Index = room number.
WAVES = [
    [["skeleton", "skeleton"], ["skeleton", "skull"]],
    [["skeleton", "skeleton", "skull"], ["skeleton", "skeleton", "skeleton"]],
    [["armored", "skeleton"], ["armored", "skull"]],
    [["vampire", "skeleton"], ["vampire", "skull", "skull"]],
    [["armored", "armored", "skull"], ["armored", "vampire"]],
    [["skeleton", "skeleton", "skeleton", "skull", "skull"], ["vampire", "vampire"]],
    [["armored", "vampire", "skull"], ["armored", "armored", "skeleton", "skull"]],
    [["vampire", "vampire", "skull", "skull"], ["armored", "armored", "vampire", "skeleton"]],
    [["count", "skull"]],
]
assert len(WAVES) == ROOMS


class RunState:
    def __init__(self, bag_id, arenas, seed=None):
        self.rng = random.Random(seed)
        self.bag_id = bag_id
        self.backpack = Backpack(BAGS[bag_id], STARTING_KIT[bag_id])
        self.knight_hp = self.knight_max_hp = KNIGHT_MAX_HP
        # What's in his hands, carried into the next room. Either can be None.
        self.hands = {TOOL: KNIGHT_TOOL, ITEM: None}
        self.room = 0
        self.rooms = [(self.rng.randrange(len(arenas)), self.rng.choice(waves)) for waves in WAVES]
        self.rooms[-1] = (0, WAVES[-1][0])  # the boss gets the open Crypt

    @property
    def boss_room(self):
        return self.room == ROOMS - 1

    @property
    def arena_index(self):
        return self.rooms[self.room][0]

    @property
    def enemies(self):
        return self.rooms[self.room][1]

    def next_enemies(self):
        return self.rooms[self.room + 1][1] if self.room + 1 < ROOMS else []

    def shrine_next(self):
        return self.room in SHRINE_AFTER

    def roll_rewards(self, count=REWARD_CHOICES):
        return self.rng.sample(sorted(set(REWARD_POOL)), count)

    @property
    def knight_gear(self):
        return [g for g in self.hands.values() if g]

    def bigger_bag(self):
        bag = self.backpack.bag
        self.backpack.bag = dataclasses.replace(bag, slots=bag.slots + 1)

    def faster_digging(self):
        bag = self.backpack.bag
        self.backpack.bag = dataclasses.replace(bag, extract_time=round(bag.extract_time * DIG_SPEEDUP, 2))

    def heal(self, amount=SHRINE_HEAL):
        self.knight_hp = min(self.knight_max_hp, self.knight_hp + amount)
