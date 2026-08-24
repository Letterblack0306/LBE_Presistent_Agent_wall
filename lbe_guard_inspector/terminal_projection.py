"""Terminal-safe projection of persisted LBE operational events.

The terminal client receives evidence from the history owner.  It does not infer
authorization, construct receipts, or decide whether a turn completed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .memory.operational_history import OperationalEvent, SessionOperationalHistory
from .tui_view_models import TuiEventView, project_tui_events


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



@dataclass(frozen=True)
class TerminalActivityRow:
    """One compact activity row derived from a typed persisted event view."""

    sequence: int
    kind: str
    target: str
    receipt: str
    state: str


def project_terminal_activity(
    *,
    history: SessionOperationalHistory,
    session_id: str,
) -> tuple[TerminalActivityRow, ...]:
    views = project_tui_events(history.events_for_session(session_id=session_id))
    return tuple(
        TerminalActivityRow(
            sequence=view.sequence,
            kind=view.kind.value,
            target=view.title,
            receipt=(
                view.receipt.receipt_id
                if view.receipt is not None and view.receipt.receipt_id is not None
                else "-"
            ),
            state=view.state.value,
        )
        for view in views
    )


def render_terminal_activity(*, history: SessionOperationalHistory, session_id: str) -> str:
    """Render a stable summary; structured details remain progressively disclosed."""
    rows = project_terminal_activity(history=history, session_id=session_id)
    if not rows:
        return "No persisted runtime events."
    return "\n".join(
        f"{row.sequence:04d}  {row.kind[:10]:10} {row.target[:40]:40} "
        f"{row.receipt[:14]:14} {row.state}"
        for row in rows
    )


def render_terminal_event_detail(
    *,
    history: SessionOperationalHistory,
    session_id: str,
    sequence: int | None = None,
) -> str:
    """Render bounded detail for one persisted event without inferring missing facts."""
    views = project_tui_events(history.events_for_session(session_id=session_id))
    if not views:
        return "DETAIL\nunavailable: no persisted runtime events"
    view = views[-1] if sequence is None else next(
        (item for item in views if item.sequence == sequence),
        None,
    )
    if view is None:
        return f"DETAIL\nunavailable: event sequence {sequence} not found"
    return _render_typed_detail(view)


def _render_typed_detail(view: TuiEventView) -> str:
    lines = [
        f"DETAIL event={view.sequence} type={view.event_type}",
        f"kind={view.kind.value} state={view.state.value} title={view.title}",
    ]
    if view.text is not None:
        lines.append(f"text={view.text}")
    if view.provider_id is not None or view.model_id is not None:
        lines.append(
            f"provider={view.provider_id or 'unknown'} model={view.model_id or 'unknown'}"
        )
    if view.validation is not None:
        lines.append(
            "validation="
            f"{view.validation.state.value} task={view.validation.task_id or 'unknown'} "
            f"outcome={view.validation.outcome or 'unknown'}"
        )
    receipt = view.receipt
    if receipt is not None:
        lines.append(
            f"receipt={receipt.receipt_id or 'unavailable'} "
            f"operation={receipt.operation_id or 'unavailable'} "
            f"tool={receipt.tool_id or 'unknown'}"
        )
        if receipt.authorization is None:
            lines.append("authorization=unavailable")
        else:
            lines.append(
                f"authorization={receipt.authorization.verdict} "
                f"rationale={receipt.authorization.rationale or 'unavailable'}"
            )
        lines.append(f"evidence_count={receipt.evidence.count}")
        for index, item in enumerate(receipt.evidence.items[:3], start=1):
            lines.append(f"evidence_{index}={_bounded_mapping(item)}")
        lines.append(
            f"diff={'available' if receipt.diff.available else 'unavailable'} "
            f"summary={receipt.diff.summary or 'unavailable'}"
        )
        if receipt.output is not None:
            lines.append(f"output={_bounded_mapping(receipt.output)}")
        if receipt.error_code is not None or receipt.error_message is not None:
            lines.append(
                f"error={receipt.error_code or 'unknown'} "
                f"message={receipt.error_message or 'unavailable'}"
            )
    return "\n".join(lines)


def _bounded_mapping(value: Any, *, limit: int = 240) -> str:
    rendered = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return rendered if len(rendered) <= limit else rendered[: limit - 3] + "..."
