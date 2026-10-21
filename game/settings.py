"""settings.json: what the game remembers between sessions (music level, whether the
tour was offered, which first-run hints were shown). Not in git."""

import json

SETTINGS = "settings.json"


def load():
    """Everything saved so far, or {} if there's nothing (or it can't be read)."""
    try:
        with open(SETTINGS) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def set(key, value):
    """Save one setting, keeping the others."""
    data = load()
    data[key] = value
    try:
        with open(SETTINGS, "w") as f:
            json.dump(data, f)
    except OSError:
        pass  # read-only (or the browser): it just won't be remembered
