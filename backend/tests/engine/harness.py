"""Shared helpers for engine scenario tests."""

from __future__ import annotations

from whale.engine import (
    Account,
    Event,
    Exchange,
    MarketConfig,
    MarketStatus,
    OrderAccepted,
    OrderRejected,
    PlaceOrder,
    RejectReason,
    SetQuote,
    Side,
    Trade,
)

from .invariants import check_events, check_invariants

BUY, SELL = Side.BUY, Side.SELL
CONFIG = MarketConfig(rate_limit_per_sec=None)


class Harness:
    """Wraps an exchange: advances time 1 ms per command (or to an explicit
    ``at``) and checks every invariant after every command."""

    def __init__(
        self,
        config: MarketConfig = CONFIG,
        players: tuple[str, ...] = ("alex", "sam", "maya"),
        status: MarketStatus = MarketStatus.OPEN,
        seed: int = 0,
    ) -> None:
        self.ex = Exchange(config, players, status=status, seed=seed)
        self.ts = 0
        self._seq = 0
        self._last_ts = 0

    def send(self, cmd_type: type, at: int | None = None, **kw: object) -> list[Event]:
        self.ts = self.ts + 1 if at is None else at
        events = self.ex.apply(cmd_type(ts=self.ts, **kw))
        self._seq, self._last_ts = check_events(events, self._seq, self._last_ts)
        check_invariants(self.ex)
        return events

    def place(self, player: str, side: Side, price: int, qty: int, **kw: object) -> list[Event]:
        return self.send(PlaceOrder, player_id=player, side=side, price=price, qty=qty, **kw)

    def quote(self, player: str, bid: int, bid_qty: int, ask: int, ask_qty: int) -> list[Event]:
        return self.send(SetQuote, player_id=player, bid_price=bid, bid_qty=bid_qty, ask_price=ask, ask_qty=ask_qty)

    def order_id(self, events: list[Event]) -> int:
        return next(e.order_id for e in events if isinstance(e, OrderAccepted))

    def account(self, player: str) -> Account:
        return self.ex.accounts[player]


def trades(events: list[Event]) -> list[Trade]:
    return [e for e in events if isinstance(e, Trade)]


def of_type[T](events: list[Event], cls: type[T]) -> list[T]:
    return [e for e in events if isinstance(e, cls)]


def rejection(events: list[Event]) -> RejectReason:
    (e,) = events
    assert isinstance(e, OrderRejected), e
    return e.reason
