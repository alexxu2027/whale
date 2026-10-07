"""Scenario tests pinning down each rule in PRD §28 with a concrete example."""

from __future__ import annotations

import pytest

from whale.engine import (
    AmendOrder,
    CancelAll,
    CancelOrder,
    CancelReason,
    Event,
    Exchange,
    MarketConfig,
    MarketStatus,
    OrderAccepted,
    OrderAmended,
    OrderCancelled,
    OrderType,
    PlaceOrder,
    QuoteUpdated,
    RejectReason,
    SetStatus,
)

from .harness import BUY, SELL, Harness, rejection, trades


@pytest.fixture
def h() -> Harness:
    return Harness()


# -- matching and priority -----------------------------------------------------


def test_non_crossing_orders_rest(h: Harness) -> None:
    h.place("alex", BUY, 99, 5)
    h.place("sam", SELL, 101, 3)
    assert h.ex.book.depth(BUY) == [(99, 5)]
    assert h.ex.book.depth(SELL) == [(101, 3)]


def test_cross_fills_at_resting_price_with_fees(h: Harness) -> None:
    h.place("sam", SELL, 101, 5)
    (t,) = trades(h.place("alex", BUY, 104, 5))
    assert (t.price, t.qty, t.buyer_id, t.seller_id, t.maker_id, t.taker_id) == (101, 5, "alex", "sam", "sam", "alex")
    alex, sam = h.account("alex"), h.account("sam")
    assert alex.position == 5 and sam.position == -5
    assert alex.cash_cents == -101 * 5 * 100 - 25 * 5  # paid price plus taker fee
    assert sam.cash_cents == 101 * 5 * 100 + 25 * 5  # received price plus maker rebate
    assert h.ex.house_cash_cents == 0


def test_price_then_time_priority_and_sweep(h: Harness) -> None:
    h.place("sam", SELL, 102, 4)
    h.place("maya", SELL, 101, 2)  # better price
    h.place("maya", SELL, 102, 3)  # same price as sam, later
    fills = trades(h.place("alex", BUY, 102, 8))
    assert [(t.price, t.qty, t.maker_id) for t in fills] == [(101, 2, "maya"), (102, 4, "sam"), (102, 2, "maya")]
    assert h.ex.book.depth(SELL) == [(102, 1)]


def test_partial_fill_rests_remainder(h: Harness) -> None:
    h.place("sam", SELL, 100, 3)
    h.place("alex", BUY, 100, 10)
    assert h.ex.book.depth(BUY) == [(100, 7)]
    assert h.ex.book.depth(SELL) == []


def test_ioc_cancels_remainder(h: Harness) -> None:
    h.place("sam", SELL, 100, 3)
    events = h.place("alex", BUY, 100, 10, order_type=OrderType.IOC)
    assert sum(t.qty for t in trades(events)) == 3
    cancel = events[-1]
    assert isinstance(cancel, OrderCancelled) and cancel.reason is CancelReason.IOC_REMAINDER
    assert cancel.remaining_qty == 7
    assert len(h.ex.book) == 0


def test_post_only_rejected_when_it_would_cross(h: Harness) -> None:
    h.place("sam", SELL, 100, 3)
    assert rejection(h.place("alex", BUY, 100, 1, order_type=OrderType.POST_ONLY)) is RejectReason.WOULD_CROSS
    h.place("alex", BUY, 99, 1, order_type=OrderType.POST_ONLY)
    assert h.ex.book.depth(BUY) == [(99, 1)]


# -- self-trade prevention -----------------------------------------------------


def test_self_trade_cancels_resting_and_continues(h: Harness) -> None:
    h.place("alex", SELL, 100, 2)
    h.place("sam", SELL, 101, 2)
    events = h.place("alex", BUY, 101, 2)
    cancels = [e for e in events if isinstance(e, OrderCancelled)]
    assert [c.reason for c in cancels] == [CancelReason.SELF_TRADE_PREVENTED]
    (t,) = trades(events)
    assert (t.price, t.seller_id) == (101, "sam")


# -- risk checks ---------------------------------------------------------------


def test_position_limit_counts_resting_orders() -> None:
    h = Harness(MarketConfig(position_limit=12, rate_limit_per_sec=None))
    h.place("alex", BUY, 95, 10)
    assert rejection(h.place("alex", BUY, 96, 3)) is RejectReason.POSITION_LIMIT
    h.place("alex", BUY, 96, 2)  # exactly at the limit
    h.place("alex", SELL, 110, 10)  # the other side has its own budget


