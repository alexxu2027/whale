"""Headless simulation: bots play full rounds with no networking (PRD §32.4).

Discrete-event loop: each bot acts at its own scheduled times. Before acting,
a bot receives every event it is allowed to see (``is_visible``) since its
last action, plus a public view of the market. Its commands go through a
real ``Round``, the same code path humans will use.

    uv run python -m whale.sim.harness --rounds 500
"""

from __future__ import annotations

import argparse
import heapq
import math
import random
import statistics
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from whale.bots.bot import Bot
from whale.bots.personalities import ALL, Difficulty, Personality, with_difficulty
from whale.bots.view import build_view
from whale.engine import CENTS_PER_POINT, MarketConfig, OrderRejected, Side, Trade, TradeKind
from whale.game.recipes import FOUR_CARDS, Recipe
from whale.game.round import Round, RoundConfig, RoundResult
from whale.game.setup import Dealing
from whale.runtime.visibility import is_visible


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
    cursors = [0] * len(bots)

    queue = [(rng.randint(0, 2_000), i) for i in range(len(bots))]
    heapq.heapify(queue)
    while queue:
        t, i = heapq.heappop(queue)
        if t >= rnd.close_at:
            break
        rnd.advance(t)
        bot = bots[i]
        for e in rnd.log[cursors[i] :]:
            if is_visible(e, bot.player_id):
                bot.observe(e)
        for cmd in bot.act(build_view(rnd.exchange, bot.player_id, t)):
            stats[bot.player_id].commands += 1
            rnd.submit(cmd)
        cursors[i] = len(rnd.log)
        heapq.heappush(queue, (t + bot.next_delay(), i))

    bid, ask = rnd.exchange.book.best_price(Side.BUY), rnd.exchange.book.best_price(Side.SELL)
    rnd.advance(rnd.close_at)
    result = rnd.result
    assert result is not None
    return _summarize(seed, rnd, result, stats, bid, ask, {s.name: s.personality.name for s in seats})


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
    for r in range(rounds):
        s = simulate_round(seats, base_seed + r, **kw)
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
    args = ap.parse_args()

    by_name = {p.name: p for p in ALL}
    diff = Difficulty(args.difficulty)
    seats = [Seat(f"bot{i}", with_difficulty(by_name[n.strip()], diff)) for i, n in enumerate(args.table.split(","))]
    config = RoundConfig(dealing=Dealing(args.dealing), market=MarketConfig())
    print(run_many(seats, args.rounds, args.seed, config=config).render())


if __name__ == "__main__":
    main()
