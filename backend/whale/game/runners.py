"""Runners: mid-round private news (PRD §7.7).

Each player gets one runner per round, at a random time in the middle of the
trading window. Everyone sees the runner cross the floor toward the
recipient's booth; only the recipient reads the slip.

A runner slip is one more clue. Its question is chosen without looking at the
hidden state and answered from the question's likelihoods (``questions.py``),
so fair values stay exact. Questions are always about the recipe's
runner-only drivers, so a runner brings information nobody started with.
"""

from __future__ import annotations

import functools
import random
from collections.abc import Sequence
from dataclasses import dataclass

from whale.engine import Event

from .dealing import Clue
from .flavor import flavor_text
from .posterior import StateSpace, state_space, strength
from .questions import ExactQ, Question, RangeQ, SignQ
from .recipes import Recipe

RUNNER_STRENGTH = (0.08, 0.25)
MIN_GAP_MS = 4_000  # keep runners from landing on top of each other


@dataclass(frozen=True, slots=True, kw_only=True)
class RunnerDispatched(Event):
    """Public: a runner has left a booth and is crossing the floor."""

    runner_id: int
    recipient_id: str
    arrive_at: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RunnerArrived(Event):
    """Public: the runner reached the recipient's booth."""

    runner_id: int
    recipient_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RunnerSlip(Event):
    """Private to the recipient: what the slip says."""

    runner_id: int
    player_id: str
    flavor: str
    precise: str


@dataclass(frozen=True, slots=True)
class RunnerPlan:
    runner_id: int
    recipient: str
    dispatch_at: int
    arrive_at: int
    clue: Clue


@functools.cache
def runner_candidates(recipe: Recipe) -> dict[int, tuple[Question, ...]]:
    """Questions a runner may answer, per runner-only driver, within the strength band."""
    space = state_space(recipe)
    lo, hi = RUNNER_STRENGTH
    out: dict[int, tuple[Question, ...]] = {}
    for c in recipe.runner_drivers:
        qs: list[Question] = [ExactQ(c), SignQ(c)]
        qs += [RangeQ(c, w, o) for w in (2, 3) for o in range(w)]
        out[c] = tuple(q for q in qs if lo <= strength(space, q) <= hi)
    return out


def plan_runners(
    recipe: Recipe,
    players: Sequence[str],
    state: tuple[int, ...],
    open_at: int,
    close_at: int,
    travel_ms: int,
    question_rng: random.Random,
    answer_rng: random.Random,
    flavor_rng: random.Random,
) -> list[RunnerPlan]:
    """One runner per player, sorted by dispatch time. Questions and times are
    drawn without looking at ``state``; only the answers use it."""
    if not recipe.runner_drivers or not players:
        return []
    space: StateSpace = state_space(recipe)
    candidates = runner_candidates(recipe)
    order = list(players)
    question_rng.shuffle(order)

    window_start = open_at + (close_at - open_at) // 4
    window_end = open_at + 3 * (close_at - open_at) // 4 - travel_ms
    times: list[int] = []
    for _ in order:
        t = question_rng.randint(window_start, max(window_start, window_end))
        for _attempt in range(20):
            if all(abs(t - other) >= MIN_GAP_MS for other in times):
                break
            t = question_rng.randint(window_start, max(window_start, window_end))
        times.append(t)

    s = space.index_of(state)
    plans = []
    for k, (player, t) in enumerate(zip(order, times, strict=True)):
        driver = recipe.runner_drivers[k % len(recipe.runner_drivers)]
        q = question_rng.choice(candidates[driver])
        answer = q.answer(space, s, answer_rng)
        clue = Clue(answer=answer, flavor=flavor_text(space, answer, flavor_rng), precise=answer.text(recipe), strength=strength(space, q))
        plans.append(RunnerPlan(runner_id=k + 1, recipient=player, dispatch_at=t, arrive_at=t + travel_ms, clue=clue))
    return sorted(plans, key=lambda r: r.dispatch_at)
