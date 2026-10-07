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

from whale.engine import (
    CENTS_PER_POINT,
    Command,
    Event,
    Exchange,
    MarketConfig,
    MarketStatus,
    SetStatus,
    Tick,
)

from .dealing import Clue
from .posterior import state_space
from .recipes import Recipe
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
    # Price band and reference price are overridden from the recipe.
    market: MarketConfig = field(default_factory=MarketConfig)


@dataclass(frozen=True, slots=True)
class PlayerResult:
    player_id: str
    rank: int  # 1 = best; ties share a rank
    pnl_cents: int
    position: int
    cash_cents: int
    clue: Clue

    @property
    def pnl(self) -> float:
        return self.pnl_cents / CENTS_PER_POINT


@dataclass(frozen=True, slots=True)
class RoundResult:
    final_value: int
    state: tuple[int, ...]
    players: tuple[PlayerResult, ...]  # best first
    house_cash_cents: int


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
        root = random.Random(self.seed)
        setup_seed, exchange_seed = root.getrandbits(64), root.getrandbits(64)

        self.setup: RoundSetup = setup_round(recipe, players, setup_seed, self.config.dealing)
        market = replace(
            self.config.market,
            price_min=recipe.min_value,
            price_max=recipe.max_value,
            reference_price=round(state_space(recipe).prior_belief.mean),
        )
        self.exchange = Exchange(market, players, status=MarketStatus.PRE_OPEN, seed=exchange_seed)
        self.start_ts = start_ts
        self.open_at = start_ts + self.config.opening_ms
        self.close_at = self.open_at + self.config.trading_ms
        self.log: list[Event] = []
        self.result: RoundResult | None = None
        self._now = start_ts

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

    def _apply(self, command: Command) -> list[Event]:
        events = self.exchange.apply(command)
        self.log += events
        return events

    def _settle(self) -> RoundResult:
        v = self.setup.final_value
        settlements = self.exchange.settle(v)
        ordered = sorted(settlements.values(), key=lambda s: (-s.pnl_cents, s.player_id))
        players = []
        for s in ordered:
            rank = 1 + sum(1 for o in ordered if o.pnl_cents > s.pnl_cents)
            players.append(
                PlayerResult(
                    player_id=s.player_id,
                    rank=rank,
                    pnl_cents=s.pnl_cents,
                    position=s.position,
                    cash_cents=s.cash_cents,
                    clue=self.setup.clues[s.player_id],
                )
            )
        return RoundResult(
            final_value=v,
            state=self.setup.state,
            players=tuple(players),
            house_cash_cents=self.exchange.house_cash_cents,
        )
