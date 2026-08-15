"""Single SQLite authority for ordered session, turn, item, and event history."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .models import utc_now
from .store import WorkspaceMemoryStore


class TurnStatus(StrEnum):
    RUNNING = "running"; COMPLETED = "completed"; FAILED = "failed"; CANCELLED = "cancelled"; INCOMPLETE = "incomplete"; REFUSED = "refused"; ESCALATED = "escalated"


class ItemStatus(StrEnum):
    RUNNING = "running"; COMPLETED = "completed"; FAILED = "failed"; CANCELLED = "cancelled"; DENIED = "denied"; ESCALATED = "escalated"


@dataclass(frozen=True)
class OperationalTurn:
    turn_id: str; session_id: str; status: TurnStatus; created_at: str; finalized_at: str | None = None


@dataclass(frozen=True)
class OperationalItem:
    item_id: str; turn_id: str; kind: str; status: ItemStatus; created_at: str; finalized_at: str | None = None


@dataclass(frozen=True)
class OperationalEvent:
    session_id: str; turn_id: str; event_type: str; payload: Mapping[str, Any]
    item_id: str | None = None; provider_id: str | None = None; model_id: str | None = None
    provider_request_id: str | None = None; provider_item_id: str | None = None; provider_tool_call_id: str | None = None
    lbe_call_id: str | None = None; runtime_operation_id: str | None = None; tool_receipt_id: str | None = None
    event_id: str = field(default_factory=lambda: f"event-{uuid.uuid4().hex}")
    created_at: str = field(default_factory=utc_now)
    session_sequence: int | None = None; turn_sequence: int | None = None


class SessionOperationalHistory:
    def __init__(self, *, store: WorkspaceMemoryStore) -> None: self.store = store
    def start_turn(self, *, session_id: str) -> OperationalTurn:
        if self.store.load_session_state(session_id=session_id) is None: raise KeyError(f"session not found: {session_id}")
        turn = OperationalTurn(f"turn-{uuid.uuid4().hex}", session_id, TurnStatus.RUNNING, utc_now())
        with self.store._connect() as c: c.execute("INSERT INTO operational_turns VALUES (?, ?, ?, ?, ?)", (turn.turn_id, turn.session_id, turn.status.value, turn.created_at, None))
        return turn
    def start_item(self, *, turn_id: str, kind: str) -> OperationalItem:
        if not kind.strip(): raise ValueError("item kind must be non-empty")
        item = OperationalItem(f"item-{uuid.uuid4().hex}", turn_id, kind.strip(), ItemStatus.RUNNING, utc_now())
        with self.store._connect() as c: c.execute("INSERT INTO operational_items VALUES (?, ?, ?, ?, ?, ?)", (item.item_id,item.turn_id,item.kind,item.status.value,item.created_at,None))
        return item
    def append_event(self, event: OperationalEvent) -> OperationalEvent:
        if not event.event_type.strip() or not isinstance(event.payload, Mapping): raise ValueError("event type and payload are required")
        with self.store._connect() as c:
            s = int(c.execute("SELECT COALESCE(MAX(session_sequence),0)+1 FROM operational_events WHERE session_id=?",(event.session_id,)).fetchone()[0])
            t = int(c.execute("SELECT COALESCE(MAX(turn_sequence),0)+1 FROM operational_events WHERE turn_id=?",(event.turn_id,)).fetchone()[0])
            c.execute("INSERT INTO operational_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(event.event_id,event.session_id,event.turn_id,event.item_id,s,t,event.event_type,json.dumps(dict(event.payload),sort_keys=True),event.provider_id,event.model_id,event.provider_request_id,event.provider_item_id,event.provider_tool_call_id,event.lbe_call_id,event.runtime_operation_id,event.tool_receipt_id,event.created_at))
        return OperationalEvent(**{**event.__dict__,"session_sequence":s,"turn_sequence":t})
    def finalize_turn(self, *, turn_id: str, status: TurnStatus) -> OperationalTurn:
        now=utc_now()
        with self.store._connect() as c:
            if c.execute("UPDATE operational_turns SET status=?, finalized_at=? WHERE turn_id=? AND status='running'",(status.value,now,turn_id)).rowcount != 1: raise ValueError("turn is missing or already finalized")
            row=c.execute("SELECT * FROM operational_turns WHERE turn_id=?",(turn_id,)).fetchone()
        return OperationalTurn(row["turn_id"],row["session_id"],TurnStatus(row["status"]),row["created_at"],row["finalized_at"])
    def events_for_turn(self, *, turn_id: str) -> tuple[OperationalEvent,...]:
        with self.store._connect() as c: rows=c.execute("SELECT * FROM operational_events WHERE turn_id=? ORDER BY turn_sequence",(turn_id,)).fetchall()
        return tuple(OperationalEvent(event_id=r["event_id"],session_id=r["session_id"],turn_id=r["turn_id"],item_id=r["item_id"],event_type=r["event_type"],payload=json.loads(r["payload_json"]),provider_id=r["provider_id"],model_id=r["model_id"],provider_request_id=r["provider_request_id"],provider_item_id=r["provider_item_id"],provider_tool_call_id=r["provider_tool_call_id"],lbe_call_id=r["lbe_call_id"],runtime_operation_id=r["runtime_operation_id"],tool_receipt_id=r["tool_receipt_id"],created_at=r["created_at"],session_sequence=r["session_sequence"],turn_sequence=r["turn_sequence"]) for r in rows)
