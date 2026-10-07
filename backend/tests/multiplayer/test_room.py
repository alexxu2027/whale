"""Tests for the room core: lobby, match flow, reconnects, visibility (PRD §29, §31)."""

from __future__ import annotations

import itertools
import json
import random
from typing import Any

import pytest

from whale.multiplayer.room import RoomCore, RoomError, RoomPhase, RoomSettings

FAST = RoomSettings(rounds=2, round_seconds=60, opening_seconds=5, reveal_seconds=10)


def seeds():
    counter = itertools.count(100)
    return lambda: next(counter)


def new_room(settings: RoomSettings = FAST) -> RoomCore:
    return RoomCore("TEST", settings, seed_fn=seeds())


def inbox(room: RoomCore) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for pid, msg in room.drain():
        out.setdefault(pid, []).append(msg)
    return out


def of_type(msgs: list[dict[str, Any]], t: str) -> list[dict[str, Any]]:
    return [m for m in msgs if m["type"] == t]


def started_room(humans: int = 2, bots: int = 2) -> tuple[RoomCore, list[str]]:
    room = new_room()
    pids = [room.join(f"Human{i}", now=i)[0] for i in range(humans)]
    for _ in range(bots):
        room.handle(pids[0], {"type": "add_bot"}, now=10)
    room.handle(pids[0], {"type": "start"}, now=20)
    return room, pids


# -- lobby -------------------------------------------------------------------------


def test_join_sends_welcome_and_room() -> None:
    room = new_room()
    pid, token = room.join("Alex", now=0)
    msgs = inbox(room)[pid]
    welcome = msgs[0]
    assert welcome == {"type": "welcome", "player_id": pid, "token": token, "code": "TEST", "protocol": 1}
    assert of_type(msgs, "room")[-1]["host_id"] == pid


def test_only_host_controls_the_lobby() -> None:
    room = new_room()
    host, _ = room.join("Alex", 0)
    guest, _ = room.join("Sam", 1)
    inbox(room)
    room.handle(guest, {"type": "start"}, 2)
    assert of_type(inbox(room)[guest], "error")[0]["message"] == "Only the host can do that."
    room.handle(host, {"type": "add_bot", "personality": "Shark"}, 3)
    players = of_type(inbox(room)[guest], "room")[-1]["players"]
    assert [p["personality"] for p in players] == [None, None, "Shark"]


def test_start_needs_two_players_unless_filling_with_bots() -> None:
    room = new_room()
    host, _ = room.join("Solo", 0)
    room.handle(host, {"type": "start"}, 1)
    assert "at least 2" in of_type(inbox(room)[host], "error")[0]["message"]
    room.handle(host, {"type": "start", "fill_bots": True}, 2)
    assert room.phase is RoomPhase.PLAYING
    assert len(room.seats) == 4


def test_cannot_join_after_start() -> None:
    room, _ = started_room()
    with pytest.raises(RoomError):
        room.join("Late", 100)


def test_events_keep_their_type_and_trade_kind() -> None:
    from whale.engine import Side, Trade, TradeKind
    from whale.multiplayer.protocol import event_to_wire

    t = Trade(seq=1, ts=2, trade_id=3, kind=TradeKind.CALL, price=100, qty=5, buyer_id="a", seller_id="b",
              maker_id="b", taker_id="a", aggressor_side=Side.BUY, call_id=7)
    wire = event_to_wire(t)
    assert wire["type"] == "trade" and wire["kind"] == "call" and wire["call_id"] == 7


def test_bad_messages_become_errors() -> None:
    room, pids = started_room()
    inbox(room)
    room.handle(pids[0], {"type": "order", "side": "sideways", "price": 100, "qty": 1}, 30)
    room.handle(pids[0], {"type": "nonsense"}, 31)
    errors = of_type(inbox(room)[pids[0]], "error")
    assert len(errors) == 2


# -- a full match ------------------------------------------------------------------


