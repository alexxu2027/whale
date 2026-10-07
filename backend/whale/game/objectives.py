"""Secret objectives (PRD §10).

Each player gets one, dealt from the round's seed. Objectives are scored
purely from the round's event log and final positions, so they replay
exactly. Bonuses are in points; per PRD §10 they should stay well below
typical trading P&L (the simulator's report prints the current scale).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from whale.engine import Trade, TradeKind


@dataclass(frozen=True, slots=True)
class ObjectiveContext:
    player_id: str
    trades: Sequence[Trade]
    positions: dict[str, int]  # final position of every player
    close_at: int  # ts the round closed


@dataclass(frozen=True, slots=True)
class Objective:
    id: str
    title: str
    description: str
    bonus: int  # points
    check: Callable[[ObjectiveContext], bool]


def _mine(ctx: ObjectiveContext) -> list[Trade]:
    return [t for t in ctx.trades if ctx.player_id in (t.buyer_id, t.seller_id)]


def _volume(ctx: ObjectiveContext) -> int:
    return sum(t.qty for t in _mine(ctx))


def _passive_fills(ctx: ObjectiveContext, bought: bool) -> int:
    who = "buyer_id" if bought else "seller_id"
    return sum(1 for t in ctx.trades if t.maker_id == ctx.player_id and getattr(t, who) == ctx.player_id)


def _contrarian(ctx: ObjectiveContext) -> bool:
    mine = ctx.positions[ctx.player_id]
    table = sum(p for pid, p in ctx.positions.items() if pid != ctx.player_id)
    return table != 0 and mine != 0 and (mine > 0) != (table > 0)


def _steady(ctx: ObjectiveContext) -> bool:
    late = ctx.close_at - 30_000
    return not any(t.taker_id == ctx.player_id and t.ts >= late for t in ctx.trades)


OBJECTIVES: tuple[Objective, ...] = (
    Objective("collector", "Collector", "Finish holding at least +15.", 40,
              lambda c: c.positions[c.player_id] >= 15),
    Objective("short_king", "Short King", "Finish at -15 or lower.", 40,
              lambda c: c.positions[c.player_id] <= -15),
    Objective("volume_trader", "Volume Trader", "Trade at least 50 units this round.", 35,
              lambda c: _volume(c) >= 50),
    Objective("market_maker", "Market Maker",
              "Get your posted offers filled at least 5 times on each side. Taking others' offers doesn't count.", 50,
              lambda c: _passive_fills(c, True) >= 5 and _passive_fills(c, False) >= 5),
    Objective("steady_hands", "Steady Hands",
              "Don't buy or sell from anyone in the final 30 seconds. Your own market getting hit doesn't count.", 30,
              _steady),
    Objective("big_ticket", "Big Ticket", "Make one trade of at least 10 units.", 30,
              lambda c: any(t.qty >= 10 for t in _mine(c) if t.kind is not TradeKind.AUCTION)),
    Objective("contrarian", "Contrarian",
              "Finish on the opposite side from everyone else combined.", 40,
              _contrarian),
    Objective("flat_finish", "Flat Finish", "Finish between -3 and +3.", 40,
              lambda c: abs(c.positions[c.player_id]) <= 3),
)

BY_ID = {o.id: o for o in OBJECTIVES}


def deal_objectives(players: Sequence[str], rng: random.Random) -> dict[str, Objective]:
    """Distinct objectives while they last, then repeats."""
    pool = list(OBJECTIVES)
    rng.shuffle(pool)
    return {p: pool[i % len(pool)] for i, p in enumerate(players)}
