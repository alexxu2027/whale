"""Price-level order book.

The price band is small and bounded (e.g. 80..120), so each side is a fixed
array of FIFO queues indexed by tick. Cancels are lazy: a removed order is
flagged dead and skipped when it reaches the front of its queue, which keeps
cancel and amend O(1). Per-level live counts and quantities are maintained
eagerly, so best-price tracking and depth never look at dead orders.

The book is a data structure only. Matching, risk, and accounting live in
``exchange.py``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator

from .types import Order, Side


class OrderBook:
    def __init__(self, price_min: int, price_max: int) -> None:
        self._min = price_min
        self._n = price_max - price_min + 1
        n = self._n
        self._queues: dict[Side, list[deque[Order]]] = {
            Side.BUY: [deque() for _ in range(n)],
            Side.SELL: [deque() for _ in range(n)],
        }
        self._count: dict[Side, list[int]] = {Side.BUY: [0] * n, Side.SELL: [0] * n}
        self._qty: dict[Side, list[int]] = {Side.BUY: [0] * n, Side.SELL: [0] * n}
        self._best_bid = -1  # index of best buy level, -1 if none
        self._best_ask = n  # index of best sell level, n if none
        self._orders: dict[int, Order] = {}

    # -- mutation ---------------------------------------------------------

    def add(self, order: Order) -> None:
        i = order.price - self._min
        side = order.side
        self._queues[side][i].append(order)
        self._count[side][i] += 1
        self._qty[side][i] += order.qty
        if side is Side.BUY:
            if i > self._best_bid:
                self._best_bid = i
        elif i < self._best_ask:
            self._best_ask = i
        self._orders[order.order_id] = order

    def remove(self, order_id: int) -> Order:
        order = self._orders.pop(order_id)
        order.live = False
        i = order.price - self._min
        side = order.side
        self._count[side][i] -= 1
        self._qty[side][i] -= order.qty
        if self._count[side][i] == 0:
            self._queues[side][i].clear()
            if side is Side.BUY and i == self._best_bid:
                self._best_bid = self._scan_down(Side.BUY, i - 1)
            elif side is Side.SELL and i == self._best_ask:
                self._best_ask = self._scan_up(Side.SELL, i + 1)
        return order

    def reduce(self, order_id: int, qty: int) -> None:
        """Lower an order's remaining quantity in place, keeping its priority."""
        order = self._orders[order_id]
        if not 0 < qty < order.qty:
            raise ValueError("reduce requires 0 < qty < current qty")
        self._qty[order.side][order.price - self._min] -= order.qty - qty
        order.qty = qty

    # -- queries ----------------------------------------------------------

    def get(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)

    def best_order(self, side: Side) -> Order | None:
        i = self._best_bid if side is Side.BUY else self._best_ask
        if not 0 <= i < self._n:
            return None
        q = self._queues[side][i]
        while not q[0].live:
            q.popleft()
        return q[0]

    def best_price(self, side: Side, exclude: int | None = None) -> int | None:
        """Best price on ``side``, optionally ignoring one order by id."""
        best = self.best_order(side)
        if best is None:
            return None
        if best.order_id != exclude:
            return best.price
        i = best.price - self._min
        if self._count[side][i] > 1:
            return best.price
        j = self._scan_down(side, i - 1) if side is Side.BUY else self._scan_up(side, i + 1)
        return j + self._min if 0 <= j < self._n else None

    def depth(self, side: Side, levels: int | None = None) -> list[tuple[int, int]]:
        """Aggregated ``(price, qty)`` levels, best first."""
        out: list[tuple[int, int]] = []
        qty = self._qty[side]
        rng = range(self._best_bid, -1, -1) if side is Side.BUY else range(self._best_ask, self._n)
        for i in rng:
            if qty[i]:
                out.append((i + self._min, qty[i]))
                if levels is not None and len(out) == levels:
                    break
        return out

    def orders(self) -> Iterator[Order]:
        return iter(self._orders.values())

    def __len__(self) -> int:
        return len(self._orders)

    # -- internals --------------------------------------------------------

    def _scan_down(self, side: Side, i: int) -> int:
        count = self._count[side]
        while i >= 0 and count[i] == 0:
            i -= 1
        return i

    def _scan_up(self, side: Side, i: int) -> int:
        count = self._count[side]
        while i < self._n and count[i] == 0:
            i += 1
        return i
