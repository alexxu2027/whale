"""In-world flavor lines for clues (PRD §7.6).

Flavor is chosen from the *answer* alone (its effect on the expected value),
never from the hidden state, so the wording can't reveal more than the
precise statement does.
"""

from __future__ import annotations

import random

from .posterior import StateSpace, belief
from .questions import Answer, RumorQ

# Pools keyed by factor name, then sentiment.
_FACTOR_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "Authenticity": {
        "up": (
            "The maker's marks look genuine.",
            "A guild seal is stamped on the base.",
            "Your appraiser would stake her reputation on it.",
        ),
        "down": (
            "Something about the craftsmanship feels off.",
            "The provenance papers have suspicious smudges.",
            "A known forger went quiet when you asked about it.",
        ),
        "flat": (
            "The appraisers can't agree on whether it's genuine.",
            "Half the marks look right. Half don't.",
        ),
    },
    "Rarity": {
        "up": (
            "Only a handful like it were ever made.",
            "The archives list no other in private hands.",
        ),
        "down": (
            "A merchant down the street has two more of these.",
            "You've seen this design before. Several times.",
        ),
        "flat": (
            "Uncommon, but not unheard of.",
            "The catalog lists a few, but nobody has seen them lately.",
        ),
    },
    "Demand": {
        "up": (
            "Two noble houses have been asking about it.",
            "Collectors are already crowding the viewing room.",
        ),
        "down": (
            "The royal collector is not interested.",
            "Buyers walked past the display without stopping.",
        ),
        "flat": (
            "A few collectors have asked. None seemed desperate.",
            "Interest is polite, nothing more.",
        ),
    },
    "Condition": {
        "up": (
            "Barely a scratch on it.",
            "It's been kept in a velvet case for a century.",
        ),
        "down": (
            "There's a crack you can see from across the room.",
            "It smells faintly of swamp.",
        ),
        "flat": (
            "Some wear, as you'd expect for its age.",
            "A few scuffs, nothing a polish won't hide.",
        ),
    },
}

_GENERAL_POOL: dict[str, tuple[str, ...]] = {
    "up": (
        "A well-connected broker is quietly optimistic.",
        "The auctioneer's assistant winked at you.",
    ),
    "down": (
        "A well-connected broker is quietly pessimistic.",
        "The auctioneer's assistant avoided your eyes.",
    ),
    "flat": (
        "The rumor mill is split.",
        "Nobody on the floor will commit to a number.",
    ),
}

_RUMOR_PREFIXES = ("Overheard in a tavern:", "A street urchin swears:", "Word on the docks:")

# Shift in expected value (points) needed before flavor turns positive/negative.
_SENTIMENT_THRESHOLD = 0.75


def _sentiment(space: StateSpace, answer: Answer) -> str:
    shift = belief(space, (answer,)).mean - space.prior_belief.mean
    if shift > _SENTIMENT_THRESHOLD:
        return "up"
    if shift < -_SENTIMENT_THRESHOLD:
        return "down"
    return "flat"


def flavor_text(space: StateSpace, answer: Answer, rng: random.Random) -> str:
    q = answer.question
    sentiment = _sentiment(space, answer)
    comps = q.components
    if len(comps) == 1:
        (i,) = comps
        name = space.recipe.components[i].name
        pool = _FACTOR_POOLS.get(name, _GENERAL_POOL)[sentiment]
    else:
        pool = _GENERAL_POOL[sentiment]
    line = rng.choice(pool)
    if isinstance(q, RumorQ):
        line = f"{rng.choice(_RUMOR_PREFIXES)} {line[0].lower()}{line[1:]}"
    return line
