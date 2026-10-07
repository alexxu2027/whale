"""Scenario tests for Make Me a Market (PRD §8.2)."""

from __future__ import annotations

import pytest

from whale.engine import (
    AnswerCall,
    CallAnswered,
    CallEnded,
    CallOutcome,
    CallPlayer,
    CallStarted,
    DecideCall,
    MarketConfig,
    MarketStatus,
    RejectReason,
    SetStatus,
    Tick,
    TradeKind,
)

from .harness import BUY, CONFIG, SELL, Harness, of_type, rejection, trades

# Defaults under test: width <= 4, size >= 5, 5 s to answer, 5 s to decide,
# 15 s caller cooldown, 5 s responder busy window, 5-point no-answer penalty.
assert (CONFIG.call_max_width, CONFIG.call_min_qty, CONFIG.call_answer_ms) == (4, 5, 5_000)


@pytest.fixture
def h() -> Harness:
    return Harness()


def call(h: Harness, caller: str, target: str, at: int | None = None) -> int:
    (started,) = h.send(CallPlayer, at=at, player_id=caller, target_id=target)
    assert isinstance(started, CallStarted)
    return started.call_id


def answer(h: Harness, call_id: int, responder: str, bid: int, ask: int, qty: int = 5):
    return h.send(AnswerCall, player_id=responder, call_id=call_id, bid_price=bid, ask_price=ask, qty=qty)


def decide(h: Harness, call_id: int, caller: str, side):
    return h.send(DecideCall, player_id=caller, call_id=call_id, side=side)


# -- happy paths -------------------------------------------------------------------


def test_call_buy_trades_at_ask_with_fees(h: Harness) -> None:
    cid = call(h, "alex", "sam", at=1_000)
    (answered,) = answer(h, cid, "sam", 98, 102)
    assert isinstance(answered, CallAnswered) and answered.decide_by == 1_001 + 5_000
    events = decide(h, cid, "alex", BUY)
    (t,) = trades(events)
    assert (t.kind, t.price, t.qty, t.buyer_id, t.seller_id) == (TradeKind.CALL, 102, 5, "alex", "sam")
    assert (t.maker_id, t.taker_id, t.aggressor_side, t.call_id) == ("sam", "alex", BUY, cid)
    (ended,) = of_type(events, CallEnded)
    assert (ended.outcome, ended.trade_id) == (CallOutcome.TRADED, t.trade_id)
    assert h.account("sam").cash_cents == 102 * 5 * 100 + 25 * 5  # maker rebate
    assert h.account("alex").cash_cents == -102 * 5 * 100 - 25 * 5  # taker fee
    assert h.ex.calls == {}


def test_call_sell_trades_at_bid(h: Harness) -> None:
    cid = call(h, "alex", "sam")
    answer(h, cid, "sam", 98, 102)
    (t,) = trades(decide(h, cid, "alex", SELL))
    assert (t.price, t.buyer_id, t.seller_id) == (98, "sam", "alex")


def test_pass_releases_reservation(h: Harness) -> None:
    cid = call(h, "alex", "sam")
    answer(h, cid, "sam", 98, 102, qty=7)
    assert h.account("sam").call_reserved_qty == 7
    (ended,) = decide(h, cid, "alex", None)
    assert ended.outcome is CallOutcome.PASSED
    assert h.account("sam").call_reserved_qty == 0


# -- deadlines ---------------------------------------------------------------------


def test_no_answer_uses_qualifying_own_market_without_penalty(h: Harness) -> None:
    h.quote("sam", 99, 5, 102, 5)
    cid = call(h, "alex", "sam", at=1_000)
    (auto,) = h.send(Tick, at=6_000)
    assert isinstance(auto, CallAnswered) and auto.automatic
    assert (auto.bid_price, auto.ask_price, auto.qty, auto.penalty_cents) == (99, 102, 5, 0)
    assert auto.ts == 6_000 and auto.call_id == cid


def test_no_answer_without_market_quotes_max_width_with_penalty(h: Harness) -> None:
    call(h, "alex", "sam", at=1_000)
    (auto,) = h.send(Tick, at=6_000)
    assert (auto.bid_price, auto.ask_price, auto.penalty_cents) == (98, 102, 500)  # around reference 100
    assert h.account("sam").penalties_cents == 500
    assert h.ex.house_cash_cents == 500


def test_no_answer_too_wide_market_is_recentred_with_penalty(h: Harness) -> None:
    h.quote("sam", 90, 5, 110, 5)
    call(h, "alex", "sam", at=1_000)
    (auto,) = h.send(Tick, at=6_000)
    assert (auto.bid_price, auto.ask_price, auto.penalty_cents) == (98, 102, 500)


def test_no_answer_falls_back_to_book_middle(h: Harness) -> None:
    h.quote("maya", 105, 5, 109, 5)
    call(h, "alex", "sam", at=1_000)
    (auto,) = h.send(Tick, at=6_000)
    assert (auto.bid_price, auto.ask_price) == (105, 109)


def test_deadlines_cascade_with_exact_timestamps(h: Harness) -> None:
    cid = call(h, "alex", "sam", at=1_000)
    events = h.send(Tick, at=60_000)
    auto, ended = events
    assert isinstance(auto, CallAnswered) and auto.ts == 6_000
    assert isinstance(ended, CallEnded) and ended.ts == 11_000
    assert (ended.call_id, ended.outcome) == (cid, CallOutcome.DECISION_TIMEOUT)
    assert h.account("sam").call_reserved_qty == 0


