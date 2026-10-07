"""Pre-trade risk helpers."""

from __future__ import annotations


class TokenBucket:
    """Integer token bucket. Tokens are stored in thousandths to stay exact."""

    _UNIT = 1000

    def __init__(self, rate_per_sec: int, burst: int) -> None:
        self._rate = rate_per_sec  # thousandths of a token per millisecond
        self._capacity = burst * self._UNIT
        self._tokens = self._capacity
        self._last_ts: int | None = None

    def take(self, ts: int) -> bool:
        if self._last_ts is not None and ts > self._last_ts:
            elapsed = ts - self._last_ts
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        if self._last_ts is None or ts > self._last_ts:
            self._last_ts = ts
        if self._tokens >= self._UNIT:
            self._tokens -= self._UNIT
            return True
        return False
