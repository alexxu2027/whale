"""Commands: everything that can change exchange state.

Every command carries ``ts``, the server time in milliseconds at which the
room actor sequenced it. The engine never reads a clock itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import MarketStatus, OrderType, Side


@dataclass(frozen=True, slots=True, kw_only=True)
class PlaceOrder:
    player_id: str
    ts: int
    side: Side
    price: int
    qty: int
    order_type: OrderType = OrderType.LIMIT
    client_order_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class CancelOrder:
    player_id: str
    ts: int
    order_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CancelAll:
    player_id: str
    ts: int


@dataclass(frozen=True, slots=True, kw_only=True)
class AmendOrder:
    """Change an order's remaining quantity and/or price.

    Reducing quantity at the same price keeps queue priority. Any other change
    is a cancel-replace: the order keeps its id but goes to the back of the
    queue, and a limit order may match at its new price.
    """

    player_id: str
    ts: int
    order_id: int
    qty: int
    price: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SetQuote:
    """Atomically set the player's two-sided market ("Your Market").

    A side with qty 0 is pulled. A side whose price is unchanged keeps its
    priority if its quantity is unchanged or reduced.
    """

    player_id: str
    ts: int
    bid_price: int
    bid_qty: int
    ask_price: int
    ask_qty: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SetStatus:
    """Administrative: issued by the round controller, never by a player."""

    ts: int
    status: MarketStatus


Command = PlaceOrder | CancelOrder | CancelAll | AmendOrder | SetQuote | SetStatus