def test_round_start_is_private_and_complete() -> None:
    room, pids = started_room()
    msgs = inbox(room)
    starts = {pid: of_type(msgs[pid], "round_start")[0] for pid in pids}
    a, b = starts[pids[0]], starts[pids[1]]
    assert a["clue"] != b["clue"] and a["objective"] != b["objective"]
    assert a["closes_at"] - a["opens_at"] == 60_000
    assert a["recipe"]["min"] == 80 and a["recipe"]["max"] == 120
    assert of_type(msgs[pids[0]], "market") and of_type(msgs[pids[0]], "you")


def test_opening_quotes_are_sealed_until_the_open() -> None:
    room, pids = started_room()
    inbox(room)
    room.handle(pids[0], {"type": "quote", "bid": 97, "bid_qty": 5, "ask": 103, "ask_qty": 5}, 1_000)
    room.tick(4_000)  # bots post opening quotes too
    market = of_type(inbox(room)[pids[1]], "market")[-1]
    assert market["status"] == "pre_open" and market["bids"] == [] and market["asks"] == []
    room.tick(20 + 5_000 + 1)  # the market opens
    market = of_type(inbox(room)[pids[1]], "market")[-1]
    assert market["status"] == "open"


def test_trading_updates_market_and_private_state() -> None:
    room, pids = started_room()
    room.tick(20 + 5_000 + 1)  # past the opening phase
    inbox(room)
    room.handle(pids[0], {"type": "quote", "bid": 90, "bid_qty": 5, "ask": 110, "ask_qty": 5}, 6_000)
    msgs = inbox(room)
    you = of_type(msgs[pids[0]], "you")[-1]
    assert you["quote"] == {"bid": 90, "bid_qty": 5, "ask": 110, "ask_qty": 5}
    # The other human sees the book, but not whose quote it is.
    market = of_type(msgs[pids[1]], "market")[-1]
    from whale.engine import Side

    book = room._rs.round.exchange.book
    assert [list(x) for x in market["bids"]] == [list(x) for x in book.depth(Side.BUY, 10)]
    assert [list(x) for x in market["asks"]] == [list(x) for x in book.depth(Side.SELL, 10)]
    assert any(qty >= 5 for price, qty in book.depth(Side.BUY) if price == 90)
    assert not any(m["type"] == "event" and m["event"]["type"] == "order_accepted" for m in msgs[pids[1]])


def play_match(room: RoomCore, pids: list[str], rng: random.Random) -> dict[str, list[dict[str, Any]]]:
    """Random human play until the match is over; returns every message sent."""
    sent: dict[str, list[dict[str, Any]]] = {pid: [] for pid in pids}
    now = 30
    while room.phase is not RoomPhase.FINISHED:
        now += rng.randint(50, 1_500)
        pid = rng.choice(pids)
        roll = rng.random()
        if room.phase is RoomPhase.PLAYING:
            if roll < 0.4:
                bid = rng.randint(95, 104)
                room.handle(pid, {"type": "quote", "bid": bid, "bid_qty": 5, "ask": bid + rng.randint(1, 4), "ask_qty": 5}, now)
            elif roll < 0.7:
                room.handle(pid, {"type": "order", "side": rng.choice(["buy", "sell"]), "price": rng.randint(95, 105), "qty": rng.randint(1, 6)}, now)
            elif roll < 0.8:
                others = [x for x in room.seats if x != pid]
                room.handle(pid, {"type": "call", "target": rng.choice(others)}, now)
            else:
                room.tick(now)
        else:
            room.tick(now)
        for p, m in room.drain():
            sent[p].append(m)
    return sent