def test_deadline_is_processed_before_a_late_command(h: Harness) -> None:
    cid = call(h, "alex", "sam", at=1_000)
    events = h.send(AnswerCall, at=6_000, player_id="sam", call_id=cid, bid_price=98, ask_price=102, qty=5)
    auto, rejected = events
    assert isinstance(auto, CallAnswered) and auto.automatic
    assert rejected.reason is RejectReason.CALL_WRONG_STAGE


# -- rejections --------------------------------------------------------------------


def test_cannot_call_yourself_or_unknown_players(h: Harness) -> None:
    assert rejection(h.send(CallPlayer, player_id="alex", target_id="alex")) is RejectReason.SELF_CALL
    assert rejection(h.send(CallPlayer, player_id="alex", target_id="eve")) is RejectReason.UNKNOWN_PLAYER


def test_one_call_at_a_time_per_player(h: Harness) -> None:
    call(h, "alex", "sam")
    assert rejection(h.send(CallPlayer, player_id="maya", target_id="sam")) is RejectReason.PLAYER_BUSY
    assert rejection(h.send(CallPlayer, player_id="maya", target_id="alex")) is RejectReason.PLAYER_BUSY
    assert rejection(h.send(CallPlayer, player_id="sam", target_id="maya")) is RejectReason.PLAYER_BUSY


def test_responder_busy_window_and_caller_cooldown(h: Harness) -> None:
    cid = call(h, "alex", "sam", at=1_000)
    answer(h, cid, "sam", 98, 102)
    h.send(DecideCall, at=2_000, player_id="alex", call_id=cid, side=None)
    r = h.send(CallPlayer, at=6_999, player_id="maya", target_id="sam")
    assert rejection(r) is RejectReason.PLAYER_BUSY
    call(h, "maya", "sam", at=7_000)  # busy window over
    h.send(SetStatus, at=7_001, status=MarketStatus.HALTED)
    h.send(SetStatus, at=7_002, status=MarketStatus.OPEN)
    assert rejection(h.send(CallPlayer, at=15_999, player_id="alex", target_id="maya")) is RejectReason.CALL_COOLDOWN
    call(h, "alex", "maya", at=16_000)


def test_target_at_limit_cannot_be_called() -> None:
    h = Harness(MarketConfig(rate_limit_per_sec=None, position_limit=12))
    h.place("sam", BUY, 100, 10)  # worst case long 10: no room for 5 more
    assert rejection(h.send(CallPlayer, player_id="alex", target_id="sam")) is RejectReason.TARGET_AT_LIMIT


def test_only_the_right_player_can_answer_or_decide(h: Harness) -> None:
    cid = call(h, "alex", "sam")
    assert rejection(answer(h, cid, "alex", 98, 102)) is RejectReason.NOT_YOUR_CALL
    assert rejection(decide(h, cid, "alex", BUY)) is RejectReason.CALL_WRONG_STAGE
    answer(h, cid, "sam", 98, 102)
    assert rejection(answer(h, cid, "sam", 98, 102)) is RejectReason.CALL_WRONG_STAGE
    assert rejection(decide(h, cid, "sam", BUY)) is RejectReason.NOT_YOUR_CALL
    assert rejection(decide(h, 999, "alex", BUY)) is RejectReason.UNKNOWN_CALL


@pytest.mark.parametrize(
    ("bid", "ask", "qty", "reason"),
    [
        (98, 103, 5, RejectReason.INVALID_QUOTE),  # too wide
        (100, 100, 5, RejectReason.INVALID_QUOTE),  # zero width
        (102, 98, 5, RejectReason.INVALID_QUOTE),  # inverted
        (98, 102, 4, RejectReason.INVALID_QTY),  # below minimum size
        (78, 80, 5, RejectReason.PRICE_OUT_OF_BAND),
    ],
)
def test_answer_validation(h: Harness, bid: int, ask: int, qty: int, reason: RejectReason) -> None:
    cid = call(h, "alex", "sam")
    assert rejection(answer(h, cid, "sam", bid, ask, qty)) is reason


def test_answer_reserves_size_against_the_limit() -> None:
    h = Harness(MarketConfig(rate_limit_per_sec=None, position_limit=12))
    cid = call(h, "alex", "sam")
    answer(h, cid, "sam", 98, 102, qty=10)
    assert rejection(h.place("sam", BUY, 90, 5)) is RejectReason.POSITION_LIMIT
    assert rejection(h.place("sam", SELL, 110, 5)) is RejectReason.POSITION_LIMIT
    decide(h, cid, "alex", None)
    h.place("sam", BUY, 90, 5)


def test_caller_over_limit_cannot_take_but_can_pass() -> None:
    h = Harness(MarketConfig(rate_limit_per_sec=None, position_limit=12))
    h.place("alex", BUY, 90, 10)
    cid = call(h, "alex", "sam")
    answer(h, cid, "sam", 98, 102)
    assert rejection(decide(h, cid, "alex", BUY)) is RejectReason.POSITION_LIMIT
    assert h.ex.calls  # still open
    (t,) = trades(decide(h, cid, "alex", SELL))  # selling reduces exposure
    assert t.seller_id == "alex"


def test_halt_and_close_cancel_calls(h: Harness) -> None:
    call(h, "alex", "sam")
    events = h.send(SetStatus, status=MarketStatus.HALTED)
    (ended,) = of_type(events, CallEnded)
    assert ended.outcome is CallOutcome.CANCELLED
    h.send(SetStatus, status=MarketStatus.OPEN)
    cid = call(h, "maya", "alex")
    answer(h, cid, "alex", 98, 102)
    events = h.send(SetStatus, status=MarketStatus.CLOSED)
    assert [e.outcome for e in of_type(events, CallEnded)] == [CallOutcome.CANCELLED]
    assert h.account("alex").call_reserved_qty == 0
