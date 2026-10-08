"""Bot beliefs: exact posterior from the bot's clue, updated on order flow (PRD §19.2).

A bot starts from ``prior * L[own answer]``. When another player *takes*
liquidity (an aggressive buy or sell, or the decision on a call), that is
evidence about the taker's private information. The bot models the taker as
a level-1 trader, simplified from Glosten-Milgrom: with probability ``pi``
they are informed and buy only if their fair value exceeds the price; with
probability ``1 - pi`` they trade for reasons unrelated to value (half buys,
half sells). So a buy at ``p`` multiplies the belief by::

    pi * P(trader's FV > p | state) + (1 - pi) / 2

``P(trader's FV > p | state)`` is exact: it averages over every clue the
trader could have been dealt (given how clues are dealt and which clue the
bot itself holds) and over the answer each state would produce.

Answering a call leaks information too: a responder quoting ``bid / ask``
probably has a fair value inside that range. That is weighted the same way::

    pi * P(responder's FV in [bid, ask] | state) + (1 - pi) / 2

The constant second term stands for a quote unrelated to value, as with
trades. If the range can't contain any fair value the responder could have
(say they leaned hard on inventory), the factor is the same for every state
and the belief doesn't move.

To avoid counting a burst of trades as many independent signals, each
trader's evidence is summarized by the highest price they have bought at,
the lowest price they have sold at, and their most recent call answer.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import numpy as np

from whale.game.dealing import question_catalog
from whale.game.posterior import StateSpace, belief, state_space
from whale.game.questions import Answer, ExactQ, Question
from whale.game.recipes import Recipe
from whale.game.setup import Dealing


# Posterior means are floats; 102.00000000000003 must round to the 102 tick.
TICK_EPS = 1e-9


def tick_up(x: float) -> int:
    return math.ceil(x - TICK_EPS)


def tick_down(x: float) -> int:
    return math.floor(x + TICK_EPS)


@dataclass(frozen=True, slots=True)
class FlowModel:
    """``above[i, s] = P(another player's FV > price_i | state s)``, likewise ``below``.

    Ties (FV exactly equal to the price) count half, since an informed trader
    is indifferent there.
    """

    price_min: int
    above: np.ndarray  # (n_prices, N)
    below: np.ndarray

    def row(self, price: int, buy: bool) -> np.ndarray:
        table = self.above if buy else self.below
        return table[price - self.price_min]

    def within(self, lo: int, hi: int) -> np.ndarray:
        """P(another player's FV is in [lo, hi] | state); ties at the ends count half."""
        inside = 1.0 - self.below[lo - self.price_min] - self.above[hi - self.price_min]
        return np.clip(inside, 0.0, 1.0)


def _other_player_questions(recipe: Recipe, dealing: Dealing, own: Question) -> list[Question]:
    """The clues another player might hold, each equally likely."""
    if dealing is Dealing.ONE_CARD_EACH:
        assert isinstance(own, ExactQ)
        return [ExactQ(i) for i in recipe.starting_drivers if i != own.i]
    lo, hi = 0.15, 0.40  # mirrors choose_balanced's default range
    return [rq.question for rq in question_catalog(recipe) if lo <= rq.strength <= hi]


@functools.cache
def flow_model(recipe: Recipe, dealing: Dealing, own: Question) -> FlowModel:
    space = state_space(recipe)
    prices = np.arange(recipe.price_min, recipe.price_max + 1)
    above = np.zeros((len(prices), space.size))
    below = np.zeros((len(prices), space.size))
    questions = _other_player_questions(recipe, dealing, own)
    for q in questions:
        L = space.likelihoods(q)  # (n_answers, N)
        fv = np.array([belief(space, [Answer(q, a)]).mean for a in range(L.shape[0])])
        eq = np.isclose(fv[None, :], prices[:, None])
        gt = ((fv[None, :] > prices[:, None]) & ~eq) + 0.5 * eq
        lt = ((fv[None, :] < prices[:, None]) & ~eq) + 0.5 * eq
        above += gt @ L
        below += lt @ L
    above /= len(questions)
    below /= len(questions)
    return FlowModel(price_min=recipe.price_min, above=above, below=below)


@functools.cache
def flow_model_runner(recipe: Recipe, dealing: Dealing, own: Question) -> FlowModel:
    """Like ``flow_model``, for a trader whose runner has arrived: they hold a
    starting clue *and* the answer to a runner question (PRD §7.7).

    Exact over every (starting answer, runner answer) pair. Each pair's joint
    likelihood is added to the bucket of prices its fair value exceeds, then a
    suffix sum turns buckets into ``P(FV > price | state)``. This avoids
    materializing one price-by-state matrix per pair.
    """
    from whale.game.runners import runner_candidates

    space = state_space(recipe)
    prices = np.arange(recipe.price_min, recipe.price_max + 1, dtype=float)
    n = len(prices)
    starts = _other_player_questions(recipe, dealing, own)
    runs = [q for qs in runner_candidates(recipe).values() for q in qs]
    if not runs:
        return flow_model(recipe, dealing, own)
    gt_bucket = np.zeros((n + 1, space.size))  # by count of prices strictly below the FV
    eq = np.zeros((n, space.size))
    prior_v = space.prior * space.values
    for qs in starts:
        Ls = space.likelihoods(qs)
        for qr in runs:
            Lr = space.likelihoods(qr)
            for a in range(Ls.shape[0]):
                for b in range(Lr.shape[0]):
                    joint = Ls[a] * Lr[b]
                    mass = float(joint @ space.prior)
                    if mass <= 0:
                        continue
                    fv = float(joint @ prior_v) / mass
                    close = np.flatnonzero(np.isclose(prices, fv))
                    if close.size:
                        eq[close[0]] += joint
                        gt_bucket[close[0]] += joint
                    else:
                        gt_bucket[int(np.searchsorted(prices, fv))] += joint
    combos = len(starts) * len(runs)
    # above[i]: pairs whose FV is strictly above price i, i.e. bucket index > i.
    suffix = np.cumsum(gt_bucket[::-1], axis=0)[::-1]
    strictly_above = suffix[1:]  # rows 0..n-1: buckets i+1..n
    above = (strictly_above + 0.5 * eq) / combos
    below = (combos - strictly_above - eq + 0.5 * eq) / combos
    return FlowModel(price_min=recipe.price_min, above=above, below=below)


# After a runner reaches someone, bots treat any taker as possibly that
# player for this long, and quote accordingly: takers are assumed to hold
# runner news, and more of them are assumed informed (π raised by up to
# WARY_PI_BUMP of the remaining room, decaying linearly to nothing).
WARY_MS = 20_000
WARY_PI_BUMP = 0.6


class BeliefTracker:
    def __init__(
        self,
        recipe: Recipe,
        dealing: Dealing,
        own_answer: Answer,
        informed_pct: float,
        learns_from_flow: bool = True,
    ) -> None:
        self.space: StateSpace = state_space(recipe)
        self._base = self.space.prior * own_answer.likelihood(self.space)
        self._flow = flow_model(recipe, dealing, own_answer.question)
        runner_aware = bool(recipe.runner_drivers) and dealing is Dealing.ONE_CARD_EACH
        self._flow_r = flow_model_runner(recipe, dealing, own_answer.question) if runner_aware else self._flow
        self._pi = informed_pct
        self._learns = learns_from_flow and informed_pct > 0
        # Evidence per trader, split by whether their runner had arrived yet.
        self._max_buy: dict[tuple[str, bool], int] = {}
        self._min_sell: dict[tuple[str, bool], int] = {}
        self._answers: dict[str, tuple[int, int, bool]] = {}
        self._arrived: dict[str, int] = {}
        self._invalidate()

    def _invalidate(self) -> None:
        self._w: np.ndarray | None = None
        self._cached: tuple[float, float] | None = None
        self._wv: np.ndarray | None = None
        self._if_taken: dict[tuple[int, bool, float], float] = {}

    def _informed(self, trader: str, ts: int | None) -> bool:
        arrived = self._arrived.get(trader)
        return arrived is not None and (ts is None or ts >= arrived)

    def observe_take(self, trader: str, bought: bool, price: int, ts: int | None = None) -> None:
        if not self._learns:
            return
        key = (trader, self._informed(trader, ts))
        if bought and price > self._max_buy.get(key, -1):
            self._max_buy[key] = price
            self._invalidate()
        elif not bought and price < self._min_sell.get(key, 10**9):
            self._min_sell[key] = price
            self._invalidate()

    def observe_answer(self, responder: str, bid: int, ask: int, ts: int | None = None) -> None:
        entry = (bid, ask, self._informed(responder, ts))
        if self._learns and self._answers.get(responder) != entry:
            self._answers[responder] = entry
            self._invalidate()

    def runner_arrived(self, trader: str, ts: int) -> None:
        """Another player just got private news (PRD §7.7)."""
        self._arrived.setdefault(trader, ts)

    def add_own(self, answer: Answer) -> None:
        """The bot's own runner slip arrived."""
        self._base = self._base * answer.likelihood(self.space)
        self._invalidate()

    def _weights(self) -> np.ndarray:
        """Normalized posterior weights over the state space."""
        if self._w is None:
            w = self._base.copy()
            noise = (1 - self._pi) / 2
            for (_, informed), p in self._max_buy.items():
                w *= self._pi * (self._flow_r if informed else self._flow).row(p, buy=True) + noise
            for (_, informed), p in self._min_sell.items():
                w *= self._pi * (self._flow_r if informed else self._flow).row(p, buy=False) + noise
            for lo, hi, informed in self._answers.values():
                w *= self._pi * (self._flow_r if informed else self._flow).within(lo, hi) + noise
            total = w.sum()
            if total <= 0:  # contradictory evidence: fall back to the bot's own clue
                w, total = self._base, self._base.sum()
            self._w = w / total
        return self._w

    def fair_value(self) -> tuple[float, float]:
        """(mean, sd) of the final value under the current belief."""
        if self._cached is None:
            w = self._weights()
            v = self.space.values
            mean = float(w @ v)
            sd = float(np.sqrt(max(0.0, w @ (v * v) - mean * mean)))
            self._cached = (mean, sd)
        return self._cached

    def wariness(self, now: int | None) -> float:
        """1 just after a runner reached another player, fading to 0 over WARY_MS."""
        if now is None:
            return 0.0
        return max((1 - (now - t) / WARY_MS for t in self._arrived.values() if 0 <= now - t <= WARY_MS), default=0.0)

    def value_if_taken(self, price: int, buy: bool, wary: float = 0.0) -> float:
        """``E[V | an unknown player takes my quote at price]``.

        With ``buy=True``: given that someone buys from me there (lifts my
        ask); with ``buy=False``: given that someone sells to me (hits my
        bid). The taker is treated as a player we know nothing about yet,
        which is the worst case for the quoter. ``wary`` assumes they also
        hold runner news and raises π in proportion. A bot that doesn't model
        informed traders gets its plain fair value.
        """
        if not self._learns:
            return self.fair_value()[0]
        wary = round(wary, 2)
        key = (price, buy, wary)
        cached = self._if_taken.get(key)
        if cached is None:
            w = self._weights()
            if self._wv is None:
                self._wv = w * self.space.values
            row = (self._flow_r if wary > 0 else self._flow).row(price, buy=buy)
            pi = self._pi + (1 - self._pi) * WARY_PI_BUMP * wary
            c = (1 - pi) / 2
            num = pi * float(row @ self._wv) + c * float(self._wv.sum())
            den = pi * float(row @ w) + c
            cached = self._if_taken[key] = num / den
        return cached

    def regret_free_quote(self, now: int | None = None) -> tuple[int, int]:
        """The tightest (bid, ask) that loses nothing in expectation if hit.

        Glosten-Milgrom: the ask must be at least the expected value *given
        that someone buys there*, and the bid at most the expected value given
        that someone sells there. Scans outward from fair value on the integer
        tick grid and returns the first price on each side that qualifies.
        Right after a runner reaches someone, the taker may be that player,
        so the bot quotes as if they hold runner news.
        """
        wary = self.wariness(now)
        lo = self._flow.price_min
        hi = lo + self._flow.above.shape[0] - 1
        fv = self.fair_value()[0]
        ask = min(max(tick_up(fv), lo), hi)
        while ask < hi and ask < self.value_if_taken(ask, buy=True, wary=wary) - TICK_EPS:
            ask += 1
        bid = min(max(tick_down(fv), lo), hi)
        while bid > lo and bid > self.value_if_taken(bid, buy=False, wary=wary) + TICK_EPS:
            bid -= 1
        return bid, ask

    def informed_traders(self) -> int:
        """How many other players have revealed something so far."""
        return len({t for t, _ in self._max_buy} | {t for t, _ in self._min_sell} | self._answers.keys())
