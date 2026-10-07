"""The exchange: a deterministic state machine for one round's market.

``Exchange.apply(command) -> list[Event]`` is the only way to change state.
It performs no I/O and reads no clock or global randomness, so replaying the
same command stream always produces the same events and final state.

Semantics (PRD §28):

- Price-time priority. Fills happen at the resting order's price.
- Self-trade prevention: an incoming order never fills against its owner's
  resting order; the resting order is cancelled and matching continues.
- Pre-trade risk against worst-case exposure: position plus every live buy
  (or minus every live sell) must stay within the position limit.
- Post-only orders, including both sides of a quote, are rejected if they
  would cross any resting order.
- Every command is atomic: a rejected command changes nothing except the
  sender's rate-limit budget.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import Any, Protocol

from .accounts import Account, Settlement
from .book import OrderBook
from .commands import (
    AmendOrder,
    CancelAll,
    CancelOrder,
    Command,
    PlaceOrder,
    SetQuote,
    SetStatus,
)
from .config import CENTS_PER_POINT, MarketConfig
from .events import (
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
from .types import CancelReason, MarketStatus, Order, OrderType, RejectReason, Side


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


class _Rejected(Exception):
    def __init__(self, reason: RejectReason) -> None:
        self.reason = reason


def _crosses(side: Side, price: int, opposite_price: int) -> bool:
    return price >= opposite_price if side is Side.BUY else price <= opposite_price


class Exchange:
    def __init__(
        self,
        config: MarketConfig,
        player_ids: Iterable[str],
        *,
        book_factory: Callable[[int, int], Book] = OrderBook,
        status: MarketStatus = MarketStatus.OPEN,
    ) -> None:
        self.config = config
        self.book: Book = book_factory(config.price_min, config.price_max)
        self.status = status
        self.accounts: dict[str, Account] = {p: Account(p) for p in player_ids}
        self.house_cash_cents = 0  # taker fees minus maker rebates
        self.quotes: dict[str, tuple[int | None, int | None]] = {}
        self._limiters: dict[str, TokenBucket] = {}
        if config.rate_limit_per_sec is not None:
            self._limiters = {
                p: TokenBucket(config.rate_limit_per_sec, config.rate_limit_burst)
                for p in self.accounts
            }
        self._client_ids: dict[str, set[str]] = {p: set() for p in self.accounts}
        self._seq = 0
        self._next_order_id = 1
        self._next_trade_id = 1
        self._next_priority = 1
        self._ts = 0
        self._out: list[Event] = []

    # -- public API -------------------------------------------------------

    def apply(self, command: Command) -> list[Event]:
        self._ts = command.ts
        self._out = []
        try:
            match command:
                case PlaceOrder():
                    self._place(command)
                case CancelOrder():
                    self._cancel_order(command)
                case CancelAll():
                    self._cancel_all(command)
                case AmendOrder():
                    self._amend(command)
                case SetQuote():
                    self._set_quote(command)
                case SetStatus():
                    self._set_status(command)
                case _:
                    raise TypeError(f"unknown command {command!r}")
        except _Rejected as rej:
            self._emit(
                OrderRejected,
                player_id=getattr(command, "player_id", None),
                reason=rej.reason,
                order_id=getattr(command, "order_id", None),
                client_order_id=getattr(command, "client_order_id", None),
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

    # -- command handlers -------------------------------------------------

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
            # Size reduction: keeps priority, allowed even while halted.
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
        self._require_open()
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
        if self.status is MarketStatus.CLOSED or cmd.status is self.status:
            raise _Rejected(RejectReason.MARKET_NOT_OPEN)
        if cmd.status is MarketStatus.CLOSED:
            for order in sorted(self.book.orders(), key=lambda o: o.order_id):
                self._cancel(order, CancelReason.MARKET_CLOSED)
        self.status = cmd.status
        self._emit(StatusChanged, status=cmd.status)

    # -- matching ---------------------------------------------------------

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
        price = maker.price
        notional = price * qty * CENTS_PER_POINT
        buy, sell = (taker, maker) if taker.side is Side.BUY else (maker, taker)
        buyer, seller = self.accounts[buy.player_id], self.accounts[sell.player_id]

        buyer.position += qty
        buyer.cash_cents -= notional
        buyer.open_buy_qty -= qty
        buyer.volume += qty
        seller.position -= qty
        seller.cash_cents += notional
        seller.open_sell_qty -= qty
        seller.volume += qty

        rebate = self.config.maker_rebate_cents * qty
        fee = self.config.taker_fee_cents * qty
        maker_acct, taker_acct = self.accounts[maker.player_id], self.accounts[taker.player_id]
        maker_acct.cash_cents += rebate
        maker_acct.rebates_earned_cents += rebate
        taker_acct.cash_cents -= fee
        taker_acct.fees_paid_cents += fee
        self.house_cash_cents += fee - rebate

        taker.qty -= qty
        if maker.qty == qty:
            self.book.remove(maker.order_id)
            self._forget_quote_side(maker)
        else:
            self.book.reduce(maker.order_id, maker.qty - qty)

        trade_id = self._next_trade_id
        self._next_trade_id += 1
        self._emit(
            Trade,
            trade_id=trade_id,
            price=price,
            qty=qty,
            buyer_id=buy.player_id,
            seller_id=sell.player_id,
            maker_id=maker.player_id,
            taker_id=taker.player_id,
            maker_order_id=maker.order_id,
            taker_order_id=taker.order_id,
            aggressor_side=taker.side,
        )

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
