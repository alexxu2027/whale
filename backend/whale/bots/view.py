"""What a bot may see when it acts: public market data plus its own state.

This stands in for the client-side state a human's browser would hold. It
reads only the top of the aggregated book (public), the bot's own account,
quote, and calls, and a few public rules. It never touches other players'
orders, clues, or the hidden value.
"""

from __future__ import annotations

from dataclasses import dataclass

from whale.engine import CallStage, Exchange, MarketStatus, Side


@dataclass(frozen=True, slots=True)
class CallView:
    call_id: int
    is_responder: bool
    counterparty: str
    stage: CallStage
    bid_price: int | None
    ask_price: int | None
    qty: int


@dataclass(frozen=True, slots=True)
class MarketView:
    now: int
    status: MarketStatus
    best_bid: int | None
    best_bid_qty: int
    best_ask: int | None
    best_ask_qty: int
    position: int
    room_to_buy: int  # how many more units the bot could buy within its limit
    room_to_sell: int
    my_bid: tuple[int, int] | None  # (price, qty) of the bot's quote sides
    my_ask: tuple[int, int] | None
    my_call: CallView | None
    others: tuple[str, ...]
    price_min: int
    price_max: int
    max_order_qty: int
    call_max_width: int
    call_min_qty: int
    call_cooldown_ms: int


def build_view(ex: Exchange, player_id: str, now: int) -> MarketView:
    cfg = ex.config
    acct = ex.accounts[player_id]
    (bid, bid_qty), = ex.book.depth(Side.BUY, 1) or [(None, 0)]
    (ask, ask_qty), = ex.book.depth(Side.SELL, 1) or [(None, 0)]

    def side(order_id: int | None) -> tuple[int, int] | None:
        o = ex.book.get(order_id) if order_id is not None else None
        return (o.price, o.qty) if o is not None else None

    bid_id, ask_id = ex.quotes.get(player_id, (None, None))
    my_call = None
    for call in ex.calls.values():
        if player_id in (call.caller_id, call.responder_id):
            responder = call.responder_id == player_id
            my_call = CallView(
                call_id=call.call_id,
                is_responder=responder,
                counterparty=call.caller_id if responder else call.responder_id,
                stage=call.stage,
                bid_price=call.bid_price,
                ask_price=call.ask_price,
                qty=call.qty,
            )
    return MarketView(
        now=now,
        status=ex.status,
        best_bid=bid,
        best_bid_qty=bid_qty,
        best_ask=ask,
        best_ask_qty=ask_qty,
        position=acct.position,
        room_to_buy=cfg.position_limit - acct.worst_case_long(),
        room_to_sell=cfg.position_limit + acct.worst_case_short(),
        my_bid=side(bid_id),
        my_ask=side(ask_id),
        my_call=my_call,
        others=tuple(p for p in ex.accounts if p != player_id),
        price_min=cfg.price_min,
        price_max=cfg.price_max,
        max_order_qty=cfg.max_order_qty,
        call_max_width=cfg.call_max_width,
        call_min_qty=cfg.call_min_qty,
        call_cooldown_ms=cfg.call_cooldown_ms,
    )
