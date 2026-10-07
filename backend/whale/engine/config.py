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
    # Price the engine falls back to when it must invent a quote and the book
    # is empty (e.g. an unanswered call). None means the middle of the band.
    reference_price: int | None = None
    # Make Me a Market (PRD §8.2)
    call_max_width: int = 4
    call_min_qty: int = 5
    call_answer_ms: int = 5_000
    call_decide_ms: int = 5_000
    call_cooldown_ms: int = 15_000  # between calls by the same caller
    call_busy_ms: int = 5_000  # responder can't be called again for this long
    call_no_answer_penalty_cents: int = 500

    @property
    def reference(self) -> int:
        if self.reference_price is not None:
            return self.reference_price
        return (self.price_min + self.price_max) // 2

    def __post_init__(self) -> None:
        if self.price_min > self.price_max:
            raise ValueError("price_min must be <= price_max")
        if self.max_order_qty < 1 or self.position_limit < 1:
            raise ValueError("max_order_qty and position_limit must be positive")
        if not 1 <= self.call_min_qty <= self.max_order_qty:
            raise ValueError("call_min_qty must be between 1 and max_order_qty")
        if not 1 <= self.call_max_width <= self.price_max - self.price_min:
            raise ValueError("call_max_width must fit inside the price band")
