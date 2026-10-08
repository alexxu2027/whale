"""Runners: mid-round private news (PRD §7.7)."""

from __future__ import annotations

import random

import numpy as np
import pytest

from whale.bots.beliefs import WARY_MS, BeliefTracker, flow_model, flow_model_runner
from whale.game.posterior import belief, state_space
from whale.game.questions import Answer, ExactQ
from whale.game.recipes import FOUR_CARDS, PIT_SIX
from whale.game.round import Round, RoundConfig
from whale.game.runners import (
    MIN_GAP_MS,
    RUNNER_STRENGTH,
    RunnerArrived,
    RunnerDispatched,
    RunnerSlip,
    plan_runners,
)
from whale.game.setup import Dealing
from whale.runtime.visibility import is_visible

PLAYERS = ["ana", "ben", "cy", "dee"]


def rngs(seed: int) -> tuple[random.Random, random.Random, random.Random]:
    return random.Random(seed), random.Random(seed + 1), random.Random(seed + 2)


def test_recipe_keeps_the_price_band_and_runner_drivers() -> None:
    assert (PIT_SIX.min_value, PIT_SIX.max_value) == (82, 118)
    assert (PIT_SIX.price_min, PIT_SIX.price_max) == (80, 120)
    assert PIT_SIX.value_name == "settlement price"
    assert set(PIT_SIX.starting_drivers).isdisjoint(PIT_SIX.runner_drivers)


@pytest.mark.parametrize("seed", range(10))
def test_starting_clues_never_cover_runner_drivers(seed: int) -> None:
    rnd = Round(PIT_SIX, PLAYERS, seed=seed)
    for clue in rnd.setup.clues.values():
        assert set(clue.answer.question.components) <= set(PIT_SIX.starting_drivers)


@pytest.mark.parametrize("seed", range(20))
def test_one_runner_each_in_the_middle_of_the_window(seed: int) -> None:
    space = state_space(PIT_SIX)
    state = PIT_SIX.sample_state(random.Random(seed))
    plans = plan_runners(PIT_SIX, PLAYERS, state, 10_000, 190_000, 2_000, *rngs(seed))
    assert sorted(p.recipient for p in plans) == sorted(PLAYERS)
    assert [p.dispatch_at for p in plans] == sorted(p.dispatch_at for p in plans)
    for p in plans:
        assert 10_000 + 45_000 <= p.dispatch_at and p.arrive_at <= 10_000 + 135_000
        assert p.arrive_at - p.dispatch_at == 2_000
        q = p.clue.answer.question
        assert set(q.components) <= set(PIT_SIX.runner_drivers)
        assert RUNNER_STRENGTH[0] <= p.clue.strength <= RUNNER_STRENGTH[1]
        # Truthful: the answer is possible in the real state.
        assert p.clue.answer.likelihood(space)[space.index_of(state)] > 0
    gaps = np.diff([p.dispatch_at for p in plans])
    assert (gaps >= MIN_GAP_MS).mean() >= 0.5  # spacing is best effort


def test_questions_and_times_ignore_the_hidden_state() -> None:
    """Only the answers may depend on the state; what gets asked, of whom and
    when must not, or the schedule itself would leak information."""
    a = plan_runners(PIT_SIX, PLAYERS, (3,) * 6, 0, 180_000, 2_000, *rngs(7))
    b = plan_runners(PIT_SIX, PLAYERS, (-3,) * 6, 0, 180_000, 2_000, *rngs(7))
    shape = lambda ps: [(p.recipient, p.dispatch_at, p.clue.answer.question) for p in ps]
    assert shape(a) == shape(b)


def test_recipes_without_runner_drivers_get_no_runners() -> None:
    assert Round(FOUR_CARDS, PLAYERS, seed=1).runners == []
    assert Round(PIT_SIX, PLAYERS, RoundConfig(runners=False), seed=1).runners == []


