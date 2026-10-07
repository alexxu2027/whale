"""End-to-end tests over real WebSockets through the FastAPI app."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from whale.multiplayer.server import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def read_until(ws: Any, msg_type: str, limit: int = 200) -> dict[str, Any]:
    for _ in range(limit):
        msg = ws.receive_json()
        if msg["type"] == msg_type:
            return msg
    raise AssertionError(f"no {msg_type} message")


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json()["ok"] is True


def test_create_and_look_up_room(client: TestClient) -> None:
    code = client.post("/api/rooms", json={"rounds": 2, "round_seconds": 60}).json()["code"]
    assert len(code) == 4
    info = client.get(f"/api/rooms/{code.lower()}").json()
    assert info == {"code": code, "joinable": True, "players": 0}
    assert client.get("/api/rooms/ZZZZ").status_code == 404


def test_two_players_join_start_and_trade(client: TestClient) -> None:
    code = client.post("/api/rooms", json={}).json()["code"]
    with client.websocket_connect("/ws") as host, client.websocket_connect("/ws") as guest:
        host.send_json({"type": "hello", "name": "Alex", "code": code})
        welcome = read_until(host, "welcome")
        guest.send_json({"type": "hello", "name": "Sam", "code": code})
        read_until(guest, "welcome")

        host.send_json({"type": "start", "fill_bots": True})
        start = read_until(host, "round_start")
        assert start["clue"]["precise"] and start["objective"]["title"]
        room = read_until(guest, "room")
        while room["phase"] != "playing":
            room = read_until(guest, "room")
        assert [p["name"] for p in room["players"]][:2] == ["Alex", "Sam"]
        assert sum(p["is_bot"] for p in room["players"]) == 2

        host.send_json({"type": "quote", "bid": 90, "bid_qty": 3, "ask": 110, "ask_qty": 3})
        you = read_until(host, "you")
        while you["quote"]["bid"] != 90:
            you = read_until(host, "you")
        assert you["quote"] == {"bid": 90, "bid_qty": 3, "ask": 110, "ask_qty": 3}
        assert welcome["player_id"] == "p1"


def test_bad_first_message_and_unknown_room(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "quote"})
        assert ws.receive_json()["fatal"] is True
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "name": "Alex", "code": "QQQQ"})
        assert ws.receive_json()["message"] == "No room with that code."


def test_reconnect_with_token(client: TestClient) -> None:
    code = client.post("/api/rooms", json={}).json()["code"]
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "name": "Alex", "code": code})
        welcome = read_until(ws, "welcome")
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "resume", "code": code, "token": welcome["token"]})
        again = read_until(ws, "welcome")
        assert again["player_id"] == welcome["player_id"]
