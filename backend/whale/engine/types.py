"""Core value types shared by the order book and the exchange."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"

    @property
    def opposite(self) -> Side:
        return Side.SELL if self is Side.BUY else Side.BUY


class OrderType(StrEnum):
    LIMIT = "limit"  # match what crosses, rest the remainder
    IOC = "ioc"  # match what crosses, cancel the remainder
    POST_ONLY = "post_only"  # rejected if it would match on arrival


class MarketStatus(StrEnum):
    PRE_OPEN = "pre_open"  # opening phase: quotes rest without matching
    OPEN = "open"
    HALTED = "halted"  # no new risk; cancels and size reductions allowed
    CLOSED = "closed"  # round over; book emptied, ready to settle


class RejectReason(StrEnum):
    UNKNOWN_PLAYER = "unknown_player"
    MARKET_NOT_OPEN = "market_not_open"
    RATE_LIMITED = "rate_limited"
    PRICE_OUT_OF_BAND = "price_out_of_band"
    INVALID_QTY = "invalid_qty"
    POSITION_LIMIT = "position_limit"
    WOULD_CROSS = "would_cross"
    INVALID_QUOTE = "invalid_quote"
    UNKNOWN_ORDER = "unknown_order"
    NOT_OWNER = "not_owner"
    DUPLICATE_CLIENT_ORDER_ID = "duplicate_client_order_id"
    NO_CHANGE = "no_change"
    SELF_CALL = "self_call"
    PLAYER_BUSY = "player_busy"
    CALL_COOLDOWN = "call_cooldown"
    TARGET_AT_LIMIT = "target_at_limit"
    UNKNOWN_CALL = "unknown_call"
    NOT_YOUR_CALL = "not_your_call"
    CALL_WRONG_STAGE = "call_wrong_stage"
    INVALID_TRANSITION = "invalid_transition"


class CancelReason(StrEnum):
    USER = "user"
    IOC_REMAINDER = "ioc_remainder"
    SELF_TRADE_PREVENTED = "self_trade_prevented"
    QUOTE_REPLACED = "quote_replaced"
    MARKET_CLOSED = "market_closed"


class TradeKind(StrEnum):
    BOOK = "book"  # an incoming order matched a resting order
    AUCTION = "auction"  # opening auction; no maker or taker, no fees
    CALL = "call"  # Make Me a Market; responder is maker, caller is taker


class CallOutcome(StrEnum):
    TRADED = "traded"
    PASSED = "passed"
    DECISION_TIMEOUT = "decision_timeout"  # caller didn't decide in time
    CANCELLED = "cancelled"  # halt, close, or responder unable to quote


@dataclass(slots=True)
class Order:
    """A live order. ``qty`` is the remaining quantity.

    ``priority`` is a monotonically increasing sequence number assigned when the
    order (re)enters the book; lower means earlier in the time queue.

    Order objects are never re-inserted after removal: a cancel-replace creates
    a new object with the same ``order_id``. The fast book relies on this.
    """

    order_id: int
    player_id: str
    side: Side
    price: int
    qty: int
    priority: int
    order_type: OrderType = OrderType.LIMIT
    client_order_id: str | None = None
    is_quote: bool = False
    live: bool = True
