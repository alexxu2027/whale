"""Hypothesis value strategies for engine tests.

Prices cluster in a narrow range so orders cross often, with occasional
out-of-band values to exercise rejections.
"""

from __future__ import annotations

from hypothesis import strategies as st

from whale.engine import MarketConfig, OrderType, Side

PLAYERS = ("p0", "p1", "p2", "p3")

# Rate limit off so random runs exercise matching rather than throttling;
# a small position limit so risk checks fire regularly.
CONFIG = MarketConfig(
    price_min=90,
    price_max=110,
    max_order_qty=10,
    position_limit=15,
    rate_limit_per_sec=None,
)

players = st.sampled_from(PLAYERS * 8 + ("ghost",))
prices = st.one_of(st.integers(96, 104), st.integers(96, 104), st.integers(88, 112))
qtys = st.one_of(st.integers(1, 10), st.integers(1, 10), st.integers(-1, 12))
sides = st.sampled_from(Side)
order_types = st.sampled_from(OrderType)
client_ids = st.one_of(st.none(), st.none(), st.sampled_from(("a", "b", "c")))
