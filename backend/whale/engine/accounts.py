"""Per-player cash, position, and open-order exposure."""

from __future__ import annotations

from dataclasses import dataclass

from .config import CENTS_PER_POINT


@dataclass(slots=True)
class Account:
    player_id: str
    cash_cents: int = 0  # change in cash this round, including fees and rebates
    position: int = 0
    open_buy_qty: int = 0  # total remaining qty of this player's live buy orders
    open_sell_qty: int = 0
    fees_paid_cents: int = 0
    rebates_earned_cents: int = 0
    volume: int = 0  # units traded, both sides
    call_reserved_qty: int = 0  # size of this player's live answer to a call, either side
    penalties_cents: int = 0

    def worst_case_long(self) -> int:
        return self.position + self.open_buy_qty + self.call_reserved_qty

    def worst_case_short(self) -> int:
        return self.position - self.open_sell_qty - self.call_reserved_qty


@dataclass(frozen=True, slots=True)
class Settlement:
    player_id: str
    position: int
    cash_cents: int
    pnl_cents: int  # cash + position * final value, fees and rebates included

    @property
    def pnl(self) -> float:
        return self.pnl_cents / CENTS_PER_POINT
