"""Tests for objectives (PRD §10) and P&L attribution (PRD §17.2)."""

from __future__ import annotations

import random

import pytest

from whale.bots.personalities import ALL
from whale.engine import Side, Trade, TradeKind
from whale.game.objectives import BY_ID, OBJECTIVES, ObjectiveContext, deal_objectives
from whale.sim.harness import Seat, simulate_round

BY_NAME = {p.name: p for p in ALL}
TABLE = [Seat(f"bot{i}", BY_NAME[n]) for i, n in enumerate(("Market Maker", "Shark", "Noise Trader", "Bluffer"))]


def trade(tid: int, buyer: str, seller: str, qty: int, *, maker: str | None, ts: int = 1_000, price: int = 100) -> Trade:
    taker = None if maker is None else (seller if maker == buyer else buyer)
    return Trade(
        seq=tid, ts=ts, trade_id=tid, kind=TradeKind.BOOK if maker else TradeKind.AUCTION, price=price, qty=qty,
        buyer_id=buyer, seller_id=seller, maker_id=maker, taker_id=taker,
        aggressor_side=None if maker is None else (Side.BUY if taker == buyer else Side.SELL),
        buy_order_id=1, sell_order_id=2,
    )


def check(obj_id: str, player: str, trades: list[Trade], positions: dict[str, int], close_at: int = 190_000) -> bool:
    return BY_ID[obj_id].check(ObjectiveContext(player, trades, positions, close_at))


# -- objectives --------------------------------------------------------------------


def test_position_objectives() -> None:
    pos = {"a": 15, "b": -15, "c": 3, "d": -3}
    assert check("collector", "a", [], pos) and not check("collector", "c", [], pos)
    assert check("short_king", "b", [], pos) and not check("short_king", "d", [], pos)
    assert check("flat_finish", "c", [], pos) and check("flat_finish", "d", [], pos)
    assert not check("flat_finish", "a", [], pos)


def test_contrarian() -> None:
    assert check("contrarian", "a", [], {"a": 5, "b": -3, "c": -4})
    assert not check("contrarian", "a", [], {"a": 5, "b": 3, "c": -1})
    assert not check("contrarian", "a", [], {"a": 0, "b": 3, "c": -4})  # must hold a side
    assert not check("contrarian", "a", [], {"a": 5, "b": 3, "c": -3})  # table is flat


def test_volume_and_big_ticket() -> None:
    trades = [trade(i, "a", "b", 10, maker="b") for i in range(5)]
    assert check("volume_trader", "a", trades, {})
    assert not check("volume_trader", "a", trades[:4], {})
    assert check("big_ticket", "a", trades[:1], {})
    assert not check("big_ticket", "a", [trade(1, "a", "b", 9, maker="b")], {})
    assert not check("big_ticket", "a", [trade(1, "a", "b", 10, maker=None)], {})  # auction fills don't count


def test_market_maker_counts_only_passive_fills() -> None:
    passive = [trade(i, "a", "b", 1, maker="a") for i in range(5)] + [trade(10 + i, "b", "a", 1, maker="a") for i in range(5)]
    assert check("market_maker", "a", passive, {})
    taking = [trade(i, "a", "b", 1, maker="b") for i in range(5)] + [trade(10 + i, "b", "a", 1, maker="b") for i in range(5)]
    assert not check("market_maker", "a", taking, {})


def test_steady_hands_ignores_passive_fills() -> None:
    late = 175_000  # inside the final 30 s of a round closing at 190 s
    assert check("steady_hands", "a", [trade(1, "a", "b", 5, maker="a", ts=late)], {})
    assert not check("steady_hands", "a", [trade(1, "a", "b", 5, maker="b", ts=late)], {})
    assert check("steady_hands", "a", [trade(1, "a", "b", 5, maker="b", ts=100_000)], {})


def test_dealing_is_distinct_and_seeded() -> None:
    players = [f"p{i}" for i in range(len(OBJECTIVES))]
    dealt = deal_objectives(players, random.Random(3))
    assert len({o.id for o in dealt.values()}) == len(OBJECTIVES)
    assert dealt == deal_objectives(players, random.Random(3))


def test_bonuses_stay_below_trading() -> None:
    """PRD §10: an objective is worth about one good trade, never a whole round."""
    assert all(25 <= o.bonus <= 50 for o in OBJECTIVES)


# -- attribution -------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(12))
def test_attribution_sums_to_pnl_exactly(seed: int) -> None:
    s = simulate_round(TABLE, seed)
    for pr in s.result.players:
        assert pr.attribution.total_cents == pr.pnl_cents, pr.player_id
        assert sum(pr.attribution.adverse_by_counterparty.values()) == pr.attribution.adverse_selection_cents
        assert pr.player_id not in pr.attribution.adverse_by_counterparty
        assert pr.score_cents == pr.pnl_cents + pr.bonus_cents


def test_ranks_follow_score() -> None:
    s = simulate_round(TABLE, 5)
    scores = [p.score_cents for p in s.result.players]
    assert scores == sorted(scores, reverse=True)
    assert s.result.players[0].rank == 1


def test_makers_suffer_adverse_selection_on_average() -> None:
    """Across rounds, fills where bots were the maker lose value after the
    trade on average: informed takers pick them off (the core lesson)."""
    total = 0
    for seed in range(20):
        s = simulate_round(TABLE, seed)
        total += sum(p.attribution.adverse_selection_cents for p in s.result.players)
    assert total < 0
