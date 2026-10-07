"""Market parameters for one round."""

from __future__ import annotations

from dataclasses import dataclass

# Prices are integer ticks (1 tick = 1 point). Cash is integer cents
# (1/100 of a point) so fees and rebates of 0.25 are exact.
CENTS_PER_POINT = 100


@dataclass(frozen=True, slots=True)
class MarketConfig:
    price_min: int = 80
    price_max: int = 120
    max_order_qty: int = 10
    position_limit: int = 25
    maker_rebate_cents: int = 25  # per unit, paid to the resting order's owner
    taker_fee_cents: int = 25  # per unit, paid by the incoming order's owner
    rate_limit_per_sec: int | None = 10  # None disables rate limiting
    rate_limit_burst: int = 20

    def __post_init__(self) -> None:
        if self.price_min > self.price_max:
            raise ValueError("price_min must be <= price_max")
        if self.max_order_qty < 1 or self.position_limit < 1:
            raise ValueError("max_order_qty and position_limit must be positive")
