"""Wire protocol (PRD §29).

Client -> server messages are validated with pydantic. Server -> client
messages are plain JSON-ready dicts built by ``room.py``; engine events are
serialized with ``event_to_wire``. Every message has a ``type``.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from whale.engine import Event, Side

PROTOCOL_VERSION = 1


class _Msg(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# -- connecting ----------------------------------------------------------------------


class Hello(_Msg):
    type: Literal["hello"]
    name: Annotated[str, Field(min_length=1, max_length=20)]
    code: Annotated[str, Field(min_length=4, max_length=8)]


class Resume(_Msg):
    type: Literal["resume"]
    code: Annotated[str, Field(min_length=4, max_length=8)]
    token: Annotated[str, Field(min_length=8, max_length=64)]


ConnectMessage = Annotated[Hello | Resume, Field(discriminator="type")]
parse_connect = TypeAdapter(ConnectMessage).validate_python


# -- lobby (host only) -------------------------------------------------------------


class AddBot(_Msg):
    type: Literal["add_bot"]
    personality: str | None = None


class RemovePlayer(_Msg):
    type: Literal["remove_player"]
    player_id: str


class UpdateSettings(_Msg):
    type: Literal["settings"]
    rounds: Annotated[int, Field(ge=1, le=10)]
    round_seconds: Annotated[int, Field(ge=30, le=600)]


class Start(_Msg):
    type: Literal["start"]
    fill_bots: bool = False  # fill empty seats up to 4 players


class Ready(_Msg):
    """Done reading the briefing; the bell rings once every connected human is ready."""

    type: Literal["ready"]


class Begin(_Msg):
    """Host only: ring the bell without waiting for everyone to be ready."""

    type: Literal["begin"]


class NextRound(_Msg):
    type: Literal["next_round"]


class Rematch(_Msg):
    type: Literal["rematch"]


# -- trading -----------------------------------------------------------------------


class Quote(_Msg):
    """Set Your Market. A side with qty 0 is pulled."""

    type: Literal["quote"]
    bid: int
    bid_qty: Annotated[int, Field(ge=0)]
    ask: int
    ask_qty: Annotated[int, Field(ge=0)]


class Order(_Msg):
    type: Literal["order"]
    side: Side
    price: int
    qty: int
    kind: Literal["ioc", "limit"] = "ioc"


class Cancel(_Msg):
    type: Literal["cancel"]
    order_id: int


class CancelAll(_Msg):
    type: Literal["cancel_all"]


class Call(_Msg):
    type: Literal["call"]
    target: str


class AnswerCall(_Msg):
    type: Literal["answer"]
    call_id: int
    bid: int
    ask: int
    qty: int


class DecideCall(_Msg):
    type: Literal["decide"]
    call_id: int
    side: Side | None


ClientMessage = Annotated[
    AddBot
    | RemovePlayer
    | UpdateSettings
    | Start
    | Ready
    | Begin
    | NextRound
    | Rematch
    | Quote
    | Order
    | Cancel
    | CancelAll
    | Call
    | AnswerCall
    | DecideCall,
    Field(discriminator="type"),
]
parse_client = TypeAdapter(ClientMessage).validate_python


# -- server -> client ----------------------------------------------------------------


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def event_to_wire(event: Event) -> dict[str, Any]:
    """``Trade(...)`` -> ``{"type": "trade", ...fields}``. Enums are StrEnums,
    so they serialize as their string values. (``type`` rather than ``kind``,
    because Trade has its own ``kind`` field: book, auction, or call.)"""
    fields = dataclasses.asdict(event)
    assert "type" not in fields, "event field would shadow the event type"
    return {"type": _snake(type(event).__name__), **fields}
