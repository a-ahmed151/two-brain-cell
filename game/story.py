"""Everything the characters say. "Player 2" is a job title: the Knight (Player 1)
hired the Helper to carry the bag, for bread. See "Story" in GAME_DESIGN.md.

The bitmap font has letters, digits and  :%!?-/.',<>  only (no parentheses)."""

KNIGHT_NAME = "Sir Reginald"

# The job posting, shown before the bag select. (text, color)
NOTICE = [
    ("Must carry bag. Must not speak.", "cream"),
    ("Must not touch the gold.", "cream"),
    ("Pay: one heel of bread, on completion.", "cream"),
    ("Exposure guaranteed.", "gold"),
]
NOTICE_SIGNED = f"- {KNIGHT_NAME}, PLAYER 1"

# He sends himself into every fight.
CHARGE = "TO GLORY!"

# What he says when a room is clear, by room index. Room 3 is always armored.
ROOM_CLEAR = [
    "Did someone hand me things? Doesn't matter.",
    "Remember this, Player 2. Oh, you can't write.",
    "The pickaxe? Lucky I thought of it.",
    "Another flawless victory. Solo, basically.",
    "The bards will sing of me. You get the bag verse.",
    "New deal: you get HALF a heel of bread. Morale.",
    "If anything happens to me, the gold goes to me.",
    "The Count's next. Stay behind me. Further.",
]
BOSS_CLEAR = "Hah! My skill is unmatched."
BOSS_LEAVING = "Good work, Player 1! That's me."

# The Count talks to the Helper, not the Knight, when the boss fight starts.
COUNT = "Player 2? You do the work, he takes the gold? Even I pay my skulls."

# The priest, by the room the run is about to enter (shrines come after rooms 3 and 6).
PRIEST = {
    3: "Bless you, brave Player 1. And... the luggage.",
    6: "I've blessed many Player 2s for him. You're the first to get this far.",
}

# Player 2's score is never tracked. Shown by rooms cleared; anything else is dashes.
P2_SCORE = {3: "NOT TRACKED", 5: "SEE CONTRACT", 7: "ERROR"}
P2_BLANK = "------"

POISON_TIP = "His severance is in the bag."

# He reached the exit with the gold: the bad ending. Player 1 gets all the glory.
GLORY = "Another flawless solo run!"
RENEWED_ENDING = [
    ("The Knight keeps the gold and the glory.", "cream"),
    ("The Helper's contract is renewed.", "cream"),
    ("PLAYER 1 WINS. AGAIN.", "gold"),
]

LAST_WORDS = "Tell my mother... I was right..."
ENDING = [
    ("The Helper keeps the gold.", "cream"),
    ("The Knight gets the stale bread.", "cream"),
    ("PLAYER 2 WINS.", "gold"),
]


def p2_score(rooms_cleared):
    return P2_SCORE.get(rooms_cleared, P2_BLANK)


def p1_score(score):
    return f"{score:06d}"