def test_price_band_and_size_bounds(h: Harness) -> None:
    assert rejection(h.place("alex", BUY, 79, 1)) is RejectReason.PRICE_OUT_OF_BAND
    assert rejection(h.place("alex", BUY, 121, 1)) is RejectReason.PRICE_OUT_OF_BAND
    assert rejection(h.place("alex", BUY, 100, 0)) is RejectReason.INVALID_QTY
    assert rejection(h.place("alex", BUY, 100, 11)) is RejectReason.INVALID_QTY


def test_unknown_player_and_duplicate_client_id(h: Harness) -> None:
    assert rejection(h.place("eve", BUY, 100, 1)) is RejectReason.UNKNOWN_PLAYER
    h.place("alex", BUY, 99, 1, client_order_id="x1")
    assert rejection(h.place("alex", BUY, 98, 1, client_order_id="x1")) is RejectReason.DUPLICATE_CLIENT_ORDER_ID
    h.place("sam", BUY, 98, 1, client_order_id="x1")  # ids are per player


def test_rate_limit_refills_over_time() -> None:
    ex = Exchange(MarketConfig(rate_limit_per_sec=10, rate_limit_burst=2), ["alex"])
    place = lambda ts: ex.apply(PlaceOrder(player_id="alex", ts=ts, side=BUY, price=90, qty=1))  # noqa: E731
    assert isinstance(place(0)[0], OrderAccepted)
    assert isinstance(place(0)[0], OrderAccepted)
    assert rejection(place(0)) is RejectReason.RATE_LIMITED
    assert isinstance(place(100)[0], OrderAccepted)  # 100 ms at 10/s = 1 token
    # Cancels are never throttled.
    assert isinstance(ex.apply(CancelOrder(player_id="alex", ts=100, order_id=1))[0], OrderCancelled)


# -- cancels and amends ----------------------------------------------------------


def test_cancel_requires_ownership(h: Harness) -> None:
    oid = h.order_id(h.place("alex", BUY, 99, 5))
    assert rejection(h.send(CancelOrder, player_id="sam", order_id=oid)) is RejectReason.NOT_OWNER
    assert rejection(h.send(CancelOrder, player_id="alex", order_id=999)) is RejectReason.UNKNOWN_ORDER
    (c,) = h.send(CancelOrder, player_id="alex", order_id=oid)
    assert isinstance(c, OrderCancelled) and c.remaining_qty == 5
    assert h.account("alex").open_buy_qty == 0


def test_amend_size_down_keeps_priority(h: Harness) -> None:
    first = h.order_id(h.place("alex", BUY, 99, 5))
    h.place("maya", BUY, 99, 5)
    (amended,) = h.send(AmendOrder, player_id="alex", order_id=first, qty=2)
    assert isinstance(amended, OrderAmended) and amended.priority_kept
    (t, *_) = trades(h.place("sam", SELL, 99, 1))
    assert t.maker_id == "alex"


def test_amend_size_up_loses_priority(h: Harness) -> None:
    first = h.order_id(h.place("alex", BUY, 99, 2))
    h.place("maya", BUY, 99, 5)
    (amended,) = h.send(AmendOrder, player_id="alex", order_id=first, qty=4)
    assert not amended.priority_kept
    (t,) = trades(h.place("sam", SELL, 99, 1))
    assert t.maker_id == "maya"


def test_amend_price_into_cross_matches(h: Harness) -> None:
    h.place("sam", SELL, 101, 3)
    oid = h.order_id(h.place("alex", BUY, 98, 3))
    events = h.send(AmendOrder, player_id="alex", order_id=oid, qty=3, price=101)
    (t,) = trades(events)
    assert (t.price, t.buy_order_id, t.taker_id) == (101, oid, "alex")


def test_amend_no_change_rejected(h: Harness) -> None:
    oid = h.order_id(h.place("alex", BUY, 98, 3))
    assert rejection(h.send(AmendOrder, player_id="alex", order_id=oid, qty=3)) is RejectReason.NO_CHANGE


def test_cancel_all(h: Harness) -> None:
    h.place("alex", BUY, 98, 3)
    h.place("alex", SELL, 105, 3)
    h.place("sam", BUY, 97, 3)
    events = h.send(CancelAll, player_id="alex")
    assert len(events) == 2
    assert [o.player_id for o in h.ex.book.orders()] == ["sam"]


