"""The Helper's backpack: which bag they carry and the queue of gear inside it.

See "Backpacks" in GAME_DESIGN.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Bag:
    name: str
    slots: int
    extract_time: float  # seconds to dig out one piece of gear


# Tune here. The player starts with the satchel.
BAGS = {
    "satchel": Bag("Satchel", slots=4, extract_time=0.8),
    "hauler": Bag("Hauler", slots=6, extract_time=1.6),
    "pouch": Bag("Pouch", slots=2, extract_time=0.3),
}
STARTING_BAG = "satchel"


class Backpack:
    """An ordered queue of gear. The front entry is the next one handed to the Knight."""

    def __init__(self, bag, gear=()):
        gear = list(gear)
        if len(gear) > bag.slots:
            raise ValueError(f"{bag.name} holds {bag.slots} pieces of gear, got {len(gear)}")
        self.bag = bag
        self.queue = gear

    @property
    def full(self):
        return len(self.queue) >= self.bag.slots

    @property
    def next(self):
        return self.queue[0] if self.queue else None

    def take_next(self):
        return self.queue.pop(0)

    def add(self, gear):
        """Put gear at the end of the queue. Returns False if there's no free slot."""
        if self.full:
            return False
        self.queue.append(gear)
        return True
