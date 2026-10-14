"""Round controller: one round from deal to settlement (PRD §6, §42).

Timeline::

    start ──(opening_ms)──> open ──(trading_ms)──> close
    PRE_OPEN: quotes only    OPEN: trading, calls   CLOSED: settled

Like the exchange, a round never reads a clock. The room actor (Phase 2)
calls ``advance(now)`` on a timer and ``submit(command)`` for player input;
both process any phase changes and call deadlines that are due first, each
stamped with its own scheduled time. Given the same seed and the same
command stream, a round replays exactly.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum

from whale.analytics.attribution import Attribution, attribute
from whale.engine import (
    CENTS_PER_POINT,
    Command,
    Event,
    Exchange,
    MarketConfig,
    MarketStatus,
    SetStatus,
    Side,
    Tick,
    Trade,
)

from .dealing import Clue
from .objectives import Objective, ObjectiveContext, deal_objectives
from .posterior import state_space
from .recipes import Recipe
from .runners import RunnerArrived, RunnerDispatched, RunnerPlan, RunnerSlip, plan_runners
from .setup import Dealing, RoundSetup, new_seed, setup_round


class Phase(StrEnum):
    OPENING = "opening"
    TRADING = "trading"
    SETTLED = "settled"


@dataclass(frozen=True, slots=True)
class RoundConfig:
    opening_ms: int = 10_000
    trading_ms: int = 180_000
    dealing: Dealing = Dealing.ONE_CARD_EACH
    runners: bool = True  # only has an effect on recipes with runner-only drivers (PRD §7.7)
    runner_travel_ms: int = 2_000  # how long the runner is visible crossing the floor
    # Price band and reference price are overridden from the recipe.
    market: MarketConfig = field(default_factory=MarketConfig)


@dataclass(frozen=True, slots=True)
class PlayerResult:
    player_id: str
    rank: int  # 1 = best by score; ties share a rank
    pnl_cents: int  # trading P&L, fees included
    position: int
    cash_cents: int
    clue: Clue
    runner_clues: tuple[Clue, ...]
    objective: Objective
    objective_met: bool
    attribution: Attribution

    @property
    def bonus_cents(self) -> int:
        return self.objective.bonus * CENTS_PER_POINT if self.objective_met else 0

    @property
    def score_cents(self) -> int:
        """Round score: trading P&L plus objective bonus (PRD §15)."""
        return self.pnl_cents + self.bonus_cents

    @property
    def pnl(self) -> float:
        return self.pnl_cents / CENTS_PER_POINT


@dataclass(frozen=True, slots=True)
class RoundResult:
    final_value: int
    state: tuple[int, ...]
    players: tuple[PlayerResult, ...]  # best first
    house_cash_cents: int


def _seeds(seed: int) -> tuple[int, int, int, int]:
    """(setup, exchange, objective, runner) seeds, derived in a fixed order."""
    root = random.Random(seed)
    return root.getrandbits(64), root.getrandbits(64), root.getrandbits(64), root.getrandbits(64)


class Round:
    def __init__(
        self,
        recipe: Recipe,
        players: Sequence[str],
        config: RoundConfig | None = None,
        *,
        seed: int | None = None,
        start_ts: int = 0,
    ) -> None:
        self.config = config or RoundConfig()
        self.seed = new_seed() if seed is None else seed
        _, exchange_seed, _, runner_seed = _seeds(self.seed)

        self.setup, self.objectives = Round.deal(recipe, players, self.seed, self.config.dealing)
        market = replace(
            self.config.market,
            price_min=recipe.price_min,
            price_max=recipe.price_max,
            reference_price=round(state_space(recipe).prior_belief.mean),
        )
        self.exchange = Exchange(market, players, status=MarketStatus.PRE_OPEN, seed=exchange_seed)
        self.start_ts = start_ts
        self.open_at = start_ts + self.config.opening_ms
        self.close_at = self.open_at + self.config.trading_ms
        self.log: list[Event] = []
        self.result: RoundResult | None = None
        # Middle of the book just before the command that produced each trade (PRD §17.2).
        self.trade_mids: dict[int, float] = {}
        self._last_trade_price: int | None = None
        self._now = start_ts

        # Runners (PRD §7.7): planned up front from separate random streams, so
        # choosing questions and times never depends on the hidden state.
        self.runners: list[RunnerPlan] = []
        if self.config.runners:
            rr = random.Random(runner_seed)
            q_rng, a_rng, f_rng = (random.Random(rr.getrandbits(64)) for _ in range(3))
            self.runners = plan_runners(
                recipe, players, self.setup.state, self.open_at, self.close_at,
                self.config.runner_travel_ms, q_rng, a_rng, f_rng,
            )
        self._runner_events = sorted(
            [(r.dispatch_at, 0, r) for r in self.runners] + [(r.arrive_at, 1, r) for r in self.runners],
            key=lambda e: (e[0], e[1], e[2].runner_id),
        )
        self._runner_cursor = 0
        self.delivered: dict[str, list[Clue]] = {p: [] for p in players}

    @staticmethod
    def deal(
        recipe: Recipe, players: Sequence[str], seed: int, dealing: Dealing = Dealing.ONE_CARD_EACH
    ) -> tuple[RoundSetup, dict[str, Objective]]:
        """The clues and objectives a round with this seed deals, without
        starting its clock (the room shows them in the pre-round briefing)."""
        setup_seed, _, objective_seed, _ = _seeds(seed)
        setup = setup_round(recipe, players, setup_seed, dealing)
        return setup, deal_objectives(players, random.Random(objective_seed))

    @property
    def phase(self) -> Phase:
        match self.exchange.status:
            case MarketStatus.PRE_OPEN:
                return Phase.OPENING
            case MarketStatus.CLOSED:
                return Phase.SETTLED
            case _:
                return Phase.TRADING

    def advance(self, now: int) -> list[Event]:
        """Move time forward to ``now``, running anything scheduled before it."""
        if now < self._now:
            raise ValueError(f"time went backwards: {now} < {self._now}")
        self._now = now
        out: list[Event] = []
        if self.exchange.status is MarketStatus.PRE_OPEN and now >= self.open_at:
            out += self._apply(SetStatus(ts=self.open_at, status=MarketStatus.OPEN))
        out += self._run_runners(min(now, self.close_at - 1))
        if self.exchange.status is not MarketStatus.CLOSED:
            if now >= self.close_at:
                out += self._apply(SetStatus(ts=self.close_at, status=MarketStatus.CLOSED))
                self.result = self._settle()
            else:
                out += self._apply(Tick(ts=now))
        return out

    def submit(self, command: Command) -> list[Event]:
        """Apply a player's command at its timestamp. After close, the
        exchange rejects everything."""
        if isinstance(command, (SetStatus, Tick)):
            raise ValueError("market status and time are controlled by the round")
        out = self.advance(command.ts)
        return out + self._apply(command)

    def next_scheduled(self) -> int | None:
        """The next runner movement, if one is due before the close."""
        if self._runner_cursor < len(self._runner_events):
            ts = self._runner_events[self._runner_cursor][0]
            if ts < self.close_at:
                return ts
        return None

    def runner_clue(self, runner_id: int) -> Clue:
        return next(r.clue for r in self.runners if r.runner_id == runner_id)

    def information(self, player: str) -> list[Clue]:
        """Everything the player has been told so far: starting slip, then runners."""
        return [self.setup.clues[player], *self.delivered[player]]

    def _run_runners(self, limit: int) -> list[Event]:
        out: list[Event] = []
        while self._runner_cursor < len(self._runner_events) and self._runner_events[self._runner_cursor][0] <= limit:
            ts, kind, plan = self._runner_events[self._runner_cursor]
            self._runner_cursor += 1
            if self.exchange.status is MarketStatus.CLOSED:
                continue
            out += self._apply(Tick(ts=ts))  # deadlines due before the runner, in order
            if kind == 0:
                out.append(self._record(RunnerDispatched, ts, runner_id=plan.runner_id, recipient_id=plan.recipient, arrive_at=plan.arrive_at))
            else:
                self.delivered[plan.recipient].append(plan.clue)
                out.append(self._record(RunnerArrived, ts, runner_id=plan.runner_id, recipient_id=plan.recipient))
                out.append(self._record(RunnerSlip, ts, runner_id=plan.runner_id, player_id=plan.recipient,
                                        flavor=plan.clue.flavor, precise=plan.clue.precise))
        return out

    def _record(self, cls: type[Event], ts: int, **fields: object) -> Event:
        event = self.exchange.record(cls, ts, **fields)
        self.log.append(event)
        return event

    def mid(self) -> float:
        """Middle of the book; else the last trade price; else the reference price."""
        bid = self.exchange.book.best_price(Side.BUY)
        ask = self.exchange.book.best_price(Side.SELL)
        if bid is not None and ask is not None and bid < ask:
            return (bid + ask) / 2
        if self._last_trade_price is not None:
            return float(self._last_trade_price)
        return float(self.exchange.config.reference)

    def _apply(self, command: Command) -> list[Event]:
        mid = self.mid()
        events = self.exchange.apply(command)
        for e in events:
            if isinstance(e, Trade):
                self.trade_mids[e.trade_id] = mid
                self._last_trade_price = e.price
        self.log += events
        return events

    def _settle(self) -> RoundResult:
        v = self.setup.final_value
        settlements = self.exchange.settle(v)
        trades = [e for e in self.log if isinstance(e, Trade)]
        attribution = attribute(trades, self.trade_mids, self.exchange.accounts, v)
        positions = {p: s.position for p, s in settlements.items()}
        unranked = []
        for s in settlements.values():
            objective = self.objectives[s.player_id]
            ctx = ObjectiveContext(s.player_id, trades, positions, self.close_at)
            unranked.append(
                PlayerResult(
                    player_id=s.player_id,
                    rank=0,
                    pnl_cents=s.pnl_cents,
                    position=s.position,
                    cash_cents=s.cash_cents,
                    clue=self.setup.clues[s.player_id],
                    runner_clues=tuple(self.delivered[s.player_id]),
                    objective=objective,
                    objective_met=objective.check(ctx),
                    attribution=attribution[s.player_id],
                )
            )
        unranked.sort(key=lambda r: (-r.score_cents, r.player_id))
        players = [
            replace(r, rank=1 + sum(1 for o in unranked if o.score_cents > r.score_cents)) for r in unranked
        ]
        return RoundResult(
            final_value=v,
            state=self.setup.state,
            players=tuple(players),
            house_cash_cents=self.exchange.house_cash_cents,
        )
