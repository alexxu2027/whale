"""One room: lobby, a multi-round match, bots, and what each player is sent.

``RoomCore`` is synchronous and takes the current time as an argument, so it
is fully deterministic and testable; ``actor.py`` drives it from an asyncio
task with the real clock. All of a room's state changes happen through this
class, one call at a time.

Visibility (PRD §31): every message is built here, per recipient. Engine
events pass through ``is_visible``; the hidden value, the hidden state, and
other players' clues and objectives only appear in the reveal, after the
round has settled.
"""

from __future__ import annotations

import random
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import ValidationError

from whale.bots.bot import Bot
from whale.bots.personalities import ALL as PERSONALITIES
from whale.bots.personalities import Personality
from whale.bots.runner import BotRunner
from whale.engine import (
    CENTS_PER_POINT,
    CancelAll as EngineCancelAll,
    CancelOrder,
    CallPlayer,
    Command,
    DecideCall as EngineDecideCall,
    AnswerCall as EngineAnswerCall,
    MarketConfig,
    MarketStatus,
    OrderType,
    PlaceOrder,
    SetQuote,
    Side,
)
from whale.game.items import Item, pick_item
from whale.game.recipes import FOUR_CARDS, Recipe
from whale.game.round import Round, RoundConfig, RoundResult
from whale.game.setup import new_seed
from whale.runtime.visibility import is_visible

from . import protocol as p

BOT_NAMES = ("Gilda", "Barnaby", "Mirelle", "Otto", "Fennick", "Sable", "Quill", "Hester")
# Seat-filling order for bots. A table of only well-informed bots barely
# trades (~4 trades a round in simulation: their regret-free quotes leave
# nobody an edge), so the Noise Trader comes early; it supplies the
# uninformed flow that makes market making worthwhile (~33 trades a round),
# and the Shark supplies the informed flow that makes it risky.
DEFAULT_BOTS = ("Market Maker", "Noise Trader", "Shark", "Whale", "Conservative", "Bluffer", "Market Maker")
TABLE_SIZE_WITH_FILL = 4

Outgoing = tuple[str, dict[str, Any]]  # (player_id, message)


class RoomError(Exception):
    """A request the room refuses; the message is shown to the player."""


class RoomPhase(StrEnum):
    LOBBY = "lobby"
    PLAYING = "playing"
    REVEAL = "reveal"  # between rounds
    FINISHED = "finished"  # match over


@dataclass(frozen=True, slots=True)
class RoomSettings:
    rounds: int = 3
    round_seconds: int = 180
    opening_seconds: int = 10
    reveal_seconds: int = 25
    max_players: int = 8


@dataclass(slots=True)
class Seat:
    id: str
    name: str
    personality: Personality | None = None  # None for humans
    token: str | None = None
    connected: bool = False

    @property
    def is_bot(self) -> bool:
        return self.personality is not None


@dataclass(slots=True)
class _RoundState:
    round: Round
    item: Item
    runner: BotRunner
    cursors: dict[str, int] = field(default_factory=dict)  # per human: index into round.log
    flushed_log_len: int = 0