def test_full_match_reaches_the_end_with_scores() -> None:
    room, pids = started_room()
    inbox(room)
    sent = play_match(room, pids, random.Random(1))
    reveals = of_type(sent[pids[0]], "reveal")
    assert [r["round_number"] for r in reveals] == [1, 2]
    final = reveals[-1]
    assert final["last_round"]
    for player in final["players"]:
        b = player["breakdown"]
        assert b["spread"] + b["adverse_selection"] + b["directional"] + b["fees"] == pytest.approx(player["pnl"])
        assert player["score"] == pytest.approx(player["pnl"] + player["bonus"])
    totals = {p["id"]: 0.0 for p in final["players"]}
    for r in reveals:
        for p in r["players"]:
            totals[p["id"]] += p["score"]
    assert final["match_scores"] == pytest.approx(totals)
    assert room.phase is RoomPhase.FINISHED


def test_rematch_starts_over() -> None:
    room, pids = started_room()
    play_match(room, pids, random.Random(2))
    room.handle(pids[0], {"type": "rematch"}, 10**7)
    assert room.phase is RoomPhase.PLAYING and room.round_number == 1
    assert all(v == 0 for v in room.scores.values())


def test_host_can_skip_the_reveal() -> None:
    room, pids = started_room()
    room.tick(20 + 65_001)  # past the first round's close
    assert room.phase is RoomPhase.REVEAL
    room.handle(pids[0], {"type": "next_round"}, 20 + 65_002)
    assert room.phase is RoomPhase.PLAYING and room.round_number == 2


# -- reconnects --------------------------------------------------------------------


def test_resume_restores_full_state() -> None:
    room = new_room()
    host, token = room.join("Alex", 0)
    room.handle(host, {"type": "start", "fill_bots": True}, 1)
    room.handle(host, {"type": "quote", "bid": 97, "bid_qty": 5, "ask": 103, "ask_qty": 5}, 1_000)
    room.disconnect(host, 2_000)
    room.tick(8_000)
    assert host not in inbox(room)  # nothing sent while away
    assert room.resume(token, 9_000) == host
    msgs = inbox(room)[host]
    types = [m["type"] for m in msgs]
    assert types[:3] == ["welcome", "room", "round_start"]
    assert "market" in types and "you" in types
    with pytest.raises(RoomError):
        room.resume("not-a-real-token", 9_001)


# -- visibility (PRD §31) ----------------------------------------------------------


FORBIDDEN_KEYS = {"final_value", "state", "seed", "factors"}


def keys(obj: Any) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | set().union(*(keys(v) for v in obj.values()))
    if isinstance(obj, list):
        return set().union(*(keys(v) for v in obj)) if obj else set()
    return set()


@pytest.mark.parametrize("seed", range(4))
def test_nothing_hidden_leaks_before_the_reveal(seed: int) -> None:
    """Fuzz: random play; every message a human receives before each round's
    reveal must not contain the hidden value or state, or any other
    player's clue or objective."""
    room, pids = started_room(humans=3, bots=1)
    first = inbox(room)
    rng = random.Random(seed)
    sent = play_match(room, pids, rng)
    for pid in pids:
        stream = first.get(pid, []) + sent[pid]
        # Split into rounds, each ending with its reveal.
        rounds: list[list[dict[str, Any]]] = [[]]
        for msg in stream:
            rounds[-1].append(msg)
            if msg["type"] == "reveal":
                rounds.append([])
        for chunk in rounds:
            reveal = next((m for m in chunk if m["type"] == "reveal"), None)
            if reveal is None:
                continue
            others = {
                text
                for player in reveal["players"]
                if player["id"] != pid
                for text in (player["clue"]["precise"], player["objective"]["description"])
            }
            mine = next(pl for pl in reveal["players"] if pl["id"] == pid)
            others -= {mine["clue"]["precise"], mine["objective"]["description"]}
            before = [m for m in chunk if m["type"] != "reveal"]
            blob = json.dumps(before)
            for text in others:
                assert text not in blob, f"{pid} saw another player's secret: {text}"
            for m in before:
                assert not (keys(m) & FORBIDDEN_KEYS), (pid, m["type"], keys(m) & FORBIDDEN_KEYS)
