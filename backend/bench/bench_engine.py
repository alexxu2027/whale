"""Engine throughput benchmark (PRD §28.8).

Replays 200k random commands (60% orders, 25% quote updates, 15% cancels)
from 8 players against one exchange, with no I/O.

    uv run python bench/bench_engine.py
"""

import random
import time

from whale.engine import Exchange, MarketConfig, PlaceOrder, CancelOrder, SetQuote, Side, OrderType
cfg = MarketConfig(rate_limit_per_sec=None, position_limit=10**9, max_order_qty=10)
players = [f"p{i}" for i in range(8)]
rng = random.Random(1)
cmds = []
for i in range(200_000):
    p = rng.choice(players); r = rng.random()
    if r < 0.6:
        cmds.append(PlaceOrder(player_id=p, ts=i, side=rng.choice((Side.BUY, Side.SELL)), price=rng.randint(95,105), qty=rng.randint(1,10), order_type=OrderType.LIMIT if rng.random()<.8 else OrderType.IOC))
    elif r < 0.85:
        b = rng.randint(94,104); cmds.append(SetQuote(player_id=p, ts=i, bid_price=b, bid_qty=5, ask_price=b+rng.randint(2,5), ask_qty=5))
    else:
        cmds.append(CancelOrder(player_id=p, ts=i, order_id=rng.randint(max(1,i//2-50), i//2+1)))
ex = Exchange(cfg, players)
t = time.perf_counter(); lat = []
for c in cmds:
    s = time.perf_counter_ns(); ex.apply(c); lat.append(time.perf_counter_ns() - s)
el = time.perf_counter() - t
lat.sort()
print(f"{len(cmds)/el:,.0f} commands/s   p50 {lat[len(lat)//2]/1000:.1f} us   p99 {lat[int(len(lat)*.99)]/1000:.1f} us   resting {len(ex.book)}")
