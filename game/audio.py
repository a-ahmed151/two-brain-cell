"""Sound effects, from assets/sounds."""

import random
from functools import cache

import pygame

SOUNDS = "assets/sounds/{}.wav"
STEPS = ("Step_skeleton", "Step2_skeleton", "Step3_skeleton")


@cache
def sound(name):
    """A sound effect, or None if there's no audio (some browsers, headless runs)."""
    try:
        effect = pygame.mixer.Sound(SOUNDS.format(name))
        effect.set_volume(0.5)
        return effect
    except (pygame.error, FileNotFoundError):
        return None


def play(name):
    effect = sound(name)
    if effect:
        effect.play()


def step():
    """One footstep, picked at random so a walk doesn't sound like a metronome."""
    play(random.choice(STEPS))
