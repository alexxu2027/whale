"""Tests for bot beliefs, bot behavior, visibility, and the simulator (PRD §19, §32.4)."""

from __future__ import annotations

import itertools
import statistics

import numpy as np
import pytest

from whale.bots.beliefs import BeliefTracker, flow_model
from whale.bots.bot import Bot
from whale.bots.personalities import ALL, MARKET_MAKER, NOISE, SHARK, Difficulty, with_difficulty
from whale.engine import (
    OrderAccepted,
    OrderRejected,
    QuoteUpdated,
    RejectReason,
    Side,
    StatusChanged,
    Trade,
    TradeKind,
)
from whale.game.posterior import state_space
from whale.game.questions import Answer, ExactQ
from whale.game.recipes import FOUR_CARDS
from whale.game.setup import Dealing
from whale.runtime.visibility import is_visible
from whale.sim.harness import Seat, simulate_round

SPACE = state_space(FOUR_CARDS)
BY_NAME = {p.name: p for p in ALL}
INFORMED = [Seat(f"bot{i}", BY_NAME[n]) for i, n in enumerate(("Market Maker", "Shark", "Conservative", "Bluffer"))]


def tracker(card: int = 0, own_component: int = 0, pi: float = 0.5) -> BeliefTracker:
    answer = Answer(ExactQ(own_component), card + 5)
    return BeliefTracker(FOUR_CARDS, Dealing.ONE_CARD_EACH, answer, pi)


# -- flow model --------------------------------------------------------------------


def test_flow_model_matches_brute_force() -> None:
    """With one card each, another player's FV is 100 + one of the three
    components I don't hold, each equally likely."""
    fm = flow_model(FOUR_CARDS, Dealing.ONE_CARD_EACH, ExactQ(0))
    states = list(itertools.product(range(-5, 6), repeat=4))[::997]
    for state, price in itertools.product(states, (95, 100, 103)):
        s = SPACE.index_of(state)
        fvs = [100 + state[c] for c in (1, 2, 3)]
        above = statistics.fmean((fv > price) + 0.5 * (fv == price) for fv in fvs)
        below = statistics.fmean((fv < price) + 0.5 * (fv == price) for fv in fvs)
        assert fm.row(price, buy=True)[s] == pytest.approx(above)
        assert fm.row(price, buy=False)[s] == pytest.approx(below)
        inside = statistics.fmean(1.0 - ((fv < price) + 0.5 * (fv == price)) - ((fv > price + 2) + 0.5 * (fv == price + 2)) for fv in fvs)
        assert fm.within(price, price + 2)[s] == pytest.approx(inside)


def test_flow_model_probabilities_are_valid() -> None:
    for dealing, own in ((Dealing.ONE_CARD_EACH, ExactQ(2)), (Dealing.BALANCED, ExactQ(2))):
        fm = flow_model(FOUR_CARDS, dealing, own)
        assert (fm.above >= 0).all() and (fm.above <= 1).all()
        np.testing.assert_allclose(fm.above + fm.below <= 1 + 1e-9, True)


# -- belief tracker ----------------------------------------------------------------


def test_no_evidence_is_the_clue_posterior() -> None:
    mean, sd = tracker(card=3).fair_value()
    assert mean == pytest.approx(103)
    assert sd == pytest.approx(np.sqrt(30))


def test_buys_raise_and_sells_lower_fair_value() -> None:
    t = tracker()
    t.observe_take("sam", bought=True, price=103)
    up = t.fair_value()[0]
    assert up > 100
    t.observe_take("sam", bought=True, price=101)  # a lower buy adds nothing new
    assert t.fair_value()[0] == up
    t.observe_take("maya", bought=False, price=97)
    assert t.fair_value()[0] < up


def test_ignoring_flow_means_no_update() -> None:
    t = tracker(pi=0.0)
    t.observe_take("sam", bought=True, price=104)
    t.observe_answer("maya", 106, 110)
    assert t.fair_value()[0] == pytest.approx(100)


def test_call_answer_pulls_toward_quoted_range() -> None:
    t = tracker()
    t.observe_answer("sam", 103, 107)
    assert t.fair_value()[0] > 100.5
    t2 = tracker()
    t2.observe_answer("sam", 93, 97)
    assert t2.fair_value()[0] < 99.5


