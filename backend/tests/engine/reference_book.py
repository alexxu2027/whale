"""An obviously-correct order book for differential testing (PRD §32.5).

Linear scans over a dict of orders. Slow, but its priority logic is a single
sort key, so it is easy to trust.
"""

from __future__ import annotations

from collections.abc import Iterator

from whale.engine.types import Order, Side


def _priority_key(order: Order) -> tuple[int, int]:
    # Buys: highest price first. Sells: lowest price first. Then earliest.
    price = -order.price if order.side is Side.BUY else order.price
    return (price, order.priority)


class ReferenceOrderBook:
    def __init__(self, price_min: int, price_max: int) -> None:
        self._orders: dict[int, Order] = {}

    def add(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def remove(self, order_id: int) -> Order:
        order = self._orders.pop(order_id)
        order.live = False
        return order

    def reduce(self, order_id: int, qty: int) -> None:
        order = self._orders[order_id]
        assert 0 < qty < order.qty
        order.qty = qty

    def get(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)

    def _sorted(self, side: Side, exclude: int | None = None) -> list[Order]:
        return sorted(
            (o for o in self._orders.values() if o.side is side and o.order_id != exclude),
            key=_priority_key,
        )

    def best_order(self, side: Side) -> Order | None:
        ranked = self._sorted(side)
        return ranked[0] if ranked else None

    def best_price(self, side: Side, exclude: int | None = None) -> int | None:
        ranked = self._sorted(side, exclude)
        return ranked[0].price if ranked else None

    def depth(self, side: Side, levels: int | None = None) -> list[tuple[int, int]]:
        agg: dict[int, int] = {}
        for o in self._sorted(side):
            agg[o.price] = agg.get(o.price, 0) + o.qty
        out = list(agg.items())  # already in priority order by price
        return out if levels is None else out[:levels]

    def orders(self) -> Iterator[Order]:
        return iter(self._orders.values())

    def __len__(self) -> int:
        return len(self._orders)
