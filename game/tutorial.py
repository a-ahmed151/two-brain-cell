"""Coach prompts for the teaching levels.

A level names its script with the `tutorial` map property. A script is a list of
(condition, lines); the first step whose condition holds is shown at the top of the
map, so the prompt follows what the player actually does. Lines are at most 36
characters (the bitmap font on the 240 px wide overlay).
"""


class Moment:
    """What a coach condition can look at, read from the play scene."""

    def __init__(self, scene):
        knight, helper = scene.knight, scene.helper
        self.tool, self.item = knight.tool, knight.item
        self.held = helper.held
        self.digging = helper.digging
        self.queue = helper.backpack.queue
        self.handed = helper.handed
        self.started = knight.walking or knight.distance > 0
        self.map_viewed = scene.map_viewed
        # The obstacle he's busy with already counts as handled.
        self.done = [o.cleared or o is knight.using for o in scene.obstacles]
        self.kinds = [o.kind for o in scene.obstacles]

    def cleared(self, kind):
        return sum(1 for k, done in zip(self.kinds, self.done) if k == kind and done)

    def left(self, kind):
        return sum(1 for k, done in zip(self.kinds, self.done) if k == kind and not done)

    @property
    def next(self):
        """The kind of the next obstacle he'll reach, or None."""
        return next((k for k, done in zip(self.kinds, self.done) if not done), None)

    @property
    def idle_hands(self):
        """Not holding or digging anything."""
        return not self.held and not self.digging


DIGGING = (lambda m: m.digging, ["Digging... don't move!", "Moving cancels it."])

SCRIPTS = {
    # Level 1: dig, hold, give; he uses gear by himself; tools are kept.
    "first_blood": [
        (lambda m: m.started and m.tool != "sword" and m.held == "sword",
         ["Catch him and press E!"]),
        (lambda m: m.started and m.tool != "sword" and m.idle_hands,
         ["Quick! E: dig out the Sword,", "then catch up with him!"]),
        (lambda m: not m.started and m.tool is None and m.idle_hands,
         ["Your bag holds the Sword.", "E: dig it out. Stand still!"]),
        DIGGING,
        (lambda m: m.held and m.tool is None,
         ["Walk to the Knight (WASD)", "and press E to hand it over."]),
        (lambda m: not m.started and not m.map_viewed,
         ["He's armed. Hold TAB to see", "the whole dungeon first."]),
        (lambda m: not m.started,
         ["Skeletons block the way for you", "too. SPACE: send him in!"]),
        (lambda m: m.cleared("skeleton") == 0,
         ["He uses his gear on his own.", "Just watch."]),
        (lambda m: m.left("skeleton") > 0,
         ["Tools stay in his hand.", "One Sword, many skeletons."]),
        (lambda m: True,
         ["He'll take all the credit.", "Of course he will."]),
    ],
    # Level 2: two hands; items are used up; pack only what's needed, in order.
    "locked_in": [
        (lambda m: m.held == "pickaxe",
         ["The Pickaxe would replace", "his Sword! R: restart, repack."]),
        (lambda m: m.tool != "sword",
         ["His Sword went back in the bag!", "R: restart, repack."]),
        (lambda m: m.left("locked_door") and m.item is None and m.idle_hands and "key" not in m.queue,
         ["Out of Keys! One per door.", "R: restart, repack."]),
        (lambda m: not m.started and m.item is None and m.idle_hands,
         ["He has two hands: a tool", "and an item. E: dig a Key."]),
        DIGGING,
        (lambda m: m.held == "key" and m.item is None,
         ["Give him the Key (E)."]),
        (lambda m: not m.started,
         ["The Sword stays in his", "other hand. SPACE: go!"]),
        (lambda m: m.cleared("locked_door") and m.left("locked_door") and m.item is None,
         ["The Key was used up.", "Dig him another one!"]),
        (lambda m: m.cleared("locked_door") == 0,
         ["Doors eat Keys.", "One Key per door."]),
    ],
    # Level 3: swapping a tool sends the old one to the back of the queue; timing.
    "rubble": [
        (lambda m: m.tool == "pickaxe" and m.cleared("skeleton") == 0,
         ["Too early! He has no Sword", "for the skeleton. R: retry."]),
        (lambda m: not m.started and m.idle_hands,
         ["Rubble needs the Pickaxe.", "Dig it out now, hand it later."]),
        DIGGING,
        (lambda m: not m.started,
         ["SPACE: send him in.", "Wait for the skeleton to fall."]),
        (lambda m: m.held == "pickaxe" and m.next == "skeleton",
         ["Hold it! Give it AFTER", "he beats the skeleton."]),
        (lambda m: m.held == "sword" and m.next == "rock",
         ["Not yet! Give the Sword", "after the rubble is gone."]),
        (lambda m: m.tool == "sword" and m.held == "pickaxe" and m.next == "rock",
         ["Now! Give him the Pickaxe", "before he reaches the rubble."]),
        (lambda m: m.tool == "sword" and m.idle_hands and "pickaxe" in m.queue and m.handed.count("sword") == 1,
         ["The Pickaxe came back too!", "Dig it out for the next rubble."]),
        (lambda m: m.tool == "sword" and m.idle_hands and m.next == "rock",
         ["E: dig out the Pickaxe", "for the rubble ahead!"]),
        (lambda m: m.tool == "pickaxe" and m.held == "sword" and m.next == "skeleton",
         ["Give him the Sword (E)", "before the skeleton!"]),
        (lambda m: m.tool == "pickaxe" and m.idle_hands and m.next == "skeleton",
         ["His Sword went back in your bag!", "Dig it out for the next one."]),
        (lambda m: m.next is None,
         ["Swap, then swap back.", "That's the whole trick."]),
    ],
}


def current_tip(scene):
    """The coach lines to show right now, or None."""
    script = SCRIPTS.get(scene.level.tutorial)
    if not script or scene.outcome or scene.knight.dead:
        return None
    moment = Moment(scene)
    for condition, lines in script:
        if condition(moment):
            return lines
    return None