# -- quotes ("Your Market") --------------------------------------------------------


def quote(h: Harness, player: str, bid: int, bid_qty: int, ask: int, ask_qty: int) -> list[Event]:
    return h.quote(player, bid, bid_qty, ask, ask_qty)


def test_quote_posts_both_sides(h: Harness) -> None:
    events = quote(h, "alex", 98, 5, 102, 5)
    upd = events[-1]
    assert isinstance(upd, QuoteUpdated)
    assert h.ex.quotes["alex"] == (upd.bid_order_id, upd.ask_order_id)
    assert h.ex.book.depth(BUY) == [(98, 5)] and h.ex.book.depth(SELL) == [(102, 5)]


def test_quote_replace_is_atomic_and_may_jump_own_old_side(h: Harness) -> None:
    quote(h, "alex", 98, 5, 102, 5)
    # New bid 103 would cross the old ask 102, but the old ask is being replaced.
    quote(h, "alex", 103, 5, 107, 5)
    assert h.ex.book.depth(BUY) == [(103, 5)] and h.ex.book.depth(SELL) == [(107, 5)]


def test_quote_unchanged_side_keeps_priority(h: Harness) -> None:
    quote(h, "alex", 98, 5, 102, 5)
    h.place("maya", BUY, 98, 5)
    quote(h, "alex", 98, 5, 104, 5)  # only the ask moves
    (t, *_) = trades(h.place("sam", SELL, 98, 1))
    assert t.maker_id == "alex"


def test_invalid_quote_leaves_old_quote(h: Harness) -> None:
    quote(h, "alex", 98, 5, 102, 5)
    before = h.ex.quotes["alex"]
    assert rejection(quote(h, "alex", 102, 5, 102, 5)) is RejectReason.INVALID_QUOTE
    h.place("sam", SELL, 104, 1)
    assert rejection(quote(h, "alex", 105, 5, 108, 5)) is RejectReason.WOULD_CROSS
    assert h.ex.quotes["alex"] == before


def test_filled_quote_side_is_cleared(h: Harness) -> None:
    quote(h, "alex", 98, 5, 102, 5)
    h.place("sam", BUY, 102, 5)
    bid_id, ask_id = h.ex.quotes["alex"]
    assert bid_id is not None and ask_id is None


def test_pull_quote(h: Harness) -> None:
    quote(h, "alex", 98, 5, 102, 5)
    quote(h, "alex", 0, 0, 0, 0)
    assert h.ex.quotes["alex"] == (None, None)
    assert len(h.ex.book) == 0


# -- status and settlement ---------------------------------------------------------


def test_halt_blocks_new_risk_but_allows_reductions(h: Harness) -> None:
    oid = h.order_id(h.place("alex", BUY, 98, 5))
    h.send(SetStatus, status=MarketStatus.HALTED)
    assert rejection(h.place("sam", SELL, 98, 1)) is RejectReason.MARKET_NOT_OPEN
    assert rejection(h.send(AmendOrder, player_id="alex", order_id=oid, qty=5, price=99)) is RejectReason.MARKET_NOT_OPEN
    assert isinstance(h.send(AmendOrder, player_id="alex", order_id=oid, qty=2)[0], OrderAmended)
    assert isinstance(h.send(CancelOrder, player_id="alex", order_id=oid)[0], OrderCancelled)


def test_close_cancels_everything_and_settles(h: Harness) -> None:
    h.place("sam", SELL, 101, 5)
    h.place("alex", BUY, 101, 5)  # alex long 5 @ 101 (taker), sam short 5 (maker)
    h.place("maya", BUY, 90, 3)
    events = h.send(SetStatus, status=MarketStatus.CLOSED)
    assert [e.reason for e in events if isinstance(e, OrderCancelled)] == [CancelReason.MARKET_CLOSED]
    s = h.ex.settle(110)
    assert s["alex"].pnl_cents == (110 - 101) * 5 * 100 - 25 * 5
    assert s["sam"].pnl_cents == (101 - 110) * 5 * 100 + 25 * 5
    assert s["maya"].pnl_cents == 0
    assert rejection(h.place("alex", BUY, 100, 1)) is RejectReason.MARKET_NOT_OPEN


def test_settle_requires_closed_market(h: Harness) -> None:
    with pytest.raises(RuntimeError):
        h.ex.settle(100)
