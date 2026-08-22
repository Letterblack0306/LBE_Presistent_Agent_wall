"""Typed, truth-preserving view models for the LBE terminal client.

These models project persisted operational events. They never grant authority,
invent completion, or convert missing evidence into success.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from .memory.operational_history import OperationalEvent


class TuiEventKind(StrEnum):
    OBJECTIVE = "objective"
    AGENT = "agent"
    TOOL = "tool"
    VALIDATION = "validation"
    CONTROL = "control"
    ERROR = "error"
    UNKNOWN = "unknown"


class TuiState(StrEnum):
    ACTIVE = "active"
    PASS = "pass"
    DENIED = "denied"
    ESCALATED = "escalated"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TuiAuthorizationView:
    verdict: str
    rationale: str | None = None


@dataclass(frozen=True)
class TuiEvidenceView:
    count: int
    items: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class TuiReceiptView:
    receipt_id: str | None
    operation_id: str | None
    tool_id: str | None
    authorization: TuiAuthorizationView | None
    evidence: TuiEvidenceView
    output: Mapping[str, Any] | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class TuiEventView:
    sequence: int
    event_type: str
    kind: TuiEventKind
    state: TuiState
    title: str
    text: str | None
    receipt: TuiReceiptView | None
    provider_id: str | None
    model_id: str | None


def project_tui_event(event: OperationalEvent) -> TuiEventView:
    """Project one persisted event without inferring absent facts."""
    payload = dict(event.payload)
    event_type = event.event_type
    sequence = event.session_sequence or 0

    if event_type == "user.message":
        return _view(event, TuiEventKind.OBJECTIVE, TuiState.ACTIVE, "Objective", _clean_text(payload.get("text")))
    if event_type == "model.message.completed":
        return _view(event, TuiEventKind.AGENT, TuiState.PASS, "Agent", _clean_text(payload.get("text")))
    if event_type.startswith("tool."):
        state = {
            "tool.completed": TuiState.PASS,
            "tool.denied": TuiState.DENIED,
            "tool.escalated": TuiState.ESCALATED,
            "tool.failed": TuiState.FAILED,
        }.get(event_type, TuiState.UNKNOWN)
        tool_id = _clean_text(payload.get("tool_id"))
        return TuiEventView(
            sequence=sequence,
            event_type=event_type,
            kind=TuiEventKind.TOOL,
            state=state,
            title=tool_id or "Tool",
            text=_clean_text(payload.get("status")),
            receipt=_receipt(event, payload),
            provider_id=event.provider_id,
            model_id=event.model_id,
        )
    if event_type == "model.turn.completed":
        return _view(event, TuiEventKind.VALIDATION, TuiState.PASS, "Validated result", _clean_text(payload.get("outcome")))
    if event_type in {"model.error", "model.turn.incomplete", "model.turn.refused"}:
        text = _clean_text(payload.get("error_message")) or _clean_text(payload.get("outcome"))
        return _view(event, TuiEventKind.ERROR, TuiState.FAILED, "Runtime error", text)
    if event_type in {"model.cancelled", "turn.cancelled"}:
        return _view(event, TuiEventKind.CONTROL, TuiState.CANCELLED, "Cancelled", None)
    if event_type in {"turn.interrupt.requested", "turn.steer.requested"}:
        return _view(event, TuiEventKind.CONTROL, TuiState.ACTIVE, "Control", _clean_text(payload.get("text")))
    return _view(event, TuiEventKind.UNKNOWN, TuiState.UNKNOWN, event_type, None)


def project_tui_events(events: tuple[OperationalEvent, ...]) -> tuple[TuiEventView, ...]:
    return tuple(project_tui_event(event) for event in events)


def _view(
    event: OperationalEvent,
    kind: TuiEventKind,
    state: TuiState,
    title: str,
    text: str | None,
) -> TuiEventView:
    return TuiEventView(
        sequence=event.session_sequence or 0,
        event_type=event.event_type,
        kind=kind,
        state=state,
        title=title,
        text=text,
        receipt=None,
        provider_id=event.provider_id,
        model_id=event.model_id,
    )


def _receipt(event: OperationalEvent, payload: Mapping[str, Any]) -> TuiReceiptView:
    evidence_value = payload.get("evidence")
    evidence_items = (
        tuple(dict(item) for item in evidence_value if isinstance(item, Mapping))
        if isinstance(evidence_value, (list, tuple))
        else ()
    )
    output_value = payload.get("output")
    authorization_value = payload.get("authorization")
    authorization = None
    if isinstance(authorization_value, Mapping):
        verdict = _clean_text(authorization_value.get("verdict"))
        if verdict is not None:
            authorization = TuiAuthorizationView(
                verdict=verdict,
                rationale=_clean_text(authorization_value.get("rationale")),
            )
    return TuiReceiptView(
        receipt_id=_clean_text(payload.get("receipt_id")) or event.tool_receipt_id,
        operation_id=event.runtime_operation_id,
        tool_id=_clean_text(payload.get("tool_id")),
        authorization=authorization,
        evidence=TuiEvidenceView(count=len(evidence_items), items=evidence_items),
        output=dict(output_value) if isinstance(output_value, Mapping) else None,
        error_code=_clean_text(payload.get("error_code")),
        error_message=_clean_text(payload.get("error_message")),
    )


def _clean_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
