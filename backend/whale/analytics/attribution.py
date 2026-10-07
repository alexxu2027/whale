"""Exact P&L attribution per player (PRD §17.2).

Each fill's settlement P&L, ``q * (V - price)`` (q > 0 for a buy), splits at
``mid``, the middle of the book just before the command that caused it:

    spread       = q * (mid - price)    what the fill earned against the market then
    afterwards   = q * (V - mid)        what happened between then and settlement

"Afterwards" is adverse selection on fills where the player was the maker
(someone chose to trade with their quote) and directional P&L where they
were the taker or in the auction (they chose to trade). Adding fees,
rebates, and penalties gives the player's trading P&L exactly.

Auction fills have no meaningful pre-trade mid (the pre-open book may be
crossed), so the auction price is used: all of their P&L is directional.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from whale.engine import CENTS_PER_POINT, Account, Trade, TradeKind


@dataclass(slots=True)
class Attribution:
    """All amounts in cents."""

    spread_cents: int = 0
    adverse_selection_cents: int = 0
    directional_cents: int = 0
    fees_cents: int = 0  # rebates minus fees minus penalties
    adverse_by_counterparty: dict[str, int] = field(default_factory=dict)

    @property
    def total_cents(self) -> int:
        return self.spread_cents + self.adverse_selection_cents + self.directional_cents + self.fees_cents


def attribute(
    trades: Iterable[Trade],
    mids: dict[int, float],
    accounts: dict[str, Account],
    final_value: int,
) -> dict[str, Attribution]:
    out = {p: Attribution() for p in accounts}
    adverse: dict[str, dict[str, int]] = {p: defaultdict(int) for p in accounts}
    for t in trades:
        mid = float(t.price) if t.kind is TradeKind.AUCTION else mids[t.trade_id]
        for player, q, counterparty in ((t.buyer_id, t.qty, t.seller_id), (t.seller_id, -t.qty, t.buyer_id)):
            a = out[player]
            a.spread_cents += round(q * (mid - t.price) * CENTS_PER_POINT)
            after = round(q * (final_value - mid) * CENTS_PER_POINT)
            if t.maker_id == player:
                a.adverse_selection_cents += after
                adverse[player][counterparty] += after
            else:
                a.directional_cents += after
    for p, acct in accounts.items():
        out[p].fees_cents = acct.rebates_earned_cents - acct.fees_paid_cents - acct.penalties_cents
        out[p].adverse_by_counterparty = dict(adverse[p])
    return out
