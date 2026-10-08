"""Runs bots against a round on a schedule (shared by the simulator and live rooms).

Each bot repeatedly:

1. **decides** at time t: it receives every event it may see
   (``is_visible``) since its last decision, plus a public view of the
   market as of t, and returns commands;
2. those commands **arrive** at the exchange at t + think time, stamped
   with the arrival time (like ABIDES's computation delay), so a bot never
   reacts to anything faster than its think time;
3. it decides again a little after its commands have arrived.

The simulator calls ``run_until`` with the end of the round; a live room
calls it with the wall clock, interleaved with human commands.
"""

from __future__ import annotations

import heapq
import itertools
import random
from collections.abc import Callable, Mapping
from dataclasses import replace

from whale.engine import Command
from whale.game.round import Round
from whale.game.runners import RunnerSlip
from whale.runtime.visibility import is_visible

from .bot import Bot
from .view import build_view


class BotRunner:
    def __init__(
        self,
        rnd: Round,
        bots: Mapping[str, Bot],
        rng: random.Random,
        start: int,
        on_command: Callable[[str, Command], None] | None = None,
    ) -> None:
        self.rnd = rnd
        self.bots = dict(bots)
        self.on_command = on_command
        self._cursors = {pid: 0 for pid in self.bots}
        self._counter = itertools.count()
        # Heap entries: (time, kind, tiebreak, player, commands). At equal
        # times, arrivals (kind 0) are processed before decisions (kind 1).
        self._queue: list[tuple[int, int, int, str, list[Command]]] = [
            (start + rng.randint(0, 2_000), 1, next(self._counter), pid, []) for pid in self.bots
        ]
        heapq.heapify(self._queue)

    def next_time(self) -> int | None:
        """When the next bot action is due, or None if nothing is scheduled
        before the round closes."""
        if not self._queue or self._queue[0][0] >= self.rnd.close_at:
            return None
        return self._queue[0][0]

    def run_until(self, now: int) -> None:
        """Process every bot decision and arrival scheduled at or before ``now``."""
        rnd = self.rnd
        while self._queue and self._queue[0][0] <= now:
            t, kind, _, pid, cmds = heapq.heappop(self._queue)
            if t >= rnd.close_at:
                continue  # the round is over; this bot's schedule ends
            rnd.advance(t)
            bot = self.bots[pid]
            if kind == 0:
                for cmd in cmds:
                    if self.on_command:
                        self.on_command(pid, cmd)
                    rnd.submit(replace(cmd, ts=t))
                heapq.heappush(self._queue, (t + bot.next_delay(), 1, next(self._counter), pid, []))
                continue
            for e in rnd.log[self._cursors[pid] :]:
                if is_visible(e, pid):
                    bot.observe(e)
                    if isinstance(e, RunnerSlip) and e.player_id == pid:
                        bot.receive_clue(rnd.runner_clue(e.runner_id))  # the bot's own slip
            self._cursors[pid] = len(rnd.log)
            decided = bot.act(build_view(rnd.exchange, pid, t))
            heapq.heappush(self._queue, (t + bot.think_time(), 0, next(self._counter), pid, decided))
