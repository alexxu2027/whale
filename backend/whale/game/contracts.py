"""The pit's contract catalog (PRD §7.6). Contracts are flavor only: they never
change the recipe's math."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Contract:
    name: str
    pit: int
    description: str


CATALOG: tuple[Contract, ...] = (
    Contract("December Corn", 4, "The pit everyone watches when the weather turns."),
    Contract("Soybeans", 2, "Moves on every rumor out of Brazil."),
    Contract("Live Cattle", 7, "Feed costs, weather, and a lot of shouting."),
    Contract("Pork Bellies", 9, "The contract your uncle still talks about."),
    Contract("Frozen Orange Juice", 11, "One frost in Florida and the pit goes wild."),
    Contract("Crude Oil", 1, "Pipelines, tankers, and politics."),
)


def pick_contract(rng: random.Random) -> Contract:
    return rng.choice(CATALOG)
