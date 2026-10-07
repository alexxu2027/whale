"""Recipes: the public rules that generate a round's hidden value (PRD §7.1)."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Component:
    key: str  # short symbol used in Pro view and logs, e.g. "A"
    name: str  # themed appraisal factor, e.g. "Authenticity" (PRD §7.6)
    values: tuple[int, ...]  # equally likely outcomes

    @property
    def min(self) -> int:
        return min(self.values)

    @property
    def max(self) -> int:
        return max(self.values)


@dataclass(frozen=True, slots=True)
class Recipe:
    """Final value = base + sum of independent, uniformly distributed components.

    Non-additive recipes (e.g. PRD's "Product") will need a settlement function
    here; everything downstream works off the enumerated state space, so only
    this class and ``StateSpace`` would change.
    """

    id: str
    title: str
    base: int
    components: tuple[Component, ...]
    value_name: str = "hammer price"

    def value(self, state: tuple[int, ...]) -> int:
        return self.base + sum(state)

    @property
    def min_value(self) -> int:
        return self.base + sum(c.min for c in self.components)

    @property
    def max_value(self) -> int:
        return self.base + sum(c.max for c in self.components)

    def sample_state(self, rng: random.Random) -> tuple[int, ...]:
        return tuple(rng.choice(c.values) for c in self.components)

    def describe(self) -> str:
        names = " + ".join(c.name for c in self.components)
        lo, hi = self.components[0].min, self.components[0].max
        return (
            f"The {self.value_name} is {self.base} + {names}. "
            f"Each factor is a whole number from {lo:+d} to {hi:+d}, all equally likely."
        )


_CARD = tuple(range(-5, 6))

FOUR_CARDS = Recipe(
    id="four_cards",
    title="Four Cards",
    base=100,
    components=(
        Component("A", "Authenticity", _CARD),
        Component("B", "Rarity", _CARD),
        Component("C", "Demand", _CARD),
        Component("D", "Condition", _CARD),
    ),
)
