"""Recipes: the public rules that generate a round's hidden value (PRD §7.1, §7.6).

Components are the pit's market drivers. Each is defined as its effect on the
settlement price, so a drought that pushes prices up is "Weather +4".
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Component:
    key: str  # short symbol used in Pro view and logs, e.g. "A"
    name: str  # market driver, e.g. "Weather" (PRD §7.6)
    values: tuple[int, ...]  # equally likely outcomes

    @property
    def min(self) -> int:
        return min(self.values)

    @property
    def max(self) -> int:
        return max(self.values)


@dataclass(frozen=True, slots=True)
class Recipe:
    """Settlement price = base + sum of independent, uniformly distributed drivers.

    Non-additive recipes (e.g. PRD's "Product") will need a settlement function
    here; everything downstream works off the enumerated state space, so only
    this class and ``StateSpace`` would change.

    ``starting`` lists the drivers that starting clues are about (None: all);
    ``runner_drivers`` lists drivers reserved for runner news (PRD §7.7), so a
    runner always brings information nobody started with.
    """

    id: str
    title: str
    base: int
    components: tuple[Component, ...]
    value_name: str = "settlement price"
    band: tuple[int, int] | None = None  # tradable price range; None: the possible values
    starting: tuple[int, ...] | None = None
    runner_drivers: tuple[int, ...] = ()

    def value(self, state: tuple[int, ...]) -> int:
        return self.base + sum(state)

    @property
    def min_value(self) -> int:
        return self.base + sum(c.min for c in self.components)

    @property
    def max_value(self) -> int:
        return self.base + sum(c.max for c in self.components)

    @property
    def price_min(self) -> int:
        return self.band[0] if self.band else self.min_value

    @property
    def price_max(self) -> int:
        return self.band[1] if self.band else self.max_value

    @property
    def starting_drivers(self) -> tuple[int, ...]:
        return self.starting if self.starting is not None else tuple(range(len(self.components)))

    def sample_state(self, rng: random.Random) -> tuple[int, ...]:
        return tuple(rng.choice(c.values) for c in self.components)

    def describe(self) -> str:
        names = " + ".join(c.name for c in self.components)
        lo, hi = self.components[0].min, self.components[0].max
        return (
            f"The {self.value_name} is {self.base} + {names}. "
            f"Each driver is a whole number from {lo:+d} to {hi:+d}, all equally likely."
        )


_CARD = tuple(range(-5, 6))
_SMALL = tuple(range(-3, 4))

FOUR_CARDS = Recipe(
    id="four_cards",
    title="Four Drivers",
    base=100,
    components=(
        Component("A", "Weather", _CARD),
        Component("B", "Supply Report", _CARD),
        Component("C", "Export Demand", _CARD),
        Component("D", "Stockpiles", _CARD),
    ),
)

# The pit's default: four drivers that starting clues cover, plus two that only
# runners bring news about. 7^6 = 117,649 states, still exact to enumerate.
PIT_SIX = Recipe(
    id="pit_six",
    title="Six Drivers",
    base=100,
    components=(
        Component("A", "Weather", _SMALL),
        Component("B", "Supply Report", _SMALL),
        Component("C", "Export Demand", _SMALL),
        Component("D", "Stockpiles", _SMALL),
        Component("E", "Funds Flow", _SMALL),
        Component("F", "Freight", _SMALL),
    ),
    band=(80, 120),
    starting=(0, 1, 2, 3),
    runner_drivers=(4, 5),
)

RECIPES = {r.id: r for r in (FOUR_CARDS, PIT_SIX)}