def test_round_runs_runners_in_order_and_privately() -> None:
    rnd = Round(PIT_SIX, PLAYERS, seed=4)
    first = rnd.runners[0]
    rnd.advance(first.dispatch_at - 1)
    assert not [e for e in rnd.log if isinstance(e, RunnerDispatched)]
    assert rnd.next_scheduled() == first.dispatch_at
    rnd.advance(first.dispatch_at)
    assert rnd.information(first.recipient) == [rnd.setup.clues[first.recipient]]  # not arrived yet
    rnd.advance(first.arrive_at)
    assert rnd.information(first.recipient)[-1] is first.clue
    rnd.advance(rnd.close_at)

    runner_events = [e for e in rnd.log if isinstance(e, (RunnerDispatched, RunnerArrived, RunnerSlip))]
    assert len(runner_events) == 3 * len(PLAYERS)
    seqs = [e.seq for e in rnd.log]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    for e in runner_events:
        if isinstance(e, RunnerSlip):
            assert [p for p in PLAYERS if is_visible(e, p)] == [e.player_id]
        else:
            assert all(is_visible(e, p) for p in PLAYERS)
            assert not hasattr(e, "precise")
    assert rnd.result is not None
    for pr in rnd.result.players:
        assert len(pr.runner_clues) == 1


def test_late_runners_never_arrive_after_the_close() -> None:
    cfg = RoundConfig(opening_ms=1_000, trading_ms=10_000)
    rnd = Round(PIT_SIX, PLAYERS, cfg, seed=3)
    rnd.advance(rnd.close_at)
    assert all(e.ts < rnd.close_at for e in rnd.log if isinstance(e, (RunnerArrived, RunnerSlip)))


# -- bots --------------------------------------------------------------------------


def test_runner_flow_model_is_a_probability() -> None:
    f = flow_model_runner(PIT_SIX, Dealing.ONE_CARD_EACH, ExactQ(0))
    assert f.above.min() >= 0 and f.below.min() >= 0
    assert np.allclose(f.above + f.below, 1)
    # Knowing more never makes traders less likely to disagree with a price
    # far from the prior: near the band edges both models agree everyone sides one way.
    plain = flow_model(PIT_SIX, Dealing.ONE_CARD_EACH, ExactQ(0))
    assert np.allclose(f.above[0], plain.above[0]) and np.allclose(f.below[-1], plain.below[-1])


def test_runner_flow_model_matches_brute_force_on_a_few_states() -> None:
    from whale.game.runners import runner_candidates

    space = state_space(PIT_SIX)
    f = flow_model_runner(PIT_SIX, Dealing.ONE_CARD_EACH, ExactQ(0))
    starts = [ExactQ(i) for i in (1, 2, 3)]
    runs = [q for qs in runner_candidates(PIT_SIX).values() for q in qs]
    rng = random.Random(0)
    for _ in range(3):
        s = rng.randrange(space.size)
        price = rng.randint(95, 105)
        want = 0.0
        for qs in starts:
            for qr in runs:
                Ls, Lr = space.likelihoods(qs), space.likelihoods(qr)
                for a in range(Ls.shape[0]):
                    for b in range(Lr.shape[0]):
                        p = Ls[a, s] * Lr[b, s]
                        if p == 0:
                            continue
                        fv = belief(space, [Answer(qs, a), Answer(qr, b)]).mean
                        want += p * (1.0 if fv > price + 1e-9 else 0.5 if abs(fv - price) <= 1e-9 else 0.0)
        want /= len(starts) * len(runs)
        assert f.row(price, buy=True)[s] == pytest.approx(want)


def test_bots_widen_after_a_runner_then_relax() -> None:
    t = BeliefTracker(PIT_SIX, Dealing.ONE_CARD_EACH, Answer(ExactQ(0), 3), 0.6)
    calm_bid, calm_ask = t.regret_free_quote(None)
    t.runner_arrived("ben", 50_000)
    bid, ask = t.regret_free_quote(50_000)
    assert ask - bid > calm_ask - calm_bid
    assert t.regret_free_quote(50_000 + WARY_MS + 1) == (calm_bid, calm_ask)


def test_bot_learns_its_own_runner_slip_exactly() -> None:
    space = state_space(PIT_SIX)
    rnd = Round(PIT_SIX, PLAYERS, seed=9)
    plan = rnd.runners[0]
    own = rnd.setup.clues[plan.recipient].answer
    t = BeliefTracker(PIT_SIX, Dealing.ONE_CARD_EACH, own, 0.5)
    t.add_own(plan.clue.answer)
    assert t.fair_value()[0] == pytest.approx(belief(space, [own, plan.clue.answer]).mean)


def test_simulated_round_with_runners_trades_and_settles() -> None:
    from whale.sim.harness import default_table, simulate_round

    s = simulate_round(default_table(), seed=2, recipe=PIT_SIX)
    assert len(s.runners) == 4
    assert s.trades > 0
