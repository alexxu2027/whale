"""Runs a ``RoomCore`` as an asyncio task (PRD §28.1).

Every change to a room goes through this task's inbox, so the room is only
ever touched by one coroutine at a time: no locks, no races. The task sleeps
until the next input or the next scheduled moment (round open/close, a bot
action, a call deadline), then hands the core the current time and forwards
whatever it produced to each player's connection queue.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from .room import RoomCore

log = logging.getLogger(__name__)
T = TypeVar("T")


class Clock(Protocol):
    def now(self) -> int: ...


class MonotonicClock:
    """Milliseconds since the room was created."""

    def __init__(self) -> None:
        self._start = time.monotonic()

    def now(self) -> int:
        return int((time.monotonic() - self._start) * 1000)


Outbox = asyncio.Queue[dict[str, Any] | None]  # None tells the sender to stop


class RoomActor:
    def __init__(self, core: RoomCore, clock: Clock | None = None) -> None:
        self.core = core
        self.clock = clock or MonotonicClock()
        self._inbox: asyncio.Queue[tuple[Callable[[int], Any], asyncio.Future[Any] | None]] = asyncio.Queue()
        self._conns: dict[str, Outbox] = {}
        self._task: asyncio.Task[None] | None = None
        self.idle_since: float | None = time.monotonic()

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name=f"room-{self.core.code}")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        for q in self._conns.values():
            q.put_nowait(None)

    # -- API used by connections --------------------------------------------

    async def join(self, name: str) -> tuple[str, Outbox]:
        def step(now: int) -> tuple[str, Outbox]:
            pid, _token = self.core.join(name, now)
            return pid, self._attach(pid)

        return await self._call(step)

    async def resume(self, token: str) -> tuple[str, Outbox]:
        def step(now: int) -> tuple[str, Outbox]:
            pid = self.core.resume(token, now)
            return pid, self._attach(pid)

        return await self._call(step)

    def send(self, pid: str, msg: dict[str, Any]) -> None:
        self._inbox.put_nowait((lambda now: self.core.handle(pid, msg, now), None))

    def disconnect(self, pid: str, queue: Outbox) -> None:
        def step(now: int) -> None:
            if self._conns.get(pid) is queue:  # not already replaced by a reconnect
                del self._conns[pid]
                self.core.disconnect(pid, now)

        self._inbox.put_nowait((step, None))

    # -- internals -------------------------------------------------------------

    def _attach(self, pid: str) -> Outbox:
        old = self._conns.get(pid)
        if old is not None:
            old.put_nowait(None)  # a newer connection for the same seat wins
        q: Outbox = asyncio.Queue()
        self._conns[pid] = q
        return q

    async def _call(self, fn: Callable[[int], T]) -> T:
        fut: asyncio.Future[T] = asyncio.get_running_loop().create_future()
        self._inbox.put_nowait((fn, fut))
        return await fut

    async def _run(self) -> None:
        while True:
            wake = self.core.next_wakeup()
            timeout = None if wake is None else max(0.0, (wake - self.clock.now()) / 1000)
            try:
                item = await asyncio.wait_for(self._inbox.get(), timeout)
            except TimeoutError:
                item = None
            now = self.clock.now()
            if item is not None:
                fn, fut = item
                try:
                    result = fn(now)
                except Exception as exc:  # RoomError for joins; anything else is a bug
                    if fut is not None:
                        fut.set_exception(exc)
                    else:
                        log.exception("room %s: error handling input", self.core.code)
                else:
                    if fut is not None:
                        fut.set_result(result)
            try:
                self.core.tick(now)
            except Exception:
                log.exception("room %s: error on tick", self.core.code)
            for pid, msg in self.core.drain():
                q = self._conns.get(pid)
                if q is not None:
                    q.put_nowait(msg)
            self.idle_since = None if self._conns else (self.idle_since or time.monotonic())
