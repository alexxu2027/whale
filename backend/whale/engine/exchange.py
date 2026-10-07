"""The exchange: a deterministic state machine for one round's market.

``Exchange.apply(command) -> list[Event]`` is the only way to change state.
It performs no I/O and reads no clock or global randomness (auction ties use
a seeded generator), so replaying the same command stream always produces
the same events and final state.

Semantics (PRD §28, §8.2):

- Price-time priority. Fills happen at the resting order's price.
- Self-trade prevention: an incoming order never fills against its owner's
  resting order; the resting order is cancelled and matching continues.
- Pre-trade risk against worst-case exposure: position plus every live buy
  (or minus every live sell), plus any live call answer, must stay within the
  position limit.
- Post-only orders, including both sides of a quote, are rejected if they
  would cross any resting order.
- Pre-open: only quotes (and cancels) are accepted, and they rest without
  matching. Opening the market runs a single-price auction.
- Make Me a Market calls are bilateral trades outside the book, with
  deadlines. Deadlines are processed at the start of every command, stamped
  with the deadline's own time, so no clock is needed and replays are exact.
- Every command is atomic: a rejected command changes nothing except the
  sender's rate-limit budget (and any deadlines that had already passed).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Protocol

from .accounts import Account, Settlement
from .book import OrderBook
from .commands import (
    AmendOrder,
    AnswerCall,
    CallPlayer,
    CancelAll,
    CancelOrder,
    Command,
    DecideCall,
    PlaceOrder,
    SetQuote,
    SetStatus,
    Tick,
)
from .config import CENTS_PER_POINT, MarketConfig
from .events import (
    CallAnswered,
    CallEnded,
    CallStarted,
    Event,
    OrderAccepted,
    OrderAmended,
    OrderCancelled,
    OrderRejected,
    QuoteUpdated,
    StatusChanged,
    Trade,
)
from .risk import TokenBucket
from .types import (
    CallOutcome,
    CancelReason,
    MarketStatus,
    Order,
    OrderType,
    RejectReason,
    Side,
    TradeKind,
)


class Book(Protocol):
    def add(self, order: Order) -> None: ...
    def remove(self, order_id: int) -> Order: ...
    def reduce(self, order_id: int, qty: int) -> None: ...
    def get(self, order_id: int) -> Order | None: ...
    def best_order(self, side: Side) -> Order | None: ...
    def best_price(self, side: Side, exclude: int | None = None) -> int | None: ...
    def depth(self, side: Side, levels: int | None = None) -> list[tuple[int, int]]: ...
    def orders(self) -> Iterable[Order]: ...
    def __len__(self) -> int: ...


class CallStage(Enum):
    AWAITING_ANSWER = "awaiting_answer"
    AWAITING_DECISION = "awaiting_decision"


@dataclass(slots=True)
class Call:
    call_id: int
    caller_id: str
    responder_id: str
    stage: CallStage
    answer_by: int
    decide_by: int | None = None
    bid_price: int | None = None
    ask_price: int | None = None
    qty: int = 0

    @property
    def deadline(self) -> int:
        return self.answer_by if self.stage is CallStage.AWAITING_ANSWER else self.decide_by  # type: ignore[return-value]


class _Rejected(Exception):
    def __init__(self, reason: RejectReason) -> None:
        self.reason = reason


def _crosses(side: Side, price: int, opposite_price: int) -> bool:
    return price >= opposite_price if side is Side.BUY else price <= opposite_price


_TRANSITIONS: dict[MarketStatus, set[MarketStatus]] = {
    MarketStatus.PRE_OPEN: {MarketStatus.OPEN, MarketStatus.CLOSED},
    MarketStatus.OPEN: {MarketStatus.HALTED, MarketStatus.CLOSED},
    MarketStatus.HALTED: {MarketStatus.OPEN, MarketStatus.CLOSED},
    MarketStatus.CLOSED: set(),
}


class Exchange:
    def __init__(
        self,
        config: MarketConfig,
        player_ids: Iterable[str],
        *,
        book_factory: Callable[[int, int], Book] = OrderBook,
        status: MarketStatus = MarketStatus.OPEN,
        seed: int = 0,
    ) -> None:
        self.config = config
        self.book: Book = book_factory(config.price_min, config.price_max)
        self.status = status
        self.accounts: dict[str, Account] = {p: Account(p) for p in player_ids}
        self.house_cash_cents = 0  # taker fees minus maker rebates, plus penalties
        self.quotes: dict[str, tuple[int | None, int | None]] = {}
        self.calls: dict[int, Call] = {}
        self._rng = random.Random(seed)
        self._limiters: dict[str, TokenBucket] = {}
        if config.rate_limit_per_sec is not None:
            self._limiters = {
                p: TokenBucket(config.rate_limit_per_sec, config.rate_limit_burst)
                for p in self.accounts
            }
        self._client_ids: dict[str, set[str]] = {p: set() for p in self.accounts}
        self._in_call: dict[str, int] = {}
        self._busy_until: dict[str, int] = {}
        self._last_call_at: dict[str, int] = {}
        self._seq = 0
        self._next_order_id = 1
        self._next_trade_id = 1
        self._next_call_id = 1
        self._next_priority = 1
        self._ts = 0
        self._out: list[Event] = []
        self._handlers: dict[type, Callable[[Any], None]] = {
            PlaceOrder: self._place,
            CancelOrder: self._cancel_order,
            CancelAll: self._cancel_all,
            AmendOrder: self._amend,
            SetQuote: self._set_quote,
            CallPlayer: self._call_player,
            AnswerCall: self._answer_call,
            DecideCall: self._decide_call,
            Tick: lambda _: None,  # deadlines were already processed above
            SetStatus: self._set_status,
        }

    # -- public API -------------------------------------------------------

    def apply(self, command: Command) -> list[Event]:
        self._out = []
        self._expire_calls(command.ts)
        self._ts = command.ts
        handler = self._handlers.get(type(command))
        if handler is None:
            raise TypeError(f"unknown command {command!r}")
        try:
            handler(command)
        except _Rejected as rej:
            self._emit(
                OrderRejected,
                player_id=getattr(command, "player_id", None),
                reason=rej.reason,
                order_id=getattr(command, "order_id", None),
                client_order_id=getattr(command, "client_order_id", None),
                call_id=getattr(command, "call_id", None),
            )
        out, self._out = self._out, []
        return out

    def settle(self, final_value: int) -> dict[str, Settlement]:
        if self.status is not MarketStatus.CLOSED:
            raise RuntimeError("settle requires a closed market")
        return {
            p: Settlement(
                player_id=p,
                position=a.position,
                cash_cents=a.cash_cents,
                pnl_cents=a.cash_cents + a.position * final_value * CENTS_PER_POINT,
            )
            for p, a in self.accounts.items()
        }

    # -- order handlers ---------------------------------------------------

    def _place(self, cmd: PlaceOrder) -> None:
        acct = self._account(cmd.player_id)
        self._require_open()
        self._rate_limit(cmd.player_id)
        if cmd.client_order_id is not None and cmd.client_order_id in self._client_ids[cmd.player_id]:
            raise _Rejected(RejectReason.DUPLICATE_CLIENT_ORDER_ID)
        self._validate_price_qty(cmd.price, cmd.qty)
        self._check_limit(acct, cmd.side, cmd.qty)
        if cmd.order_type is OrderType.POST_ONLY:
            self._check_post_only(cmd.side, cmd.price)

        if cmd.client_order_id is not None:
            self._client_ids[cmd.player_id].add(cmd.client_order_id)
        order = self._new_order(
            cmd.player_id, cmd.side, cmd.price, cmd.qty, cmd.order_type, cmd.client_order_id
        )
        self._execute(order)

    def _cancel_order(self, cmd: CancelOrder) -> None:
        self._account(cmd.player_id)
        order = self._owned_order(cmd.player_id, cmd.order_id)
        self._cancel(order, CancelReason.USER)

    def _cancel_all(self, cmd: CancelAll) -> None:
        self._account(cmd.player_id)
        mine = sorted(
            (o for o in self.book.orders() if o.player_id == cmd.player_id),
            key=lambda o: o.order_id,
        )
        for order in mine:
            self._cancel(order, CancelReason.USER)

    def _amend(self, cmd: AmendOrder) -> None:
        acct = self._account(cmd.player_id)
        if self.status is MarketStatus.CLOSED:
            raise _Rejected(RejectReason.MARKET_NOT_OPEN)
        self._rate_limit(cmd.player_id)
        order = self._owned_order(cmd.player_id, cmd.order_id)
        price = order.price if cmd.price is None else cmd.price
        self._validate_price_qty(price, cmd.qty)
        if price == order.price and cmd.qty == order.qty:
            raise _Rejected(RejectReason.NO_CHANGE)

        if price == order.price and cmd.qty < order.qty:
            # Size reduction: keeps priority, allowed in any phase but closed.
            self._release(acct, order.side, order.qty - cmd.qty)
            self.book.reduce(order.order_id, cmd.qty)
            self._emit(
                OrderAmended,
                order_id=order.order_id,
                player_id=order.player_id,
                price=price,
                qty=cmd.qty,
                priority_kept=True,
            )
            return

        self._require_open()
        self._check_limit(acct, order.side, cmd.qty, release=order.qty)
        if order.order_type is OrderType.POST_ONLY:
            self._check_post_only(order.side, price)

        self.book.remove(order.order_id)
        self._release(acct, order.side, order.qty)
        new = replace(order, price=price, qty=cmd.qty, priority=self._take_priority(), live=True)
        self._reserve(acct, new.side, new.qty)
        self._emit(
            OrderAmended,
            order_id=new.order_id,
            player_id=new.player_id,
            price=price,
            qty=cmd.qty,
            priority_kept=False,
        )
        self._match_and_rest(new)

    def _set_quote(self, cmd: SetQuote) -> None:
        acct = self._account(cmd.player_id)
        if self.status not in (MarketStatus.OPEN, MarketStatus.PRE_OPEN):
            raise _Rejected(RejectReason.MARKET_NOT_OPEN)
        self._rate_limit(cmd.player_id)
        if cmd.bid_qty < 0 or cmd.ask_qty < 0:
            raise _Rejected(RejectReason.INVALID_QTY)
        if cmd.bid_qty:
            self._validate_price_qty(cmd.bid_price, cmd.bid_qty)
        if cmd.ask_qty:
            self._validate_price_qty(cmd.ask_price, cmd.ask_qty)
        if cmd.bid_qty and cmd.ask_qty and cmd.bid_price >= cmd.ask_price:
            raise _Rejected(RejectReason.INVALID_QUOTE)

        old_bid_id, old_ask_id = self.quotes.get(cmd.player_id, (None, None))
        old_bid = self.book.get(old_bid_id) if old_bid_id is not None else None
        old_ask = self.book.get(old_ask_id) if old_ask_id is not None else None

        # Validate everything before touching the book, so a rejection leaves
        # the old quote exactly as it was.
        self._check_limit(acct, Side.BUY, cmd.bid_qty, release=old_bid.qty if old_bid else 0)
        self._check_limit(acct, Side.SELL, cmd.ask_qty, release=old_ask.qty if old_ask else 0)
        if self.status is MarketStatus.OPEN:  # pre-open quotes may cross
            if cmd.bid_qty:
                self._check_post_only(Side.BUY, cmd.bid_price, exclude=old_ask_id)
            if cmd.ask_qty:
                self._check_post_only(Side.SELL, cmd.ask_price, exclude=old_bid_id)

        # Retire both old sides before posting either new one; otherwise a new
        # bid could briefly cross the player's own outgoing ask.
        keep_bid = self._retire_quote_side(acct, old_bid, cmd.bid_price, cmd.bid_qty)
        keep_ask = self._retire_quote_side(acct, old_ask, cmd.ask_price, cmd.ask_qty)
        bid_id = old_bid_id if keep_bid else self._post_quote_side(acct, Side.BUY, cmd.bid_price, cmd.bid_qty)
        ask_id = old_ask_id if keep_ask else self._post_quote_side(acct, Side.SELL, cmd.ask_price, cmd.ask_qty)
        self.quotes[cmd.player_id] = (bid_id, ask_id)
        self._emit(QuoteUpdated, player_id=cmd.player_id, bid_order_id=bid_id, ask_order_id=ask_id)

    def _set_status(self, cmd: SetStatus) -> None:
        if cmd.status not in _TRANSITIONS[self.status]:
            raise _Rejected(RejectReason.INVALID_TRANSITION)
        if cmd.status in (MarketStatus.HALTED, MarketStatus.CLOSED):
            for call in sorted(self.calls.values(), key=lambda c: c.call_id):
                self._end_call(call, CallOutcome.CANCELLED)
        if cmd.status is MarketStatus.CLOSED:
            for order in sorted(self.book.orders(), key=lambda o: o.order_id):
                self._cancel(order, CancelReason.MARKET_CLOSED)
        was_pre_open = self.status is MarketStatus.PRE_OPEN
        self.status = cmd.status
        self._emit(StatusChanged, status=cmd.status)
        if was_pre_open and cmd.status is MarketStatus.OPEN:
            self._run_opening_auction()

    # -- continuous matching ----------------------------------------------

    def _execute(self, order: Order) -> None:
        self._reserve(self.accounts[order.player_id], order.side, order.qty)
        self._emit(
            OrderAccepted,
            order_id=order.order_id,
            player_id=order.player_id,
            side=order.side,
            price=order.price,
            qty=order.qty,
            order_type=order.order_type,
            client_order_id=order.client_order_id,
            is_quote=order.is_quote,
        )
        if self.status is MarketStatus.PRE_OPEN:
            self.book.add(order)  # rests unmatched until the opening auction
        else:
            self._match_and_rest(order)

    def _match_and_rest(self, order: Order) -> None:
        opposite = order.side.opposite
        while order.qty > 0:
            maker = self.book.best_order(opposite)
            if maker is None or not _crosses(order.side, order.price, maker.price):
                break
            if maker.player_id == order.player_id:
                self._cancel(maker, CancelReason.SELF_TRADE_PREVENTED)
                continue
            self._fill(maker, order, min(order.qty, maker.qty))

        if order.qty == 0:
            self._forget_quote_side(order)
        elif order.order_type is OrderType.IOC:
            self._release(self.accounts[order.player_id], order.side, order.qty)
            self._emit_cancelled(order, CancelReason.IOC_REMAINDER)
        else:
            self.book.add(order)

    def _fill(self, maker: Order, taker: Order, qty: int) -> None:
        buy, sell = (taker, maker) if taker.side is Side.BUY else (maker, taker)
        self.accounts[buy.player_id].open_buy_qty -= qty
        self.accounts[sell.player_id].open_sell_qty -= qty
        taker.qty -= qty
        self._take_from_book(maker, qty)
        self._trade(
            TradeKind.BOOK,
            maker.price,
            qty,
            buy.player_id,
            sell.player_id,
            maker_id=maker.player_id,
            taker_id=taker.player_id,
            aggressor_side=taker.side,
            buy_order_id=buy.order_id,
            sell_order_id=sell.order_id,
        )

    def _take_from_book(self, order: Order, qty: int) -> None:
        if order.qty == qty:
            self.book.remove(order.order_id)
            self._forget_quote_side(order)
        else:
            self.book.reduce(order.order_id, order.qty - qty)

    def _trade(
        self,
        kind: TradeKind,
        price: int,
        qty: int,
        buyer_id: str,
        seller_id: str,
        *,
        maker_id: str | None,
        taker_id: str | None,
        aggressor_side: Side | None,
        buy_order_id: int | None = None,
        sell_order_id: int | None = None,
        call_id: int | None = None,
    ) -> int:
        """Move units and cash, charge fees, and emit the Trade event."""
        notional = price * qty * CENTS_PER_POINT
        buyer, seller = self.accounts[buyer_id], self.accounts[seller_id]
        buyer.position += qty
        buyer.cash_cents -= notional
        buyer.volume += qty
        seller.position -= qty
        seller.cash_cents += notional
        seller.volume += qty

        if maker_id is not None and taker_id is not None:
            rebate = self.config.maker_rebate_cents * qty
            fee = self.config.taker_fee_cents * qty
            maker, taker = self.accounts[maker_id], self.accounts[taker_id]
            maker.cash_cents += rebate
            maker.rebates_earned_cents += rebate
            taker.cash_cents -= fee
            taker.fees_paid_cents += fee
            self.house_cash_cents += fee - rebate

        trade_id = self._next_trade_id
        self._next_trade_id += 1
        self._emit(
            Trade,
            trade_id=trade_id,
            kind=kind,
            price=price,
            qty=qty,
            buyer_id=buyer_id,
            seller_id=seller_id,
            maker_id=maker_id,
            taker_id=taker_id,
            aggressor_side=aggressor_side,
            buy_order_id=buy_order_id,
            sell_order_id=sell_order_id,
            call_id=call_id,
        )
        return trade_id

    # -- opening auction (PRD §28.7) ----------------------------------------

    def _run_opening_auction(self) -> None:
        """Cross pre-open quotes at the single price that maximizes volume.

        Ties: smallest buy/sell imbalance, then closest to the reference price,
        then the lower price. Orders are filled in price priority, and in a
        seeded random order within a price, so arriving first in pre-open
        earns nothing. Unfilled orders then rest in that same order.

        Pre-open only accepts quotes, and a quote's bid is below its ask, so a
        player can never be on both sides of the auction.
        """
        buys = self._auction_ranking(Side.BUY)
        sells = self._auction_ranking(Side.SELL)

        best: tuple[tuple[int, int, int, int], int] | None = None
        ref = self.config.reference
        for p in sorted({o.price for o in buys + sells}):
            bv = sum(o.qty for o in buys if o.price >= p)
            sv = sum(o.qty for o in sells if o.price <= p)
            matched = min(bv, sv)
            if matched:
                key = (-matched, abs(bv - sv), abs(p - ref), p)
                if best is None or key < best[0]:
                    best = (key, p)

        if best is not None:
            price = best[1]
            eligible_buys = [o for o in buys if o.price >= price]
            eligible_sells = [o for o in sells if o.price <= price]
            i = j = 0
            while i < len(eligible_buys) and j < len(eligible_sells):
                b, s = eligible_buys[i], eligible_sells[j]
                qty = min(b.qty, s.qty)
                self.accounts[b.player_id].open_buy_qty -= qty
                self.accounts[s.player_id].open_sell_qty -= qty
                self._take_from_book(b, qty)
                self._take_from_book(s, qty)
                self._trade(
                    TradeKind.AUCTION,
                    price,
                    qty,
                    b.player_id,
                    s.player_id,
                    maker_id=None,
                    taker_id=None,
                    aggressor_side=None,
                    buy_order_id=b.order_id,
                    sell_order_id=s.order_id,
                )
                i += not b.live
                j += not s.live

        # Re-queue survivors in auction order with fresh priorities.
        for order in buys + sells:
            if order.live:
                self.book.remove(order.order_id)
                self.book.add(replace(order, priority=self._take_priority(), live=True))

    def _auction_ranking(self, side: Side) -> list[Order]:
        orders = sorted((o for o in self.book.orders() if o.side is side), key=lambda o: o.order_id)
        self._rng.shuffle(orders)
        # Stable sort: price priority, shuffled order within a price.
        return sorted(orders, key=lambda o: -o.price if side is Side.BUY else o.price)

    # -- Make Me a Market (PRD §8.2) -----------------------------------------

    def _call_player(self, cmd: CallPlayer) -> None:
        self._account(cmd.player_id)
        target = self._account(cmd.target_id)
        self._require_open()
        self._rate_limit(cmd.player_id)
        if cmd.target_id == cmd.player_id:
            raise _Rejected(RejectReason.SELF_CALL)
        if cmd.player_id in self._in_call or cmd.target_id in self._in_call:
            raise _Rejected(RejectReason.PLAYER_BUSY)
        if cmd.ts < self._busy_until.get(cmd.target_id, cmd.ts):
            raise _Rejected(RejectReason.PLAYER_BUSY)
        last = self._last_call_at.get(cmd.player_id)
        if last is not None and cmd.ts < last + self.config.call_cooldown_ms:
            raise _Rejected(RejectReason.CALL_COOLDOWN)
        if not self._can_quote_both(target, self.config.call_min_qty):
            raise _Rejected(RejectReason.TARGET_AT_LIMIT)

        call = Call(
            call_id=self._next_call_id,
            caller_id=cmd.player_id,
            responder_id=cmd.target_id,
            stage=CallStage.AWAITING_ANSWER,
            answer_by=cmd.ts + self.config.call_answer_ms,
        )
        self._next_call_id += 1
        self.calls[call.call_id] = call
        self._in_call[call.caller_id] = self._in_call[call.responder_id] = call.call_id
        self._last_call_at[cmd.player_id] = cmd.ts
        self._emit(
            CallStarted,
            call_id=call.call_id,
            caller_id=call.caller_id,
            responder_id=call.responder_id,
            answer_by=call.answer_by,
        )

    def _answer_call(self, cmd: AnswerCall) -> None:
        acct = self._account(cmd.player_id)
        call = self._call_for(cmd.call_id, cmd.player_id, responder=True)
        if call.stage is not CallStage.AWAITING_ANSWER:
            raise _Rejected(RejectReason.CALL_WRONG_STAGE)
        if cmd.qty < self.config.call_min_qty:
            raise _Rejected(RejectReason.INVALID_QTY)
        self._validate_price_qty(cmd.bid_price, cmd.qty)
        self._validate_price_qty(cmd.ask_price, cmd.qty)
        if not 0 < cmd.ask_price - cmd.bid_price <= self.config.call_max_width:
            raise _Rejected(RejectReason.INVALID_QUOTE)
        if not self._can_quote_both(acct, cmd.qty):
            raise _Rejected(RejectReason.POSITION_LIMIT)
        self._quote_call(call, cmd.bid_price, cmd.ask_price, cmd.qty, automatic=False, penalty=0)

    def _decide_call(self, cmd: DecideCall) -> None:
        caller = self._account(cmd.player_id)
        call = self._call_for(cmd.call_id, cmd.player_id, responder=False)
        if call.stage is not CallStage.AWAITING_DECISION:
            raise _Rejected(RejectReason.CALL_WRONG_STAGE)
        if cmd.side is None:
            self._end_call(call, CallOutcome.PASSED)
            return
        self._check_limit(caller, cmd.side, call.qty)
        if cmd.side is Side.BUY:
            price, buyer, seller = call.ask_price, call.caller_id, call.responder_id
        else:
            price, buyer, seller = call.bid_price, call.responder_id, call.caller_id
        assert price is not None
        trade_id = self._trade(
            TradeKind.CALL,
            price,
            call.qty,
            buyer,
            seller,
            maker_id=call.responder_id,
            taker_id=call.caller_id,
            aggressor_side=cmd.side,
            call_id=call.call_id,
        )
        self._end_call(call, CallOutcome.TRADED, trade_id)

    def _quote_call(self, call: Call, bid: int, ask: int, qty: int, *, automatic: bool, penalty: int) -> None:
        call.stage = CallStage.AWAITING_DECISION
        call.bid_price, call.ask_price, call.qty = bid, ask, qty
        call.decide_by = self._ts + self.config.call_decide_ms
        acct = self.accounts[call.responder_id]
        acct.call_reserved_qty += qty
        if penalty:
            acct.cash_cents -= penalty
            acct.penalties_cents += penalty
            self.house_cash_cents += penalty
        self._emit(
            CallAnswered,
            call_id=call.call_id,
            responder_id=call.responder_id,
            bid_price=bid,
            ask_price=ask,
            qty=qty,
            automatic=automatic,
            penalty_cents=penalty,
            decide_by=call.decide_by,
        )

    def _end_call(self, call: Call, outcome: CallOutcome, trade_id: int | None = None) -> None:
        if call.stage is CallStage.AWAITING_DECISION:
            self.accounts[call.responder_id].call_reserved_qty -= call.qty
        del self.calls[call.call_id]
        del self._in_call[call.caller_id]
        del self._in_call[call.responder_id]
        self._busy_until[call.responder_id] = self._ts + self.config.call_busy_ms
        self._emit(CallEnded, call_id=call.call_id, outcome=outcome, trade_id=trade_id)

    def _expire_calls(self, now: int) -> None:
        """Process every call deadline at or before ``now``, in deadline order."""
        while self.calls:
            call = min(self.calls.values(), key=lambda c: (c.deadline, c.call_id))
            if call.deadline > now:
                return
            self._ts = call.deadline
            if call.stage is CallStage.AWAITING_DECISION:
                self._end_call(call, CallOutcome.DECISION_TIMEOUT)
            else:
                self._auto_answer(call)

    def _auto_answer(self, call: Call) -> None:
        """The responder ran out of time: answer with their own market if it
        qualifies, otherwise with the widest allowed market and a penalty."""
        cfg = self.config
        acct = self.accounts[call.responder_id]
        if not self._can_quote_both(acct, cfg.call_min_qty):
            self._end_call(call, CallOutcome.CANCELLED)
            return

        bid_id, ask_id = self.quotes.get(call.responder_id, (None, None))
        bid = self.book.get(bid_id) if bid_id is not None else None
        ask = self.book.get(ask_id) if ask_id is not None else None
        if (
            bid is not None
            and ask is not None
            and ask.price - bid.price <= cfg.call_max_width
            and min(bid.qty, ask.qty) >= cfg.call_min_qty
        ):
            self._quote_call(call, bid.price, ask.price, cfg.call_min_qty, automatic=True, penalty=0)
            return

        if bid is not None and ask is not None:
            twice_mid = bid.price + ask.price
        else:
            best_bid, best_ask = self.book.best_price(Side.BUY), self.book.best_price(Side.SELL)
            twice_mid = best_bid + best_ask if best_bid is not None and best_ask is not None else 2 * cfg.reference
        lo = min(max((twice_mid - cfg.call_max_width) // 2, cfg.price_min), cfg.price_max - cfg.call_max_width)
        self._quote_call(
            call,
            lo,
            lo + cfg.call_max_width,
            cfg.call_min_qty,
            automatic=True,
            penalty=cfg.call_no_answer_penalty_cents,
        )

    def _call_for(self, call_id: int, player_id: str, *, responder: bool) -> Call:
        call = self.calls.get(call_id)
        if call is None:
            raise _Rejected(RejectReason.UNKNOWN_CALL)
        if player_id != (call.responder_id if responder else call.caller_id):
            raise _Rejected(RejectReason.NOT_YOUR_CALL)
        return call

    def _can_quote_both(self, acct: Account, qty: int) -> bool:
        limit = self.config.position_limit
        return acct.worst_case_long() + qty <= limit and acct.worst_case_short() - qty >= -limit

    # -- quotes -----------------------------------------------------------

    def _retire_quote_side(self, acct: Account, old: Order | None, price: int, qty: int) -> bool:
        """Cancel or shrink an old quote side. Returns True if it is kept as-is."""
        if old is None:
            return False
        if qty and old.price == price and qty <= old.qty:
            if qty < old.qty:
                self._release(acct, old.side, old.qty - qty)
                self.book.reduce(old.order_id, qty)
                self._emit(
                    OrderAmended,
                    order_id=old.order_id,
                    player_id=old.player_id,
                    price=price,
                    qty=qty,
                    priority_kept=True,
                )
            return True
        self._cancel(old, CancelReason.QUOTE_REPLACED)
        return False

    def _post_quote_side(self, acct: Account, side: Side, price: int, qty: int) -> int | None:
        if not qty:
            return None
        order = self._new_order(acct.player_id, side, price, qty, OrderType.POST_ONLY, None, True)
        self._execute(order)
        return order.order_id

    def _forget_quote_side(self, order: Order) -> None:
        if not order.is_quote:
            return
        bid_id, ask_id = self.quotes.get(order.player_id, (None, None))
        if order.order_id == bid_id:
            bid_id = None
        elif order.order_id == ask_id:
            ask_id = None
        self.quotes[order.player_id] = (bid_id, ask_id)

    # -- helpers ----------------------------------------------------------

    def _cancel(self, order: Order, reason: CancelReason) -> None:
        self.book.remove(order.order_id)
        self._release(self.accounts[order.player_id], order.side, order.qty)
        self._forget_quote_side(order)
        self._emit_cancelled(order, reason)

    def _emit_cancelled(self, order: Order, reason: CancelReason) -> None:
        self._emit(
            OrderCancelled,
            order_id=order.order_id,
            player_id=order.player_id,
            side=order.side,
            price=order.price,
            remaining_qty=order.qty,
            reason=reason,
        )

    def _new_order(
        self,
        player_id: str,
        side: Side,
        price: int,
        qty: int,
        order_type: OrderType,
        client_order_id: str | None,
        is_quote: bool = False,
    ) -> Order:
        order_id = self._next_order_id
        self._next_order_id += 1
        return Order(
            order_id=order_id,
            player_id=player_id,
            side=side,
            price=price,
            qty=qty,
            priority=self._take_priority(),
            order_type=order_type,
            client_order_id=client_order_id,
            is_quote=is_quote,
        )

    def _take_priority(self) -> int:
        p = self._next_priority
        self._next_priority += 1
        return p

    def _reserve(self, acct: Account, side: Side, qty: int) -> None:
        if side is Side.BUY:
            acct.open_buy_qty += qty
        else:
            acct.open_sell_qty += qty

    def _release(self, acct: Account, side: Side, qty: int) -> None:
        if side is Side.BUY:
            acct.open_buy_qty -= qty
        else:
            acct.open_sell_qty -= qty

    def _account(self, player_id: str) -> Account:
        acct = self.accounts.get(player_id)
        if acct is None:
            raise _Rejected(RejectReason.UNKNOWN_PLAYER)
        return acct

    def _owned_order(self, player_id: str, order_id: int) -> Order:
        order = self.book.get(order_id)
        if order is None:
            raise _Rejected(RejectReason.UNKNOWN_ORDER)
        if order.player_id != player_id:
            raise _Rejected(RejectReason.NOT_OWNER)
        return order

    def _require_open(self) -> None:
        if self.status is not MarketStatus.OPEN:
            raise _Rejected(RejectReason.MARKET_NOT_OPEN)

    def _rate_limit(self, player_id: str) -> None:
        limiter = self._limiters.get(player_id)
        if limiter is not None and not limiter.take(self._ts):
            raise _Rejected(RejectReason.RATE_LIMITED)

    def _validate_price_qty(self, price: int, qty: int) -> None:
        if not self.config.price_min <= price <= self.config.price_max:
            raise _Rejected(RejectReason.PRICE_OUT_OF_BAND)
        if not 1 <= qty <= self.config.max_order_qty:
            raise _Rejected(RejectReason.INVALID_QTY)

    def _check_limit(self, acct: Account, side: Side, qty: int, release: int = 0) -> None:
        limit = self.config.position_limit
        if side is Side.BUY:
            ok = acct.worst_case_long() - release + qty <= limit
        else:
            ok = acct.worst_case_short() + release - qty >= -limit
        if not ok:
            raise _Rejected(RejectReason.POSITION_LIMIT)

    def _check_post_only(self, side: Side, price: int, exclude: int | None = None) -> None:
        opposite = self.book.best_price(side.opposite, exclude)
        if opposite is not None and _crosses(side, price, opposite):
            raise _Rejected(RejectReason.WOULD_CROSS)

    def _emit(self, cls: type[Event], **fields: Any) -> None:
        self._seq += 1
        self._out.append(cls(seq=self._seq, ts=self._ts, **fields))
