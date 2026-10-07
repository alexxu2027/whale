"""Stateful property tests (PRD §32.1, §32.3, §32.5).

Hypothesis drives random sequences of commands, picking real live orders to
cancel and amend. Every command goes to two exchanges, one on the fast order
book and one on the reference book. After every step:

- both exchanges emitted identical events (differential test; since both run
  the same deterministic engine, this also checks replay determinism)
- every invariant in ``invariants.py`` holds

Each run starts in pre-open (quotes may cross), opens with the auction at a
random point, and includes Make Me a Market calls and time jumps that make
call deadlines expire. At teardown the market is closed and settlement must
be zero-sum.
"""

from __future__ import annotations

from hypothesis import HealthCheck, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from whale.engine import (
    AmendOrder,
    AnswerCall,
    CallPlayer,
    CallStage,
    CancelAll,
    CancelOrder,
    Command,
    DecideCall,
    Exchange,
    MarketStatus,
    Order,
    PlaceOrder,
    SetQuote,
    SetStatus,
    Side,
    Tick,
)

from .invariants import check_events, check_invariants
from .reference_book import ReferenceOrderBook
from .strategies import CONFIG, PLAYERS, client_ids, order_types, players, prices, qtys, sides


class ExchangeMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        pre_open = MarketStatus.PRE_OPEN
        self.fast = Exchange(CONFIG, PLAYERS, status=pre_open, seed=7)
        self.ref = Exchange(CONFIG, PLAYERS, book_factory=ReferenceOrderBook, status=pre_open, seed=7)
        self.ts = 0
        self.seq = 0
        self.last_ts = 0

    def send(self, cmd: Command) -> None:
        events = self.fast.apply(cmd)
        assert events == self.ref.apply(cmd)
        self.seq, self.last_ts = check_events(events, self.seq, self.last_ts)

    def tick(self) -> int:
        self.ts += 10
        return self.ts

    def pick_order(self, data: st.DataObject) -> tuple[str, int]:
        """A (player, order_id) pair: usually a live order and its owner."""
        live: list[Order] = sorted(self.fast.book.orders(), key=lambda o: o.order_id)
        if data.draw(st.integers(0, 9)) == 0:
            return data.draw(players), data.draw(st.integers(1, 500))
        order = data.draw(st.sampled_from(live))
        owner = order.player_id if data.draw(st.integers(0, 9)) else data.draw(players)
        return owner, order.order_id

    # -- rules -------------------------------------------------------------

    @rule(p=players, side=sides, price=prices, qty=qtys, kind=order_types, cid=client_ids)
    def place_again(self, p: str, side: Side, price: int, qty: int, kind, cid: str | None) -> None:
        self.place(p, side, price, qty, kind, cid)  # doubles the weight of order placement

    @rule(p=players, side=sides, price=prices, qty=qtys, kind=order_types, cid=client_ids)
    def place(self, p: str, side: Side, price: int, qty: int, kind, cid: str | None) -> None:
        self.send(PlaceOrder(player_id=p, ts=self.tick(), side=side, price=price, qty=qty, order_type=kind, client_order_id=cid))

    @rule(p=players, bid=prices, width=st.integers(-1, 6), bid_qty=qtys | st.just(0), ask_qty=qtys | st.just(0))
    def quote(self, p: str, bid: int, width: int, bid_qty: int, ask_qty: int) -> None:
        self.send(SetQuote(player_id=p, ts=self.tick(), bid_price=bid, bid_qty=bid_qty, ask_price=bid + width, ask_qty=ask_qty))

    @precondition(lambda self: self.fast.status is MarketStatus.PRE_OPEN)
    @rule(p=players, bid=st.integers(90, 108), width=st.integers(1, 4), bid_qty=st.integers(1, 10), ask_qty=st.integers(1, 10))
    def opening_quote(self, p: str, bid: int, width: int, bid_qty: int, ask_qty: int) -> None:
        # Opening quotes spread across the band, so they often cross and the
        # auction has something to do.
        self.quote(p, bid, width, bid_qty, ask_qty)

    @precondition(lambda self: len(self.fast.book) > 0)
    @rule(data=st.data())
    def cancel(self, data: st.DataObject) -> None:
        p, oid = self.pick_order(data)
        self.send(CancelOrder(player_id=p, ts=self.tick(), order_id=oid))

    @precondition(lambda self: len(self.fast.book) > 0)
    @rule(data=st.data(), qty=qtys, price=st.none() | prices)
    def amend(self, data: st.DataObject, qty: int, price: int | None) -> None:
        p, oid = self.pick_order(data)
        self.send(AmendOrder(player_id=p, ts=self.tick(), order_id=oid, qty=qty, price=price))

    @rule(p=players)
    def cancel_all(self, p: str) -> None:
        self.send(CancelAll(player_id=p, ts=self.tick()))

    @rule(roll=st.integers(0, 9))
    def change_status(self, roll: int) -> None:
        # Open from pre-open after a few steps; resume promptly from halts;
        # halt rarely, so most of the run is open trading.
        status = self.fast.status
        if status is MarketStatus.PRE_OPEN and roll < 3:
            self.send(SetStatus(ts=self.tick(), status=MarketStatus.OPEN))
        elif status is MarketStatus.HALTED:
            self.send(SetStatus(ts=self.tick(), status=MarketStatus.OPEN))
        elif status is MarketStatus.OPEN and roll == 0:
            self.send(SetStatus(ts=self.tick(), status=MarketStatus.HALTED))

    @rule(jump=st.sampled_from((100, 1_000, 4_000, 6_000, 16_000)))
    def wait(self, jump: int) -> None:
        self.ts += jump
        self.send(Tick(ts=self.ts))

    @rule(caller=players, callee=players)
    def call(self, caller: str, callee: str) -> None:
        self.send(CallPlayer(player_id=caller, ts=self.tick(), target_id=callee))

    @rule(data=st.data(), bid=prices, width=st.integers(0, 5), qty=st.integers(3, 10))
    def answer(self, data: st.DataObject, bid: int, width: int, qty: int) -> None:
        call = self.pick_call(data, CallStage.AWAITING_ANSWER)
        if call is None:
            return
        p = call.responder_id if data.draw(st.integers(0, 9)) else call.caller_id
        self.send(AnswerCall(player_id=p, ts=self.tick(), call_id=call.call_id, bid_price=bid, ask_price=bid + width, qty=qty))

    @rule(data=st.data(), side=st.none() | sides)
    def decide(self, data: st.DataObject, side: Side | None) -> None:
        call = self.pick_call(data, CallStage.AWAITING_DECISION)
        if call is None:
            return
        p = call.caller_id if data.draw(st.integers(0, 9)) else call.responder_id
        self.send(DecideCall(player_id=p, ts=self.tick(), call_id=call.call_id, side=side))

    def pick_call(self, data: st.DataObject, stage: CallStage):
        """Usually a call in the given stage; sometimes any call, to hit wrong-stage paths."""
        calls = sorted(self.fast.calls.values(), key=lambda c: c.call_id)
        if data.draw(st.integers(0, 9)):
            calls = [c for c in calls if c.stage is stage]
        return data.draw(st.sampled_from(calls)) if calls else None

    # -- checks ------------------------------------------------------------

    @invariant()
    def consistent(self) -> None:
        check_invariants(self.fast)
        check_invariants(self.ref)
        for side in Side:
            assert self.fast.book.depth(side) == self.ref.book.depth(side)
        assert self.fast.accounts == self.ref.accounts
        assert self.fast.quotes == self.ref.quotes
        assert self.fast.calls == self.ref.calls

    def teardown(self) -> None:
        self.send(SetStatus(ts=self.tick(), status=MarketStatus.CLOSED))
        assert len(self.fast.book) == 0
        check_invariants(self.fast)
        for final_value in (CONFIG.price_min, 100, CONFIG.price_max):
            total = sum(s.pnl_cents for s in self.fast.settle(final_value).values())
            assert total + self.fast.house_cash_cents == 0


TestExchangeMachine = ExchangeMachine.TestCase
TestExchangeMachine.settings = settings(
    max_examples=300,
    stateful_step_count=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
