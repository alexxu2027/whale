"""Who may see which event (PRD §29.1, §31).

Public: trades, calls, and market status. Everything about individual orders
(accepted, amended, cancelled, rejected) and quote bookkeeping goes only to
the order's owner; other players see the book as aggregated price levels.

Phase 2's network layer and the bots both go through this one function, so
there is a single place to audit what leaves the server.
"""

from __future__ import annotations

from whale.engine import (
    CallAnswered,
    CallEnded,
    CallStarted,
    Event,
    OrderAccepted,
    OrderAmended,
    OrderCancelled,
    OrderRejected,
    QuoteUpdated,
    StatusChanged,
    Trade,
)

_PUBLIC = (Trade, CallStarted, CallAnswered, CallEnded, StatusChanged)
_OWNER_ONLY = (OrderAccepted, OrderAmended, OrderCancelled, OrderRejected, QuoteUpdated)


def is_visible(event: Event, player_id: str) -> bool:
    if isinstance(event, _PUBLIC):
        return True
    if isinstance(event, _OWNER_ONLY):
        return event.player_id == player_id
    return False  # unknown event types are private by default
