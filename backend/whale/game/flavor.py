"""In-world flavor lines for clues (PRD §7.6).

Flavor is chosen from the *answer* alone (its effect on the expected value),
never from the hidden state, so the wording can't reveal more than the
precise statement does.
"""

from __future__ import annotations

import random

from .posterior import StateSpace, belief
from .questions import Answer, RumorQ

# Pools keyed by driver name, then the direction the answer moves the price.
# Lines must work for any contract in the catalog.
_FACTOR_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "Weather": {
        "up": (
            "Drought watch across the growing region. Keep it quiet.",
            "Storms are hitting supply hard.",
            "The weather desk says the season is turning ugly.",
        ),
        "down": (
            "Perfect weather all week. Supply looks great.",
            "The rain came right on time.",
            "Mild season. Nobody's worried about supply.",
        ),
        "flat": (
            "Weather's doing nothing interesting.",
            "The forecast is mixed. Could go either way.",
        ),
    },
    "Supply Report": {
        "up": (
            "The supply report is going to come in short.",
            "Production numbers are worse than anyone thinks.",
        ),
        "down": (
            "The supply report is going to be huge.",
            "Record production numbers are coming.",
        ),
        "flat": (
            "The supply report looks in line.",
            "Nothing surprising in the supply numbers.",
        ),
    },
    "Export Demand": {
        "up": (
            "Big export sale on the wire tonight.",
            "Overseas buyers are back in force.",
        ),
        "down": (
            "Exporters are cancelling orders.",
            "Nobody overseas is buying.",
        ),
        "flat": (
            "The export desk says it's quiet.",
            "Export business is steady. Nothing new.",
        ),
    },
    "Stockpiles": {
        "up": (
            "Warehouses are nearly empty.",
            "Stocks are drawing down fast.",
        ),
        "down": (
            "The elevators are full from here to Kansas.",
            "Warehouses can't take any more.",
        ),
        "flat": (
            "Stockpiles are about normal.",
            "Inventories haven't moved.",
        ),
    },
    "Funds Flow": {
        "up": (
            "A big fund just got an order to go long.",
            "The funds are buying everything in sight.",
        ),
        "down": (
            "A big fund is liquidating.",
            "The funds are dumping their positions.",
        ),
        "flat": (
            "The funds are sitting on their hands.",
            "No big money moving either way.",
        ),
    },
    "Freight": {
        "up": (
            "Rail cars are stuck. Delivery is a mess.",
            "Barge traffic halted on the river.",
        ),
        "down": (
            "Freight is cheap and moving fast.",
            "Plenty of trucks, no delays anywhere.",
        ),
        "flat": (
            "Freight's running normally.",
            "Shipping is on schedule.",
        ),
    },
}

_GENERAL_POOL: dict[str, tuple[str, ...]] = {
    "up": (
        "Your desk thinks this one's going up.",
        "Your clerk says lean long.",
    ),
    "down": (
        "Your desk thinks this one's heading down.",
        "Your clerk says lean short.",
    ),
    "flat": (
        "Your desk can't call it.",
        "Nobody on the phones will commit to a number.",
    ),
}

_RUMOR_PREFIXES = ("Overheard at the coffee stand:", "A runner from another booth swears:", "Word on the floor:")

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
