"""Exchange invariants that must hold after every command (PRD §32.1)."""

from __future__ import annotations

from collections import defaultdict

from whale.engine import Event, Exchange, OrderCancelled, Side, Trade


def check_invariants(ex: Exchange) -> None:
    book = ex.book
    limit = ex.config.position_limit

    # Book is never crossed.
    bid, ask = book.best_price(Side.BUY), book.best_price(Side.SELL)
    if bid is not None and ask is not None:
        assert bid < ask, f"crossed book {bid} / {ask}"

    # Every resting order is live, positive, in band, and reflected in depth.
    level_qty: dict[tuple[Side, int], int] = defaultdict(int)
    open_buy: dict[str, int] = defaultdict(int)
    open_sell: dict[str, int] = defaultdict(int)
    for o in book.orders():
        assert o.live and o.qty > 0
        assert ex.config.price_min <= o.price <= ex.config.price_max
        level_qty[(o.side, o.price)] += o.qty
        (open_buy if o.side is Side.BUY else open_sell)[o.player_id] += o.qty
    for side in Side:
        depth = book.depth(side)
        assert depth == sorted(
            ((p, q) for (s, p), q in level_qty.items() if s is side),
            key=lambda pq: -pq[0] if side is Side.BUY else pq[0],
        )
        best = book.best_order(side)
        assert (best.price if best else None) == (depth[0][0] if depth else None)

    # Conservation: units and cash net to zero across players and the house.
    assert sum(a.position for a in ex.accounts.values()) == 0
    assert sum(a.cash_cents for a in ex.accounts.values()) + ex.house_cash_cents == 0

    for p, a in ex.accounts.items():
        # Open-order exposure is tracked exactly.
        assert a.open_buy_qty == open_buy[p], p
        assert a.open_sell_qty == open_sell[p], p
        # Worst-case exposure never exceeds the position limit.
        assert a.worst_case_long() <= limit, p
        assert a.worst_case_short() >= -limit, p

    # Quote references point at the player's own live quote orders.
    for p, (bid_id, ask_id) in ex.quotes.items():
        for oid, side in ((bid_id, Side.BUY), (ask_id, Side.SELL)):
            if oid is None:
                continue
            o = book.get(oid)
            assert o is not None and o.player_id == p and o.is_quote and o.side is side


def check_events(events: list[Event], last_seq: int) -> int:
    """Check one command's events; returns the new last sequence number."""
    for e in events:
        assert e.seq == last_seq + 1
        last_seq = e.seq
        if isinstance(e, Trade):
            assert e.buyer_id != e.seller_id, "self-trade"
            assert e.qty > 0
            assert e.maker_id != e.taker_id
            assert e.aggressor_side is (Side.BUY if e.taker_id == e.buyer_id else Side.SELL)
        if isinstance(e, OrderCancelled):
            assert e.remaining_qty > 0
    return last_seq
