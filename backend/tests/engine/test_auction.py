"""Scenario tests for pre-open and the opening auction (PRD §6 Phase 3, §28.7)."""

from __future__ import annotations

from whale.engine import (
    AmendOrder,
    CallPlayer,
    MarketConfig,
    MarketStatus,
    RejectReason,
    SetStatus,
    TradeKind,
)

from .harness import BUY, SELL, Harness, rejection, trades

PRE_OPEN = MarketStatus.PRE_OPEN
PLAYERS = ("alex", "sam", "maya", "jordan")


def open_market(h: Harness):
    return h.send(SetStatus, status=MarketStatus.OPEN)


def test_prd_example_opening() -> None:
    """PRD §43: Alex's 102 bid crosses Maya's 101 ask; the auction clears at
    102 with no imbalance, so Alex buys 5 from Maya at 102."""
    h = Harness(players=PLAYERS, status=PRE_OPEN)
    h.quote("alex", 102, 5, 106, 5)
    h.quote("sam", 101, 5, 105, 5)
    h.quote("maya", 97, 5, 101, 5)
    h.quote("jordan", 99, 5, 104, 5)
    assert h.ex.book.best_price(BUY) == 102 and h.ex.book.best_price(SELL) == 101  # crossed in pre-open

    (t,) = trades(open_market(h))
    assert (t.kind, t.price, t.qty, t.buyer_id, t.seller_id) == (TradeKind.AUCTION, 102, 5, "alex", "maya")
    assert t.maker_id is t.taker_id is t.aggressor_side is None
    assert h.ex.book.depth(BUY) == [(101, 5), (99, 5), (97, 5)]
    assert h.ex.book.depth(SELL) == [(104, 5), (105, 5), (106, 5)]
    # No fees in the auction.
    assert h.account("alex").cash_cents == -102 * 5 * 100
    assert h.account("maya").cash_cents == 102 * 5 * 100
    # Both filled quote sides are gone from the players' markets.
    assert h.ex.quotes["alex"][0] is None and h.ex.quotes["maya"][1] is None


def test_no_cross_no_trades() -> None:
    h = Harness(status=PRE_OPEN)
    h.quote("alex", 98, 5, 102, 5)
    h.quote("sam", 99, 5, 103, 5)
    assert trades(open_market(h)) == []
    assert h.ex.book.depth(BUY) == [(99, 5), (98, 5)]


def test_pre_open_only_accepts_quotes() -> None:
    h = Harness(status=PRE_OPEN)
    assert rejection(h.place("alex", BUY, 100, 1)) is RejectReason.MARKET_NOT_OPEN
    assert rejection(h.send(CallPlayer, player_id="alex", target_id="sam")) is RejectReason.MARKET_NOT_OPEN
    h.quote("alex", 98, 5, 102, 5)
    bid_id, _ = h.ex.quotes["alex"]
    assert rejection(h.send(AmendOrder, player_id="alex", order_id=bid_id, qty=5, price=99)) is RejectReason.MARKET_NOT_OPEN
    h.send(AmendOrder, player_id="alex", order_id=bid_id, qty=3)  # size reductions are fine
    assert rejection(h.send(SetStatus, status=MarketStatus.HALTED)) is RejectReason.INVALID_TRANSITION


def test_maximizes_volume_then_minimizes_imbalance() -> None:
    h = Harness(players=PLAYERS, status=PRE_OPEN)
    h.quote("alex", 104, 10, 110, 1)
    h.quote("sam", 101, 10, 111, 1)
    h.quote("maya", 90, 1, 100, 10)
    h.quote("jordan", 90, 1, 103, 5)
    fills = trades(open_market(h))
    # Buyers at or above p / sellers at or below p:
    #   p=100: 20/10   p=101: 20/10   p=103: 10/15   p=104: 10/15
    # Volume is 10 at all four. Imbalance is smallest (5) at 103 and 104,
    # and 103 is closer to the reference price of 100.
    assert sum(t.qty for t in fills) == 10
    assert {t.price for t in fills} == {103}


def test_tie_breaks_toward_reference_price() -> None:
    for ref, expected in ((None, 99), (101, 101)):
        h = Harness(MarketConfig(rate_limit_per_sec=None, reference_price=ref), status=PRE_OPEN)
        h.quote("alex", 101, 5, 115, 1)
        h.quote("sam", 85, 1, 99, 5)
        (t,) = trades(open_market(h))
        # 99 and 101 both clear 5 with no imbalance and are 1 from 100; the
        # lower wins by default, and a reference of 101 picks 101.
        assert t.price == expected


def test_ties_at_a_price_are_random_but_seeded() -> None:
    winners = set()
    for seed in range(20):
        results = []
        for _ in range(2):
            h = Harness(status=PRE_OPEN, seed=seed)
            h.quote("alex", 102, 5, 110, 1)
            h.quote("sam", 102, 5, 111, 1)
            h.quote("maya", 90, 1, 100, 5)
            (t,) = trades(open_market(h))
            results.append(t.buyer_id)
        assert results[0] == results[1]  # same seed, same allocation
        winners.add(results[0])
    assert winners == {"alex", "sam"}  # arriving first doesn't decide it


def test_market_is_uncrossed_after_auction() -> None:
    h = Harness(players=PLAYERS, status=PRE_OPEN, seed=3)
    for p, (bid, ask) in zip(PLAYERS, ((105, 108), (100, 103), (95, 99), (102, 106))):
        h.quote(p, bid, 7, ask, 4)
    open_market(h)  # the harness checks the uncrossed-book invariant
    bid, ask = h.ex.book.best_price(BUY), h.ex.book.best_price(SELL)
    assert bid is not None and ask is not None and bid < ask
