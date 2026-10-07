"""Tests for the round controller (PRD §6, §42)."""

from __future__ import annotations

import random

import pytest

from whale.engine import (
    CallAnswered,
    CallPlayer,
    MarketConfig,
    OrderRejected,
    PlaceOrder,
    RejectReason,
    SetQuote,
    SetStatus,
    Side,
    StatusChanged,
    Tick,
    Trade,
    TradeKind,
)
from whale.game.recipes import FOUR_CARDS
from whale.game.round import Phase, Round, RoundConfig

PLAYERS = ["alex", "sam", "maya", "jordan"]
CONFIG = RoundConfig(market=MarketConfig(rate_limit_per_sec=None))


def quote(p: str, ts: int, bid: int, ask: int, qty: int = 5) -> SetQuote:
    return SetQuote(player_id=p, ts=ts, bid_price=bid, bid_qty=qty, ask_price=ask, ask_qty=qty)


def test_timeline_and_settlement() -> None:
    r = Round(FOUR_CARDS, PLAYERS, CONFIG, seed=1)
    assert (r.open_at, r.close_at) == (10_000, 190_000)
    assert (r.exchange.config.price_min, r.exchange.config.price_max) == (80, 120)
    assert r.phase is Phase.OPENING

    # Opening phase: quotes only, and they may cross.
    r.submit(quote("alex", 1_000, 102, 106))
    r.submit(quote("maya", 2_000, 97, 101))
    (rej,) = r.submit(PlaceOrder(player_id="sam", ts=3_000, side=Side.BUY, price=100, qty=1))
    assert isinstance(rej, OrderRejected) and rej.reason is RejectReason.MARKET_NOT_OPEN

    # The first command after 10 s opens the market (stamped at 10 s) and runs the auction.
    events = r.submit(PlaceOrder(player_id="sam", ts=12_000, side=Side.SELL, price=101, qty=3))
    opened, *rest = events
    assert isinstance(opened, StatusChanged) and opened.ts == 10_000
    auction = [e for e in rest if isinstance(e, Trade) and e.kind is TradeKind.AUCTION]
    # 101 and 102 both clear 5 with no imbalance; 101 is closer to the
    # reference price (100, the recipe mean).
    assert [(t.price, t.qty, t.buyer_id, t.seller_id) for t in auction] == [(101, 5, "alex", "maya")]
    assert r.phase is Phase.TRADING

    # Closing at 190 s settles the round.
    r.advance(200_000)
    assert r.phase is Phase.SETTLED and r.result is not None
    res = r.result
    assert res.final_value == r.setup.final_value
    assert sum(p.pnl_cents for p in res.players) + res.house_cash_cents == 0
    assert [p.rank for p in res.players] == sorted(p.rank for p in res.players)
    assert {p.player_id for p in res.players} == set(PLAYERS)
    assert all(p.clue is r.setup.clues[p.player_id] for p in res.players)

    (late,) = r.submit(PlaceOrder(player_id="sam", ts=200_001, side=Side.BUY, price=100, qty=1))
    assert late.reason is RejectReason.MARKET_NOT_OPEN


def test_advance_expires_calls() -> None:
    r = Round(FOUR_CARDS, PLAYERS, CONFIG, seed=2)
    r.advance(10_000)
    r.submit(CallPlayer(player_id="alex", ts=20_000, target_id="sam"))
    (auto,) = r.advance(26_000)
    assert isinstance(auto, CallAnswered) and auto.automatic and auto.ts == 25_000


def test_round_controls_status_and_time() -> None:
    r = Round(FOUR_CARDS, PLAYERS, CONFIG, seed=3)
    with pytest.raises(ValueError):
        r.submit(SetStatus(ts=1, status="open"))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        r.submit(Tick(ts=1))
    r.advance(5_000)
    with pytest.raises(ValueError):
        r.advance(4_999)


def random_commands(seed: int, n: int = 400) -> list:
    rng = random.Random(seed)
    cmds = []
    ts = 0
    for _ in range(n):
        ts += rng.randint(50, 900)
        p = rng.choice(PLAYERS)
        roll = rng.random()
        if roll < 0.5:
            bid = rng.randint(94, 106)
            cmds.append(quote(p, ts, bid, bid + rng.randint(1, 5), rng.randint(1, 10)))
        elif roll < 0.9:
            cmds.append(PlaceOrder(player_id=p, ts=ts, side=rng.choice(list(Side)), price=rng.randint(94, 106), qty=rng.randint(1, 10)))
        else:
            cmds.append(CallPlayer(player_id=p, ts=ts, target_id=rng.choice(PLAYERS)))
    return cmds


@pytest.mark.parametrize("seed", range(5))
def test_full_round_replays_exactly(seed: int) -> None:
    cmds = random_commands(seed)
    a = Round(FOUR_CARDS, PLAYERS, CONFIG, seed=seed)
    b = Round(FOUR_CARDS, PLAYERS, CONFIG, seed=seed)
    for cmd in cmds:
        a.submit(cmd)
        b.submit(cmd)
    end = max(a.close_at, cmds[-1].ts)
    a.advance(end)
    b.advance(end)
    assert a.log == b.log
    assert a.result == b.result
    assert a.result is not None
    assert sum(p.pnl_cents for p in a.result.players) + a.result.house_cash_cents == 0
    assert any(isinstance(e, Trade) for e in a.log)


def test_default_seed_is_random() -> None:
    assert Round(FOUR_CARDS, PLAYERS).seed != Round(FOUR_CARDS, PLAYERS).seed
