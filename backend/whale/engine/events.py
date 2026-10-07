"""Events: the exchange's complete, ordered output.

Each event has a room-wide ``seq`` that increases by exactly one per event.
The event stream is the source of truth for replays, market data, and
analytics; the visibility layer decides which recipients see which events.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import CancelReason, MarketStatus, OrderType, RejectReason, Side


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    seq: int
    ts: int


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderAccepted(Event):
    order_id: int
    player_id: str
    side: Side
    price: int
    qty: int
    order_type: OrderType
    client_order_id: str | None
    is_quote: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderRejected(Event):
    player_id: str | None
    reason: RejectReason
    order_id: int | None = None
    client_order_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderAmended(Event):
    order_id: int
    player_id: str
    price: int
    qty: int
    priority_kept: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderCancelled(Event):
    order_id: int
    player_id: str
    side: Side
    price: int
    remaining_qty: int
    reason: CancelReason


@dataclass(frozen=True, slots=True, kw_only=True)
class Trade(Event):
    trade_id: int
    price: int
    qty: int
    buyer_id: str
    seller_id: str
    maker_id: str
    taker_id: str
    maker_order_id: int
    taker_order_id: int
    aggressor_side: Side


@dataclass(frozen=True, slots=True, kw_only=True)
class QuoteUpdated(Event):
    player_id: str
    bid_order_id: int | None
    ask_order_id: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class StatusChanged(Event):
    status: MarketStatus
