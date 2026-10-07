"""Bot personalities and difficulty (PRD §19.3, §19.4).

Every bot runs the same reasoning core; personalities are parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Personality:
    name: str
    latency_ms: tuple[int, int]  # time between actions, uniform in range
    # Quoting ("Your Market"); quote_size 0 means the bot doesn't make markets.
    quote_size: int
    base_half_width: float  # points
    k_sigma: float  # extra half-width per point of belief sd
    inventory_skew: float  # gamma: points the center moves per unit held
    # Taking liquidity
    take_edge: float  # minimum expected edge (points) to take an offer
    take_size: int
    # Beliefs
    informed_pct: float  # pi: how informed the bot assumes other takers are
    learns_from_flow: bool = True
    # Calls
    call_rate: float = 0.0  # chance per action of calling someone
    # Behavior
    noise_rate: float = 0.0  # chance per action of a random trade
    fv_noise: float = 0.0  # sd of noise added to the bot's own fair value
    bluff_rate: float = 0.0  # chance per action of trading against its view


MARKET_MAKER = Personality(
    name="Market Maker",
    latency_ms=(300, 900),
    quote_size=5,
    base_half_width=1.0,
    k_sigma=0.15,
    inventory_skew=0.15,
    take_edge=2.5,
    take_size=5,
    informed_pct=0.5,
    call_rate=0.02,
)

CONSERVATIVE = Personality(
    name="Conservative",
    latency_ms=(900, 2_000),
    quote_size=3,
    base_half_width=2.5,
    k_sigma=0.3,
    inventory_skew=0.3,
    take_edge=4.0,
    take_size=3,
    informed_pct=0.5,
    call_rate=0.01,
)

WHALE = Personality(
    name="Whale",
    latency_ms=(600, 1_500),
    quote_size=10,
    base_half_width=1.5,
    k_sigma=0.2,
    inventory_skew=0.05,
    take_edge=1.0,
    take_size=10,
    informed_pct=0.3,
    call_rate=0.03,
)

SHARK = Personality(
    name="Shark",
    latency_ms=(400, 1_000),
    quote_size=0,
    base_half_width=0.0,
    k_sigma=0.0,
    inventory_skew=0.1,
    take_edge=1.5,
    take_size=8,
    informed_pct=0.6,
    call_rate=0.05,
)

NOISE = Personality(
    name="Noise Trader",
    latency_ms=(500, 1_500),
    quote_size=4,
    base_half_width=1.5,
    k_sigma=0.0,
    inventory_skew=0.05,
    take_edge=0.5,
    take_size=4,
    informed_pct=0.0,
    learns_from_flow=False,
    call_rate=0.02,
    noise_rate=0.35,
    fv_noise=4.0,
)

BLUFFER = Personality(
    name="Bluffer",
    latency_ms=(400, 1_000),
    quote_size=5,
    base_half_width=1.2,
    k_sigma=0.15,
    inventory_skew=0.1,
    take_edge=2.0,
    take_size=5,
    informed_pct=0.5,
    call_rate=0.03,
    bluff_rate=0.12,
)

ALL = (MARKET_MAKER, CONSERVATIVE, WHALE, SHARK, NOISE, BLUFFER)


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


def with_difficulty(p: Personality, d: Difficulty) -> Personality:
    """EASY bots react slowly, ignore order flow, and misprice; HARD bots are
    faster and price more precisely. MEDIUM is the personality as defined."""
    lo, hi = p.latency_ms
    match d:
        case Difficulty.EASY:
            return replace(
                p,
                latency_ms=(lo * 2, hi * 2),
                learns_from_flow=False,
                fv_noise=max(p.fv_noise, 3.0),
            )
        case Difficulty.HARD:
            return replace(p, latency_ms=(max(200, lo * 2 // 3), max(300, hi * 2 // 3)))
        case _:
            return p
