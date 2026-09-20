"""Single SQLite authority for ordered session, turn, item, and event history."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .models import utc_now
from .store import WorkspaceMemoryStore
from ..runtime.tool_orchestration import ToolReceipt, ToolReceiptStatus


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


class ChildAgentStatus(StrEnum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ChildAgentRun:
    child_agent_run_id: str
    turn_id: str
    session_id: str
    correlation_id: str
    parent_agent: str
    status: ChildAgentStatus
    child_tools: tuple[str, ...] = ()
    child_session_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    receipt_id: str | None = None
    evidence_ref: str | None = None
    authorization_rationale: str | None = None
    recursive_spawn_authorized: bool = False


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
    def finalize_item(self, *, item_id: str, status: ItemStatus) -> OperationalItem:
        now=utc_now()
        with self.store._connect() as c:
            if c.execute("UPDATE operational_items SET status=?, finalized_at=? WHERE item_id=? AND status='running'",(status.value,now,item_id)).rowcount != 1: raise ValueError("item is missing or already finalized")
            row=c.execute("SELECT * FROM operational_items WHERE item_id=?",(item_id,)).fetchone()
        return OperationalItem(row["item_id"],row["turn_id"],row["kind"],ItemStatus(row["status"]),row["created_at"],row["finalized_at"])
    def get_turn(self, *, turn_id: str) -> OperationalTurn | None:
        with self.store._connect() as c: row=c.execute("SELECT * FROM operational_turns WHERE turn_id=?",(turn_id,)).fetchone()
        return None if row is None else OperationalTurn(row["turn_id"],row["session_id"],TurnStatus(row["status"]),row["created_at"],row["finalized_at"])
    def latest_running_turn(self, *, session_id: str) -> OperationalTurn | None:
        with self.store._connect() as c: row=c.execute("SELECT * FROM operational_turns WHERE session_id=? AND status='running' ORDER BY created_at DESC LIMIT 1",(session_id,)).fetchone()
        return None if row is None else OperationalTurn(row["turn_id"],row["session_id"],TurnStatus(row["status"]),row["created_at"],row["finalized_at"])
    def replay_turn_status(self, *, turn_id: str) -> TurnStatus:
        events=self.events_for_turn(turn_id=turn_id)
        mapping={"model.turn.completed":TurnStatus.COMPLETED,"model.turn.incomplete":TurnStatus.INCOMPLETE,"model.turn.refused":TurnStatus.REFUSED,"model.cancelled":TurnStatus.CANCELLED,"model.error":TurnStatus.FAILED,"tool.escalated":TurnStatus.ESCALATED}
        for event in reversed(events):
            if event.event_type in mapping: return mapping[event.event_type]
        raise ValueError("turn events do not contain a replayable terminal state")
    def project_tool_receipt(self, *, session_id: str, turn_id: str, item_id: str | None, receipt: ToolReceipt, provider_tool_call_id: str | None = None, lbe_call_id: str | None = None) -> OperationalEvent:
        if not isinstance(receipt, ToolReceipt): raise TypeError("receipt must be ToolReceipt")
        event_type={ToolReceiptStatus.EXECUTED:"tool.completed",ToolReceiptStatus.DENIED:"tool.denied",ToolReceiptStatus.ESCALATED:"tool.escalated",ToolReceiptStatus.FAILED:"tool.failed"}[receipt.status]
        return self.append_event(OperationalEvent(session_id=session_id,turn_id=turn_id,item_id=item_id,event_type=event_type,payload={"tool_id":receipt.tool_id,"receipt_id":receipt.receipt_id,"status":receipt.status.value,"output":dict(receipt.output or {}),"evidence":[dict(value) for value in receipt.evidence],"error_code":receipt.error_code,"error_message":receipt.error_message},provider_tool_call_id=provider_tool_call_id,lbe_call_id=lbe_call_id,runtime_operation_id=receipt.operation_id,tool_receipt_id=receipt.receipt_id))
    def events_for_turn(self, *, turn_id: str) -> tuple[OperationalEvent,...]:
        with self.store._connect() as c: rows=c.execute("SELECT * FROM operational_events WHERE turn_id=? ORDER BY turn_sequence",(turn_id,)).fetchall()
        return tuple(OperationalEvent(event_id=r["event_id"],session_id=r["session_id"],turn_id=r["turn_id"],item_id=r["item_id"],event_type=r["event_type"],payload=json.loads(r["payload_json"]),provider_id=r["provider_id"],model_id=r["model_id"],provider_request_id=r["provider_request_id"],provider_item_id=r["provider_item_id"],provider_tool_call_id=r["provider_tool_call_id"],lbe_call_id=r["lbe_call_id"],runtime_operation_id=r["runtime_operation_id"],tool_receipt_id=r["tool_receipt_id"],created_at=r["created_at"],session_sequence=r["session_sequence"],turn_sequence=r["turn_sequence"]) for r in rows)
    def events_for_session(self, *, session_id: str) -> tuple[OperationalEvent,...]:
        with self.store._connect() as c: rows=c.execute("SELECT * FROM operational_events WHERE session_id=? ORDER BY session_sequence",(session_id,)).fetchall()
        return tuple(OperationalEvent(event_id=r["event_id"],session_id=r["session_id"],turn_id=r["turn_id"],item_id=r["item_id"],event_type=r["event_type"],payload=json.loads(r["payload_json"]),provider_id=r["provider_id"],model_id=r["model_id"],provider_request_id=r["provider_request_id"],provider_item_id=r["provider_item_id"],provider_tool_call_id=r["provider_tool_call_id"],lbe_call_id=r["lbe_call_id"],runtime_operation_id=r["runtime_operation_id"],tool_receipt_id=r["tool_receipt_id"],created_at=r["created_at"],session_sequence=r["session_sequence"],turn_sequence=r["turn_sequence"]) for r in rows)
    def create_child_agent_run(self, *, session_id: str, turn_id: str, correlation_id: str, parent_agent: str, child_tools: tuple[str, ...] = (), recursive_spawn_authorized: bool = False, authorization_rationale: str | None = None) -> ChildAgentRun:
        if not str(correlation_id).strip() or not str(parent_agent).strip(): raise ValueError("child agent correlation_id and parent_agent are required")
        turn = self.get_turn(turn_id=turn_id)
        if turn is None or turn.session_id != session_id: raise ValueError("child agent turn does not belong to the parent session")
        item = self.start_item(turn_id=turn_id, kind="child_agent_run")
        run = ChildAgentRun(child_agent_run_id=item.item_id, turn_id=turn_id, session_id=session_id, correlation_id=str(correlation_id).strip(), parent_agent=str(parent_agent).strip(), status=ChildAgentStatus.PENDING, child_tools=tuple(child_tools), authorization_rationale=authorization_rationale, recursive_spawn_authorized=bool(recursive_spawn_authorized))
        self.append_event(OperationalEvent(session_id=session_id,turn_id=turn_id,item_id=run.child_agent_run_id,event_type="child_agent.created",payload={"correlation_id":run.correlation_id,"parent_agent":run.parent_agent,"child_tools":list(run.child_tools),"recursive_spawn_authorized":run.recursive_spawn_authorized,"authorization_rationale":run.authorization_rationale}))
        return run
    def start_child_agent_run(self, *, session_id: str, turn_id: str, child_agent_run_id: str, child_session_id: str | None = None) -> ChildAgentRun:
        item = self._child_agent_item(turn_id=turn_id, child_agent_run_id=child_agent_run_id)
        events = self._child_agent_events(turn_id=turn_id, child_agent_run_id=child_agent_run_id)
        if any(e.event_type.startswith("child_agent.") and e.event_type.endswith(("completed","failed","cancelled","rejected")) for e in events): raise ValueError("child agent run is already finalized")
        if any(e.event_type == "child_agent.started" for e in events): raise ValueError("child agent run has already started")
        self.append_event(OperationalEvent(session_id=session_id,turn_id=turn_id,item_id=item.item_id,event_type="child_agent.started",payload={"child_session_id":child_session_id}))
        return self.child_agent_run(session_id=session_id, turn_id=turn_id, child_agent_run_id=item.item_id)
    def finalize_child_agent_run(self, *, session_id: str, turn_id: str, child_agent_run_id: str, status: ChildAgentStatus, receipt_id: str | None = None, evidence_ref: str | None = None, authorization_rationale: str | None = None) -> ChildAgentRun:
        terminal = {ChildAgentStatus.COMPLETED:("child_agent.completed",ItemStatus.COMPLETED),ChildAgentStatus.FAILED:("child_agent.failed",ItemStatus.FAILED),ChildAgentStatus.CANCELLED:("child_agent.cancelled",ItemStatus.CANCELLED),ChildAgentStatus.REJECTED:("child_agent.rejected",ItemStatus.DENIED)}
        if status not in terminal: raise ValueError(f"child agent finalize status must be terminal: {status!r}")
        item = self._child_agent_item(turn_id=turn_id, child_agent_run_id=child_agent_run_id)
        if item.status is not ItemStatus.RUNNING: raise ValueError("child agent run is already finalized")
        event_type, item_status = terminal[status]
        self.finalize_item(item_id=item.item_id, status=item_status)
        self.append_event(OperationalEvent(session_id=session_id,turn_id=turn_id,item_id=item.item_id,event_type=event_type,payload={"receipt_id":receipt_id,"evidence_ref":evidence_ref,"authorization_rationale":authorization_rationale}))
        return self.child_agent_run(session_id=session_id, turn_id=turn_id, child_agent_run_id=item.item_id)
    def child_agent_run(self, *, session_id: str, turn_id: str, child_agent_run_id: str) -> ChildAgentRun | None:
        try:
            item = self._child_agent_item(turn_id=turn_id, child_agent_run_id=child_agent_run_id)
        except KeyError:
            return None
        return self._project_child_agent_run(item, session_id, self._child_agent_events(turn_id=turn_id, child_agent_run_id=child_agent_run_id))
    def child_agent_runs_for_turn(self, *, turn_id: str) -> tuple[ChildAgentRun,...]:
        turn = self.get_turn(turn_id=turn_id)
        if turn is None: return ()
        with self.store._connect() as c: rows=c.execute("SELECT * FROM operational_items WHERE turn_id=? AND kind='child_agent_run' ORDER BY created_at, item_id",(turn_id,)).fetchall()
        events = self.events_for_turn(turn_id=turn_id)
        return tuple(self._project_child_agent_run(OperationalItem(r["item_id"],r["turn_id"],r["kind"],ItemStatus(r["status"]),r["created_at"],r["finalized_at"]), turn.session_id, events) for r in rows)
    def _child_agent_item(self, *, turn_id: str, child_agent_run_id: str) -> OperationalItem:
        if not str(child_agent_run_id).strip(): raise ValueError("child_agent_run_id must not be empty")
        with self.store._connect() as c: row=c.execute("SELECT * FROM operational_items WHERE item_id=? AND turn_id=?",(child_agent_run_id,turn_id)).fetchone()
        if row is None: raise KeyError(f"child agent run not found: {child_agent_run_id}")
        item=OperationalItem(row["item_id"],row["turn_id"],row["kind"],ItemStatus(row["status"]),row["created_at"],row["finalized_at"])
        if item.kind != "child_agent_run": raise ValueError(f"item {child_agent_run_id} is not a child agent run")
        return item
    def _child_agent_events(self, *, turn_id: str, child_agent_run_id: str) -> tuple[OperationalEvent,...]:
        return tuple(e for e in self.events_for_turn(turn_id=turn_id) if e.item_id == child_agent_run_id)
    @staticmethod
    def _project_child_agent_run(item: OperationalItem, session_id: str, events: tuple[OperationalEvent,...]) -> ChildAgentRun:
        run_events=[e for e in events if e.item_id==item.item_id]
        terminal_types={"child_agent.completed":ChildAgentStatus.COMPLETED,"child_agent.failed":ChildAgentStatus.FAILED,"child_agent.cancelled":ChildAgentStatus.CANCELLED,"child_agent.rejected":ChildAgentStatus.REJECTED}
        created=next((e for e in run_events if e.event_type=="child_agent.created"),None)
        started=next((e for e in run_events if e.event_type=="child_agent.started"),None)
        terminal=next((e for e in reversed(run_events) if e.event_type in terminal_types),None)
        if terminal is not None: status=terminal_types[terminal.event_type]
        elif started is not None: status=ChildAgentStatus.RUNNING
        elif created is not None: status=ChildAgentStatus.PENDING
        else:
            status={ItemStatus.COMPLETED:ChildAgentStatus.COMPLETED,ItemStatus.FAILED:ChildAgentStatus.FAILED,ItemStatus.CANCELLED:ChildAgentStatus.CANCELLED,ItemStatus.DENIED:ChildAgentStatus.REJECTED}.get(item.status,ChildAgentStatus.PENDING)
        payload=dict(created.payload) if created is not None else {}
        terminal_payload=dict(terminal.payload) if terminal is not None else {}
        return ChildAgentRun(child_agent_run_id=item.item_id,turn_id=item.turn_id,session_id=session_id,correlation_id=str(payload.get("correlation_id") or item.item_id),parent_agent=str(payload.get("parent_agent") or ""),status=status,child_tools=tuple(payload.get("child_tools") or ()),child_session_id=started.payload.get("child_session_id") if started is not None else None,started_at=started.created_at if started is not None else None,completed_at=terminal.created_at if terminal is not None else None,receipt_id=terminal_payload.get("receipt_id"),evidence_ref=terminal_payload.get("evidence_ref"),authorization_rationale=payload.get("authorization_rationale"),recursive_spawn_authorized=bool(payload.get("recursive_spawn_authorized",False)))
