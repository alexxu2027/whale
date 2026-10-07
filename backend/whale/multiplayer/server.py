"""HTTP + WebSocket server.

    uv run uvicorn whale.multiplayer.server:app --reload

- ``POST /api/rooms``: create a room, returns its code.
- ``GET /api/rooms/{code}``: whether a room exists and can be joined.
- ``WS /ws``: first message ``hello`` (name + code) or ``resume`` (code +
  token); after that, the client messages in ``protocol.py``.

If ``frontend/dist`` exists (``npm run build``), it is served at ``/``.
Rooms live in memory; rooms with nobody connected are removed after a while.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from . import protocol as p
from .actor import Clock, MonotonicClock, Outbox, RoomActor
from .room import RoomCore, RoomError, RoomPhase, RoomSettings

log = logging.getLogger(__name__)

CODE_ALPHABET = "BCDFGHJKLMNPQRSTVWXZ"  # no vowels: codes can't spell words
CODE_LENGTH = 4
IDLE_ROOM_SECONDS = 30 * 60
FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


class CreateRoom(BaseModel):
    rounds: Annotated[int, Field(ge=1, le=10)] = 3
    round_seconds: Annotated[int, Field(ge=30, le=600)] = 180


def create_app(clock_factory: Callable[[], Clock] = MonotonicClock) -> FastAPI:
    rooms: dict[str, RoomActor] = {}

    async def collect_idle_rooms() -> None:
        while True:
            await asyncio.sleep(60)
            now = time.monotonic()
            for code, actor in list(rooms.items()):
                if actor.idle_since is not None and now - actor.idle_since > IDLE_ROOM_SECONDS:
                    await actor.stop()
                    del rooms[code]

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        gc = asyncio.create_task(collect_idle_rooms())
        yield
        gc.cancel()
        for actor in rooms.values():
            await actor.stop()

    app = FastAPI(title="Whale", lifespan=lifespan)
    app.state.rooms = rooms

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {"ok": True, "rooms": len(rooms), "protocol": p.PROTOCOL_VERSION}

    @app.post("/api/rooms")
    async def create_room(body: CreateRoom | None = None) -> dict[str, str]:
        body = body or CreateRoom()
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        while code in rooms:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        actor = RoomActor(RoomCore(code, RoomSettings(rounds=body.rounds, round_seconds=body.round_seconds)),
                          clock_factory())
        actor.start()
        rooms[code] = actor
        return {"code": code}

    @app.get("/api/rooms/{code}")
    async def room_info(code: str) -> dict[str, object]:
        actor = rooms.get(code.upper())
        if actor is None:
            raise HTTPException(404, "No room with that code.")
        core = actor.core
        return {"code": core.code, "joinable": core.phase is RoomPhase.LOBBY, "players": len(core.seats)}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            hello = p.parse_connect(await websocket.receive_json())
        except (ValidationError, ValueError):
            await websocket.send_json({"type": "error", "message": "Expected hello or resume.", "fatal": True})
            await websocket.close()
            return
        actor = rooms.get(hello.code.upper())
        if actor is None:
            await websocket.send_json({"type": "error", "message": "No room with that code.", "fatal": True})
            await websocket.close()
            return
        try:
            if isinstance(hello, p.Hello):
                pid, outbox = await actor.join(hello.name)
            else:
                pid, outbox = await actor.resume(hello.token)
        except RoomError as exc:
            await websocket.send_json({"type": "error", "message": str(exc), "fatal": True})
            await websocket.close()
            return

        sender = asyncio.create_task(_pump(websocket, outbox))
        try:
            while True:
                data = await websocket.receive_json()
                if isinstance(data, dict):
                    actor.send(pid, data)
        except (WebSocketDisconnect, ValueError):
            pass
        finally:
            sender.cancel()
            actor.disconnect(pid, outbox)

    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


async def _pump(websocket: WebSocket, outbox: Outbox) -> None:
    with contextlib.suppress(Exception):
        while (msg := await outbox.get()) is not None:
            await websocket.send_json(msg)
        await websocket.close()


app = create_app()
