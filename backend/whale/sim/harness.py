"""Headless simulation: bots play full rounds with no networking (PRD §32.4).

Bots are scheduled by ``BotRunner`` (decide, think, arrive), the same code
live rooms use, and their commands go through a real ``Round``.

    uv run python -m whale.sim.harness --rounds 500
    uv run python -m whale.sim.harness --recipe pit_six --rounds 200   # with runners
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from whale.bots.bot import Bot
from whale.bots.runner import BotRunner
from whale.bots.personalities import ALL, Difficulty, Personality, with_difficulty
from whale.engine import CENTS_PER_POINT, MarketConfig, OrderRejected, Side, Trade, TradeKind
from whale.game.recipes import FOUR_CARDS, RECIPES, Recipe
from whale.game.round import Round, RoundConfig, RoundResult
from whale.game.setup import Dealing


@dataclass(frozen=True, slots=True)
class Seat:
    name: str
    personality: Personality


@dataclass(slots=True)
class PlayerStats:
    pnl: float = 0.0
    rank: int = 0
    volume: int = 0
    passive_qty: int = 0  # filled as maker
    aggressive_qty: int = 0  # filled as taker
    calls_made: int = 0
    rejections: int = 0
    commands: int = 0


@dataclass(slots=True)
class RoundSummary:
    seed: int
    result: RoundResult
    players: dict[str, PlayerStats]
    trades: int
    auction_qty: int
    call_trades: int
    end_mid: float | None
    discovery: float | None  # 1 - |mid_end - V| / |prior mean - V|; None if V == prior mean
    events: int = 0
    personality_of: dict[str, str] = field(default_factory=dict)
    runners: list[RunnerStats] = field(default_factory=list)


RUNNER_WINDOW_MS = 20_000  # how long after arrival we measure a runner's effect
SAMPLE_MS = 500  # spread sampling interval


@dataclass(frozen=True, slots=True)
class RunnerStats:
    """What one runner did to the market (PRD §7.7 tuning)."""

    edge: float  # recipient's trading P&L, marked to the final value, in the window after arrival
    trades_before: int  # trades in the window before arrival
    trades_after: int  # trades in the window after arrival
    spread_before: float | None  # mean quoted spread before arrival
    spread_after: float | None


def simulate_round(
    seats: Sequence[Seat],
    seed: int,
    recipe: Recipe = FOUR_CARDS,
    config: RoundConfig | None = None,
) -> RoundSummary:
    config = config or RoundConfig(market=MarketConfig())
    names = [s.name for s in seats]
    rnd = Round(recipe, names, config, seed=seed)
    rng = random.Random(seed ^ 0x5EED_B075)
    bots = [
        Bot(s.name, s.personality, rnd.setup.clues[s.name], recipe, config.dealing, random.Random(rng.getrandbits(64)))
        for s in seats
    ]
    stats = {n: PlayerStats() for n in names}

    def count(pid: str, _cmd: object) -> None:
        stats[pid].commands += 1

    runner = BotRunner(rnd, {b.player_id: b for b in bots}, rng, start=0, on_command=count)
    spreads: list[tuple[int, int | None]] = []
    if rnd.runners:
        # Sample the quoted spread over time so runner effects can be measured.
        for t in range(0, rnd.close_at - 1, SAMPLE_MS):
            runner.run_until(t)
            rnd.advance(t)
            b, a = rnd.exchange.book.best_price(Side.BUY), rnd.exchange.book.best_price(Side.SELL)
            spreads.append((t, a - b if b is not None and a is not None else None))
    runner.run_until(rnd.close_at - 1)

    bid, ask = rnd.exchange.book.best_price(Side.BUY), rnd.exchange.book.best_price(Side.SELL)
    rnd.advance(rnd.close_at)
    result = rnd.result
    assert result is not None
    summary = _summarize(seed, rnd, result, stats, bid, ask, {s.name: s.personality.name for s in seats})
    summary.runners = _runner_stats(rnd, result.final_value, spreads)
    return summary


def _runner_stats(rnd: Round, final_value: int, spreads: list[tuple[int, int | None]]) -> list[RunnerStats]:
    trades = [e for e in rnd.log if isinstance(e, Trade)]
    out = []
    for plan in rnd.runners:
        t0, w = plan.arrive_at, RUNNER_WINDOW_MS
        after = [t for t in trades if t0 <= t.ts < t0 + w]
        edge = 0
        for t in after:
            if t.buyer_id == plan.recipient:
                edge += (final_value - t.price) * t.qty
            if t.seller_id == plan.recipient:
                edge += (t.price - final_value) * t.qty

        def mean_spread(lo: int, hi: int) -> float | None:
            xs = [x for ts, x in spreads if lo <= ts < hi and x is not None]
            return statistics.fmean(xs) if xs else None

        out.append(RunnerStats(
            edge=float(edge),
            trades_before=sum(1 for t in trades if t0 - w <= t.ts < t0),
            trades_after=len(after),
            spread_before=mean_spread(t0 - w, t0),
            spread_after=mean_spread(t0, t0 + w),
        ))
    return out


def _summarize(
    seed: int,
    rnd: Round,
    result: RoundResult,
    stats: dict[str, PlayerStats],
    bid: int | None,
    ask: int | None,
    personality_of: dict[str, str],
) -> RoundSummary:
    trades = [e for e in rnd.log if isinstance(e, Trade)]
    for e in rnd.log:
        if isinstance(e, OrderRejected) and e.player_id in stats:
            stats[e.player_id].rejections += 1
    for t in trades:
        stats[t.buyer_id].volume += t.qty
        stats[t.seller_id].volume += t.qty
        if t.maker_id is not None and t.taker_id is not None:
            stats[t.maker_id].passive_qty += t.qty
            stats[t.taker_id].aggressive_qty += t.qty
        if t.kind is TradeKind.CALL and t.taker_id is not None:
            stats[t.taker_id].calls_made += 1
    for pr in result.players:
        stats[pr.player_id].pnl = pr.pnl_cents / CENTS_PER_POINT
        stats[pr.player_id].rank = pr.rank

    if bid is not None and ask is not None:
        end_mid: float | None = (bid + ask) / 2
    else:
        last = [t.price for t in trades if t.kind is not TradeKind.CALL]
        end_mid = float(last[-1]) if last else None
    prior = rnd.setup.public_belief().mean
    v = result.final_value
    discovery = None
    if end_mid is not None and not math.isclose(v, prior):
        discovery = 1 - abs(end_mid - v) / abs(prior - v)
    return RoundSummary(
        seed=seed,
        result=result,
        players=stats,
        trades=len(trades),
        auction_qty=sum(t.qty for t in trades if t.kind is TradeKind.AUCTION),
        call_trades=sum(1 for t in trades if t.kind is TradeKind.CALL),
        end_mid=end_mid,
        discovery=discovery,
        events=len(rnd.log),
        personality_of=personality_of,
    )


# -- many rounds ----------------------------------------------------------------------


@dataclass(slots=True)
class Report:
    rounds: int
    seconds: float
    by_personality: dict[str, list[float]]  # P&L per round, per seat with that personality
    wins: dict[str, int]
    passive_share: dict[str, float]  # share of each personality's fills where it was the maker
    trades_per_round: float
    calls_per_round: float
    discovery_median: float
    rejection_rate: float
    runners: list[RunnerStats] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"{self.rounds} rounds in {self.seconds:.1f}s ({self.rounds / self.seconds:.1f} rounds/s)",
            f"trades/round {self.trades_per_round:.1f}   call trades/round {self.calls_per_round:.2f}   "
            f"price discovery (median) {self.discovery_median:.2f}   bot command rejections {self.rejection_rate:.1%}",
            f"median |round P&L| {self.median_abs_pnl:.1f}  (PRD §10: objective bonuses <= 25% of this)",
            "",
            f"{'personality':<16}{'mean P&L':>10}{'±95%':>8}{'sd':>8}{'win %':>8}{'maker %':>9}",
        ]
        for name, pnls in sorted(self.by_personality.items(), key=lambda kv: -statistics.fmean(kv[1])):
            mean = statistics.fmean(pnls)
            sd = statistics.stdev(pnls) if len(pnls) > 1 else 0.0
            ci = 1.96 * sd / math.sqrt(len(pnls))
            win = self.wins.get(name, 0) / self.rounds
            maker = self.passive_share.get(name, 0.0)
            lines.append(f"{name:<16}{mean:>10.1f}{ci:>8.1f}{sd:>8.1f}{win:>8.0%}{maker:>9.0%}")
        if self.runners:
            rs = self.runners
            edges = [r.edge for r in rs]
            ci = 1.96 * statistics.stdev(edges) / math.sqrt(len(edges)) if len(edges) > 1 else 0.0
            sb = [r.spread_before for r in rs if r.spread_before is not None]
            sa = [r.spread_after for r in rs if r.spread_after is not None]
            frozen = sum(1 for r in rs if r.trades_before > 0 and r.trades_after == 0) / len(rs)
            lines += [
                "",
                f"runners ({len(rs)}; {RUNNER_WINDOW_MS // 1000}s windows around arrival)",
                f"  recipient edge after arrival  {statistics.fmean(edges):+.1f} ±{ci:.1f} points",
                (f"  quoted spread  before {statistics.fmean(sb) if sb else float('nan'):.2f}   "
                 f"after {statistics.fmean(sa) if sa else float('nan'):.2f}"),
                (f"  trades  before {statistics.fmean(r.trades_before for r in rs):.1f}   "
                 f"after {statistics.fmean(r.trades_after for r in rs):.1f}   market froze {frozen:.0%}"),
            ]
        return "\n".join(lines)

    @property
    def median_abs_pnl(self) -> float:
        return statistics.median(abs(x) for pnls in self.by_personality.values() for x in pnls)


def run_many(seats: Sequence[Seat], rounds: int, base_seed: int = 0, **kw) -> Report:
    start = time.perf_counter()
    by_personality: dict[str, list[float]] = defaultdict(list)
    wins: dict[str, int] = defaultdict(int)
    passive: dict[str, int] = defaultdict(int)
    aggressive: dict[str, int] = defaultdict(int)
    trades = calls = rejections = commands = 0
    discoveries: list[float] = []
    runner_stats: list[RunnerStats] = []
    for r in range(rounds):
        s = simulate_round(seats, base_seed + r, **kw)
        runner_stats += s.runners
        trades += s.trades
        calls += s.call_trades
        for name, ps in s.players.items():
            kind = s.personality_of[name]
            by_personality[kind].append(ps.pnl)
            passive[kind] += ps.passive_qty
            aggressive[kind] += ps.aggressive_qty
            rejections += ps.rejections
            commands += ps.commands
            if ps.rank == 1:
                wins[s.personality_of[name]] += 1
        if s.discovery is not None:
            discoveries.append(s.discovery)
    return Report(
        rounds=rounds,
        seconds=time.perf_counter() - start,
        by_personality=dict(by_personality),
        wins=dict(wins),
        passive_share={k: passive[k] / max(1, passive[k] + aggressive[k]) for k in by_personality},
        trades_per_round=trades / rounds,
        calls_per_round=calls / rounds,
        discovery_median=statistics.median(discoveries) if discoveries else float("nan"),
        rejection_rate=rejections / max(1, commands),
        runners=runner_stats,
    )


def default_table(difficulty: Difficulty = Difficulty.MEDIUM) -> list[Seat]:
    by_name = {p.name: p for p in ALL}
    picks = ("Market Maker", "Shark", "Noise Trader", "Conservative")
    return [Seat(f"bot{i}", with_difficulty(by_name[n], difficulty)) for i, n in enumerate(picks)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dealing", choices=[d.value for d in Dealing], default=Dealing.ONE_CARD_EACH.value)
    ap.add_argument("--table", default="Market Maker,Shark,Noise Trader,Conservative",
                    help="comma-separated personalities, one per seat")
    ap.add_argument("--difficulty", choices=[d.value for d in Difficulty], default=Difficulty.MEDIUM.value)
    ap.add_argument("--recipe", choices=sorted(RECIPES), default=FOUR_CARDS.id)
    ap.add_argument("--no-runners", action="store_true", help="turn runners off (pit_six only)")
    ap.add_argument("--travel-ms", type=int, default=2_000, help="how long a runner is visible before arriving")
    args = ap.parse_args()

    by_name = {p.name: p for p in ALL}
    diff = Difficulty(args.difficulty)
    seats = [Seat(f"bot{i}", with_difficulty(by_name[n.strip()], diff)) for i, n in enumerate(args.table.split(","))]
    config = RoundConfig(dealing=Dealing(args.dealing), market=MarketConfig(),
                         runners=not args.no_runners, runner_travel_ms=args.travel_ms)
    print(run_many(seats, args.rounds, args.seed, config=config, recipe=RECIPES[args.recipe]).render())


if __name__ == "__main__":
    main()
