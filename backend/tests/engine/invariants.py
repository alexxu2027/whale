"""Exchange invariants that must hold after every command (PRD §32.1)."""

from __future__ import annotations

from collections import defaultdict

from whale.engine import Event, Exchange, MarketStatus, OrderCancelled, Side, Trade, TradeKind
from whale.engine.exchange import CallStage


def check_invariants(ex: Exchange) -> None:
    book = ex.book
    limit = ex.config.position_limit

    # Book is never crossed outside pre-open.
    bid, ask = book.best_price(Side.BUY), book.best_price(Side.SELL)
    if bid is not None and ask is not None and ex.status is not MarketStatus.PRE_OPEN:
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

    # Call reservations match live answered calls; each player is in at most one call.
    reserved: dict[str, int] = defaultdict(int)
    in_call: list[str] = []
    for call in ex.calls.values():
        in_call += [call.caller_id, call.responder_id]
        if call.stage is CallStage.AWAITING_DECISION:
            reserved[call.responder_id] += call.qty
            assert call.bid_price < call.ask_price <= call.bid_price + ex.config.call_max_width
    assert len(in_call) == len(set(in_call))
    for p, a in ex.accounts.items():
        assert a.call_reserved_qty == reserved[p], p
    if ex.status is not MarketStatus.OPEN:
        assert not ex.calls

    # Quote references point at the player's own live quote orders.
    for p, (bid_id, ask_id) in ex.quotes.items():
        for oid, side in ((bid_id, Side.BUY), (ask_id, Side.SELL)):
            if oid is None:
                continue
            o = book.get(oid)
            assert o is not None and o.player_id == p and o.is_quote and o.side is side


def check_events(events: list[Event], last_seq: int, last_ts: int = 0) -> tuple[int, int]:
    """Check one command's events; returns the new last (seq, ts)."""
    for e in events:
        assert e.seq == last_seq + 1
        last_seq = e.seq
        if isinstance(e, Trade):
            assert e.buyer_id != e.seller_id, "self-trade"
            assert e.qty > 0
            if e.kind is TradeKind.AUCTION:
                assert e.maker_id is e.taker_id is e.aggressor_side is None
            else:
                assert e.maker_id is not None and e.taker_id is not None
                assert e.maker_id != e.taker_id
                assert e.aggressor_side is (Side.BUY if e.taker_id == e.buyer_id else Side.SELL)
            if e.kind is TradeKind.CALL:
                assert e.call_id is not None and e.buy_order_id is e.sell_order_id is None
            else:
                assert e.buy_order_id is not None and e.sell_order_id is not None
        if isinstance(e, OrderCancelled):
            assert e.remaining_qty > 0
        assert e.ts >= last_ts, "event time went backwards"
        last_ts = e.ts
    return last_seq, last_ts
