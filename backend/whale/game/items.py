"""The auction house's item catalog (PRD §7.6). Items are flavor only: they
never change the recipe's math."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Item:
    name: str
    unit: str  # what one unit is called
    description: str


CATALOG: tuple[Item, ...] = (
    Item("The Dragon's Eye", "share", "A fist-sized ruby said to see through lies."),
    Item("Basilisk Eggs", "egg", "Handle with gloves. Do not make eye contact."),
    Item("Saffron of Qarth", "sack", "Worth more than gold, if it's real."),
    Item("The Drowned Captain's Map", "share", "Leads to treasure, or to the bottom of the sea."),
    Item("Cursed Locket", "share", "Beautiful. Previous owners unavailable for comment."),
    Item("Phoenix Feathers", "feather", "Still warm. Nobody knows how."),
    Item("The Lich King's Crown", "share", "Slightly cold to the touch. Slightly whispering."),
    Item("Mermaid Pearls", "pearl", "Harvested ethically, the seller insists."),
)


def pick_item(rng: random.Random) -> Item:
    return rng.choice(CATALOG)
