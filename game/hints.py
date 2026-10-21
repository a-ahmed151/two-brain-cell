"""First-run hints: a short box of advice the first time something happens in a real run
(the first dig, the first enemy after you...). Each one shows once, ever; the ones
already shown are kept in settings.json. See "Tutorial" in GAME_DESIGN.md."""

from game import settings

# id -> (title, lines). The font has letters, digits and  :%!?-/.',<>  only.
HINTS = {
    "held": ("Got it!", ["Walk next to him - a ring shows - and press E to hand it over."]),
    "key": ("The Key is yours", ["Press E at the chest to open it.", "E anywhere else puts it back in the bag."]),
    "chased": ("It's after you!", ["You can't fight. Run - you're faster than all of them.",
                                    "Lead it back to him."]),
    "hurt": ("Ouch", ["You have 4 hearts for the whole run.", "They never come back."]),
    "low": ("He's hurting", ["Hand him a Potion. He drinks it by himself when he's low."]),
    "swapped": ("Back in the bag", ["What he was holding went to the back of your bag."]),
    "get_ready": ("Get ready", ["The gold slot is dug out first.", "Click two slots to swap them.",
                                "The last two slots are his hands."]),
    "reward": ("Pick a reward", ["Pick 1 card: it goes into the bag.", "Click it again to give it back."]),
}


_seen = None  # read from settings.json once, then kept here: hints are checked every frame


def seen():
    global _seen
    if _seen is None:
        saved = settings.load().get("hints_seen", [])
        _seen = set(saved) if isinstance(saved, list) else set()
    return _seen


def take(hint_id):
    """(title, lines) for a hint that hasn't been shown yet, marking it shown; else None."""
    if hint_id in seen():
        return None
    _seen.add(hint_id)
    settings.set("hints_seen", sorted(_seen))
    return HINTS[hint_id]
