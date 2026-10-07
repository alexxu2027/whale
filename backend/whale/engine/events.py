"""Events: the exchange's complete, ordered output.

Each event has a room-wide ``seq`` that increases by exactly one per event.
The event stream is the source of truth for replays, market data, and
analytics; the visibility layer decides which recipients see which events.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import CallOutcome, CancelReason, MarketStatus, OrderType, RejectReason, Side, TradeKind


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
    call_id: int | None = None


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
    """One fill. Who was maker and taker depends on ``kind``:

    - BOOK: the resting order's owner is maker, the incoming order's is taker.
    - CALL: the called player is maker, the caller is taker. No order ids.
    - AUCTION: no maker or taker, no aggressor, no fees.
    """

    trade_id: int
    kind: TradeKind
    price: int
    qty: int
    buyer_id: str
    seller_id: str
    maker_id: str | None
    taker_id: str | None
    aggressor_side: Side | None
    buy_order_id: int | None = None
    sell_order_id: int | None = None
    call_id: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class QuoteUpdated(Event):
    player_id: str
    bid_order_id: int | None
    ask_order_id: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class CallStarted(Event):
    call_id: int
    caller_id: str
    responder_id: str
    answer_by: int  # ts deadline


@dataclass(frozen=True, slots=True, kw_only=True)
class CallAnswered(Event):
    call_id: int
    responder_id: str
    bid_price: int
    ask_price: int
    qty: int
    automatic: bool  # the responder didn't answer; the engine quoted for them
    penalty_cents: int
    decide_by: int  # ts deadline


@dataclass(frozen=True, slots=True, kw_only=True)
class CallEnded(Event):
    call_id: int
    outcome: CallOutcome
    trade_id: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class StatusChanged(Event):
    status: MarketStatus