class RoomCore:
    def __init__(
        self,
        code: str,
        settings: RoomSettings | None = None,
        *,
        recipe: Recipe = FOUR_CARDS,
        seed_fn: Callable[[], int] = new_seed,
    ) -> None:
        self.code = code
        self.settings = settings or RoomSettings()
        self.recipe = recipe
        self._seed_fn = seed_fn
        self.phase = RoomPhase.LOBBY
        self.seats: dict[str, Seat] = {}
        self.host_id: str | None = None
        self.round_number = 0
        self.scores: dict[str, int] = {}  # cents, across the match
        self.reveals: list[dict[str, Any]] = []
        self.reveal_until: int | None = None
        self._rs: _RoundState | None = None
        self._out: list[Outgoing] = []
        self._now = 0
        self._next_human = 1
        self._next_bot = 1

    # -- connections -------------------------------------------------------

    def join(self, name: str, now: int) -> tuple[str, str]:
        """A new human takes a seat. Returns (player_id, resume token)."""
        self._advance(now)
        if self.phase is not RoomPhase.LOBBY:
            raise RoomError("This game has already started.")
        if len(self.seats) >= self.settings.max_players:
            raise RoomError("This room is full.")
        pid = f"p{self._next_human}"
        self._next_human += 1
        seat = Seat(pid, name.strip() or "Player", token=secrets.token_urlsafe(18), connected=True)
        self.seats[pid] = seat
        if self.host_id is None:
            self.host_id = pid
        self._send_full_state(pid)
        self._broadcast_room()
        return pid, seat.token  # type: ignore[return-value]

    def resume(self, token: str, now: int) -> str:
        self._advance(now)
        seat = next((s for s in self.seats.values() if s.token == token), None)
        if seat is None:
            raise RoomError("That session has expired. Join again with the room code.")
        seat.connected = True
        self._send_full_state(seat.id)
        self._broadcast_room()
        return seat.id

    def disconnect(self, pid: str, now: int) -> None:
        self._advance(now)
        seat = self.seats.get(pid)
        if seat is None:
            return
        seat.connected = False
        if self.phase is RoomPhase.LOBBY and pid == self.host_id:
            self.host_id = next((s.id for s in self.seats.values() if not s.is_bot and s.connected), self.host_id)
        self._broadcast_room()

    def has_connected_humans(self) -> bool:
        return any(s.connected for s in self.seats.values() if not s.is_bot)

    # -- input ---------------------------------------------------------------

    def handle(self, pid: str, raw: dict[str, Any], now: int) -> None:
        """Apply one client message. Problems become an ``error`` message to
        that player; the room never raises on bad client input."""
        self._advance(now)
        try:
            msg = p.parse_client(raw)
        except ValidationError as exc:
            self._send(pid, {"type": "error", "message": f"Bad message: {exc.errors()[0]['msg']}"})
            return
        try:
            self._dispatch(pid, msg, now)
        except RoomError as exc:
            self._send(pid, {"type": "error", "message": str(exc)})
        self._flush_round()

    def tick(self, now: int) -> None:
        self._advance(now)
        self._flush_round()

    def next_wakeup(self) -> int | None:
        """The next time something is scheduled to happen without input."""
        times: list[int] = []
        if self.phase is RoomPhase.REVEAL and self.reveal_until is not None:
            times.append(self.reveal_until)
        rs = self._rs
        if self.phase is RoomPhase.PLAYING and rs is not None:
            rnd = rs.round
            if rnd.exchange.status is MarketStatus.PRE_OPEN:
                times.append(rnd.open_at)
            times.append(rnd.close_at)
            bot_time = rs.runner.next_time()
            if bot_time is not None:
                times.append(bot_time)
            times += [c.deadline for c in rnd.exchange.calls.values()]
        return min(times) if times else None

    def drain(self) -> list[Outgoing]:
        """Messages for connected humans, in order."""
        out = [(pid, m) for pid, m in self._out if (s := self.seats.get(pid)) is not None and s.connected]
        self._out = []
        return out

    # -- dispatch --------------------------------------------------------------

    def _dispatch(self, pid: str, msg: Any, now: int) -> None:
        match msg:
            case p.AddBot() | p.RemovePlayer() | p.UpdateSettings() | p.Start():
                self._require_host(pid, RoomPhase.LOBBY)
                self._lobby_action(msg, now)
            case p.NextRound():
                self._require_host(pid, RoomPhase.REVEAL)
                self._next_round(now)
            case p.Rematch():
                self._require_host(pid, RoomPhase.FINISHED)
                self.scores = {sid: 0 for sid in self.seats}
                self.reveals = []
                self.round_number = 0
                self._start_round(now)
            case _:
                self._trade(pid, msg, now)

    def _lobby_action(self, msg: Any, now: int) -> None:
        match msg:
            case p.AddBot():
                self._add_bot(msg.personality)
            case p.RemovePlayer():
                seat = self.seats.get(msg.player_id)
                if seat is None or not seat.is_bot:
                    raise RoomError("Only bots can be removed.")
                del self.seats[msg.player_id]
            case p.UpdateSettings():
                self.settings = RoomSettings(
                    rounds=msg.rounds,
                    round_seconds=msg.round_seconds,
                    opening_seconds=self.settings.opening_seconds,
                    reveal_seconds=self.settings.reveal_seconds,
                    max_players=self.settings.max_players,
                )
            case p.Start():
                if msg.fill_bots:
                    while len(self.seats) < TABLE_SIZE_WITH_FILL:
                        self._add_bot(None)
                if len(self.seats) < 2:
                    raise RoomError("You need at least 2 players. Add a bot!")
                self.scores = {sid: 0 for sid in self.seats}
                self._start_round(now)
                return
        self._broadcast_room()

    def _add_bot(self, personality: str | None) -> None:
        if len(self.seats) >= self.settings.max_players:
            raise RoomError("This room is full.")
        by_name = {x.name: x for x in PERSONALITIES}
        n_bots = sum(1 for s in self.seats.values() if s.is_bot)
        name = personality or DEFAULT_BOTS[n_bots % len(DEFAULT_BOTS)]
        if name not in by_name:
            raise RoomError(f"Unknown bot type: {name}")
        pid = f"b{self._next_bot}"
        self._next_bot += 1
        used = {s.name for s in self.seats.values()}
        bot_name = next((b for b in BOT_NAMES if b not in used), f"Bot {pid}")
        self.seats[pid] = Seat(pid, bot_name, personality=by_name[name])

    def _trade(self, pid: str, msg: Any, now: int) -> None:
        if self.phase is not RoomPhase.PLAYING or self._rs is None:
            raise RoomError("The round isn't running.")
        cmd: Command
        match msg:
            case p.Quote():
                cmd = SetQuote(player_id=pid, ts=now, bid_price=msg.bid, bid_qty=msg.bid_qty,
                               ask_price=msg.ask, ask_qty=msg.ask_qty)
            case p.Order():
                kind = OrderType.IOC if msg.kind == "ioc" else OrderType.LIMIT
                cmd = PlaceOrder(player_id=pid, ts=now, side=msg.side, price=msg.price, qty=msg.qty, order_type=kind)
            case p.Cancel():
                cmd = CancelOrder(player_id=pid, ts=now, order_id=msg.order_id)
            case p.CancelAll():
                cmd = EngineCancelAll(player_id=pid, ts=now)
            case p.Call():
                cmd = CallPlayer(player_id=pid, ts=now, target_id=msg.target)
            case p.AnswerCall():
                cmd = EngineAnswerCall(player_id=pid, ts=now, call_id=msg.call_id, bid_price=msg.bid,
                                       ask_price=msg.ask, qty=msg.qty)
            case p.DecideCall():
                cmd = EngineDecideCall(player_id=pid, ts=now, call_id=msg.call_id, side=msg.side)
            case _:
                raise RoomError("Unsupported message.")
        self._rs.round.submit(cmd)
        self._after_round_progress(now)

    def _require_host(self, pid: str, phase: RoomPhase) -> None:
        if pid != self.host_id:
            raise RoomError("Only the host can do that.")
        if self.phase is not phase:
            raise RoomError("You can't do that right now.")

    # -- match flow --------------------------------------------------------------

    def _advance(self, now: int) -> None:
        now = max(now, self._now)
        self._now = now
        if self.phase is RoomPhase.PLAYING and self._rs is not None:
            self._rs.runner.run_until(now)
            self._rs.round.advance(now)
            self._after_round_progress(now)
        if self.phase is RoomPhase.REVEAL and self.reveal_until is not None and now >= self.reveal_until:
            self._next_round(now)

    def _after_round_progress(self, now: int) -> None:
        rs = self._rs
        if rs is None or rs.round.result is None or self.phase is not RoomPhase.PLAYING:
            return
        self._flush_round()
        result = rs.round.result
        for pr in result.players:
            self.scores[pr.player_id] = self.scores.get(pr.player_id, 0) + pr.score_cents
        reveal = self._reveal_message(rs, result)
        self.reveals.append(reveal)
        last = self.round_number >= self.settings.rounds
        self.phase = RoomPhase.FINISHED if last else RoomPhase.REVEAL
        self.reveal_until = None if last else now + self.settings.reveal_seconds * 1000
        for pid in self._humans():
            self._send(pid, reveal)
        self._broadcast_room()

    def _next_round(self, now: int) -> None:
        if self.round_number >= self.settings.rounds:
            self.phase = RoomPhase.FINISHED
            self._broadcast_room()
            return
        self._start_round(now)

    def _start_round(self, now: int) -> None:
        self.round_number += 1
        seed = self._seed_fn()
        players = list(self.seats)
        config = RoundConfig(
            opening_ms=self.settings.opening_seconds * 1000,
            trading_ms=self.settings.round_seconds * 1000,
            market=MarketConfig(),
        )
        rnd = Round(self.recipe, players, config, seed=seed, start_ts=now)
        rng = random.Random(seed ^ 0xB075)
        bots = {
            pid: Bot(pid, s.personality, rnd.setup.clues[pid], self.recipe, config.dealing, random.Random(rng.getrandbits(64)))
            for pid, s in self.seats.items()
            if s.personality is not None
        }
        self._rs = _RoundState(
            round=rnd,
            item=pick_item(rng),
            runner=BotRunner(rnd, bots, rng, start=now),
            cursors={pid: 0 for pid in self._humans()},
        )
        self.phase = RoomPhase.PLAYING
        self.reveal_until = None
        self._broadcast_room()
        for pid in self._humans():
            self._send(pid, self._round_start_message(pid))
        self._flush_round(force=True)

    # -- output ------------------------------------------------------------------

    def _humans(self) -> list[str]:
        return [pid for pid, s in self.seats.items() if not s.is_bot]

    def _send(self, pid: str, msg: dict[str, Any]) -> None:
        self._out.append((pid, msg))

    def _broadcast_room(self) -> None:
        msg = self._room_message()
        for pid in self._humans():
            self._send(pid, msg)

    def _flush_round(self, force: bool = False) -> None:
        """Send each human the events they may see, then fresh market and
        private snapshots if anything happened."""
        rs = self._rs
        if rs is None:
            return
        log = rs.round.log
        if not force and len(log) == rs.flushed_log_len:
            return
        market = self._market_message(rs)
        for pid in self._humans():
            start = rs.cursors.get(pid, 0)
            for e in log[start:]:
                if is_visible(e, pid):
                    self._send(pid, {"type": "event", "event": p.event_to_wire(e)})
            rs.cursors[pid] = len(log)
            self._send(pid, market)
            self._send(pid, self._you_message(rs, pid))
        rs.flushed_log_len = len(log)

    def _send_full_state(self, pid: str) -> None:
        seat = self.seats[pid]
        self._send(pid, {"type": "welcome", "player_id": pid, "token": seat.token, "code": self.code,
                         "protocol": p.PROTOCOL_VERSION})
        self._send(pid, self._room_message())
        rs = self._rs
        if rs is not None and pid in rs.round.setup.clues:
            self._send(pid, self._round_start_message(pid))
            recent = [e for e in rs.round.log if is_visible(e, pid)][-60:]
            for e in recent:
                self._send(pid, {"type": "event", "event": p.event_to_wire(e)})
            rs.cursors[pid] = len(rs.round.log)
            self._send(pid, self._market_message(rs))
            self._send(pid, self._you_message(rs, pid))
        if self.phase in (RoomPhase.REVEAL, RoomPhase.FINISHED) and self.reveals:
            self._send(pid, self.reveals[-1])

    def _room_message(self) -> dict[str, Any]:
        return {
            "type": "room",
            "code": self.code,
            "phase": self.phase,
            "host_id": self.host_id,
            "round_number": self.round_number,
            "settings": {"rounds": self.settings.rounds, "round_seconds": self.settings.round_seconds},
            "players": [
                {
                    "id": s.id,
                    "name": s.name,
                    "is_bot": s.is_bot,
                    "personality": s.personality.name if s.personality else None,
                    "connected": s.connected or s.is_bot,
                }
                for s in self.seats.values()
            ],
            "scores": {pid: c / CENTS_PER_POINT for pid, c in self.scores.items()},
            "reveal_until": self.reveal_until,
            "server_now": self._now,
            "bot_types": [x.name for x in PERSONALITIES],
        }

    def _round_start_message(self, pid: str) -> dict[str, Any]:
        rs = self._rs
        assert rs is not None
        rnd = rs.round
        cfg = rnd.exchange.config
        clue = rnd.setup.clues[pid]
        objective = rnd.objectives[pid]
        return {
            "type": "round_start",
            "round_number": self.round_number,
            "rounds": self.settings.rounds,
            "item": {"name": rs.item.name, "unit": rs.item.unit, "description": rs.item.description},
            "recipe": {
                "title": self.recipe.title,
                "description": self.recipe.describe(),
                "factor_names": [c.name for c in self.recipe.components],
                "min": self.recipe.min_value,
                "max": self.recipe.max_value,
                "average": cfg.reference,
            },
            "clue": {"flavor": clue.flavor, "precise": clue.precise},
            "objective": {"id": objective.id, "title": objective.title, "description": objective.description,
                          "bonus": objective.bonus},
            "opens_at": rnd.open_at,
            "closes_at": rnd.close_at,
            "server_now": self._now,
            "rules": {
                "position_limit": cfg.position_limit,
                "max_order_qty": cfg.max_order_qty,
                "call_max_width": cfg.call_max_width,
                "call_min_qty": cfg.call_min_qty,
                "call_answer_ms": cfg.call_answer_ms,
                "call_decide_ms": cfg.call_decide_ms,
                "call_cooldown_ms": cfg.call_cooldown_ms,
                "maker_rebate": cfg.maker_rebate_cents / CENTS_PER_POINT,
                "taker_fee": cfg.taker_fee_cents / CENTS_PER_POINT,
            },
        }

    def _market_message(self, rs: _RoundState) -> dict[str, Any]:
        ex = rs.round.exchange
        # Opening markets are sealed until the open (PRD §6, phase 3).
        sealed = ex.status is MarketStatus.PRE_OPEN
        return {
            "type": "market",
            "seq": rs.round.log[-1].seq if rs.round.log else 0,
            "server_now": self._now,
            "status": ex.status,
            "bids": [] if sealed else ex.book.depth(Side.BUY, 10),
            "asks": [] if sealed else ex.book.depth(Side.SELL, 10),
            "mid": float(ex.config.reference) if sealed else rs.round.mid(),
        }

    def _you_message(self, rs: _RoundState, pid: str) -> dict[str, Any]:
        ex = rs.round.exchange
        cfg = ex.config
        acct = ex.accounts[pid]
        bid_id, ask_id = ex.quotes.get(pid, (None, None))
        bid = ex.book.get(bid_id) if bid_id is not None else None
        ask = ex.book.get(ask_id) if ask_id is not None else None
        call = next((c for c in ex.calls.values() if pid in (c.caller_id, c.responder_id)), None)
        mid = rs.round.mid()
        return {
            "type": "you",
            "position": acct.position,
            "cash": acct.cash_cents / CENTS_PER_POINT,
            "pnl_at_mid": (acct.cash_cents + acct.position * mid * CENTS_PER_POINT) / CENTS_PER_POINT,
            "room_to_buy": cfg.position_limit - acct.worst_case_long(),
            "room_to_sell": cfg.position_limit + acct.worst_case_short(),
            "quote": {
                "bid": bid.price if bid else None,
                "bid_qty": bid.qty if bid else 0,
                "ask": ask.price if ask else None,
                "ask_qty": ask.qty if ask else 0,
            },
            "orders": [
                {"id": o.order_id, "side": o.side, "price": o.price, "qty": o.qty}
                for o in sorted(ex.book.orders(), key=lambda o: o.order_id)
                if o.player_id == pid and not o.is_quote
            ],
            "call": None
            if call is None
            else {
                "call_id": call.call_id,
                "role": "responder" if call.responder_id == pid else "caller",
                "counterparty": call.caller_id if call.responder_id == pid else call.responder_id,
                "stage": call.stage.value,
                "bid": call.bid_price,
                "ask": call.ask_price,
                "qty": call.qty,
                "deadline": call.deadline,
            },
            "server_now": self._now,
        }

    def _reveal_message(self, rs: _RoundState, result: RoundResult) -> dict[str, Any]:
        names = {pid: s.name for pid, s in self.seats.items()}
        return {
            "type": "reveal",
            "round_number": self.round_number,
            "rounds": self.settings.rounds,
            "item": {"name": rs.item.name, "unit": rs.item.unit},
            "final_value": result.final_value,
            "factors": [
                {"name": c.name, "value": v} for c, v in zip(self.recipe.components, result.state, strict=True)
            ],
            "players": [
                {
                    "id": pr.player_id,
                    "name": names.get(pr.player_id, pr.player_id),
                    "rank": pr.rank,
                    "position": pr.position,
                    "pnl": pr.pnl_cents / CENTS_PER_POINT,
                    "bonus": pr.bonus_cents / CENTS_PER_POINT,
                    "score": pr.score_cents / CENTS_PER_POINT,
                    "clue": {"flavor": pr.clue.flavor, "precise": pr.clue.precise},
                    "objective": {"title": pr.objective.title, "description": pr.objective.description,
                                  "bonus": pr.objective.bonus, "met": pr.objective_met},
                    "breakdown": {
                        "spread": pr.attribution.spread_cents / CENTS_PER_POINT,
                        "adverse_selection": pr.attribution.adverse_selection_cents / CENTS_PER_POINT,
                        "directional": pr.attribution.directional_cents / CENTS_PER_POINT,
                        "fees": pr.attribution.fees_cents / CENTS_PER_POINT,
                        "lost_to": {
                            names.get(cp, cp): v / CENTS_PER_POINT
                            for cp, v in sorted(pr.attribution.adverse_by_counterparty.items(), key=lambda kv: kv[1])
                            if v < 0
                        },
                    },
                }
                for pr in result.players
            ],
            "match_scores": {pid: c / CENTS_PER_POINT for pid, c in self.scores.items()},
            "last_round": self.round_number >= self.settings.rounds,
        }