def test_impossible_evidence_does_not_break_the_belief() -> None:
    t = tracker(pi=1.0)
    t.observe_answer("sam", 116, 120)  # no single card puts anyone's FV here
    mean, sd = t.fair_value()
    assert np.isfinite(mean) and np.isfinite(sd)


# -- visibility --------------------------------------------------------------------


def test_visibility() -> None:
    accepted = OrderAccepted(
        seq=1, ts=0, order_id=1, player_id="alex", side=Side.BUY, price=100, qty=1,
        order_type="limit", client_order_id=None, is_quote=False,  # type: ignore[arg-type]
    )
    rejected = OrderRejected(seq=2, ts=0, player_id="alex", reason=RejectReason.INVALID_QTY)
    quote = QuoteUpdated(seq=3, ts=0, player_id="alex", bid_order_id=1, ask_order_id=None)
    trade = Trade(
        seq=4, ts=0, trade_id=1, kind=TradeKind.BOOK, price=100, qty=1, buyer_id="alex",
        seller_id="sam", maker_id="sam", taker_id="alex", aggressor_side=Side.BUY,
    )
    status = StatusChanged(seq=5, ts=0, status="open")  # type: ignore[arg-type]
    for private in (accepted, rejected, quote):
        assert is_visible(private, "alex") and not is_visible(private, "sam")
    for public in (trade, status):
        assert is_visible(public, "alex") and is_visible(public, "maya")


# -- simulation --------------------------------------------------------------------


def test_simulation_is_deterministic_and_zero_sum() -> None:
    a = simulate_round(INFORMED, seed=11)
    b = simulate_round(INFORMED, seed=11)
    assert a.result == b.result
    assert {k: (v.pnl, v.volume) for k, v in a.players.items()} == {k: (v.pnl, v.volume) for k, v in b.players.items()}
    total = sum(p.pnl_cents for p in a.result.players) + a.result.house_cash_cents
    assert total == 0


def test_bots_play_cleanly_and_make_markets() -> None:
    rejections = commands = 0
    quoted_both_sides = False
    for seed in range(15):
        s = simulate_round(INFORMED, seed)
        rejections += sum(p.rejections for p in s.players.values())
        commands += sum(p.commands for p in s.players.values())
        mm = s.players["bot0"]
        quoted_both_sides |= mm.passive_qty > 0
        assert s.trades > 0
    assert rejections / commands < 0.06
    assert quoted_both_sides


def test_learning_makes_bots_more_accurate(monkeypatch: pytest.MonkeyPatch) -> None:
    last_fv: dict[str, float] = {}
    act = Bot.act

    def spy(self: Bot, view):  # record each bot's latest belief
        last_fv[self.player_id] = self.tracker.fair_value()[0]
        return act(self, view)

    monkeypatch.setattr(Bot, "act", spy)
    start, end = [], []
    for seed in range(30):
        s = simulate_round(INFORMED, seed)
        v = s.result.final_value
        for pr in s.result.players:
            start.append(abs(100 + s.result.state[pr.clue.answer.question.i] - v))
            end.append(abs(last_fv[pr.player_id] - v))
    assert statistics.fmean(end) < statistics.fmean(start) - 0.5


def test_noise_trader_loses_on_average() -> None:
    seats = [Seat("mm", MARKET_MAKER), Seat("shark", SHARK), Seat("noise", NOISE), Seat("mm2", MARKET_MAKER)]
    pnl = [simulate_round(seats, seed).players["noise"].pnl for seed in range(30)]
    assert statistics.fmean(pnl) < 0


def test_hard_bots_beat_easy_bots() -> None:
    seats = [
        Seat(f"{d.value}{i}", with_difficulty(SHARK, d))
        for i, d in enumerate((Difficulty.HARD, Difficulty.EASY, Difficulty.HARD, Difficulty.EASY))
    ]
    hard, easy = [], []
    for seed in range(60):
        for name, ps in simulate_round(seats, seed).players.items():
            (hard if name.startswith("hard") else easy).append(ps.pnl)
    assert statistics.fmean(hard) > statistics.fmean(easy)
