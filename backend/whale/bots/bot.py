"""The bot: one reasoning core, parameterized by personality (PRD §19).

A bot is an ordinary client. It learns only from events it is allowed to see
(``observe``) and the public view of the market (``act``), and it acts by
returning the same commands a human's client would send.

Each action, in priority order:

1. Answer or decide a call it is part of.
2. Maybe trade randomly (noise) or against its own view (bluff).
3. Otherwise take an offer if its edge beats ``take_edge``.
4. Maybe call another player.
5. Re-quote its market around fair value, leaning against inventory.
"""

from __future__ import annotations

import math
import random

from whale.engine import (
    AnswerCall,
    CallAnswered,
    CallPlayer,
    CallStage,
    Command,
    DecideCall,
    Event,
    MarketStatus,
    OrderRejected,
    OrderType,
    PlaceOrder,
    RejectReason,
    SetQuote,
    Side,
    Trade,
)
from whale.game.dealing import Clue
from whale.game.recipes import Recipe
from whale.game.setup import Dealing

from .beliefs import BeliefTracker
from .personalities import Personality
from .view import MarketView


class Bot:
    def __init__(
        self,
        player_id: str,
        personality: Personality,
        clue: Clue,
        recipe: Recipe,
        dealing: Dealing,
        rng: random.Random,
    ) -> None:
        self.player_id = player_id
        self.p = personality
        self.rng = rng
        self.tracker = BeliefTracker(
            recipe,
            dealing,
            clue.answer,
            personality.informed_pct,
            learns_from_flow=personality.learns_from_flow,
        )
        # A fixed misjudgment for the round, so a noisy bot is consistently
        # wrong rather than jittering around the right answer.
        self._bias = rng.gauss(0, personality.fv_noise) if personality.fv_noise else 0.0
        self._last_call_ts: int | None = None
        self._last_target: str | None = None
        self._avoid_until: dict[str, int] = {}  # players found at their limit

    # -- information ---------------------------------------------------------

    def observe(self, event: Event) -> None:
        if (
            isinstance(event, OrderRejected)
            and event.reason is RejectReason.TARGET_AT_LIMIT
            and self._last_target is not None
        ):
            self._avoid_until[self._last_target] = event.ts + 20_000
        if (
            isinstance(event, Trade)
            and event.taker_id is not None
            and event.taker_id != self.player_id
        ):
            self.tracker.observe_take(event.taker_id, event.aggressor_side is Side.BUY, event.price)
        if isinstance(event, CallAnswered) and not event.automatic and event.responder_id != self.player_id:
            self.tracker.observe_answer(event.responder_id, event.bid_price, event.ask_price)

    def fair_value(self) -> tuple[float, float]:
        mean, sd = self.tracker.fair_value()
        return mean + self._bias, sd

    def next_delay(self) -> int:
        return self.rng.randint(*self.p.latency_ms)

    # -- decisions -----------------------------------------------------------

    def act(self, view: MarketView) -> list[Command]:
        fv, sd = self.fair_value()
        center = fv - self.p.inventory_skew * view.position

        if view.status is MarketStatus.PRE_OPEN:
            q = self._quote(view, center, sd)
            return [q] if q else []
        if view.status is not MarketStatus.OPEN:
            return []

        if view.my_call is not None:
            c = self._handle_call(view, center, sd)
            return [c] if c else []

        cmds: list[Command] = []
        roll = self.rng.random()
        if roll < self.p.noise_rate:
            trade = self._random_trade(view)
        elif roll < self.p.noise_rate + self.p.bluff_rate:
            trade = self._bluff(view, center)
        else:
            trade = self._take(view, center)
        if trade:
            cmds.append(trade)

        if self.p.call_rate and self.rng.random() < self.p.call_rate and self._may_call(view):
            targets = [o for o in view.others if self._avoid_until.get(o, 0) <= view.now]
            if targets:
                self._last_call_ts = view.now
                self._last_target = self.rng.choice(targets)
                cmds.append(CallPlayer(player_id=self.player_id, ts=view.now, target_id=self._last_target))

        # The view predates this action's trade, so re-quote on the next
        # action instead of quoting from a stale position.
        if not trade:
            q = self._quote(view, center, sd)
            if q:
                cmds.append(q)
        return cmds

    def _take(self, view: MarketView, center: float) -> Command | None:
        p = self.p
        mine_ask = view.my_ask[0] if view.my_ask else None
        mine_bid = view.my_bid[0] if view.my_bid else None
        if view.best_ask is not None and view.best_ask != mine_ask and center - view.best_ask >= p.take_edge:
            qty = min(p.take_size, view.best_ask_qty, view.room_to_buy, view.max_order_qty)
            if qty > 0:
                return self._ioc(view, Side.BUY, view.best_ask, qty)
        if view.best_bid is not None and view.best_bid != mine_bid and view.best_bid - center >= p.take_edge:
            qty = min(p.take_size, view.best_bid_qty, view.room_to_sell, view.max_order_qty)
            if qty > 0:
                return self._ioc(view, Side.SELL, view.best_bid, qty)
        return None

    def _random_trade(self, view: MarketView) -> Command | None:
        side = self.rng.choice((Side.BUY, Side.SELL))
        price = view.best_ask if side is Side.BUY else view.best_bid
        room = view.room_to_buy if side is Side.BUY else view.room_to_sell
        if price is None or room <= 0:
            return None
        return self._ioc(view, side, price, min(self.rng.randint(1, self.p.take_size), room))

    def _bluff(self, view: MarketView, center: float) -> Command | None:
        """Trade a little in the wrong direction to muddy what others infer."""
        if view.best_bid is None or view.best_ask is None:
            return None
        mid = (view.best_bid + view.best_ask) / 2
        if center > mid and view.room_to_sell > 0:
            return self._ioc(view, Side.SELL, view.best_bid, min(2, view.room_to_sell))
        if center < mid and view.room_to_buy > 0:
            return self._ioc(view, Side.BUY, view.best_ask, min(2, view.room_to_buy))
        return None

    def _ioc(self, view: MarketView, side: Side, price: int, qty: int) -> PlaceOrder:
        return PlaceOrder(
            player_id=self.player_id,
            ts=view.now,
            side=side,
            price=price,
            qty=qty,
            order_type=OrderType.IOC,
        )

    def _quote(self, view: MarketView, center: float, sd: float) -> SetQuote | None:
        p = self.p
        if not p.quote_size:
            return None
        half = p.base_half_width + p.k_sigma * sd
        bid = math.floor(center - half)
        ask = math.ceil(center + half)
        if ask <= bid:
            ask = bid + 1
        bid = min(max(bid, view.price_min), view.price_max - 1)
        ask = min(max(ask, bid + 1), view.price_max)

        if view.status is MarketStatus.OPEN:
            # Don't post into someone else's price (it would be rejected as crossing).
            if view.best_ask is not None and view.my_ask != (view.best_ask, view.best_ask_qty) and bid >= view.best_ask:
                bid = view.best_ask - 1
            if view.best_bid is not None and view.my_bid != (view.best_bid, view.best_bid_qty) and ask <= view.best_bid:
                ask = view.best_bid + 1
            if bid < view.price_min or ask > view.price_max or bid >= ask:
                return None

        cur_bid_qty = view.my_bid[1] if view.my_bid else 0
        cur_ask_qty = view.my_ask[1] if view.my_ask else 0
        bid_qty = max(0, min(p.quote_size, view.room_to_buy + cur_bid_qty))
        ask_qty = max(0, min(p.quote_size, view.room_to_sell + cur_ask_qty))
        want_bid = (bid, bid_qty) if bid_qty else None
        want_ask = (ask, ask_qty) if ask_qty else None
        if (want_bid, want_ask) == (view.my_bid, view.my_ask):
            return None
        return SetQuote(
            player_id=self.player_id,
            ts=view.now,
            bid_price=bid,
            bid_qty=bid_qty,
            ask_price=ask,
            ask_qty=ask_qty,
        )

    # -- calls ---------------------------------------------------------------

    def _may_call(self, view: MarketView) -> bool:
        if not view.others:
            return False
        return self._last_call_ts is None or view.now >= self._last_call_ts + view.call_cooldown_ms

    def _handle_call(self, view: MarketView, center: float, sd: float) -> Command | None:
        call = view.my_call
        assert call is not None
        if call.is_responder and call.stage is CallStage.AWAITING_ANSWER:
            # Quote a little wider to a caller who has already been taking.
            half = self.p.base_half_width + self.p.k_sigma * sd + 0.5
            width = max(1, min(view.call_max_width, round(2 * half)))
            bid = round(center - width / 2)
            bid = min(max(bid, view.price_min), view.price_max - width)
            return AnswerCall(
                player_id=self.player_id,
                ts=view.now,
                call_id=call.call_id,
                bid_price=bid,
                ask_price=bid + width,
                qty=view.call_min_qty,
            )
        if not call.is_responder and call.stage is CallStage.AWAITING_DECISION:
            assert call.bid_price is not None and call.ask_price is not None
            edge = self.p.take_edge / 2
            side = None
            if center - call.ask_price >= edge and view.room_to_buy >= call.qty:
                side = Side.BUY
            elif call.bid_price - center >= edge and view.room_to_sell >= call.qty:
                side = Side.SELL
            return DecideCall(player_id=self.player_id, ts=view.now, call_id=call.call_id, side=side)
        return None
