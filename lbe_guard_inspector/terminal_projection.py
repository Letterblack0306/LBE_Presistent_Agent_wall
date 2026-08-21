"""Terminal-safe projection of persisted LBE operational events.

The terminal client receives evidence from the history owner.  It does not infer
authorization, construct receipts, or decide whether a turn completed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .memory.operational_history import OperationalEvent, SessionOperationalHistory


@dataclass(frozen=True)
class TerminalEventCell:
    """One truthful terminal timeline cell, derived only from a persisted event."""

    sequence: int
    kind: str
    title: str
    detail: str
    tone: str


def project_terminal_timeline(*, history: SessionOperationalHistory, session_id: str) -> tuple[TerminalEventCell, ...]:
    return tuple(_project_event(event) for event in history.events_for_session(session_id=session_id))


def _project_event(event: OperationalEvent) -> TerminalEventCell:
    payload = dict(event.payload)
    sequence = event.session_sequence or 0
    if event.event_type == "user.message":
        return TerminalEventCell(sequence, event.event_type, "OBJECTIVE", _text(payload, "text"), "objective")
    if event.event_type == "model.message.completed":
        return TerminalEventCell(sequence, event.event_type, "AGENT", _text(payload, "text"), "agent")
    if event.event_type.startswith("tool."):
        status = event.event_type.removeprefix("tool.").upper()
        fields = (
            ("tool", payload.get("tool_id")),
            ("status", payload.get("status")),
            ("receipt", payload.get("receipt_id") or event.tool_receipt_id),
            ("operation", event.runtime_operation_id),
            ("output", payload.get("output")),
            ("evidence", payload.get("evidence")),
            ("error", payload.get("error_message") or payload.get("error_code")),
        )
        return TerminalEventCell(sequence, event.event_type, f"TOOL {status}", _fields(fields), _tool_tone(event.event_type))
    if event.event_type == "model.error":
        return TerminalEventCell(sequence, event.event_type, "RUNTIME ERROR", _fields((("code", payload.get("error_code")), ("message", payload.get("error_message")))), "error")
    if event.event_type == "model.turn.completed":
        return TerminalEventCell(sequence, event.event_type, "VALIDATED RESULT", _fields((("task", payload.get("task_id")), ("outcome", payload.get("outcome")))), "success")
    if event.event_type in {"turn.interrupt.requested", "turn.cancelled", "turn.steering.received"}:
        return TerminalEventCell(sequence, event.event_type, event.event_type.replace(".", " ").upper(), _fields((("text", payload.get("text")),)), "control")
    if event.event_type.startswith("model.turn.") or event.event_type.startswith("runtime.provider."):
        return TerminalEventCell(sequence, event.event_type, event.event_type.replace(".", " ").upper(), _fields(tuple(payload.items())), "status")
    return TerminalEventCell(sequence, event.event_type, event.event_type.replace(".", " ").upper(), _fields(tuple(payload.items())), "status")


def render_terminal_timeline(*, history: SessionOperationalHistory, session_id: str) -> str:
    cells = project_terminal_timeline(history=history, session_id=session_id)
    if not cells:
        return "No persisted runtime events."
    return "\n\n".join(f"[{cell.sequence:04d}] {cell.title}\n{cell.detail}" for cell in cells)


def _tool_tone(event_type: str) -> str:
    return {"tool.completed": "success", "tool.denied": "denied", "tool.escalated": "warning", "tool.failed": "error"}.get(event_type, "status")


def _text(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else "(no persisted text)"


def _fields(values: tuple[tuple[str, Any], ...]) -> str:
    parts = []
    for name, value in values:
        if value is None or value == "" or value == [] or value == {}:
            continue
        rendered = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
        parts.append(f"{name}: {rendered}")
    return "\n".join(parts) if parts else "(no persisted details)"
