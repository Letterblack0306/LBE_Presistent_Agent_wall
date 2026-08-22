"""Typed, truth-preserving view models for the LBE terminal client.

Every projection consumes an existing runtime owner or persisted event. Projection
code never authorizes work, executes tools, or decides completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence

from .memory.models import SessionState
from .memory.operational_history import OperationalEvent
from .provider_registry import ProviderDescriptor
from .runtime.tool_orchestration import ToolSpec


class TuiEventKind(StrEnum):
    OBJECTIVE = "objective"
    AGENT = "agent"
    PROVIDER = "provider"
    CAPABILITY = "capability"
    TOOL = "tool"
    AUTHORIZATION = "authorization"
    RECEIPT = "receipt"
    EVIDENCE = "evidence"
    DIFF = "diff"
    VALIDATION = "validation"
    COMPLETION = "completion"
    CONTROL = "control"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class TuiState(StrEnum):
    AVAILABLE = "available"
    ACTIVE = "active"
    LOADING = "loading"
    EMPTY = "empty"
    PASS = "pass"
    COMPLETED = "completed"
    DENIED = "denied"
    ESCALATED = "escalated"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TuiSessionView:
    session_id: str
    workspace_id: str
    workspace_root: str
    mode: str
    permission: str | None
    runtime_policy: str | None
    provider_id: str | None
    model_id: str | None
    profile_id: str | None
    active_turn: bool


@dataclass(frozen=True)
class TuiProviderView:
    provider_id: str
    model_id: str
    selected: bool
    health: TuiState
    streaming: bool
    tool_calls: bool
    structured_output: bool
    context_limit: int | None


@dataclass(frozen=True)
class TuiCapabilityView:
    tool_id: str
    capability: str
    access_class: str
    network_behavior: str
    risk_class: str
    available: bool


@dataclass(frozen=True)
class TuiAuthorizationView:
    verdict: str
    rationale: str | None = None


@dataclass(frozen=True)
class TuiEvidenceView:
    count: int
    items: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class TuiDiffView:
    available: bool
    summary: str | None
    payload: Mapping[str, Any] | None


@dataclass(frozen=True)
class TuiValidationView:
    task_id: str | None
    outcome: str | None
    state: TuiState


@dataclass(frozen=True)
class TuiReceiptView:
    receipt_id: str | None
    operation_id: str | None
    tool_id: str | None
    authorization: TuiAuthorizationView | None
    evidence: TuiEvidenceView
    diff: TuiDiffView
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
    validation: TuiValidationView | None
    receipt: TuiReceiptView | None
    provider_id: str | None
    model_id: str | None


def project_tui_session(state: SessionState, *, active_turn: bool = False) -> TuiSessionView:
    if not isinstance(state, SessionState):
        raise TypeError("state must be SessionState")
    return TuiSessionView(
        session_id=state.session_id,
        workspace_id=state.project_workspace_id,
        workspace_root=state.canonical_workspace_root,
        mode=state.mode,
        permission=state.permission,
        runtime_policy=state.runtime_policy,
        provider_id=state.provider_id,
        model_id=state.provider_model,
        profile_id=state.active_profile_id,
        active_turn=bool(active_turn),
    )


def project_tui_provider(
    descriptor: ProviderDescriptor,
    *,
    selected: bool = False,
    health: TuiState = TuiState.UNKNOWN,
) -> TuiProviderView:
    if not isinstance(descriptor, ProviderDescriptor):
        raise TypeError("descriptor must be ProviderDescriptor")
    if not isinstance(health, TuiState):
        raise TypeError("health must be TuiState")
    capabilities = descriptor.capabilities
    return TuiProviderView(
        provider_id=descriptor.provider_id,
        model_id=descriptor.model_id,
        selected=bool(selected),
        health=health,
        streaming=capabilities.streaming,
        tool_calls=capabilities.tool_calls,
        structured_output=capabilities.structured_output,
        context_limit=capabilities.context_limit,
    )


def project_tui_capabilities(specs: Sequence[ToolSpec]) -> tuple[TuiCapabilityView, ...]:
    views = []
    for spec in specs:
        if not isinstance(spec, ToolSpec):
            raise TypeError("specs must contain ToolSpec values")
        views.append(TuiCapabilityView(
            tool_id=spec.tool_id,
            capability=spec.capability,
            access_class=spec.access_class.value,
            network_behavior=spec.network_behavior.value,
            risk_class=spec.risk_class.value,
            available=True,
        ))
    return tuple(views)


def project_tui_event(event: OperationalEvent) -> TuiEventView:
    """Project one persisted event without inferring absent facts."""
    payload = dict(event.payload)
    event_type = event.event_type

    if event_type == "user.message":
        return _view(event, TuiEventKind.OBJECTIVE, TuiState.ACTIVE, "Objective", _clean_text(payload.get("text")))
    if event_type == "model.message.completed":
        return _view(event, TuiEventKind.AGENT, TuiState.COMPLETED, "Agent", _clean_text(payload.get("text")))
    if event_type.startswith("tool."):
        state = {
            "tool.completed": TuiState.COMPLETED,
            "tool.denied": TuiState.DENIED,
            "tool.escalated": TuiState.ESCALATED,
            "tool.failed": TuiState.FAILED,
        }.get(event_type, TuiState.UNKNOWN)
        return TuiEventView(
            sequence=event.session_sequence or 0,
            event_type=event_type,
            kind=TuiEventKind.TOOL,
            state=state,
            title=_clean_text(payload.get("tool_id")) or "Tool",
            text=_clean_text(payload.get("status")),
            validation=None,
            receipt=_receipt(event, payload),
            provider_id=event.provider_id,
            model_id=event.model_id,
        )
    if event_type == "model.turn.completed":
        validation = TuiValidationView(
            task_id=_clean_text(payload.get("task_id")),
            outcome=_clean_text(payload.get("outcome")),
            state=TuiState.COMPLETED,
        )
        return _view(event, TuiEventKind.COMPLETION, TuiState.COMPLETED, "Validated result", validation.outcome, validation)
    if event_type in {"model.turn.incomplete", "model.turn.refused"}:
        validation = TuiValidationView(
            task_id=_clean_text(payload.get("task_id")),
            outcome=_clean_text(payload.get("outcome")),
            state=TuiState.FAILED,
        )
        return _view(event, TuiEventKind.VALIDATION, TuiState.FAILED, event_type.replace(".", " "), validation.outcome, validation)
    if event_type == "model.error":
        return _view(event, TuiEventKind.FAILURE, TuiState.FAILED, "Runtime error", _clean_text(payload.get("error_message")))
    if event_type in {"model.cancelled", "turn.cancelled"}:
        return _view(event, TuiEventKind.CONTROL, TuiState.CANCELLED, "Cancelled", None)
    if event_type in {"turn.interrupt.requested", "turn.steering.received", "turn.steer.requested"}:
        return _view(event, TuiEventKind.CONTROL, TuiState.ACTIVE, "Control", _clean_text(payload.get("text")))
    if event_type.startswith("runtime.provider."):
        state = TuiState.FAILED if event_type.endswith((".failed", ".error")) else TuiState.ACTIVE
        return _view(event, TuiEventKind.PROVIDER, state, event_type.replace(".", " "), _clean_text(payload.get("message")))
    return _view(event, TuiEventKind.UNKNOWN, TuiState.UNKNOWN, event_type, None)


def project_tui_events(events: Sequence[OperationalEvent]) -> tuple[TuiEventView, ...]:
    return tuple(project_tui_event(event) for event in events)


def _view(
    event: OperationalEvent,
    kind: TuiEventKind,
    state: TuiState,
    title: str,
    text: str | None,
    validation: TuiValidationView | None = None,
) -> TuiEventView:
    return TuiEventView(
        sequence=event.session_sequence or 0,
        event_type=event.event_type,
        kind=kind,
        state=state,
        title=title,
        text=text,
        validation=validation,
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
    output = dict(output_value) if isinstance(output_value, Mapping) else None
    authorization_value = payload.get("authorization")
    authorization = None
    if isinstance(authorization_value, Mapping):
        verdict = _clean_text(authorization_value.get("verdict"))
        if verdict is not None:
            authorization = TuiAuthorizationView(
                verdict=verdict,
                rationale=_clean_text(authorization_value.get("rationale")),
            )
    diff_value = payload.get("diff")
    if diff_value is None and output is not None:
        diff_value = output.get("diff")
    diff_payload = dict(diff_value) if isinstance(diff_value, Mapping) else None
    diff_summary = _clean_text(diff_payload.get("summary")) if diff_payload is not None else None
    return TuiReceiptView(
        receipt_id=_clean_text(payload.get("receipt_id")) or event.tool_receipt_id,
        operation_id=event.runtime_operation_id,
        tool_id=_clean_text(payload.get("tool_id")),
        authorization=authorization,
        evidence=TuiEvidenceView(count=len(evidence_items), items=evidence_items),
        diff=TuiDiffView(available=diff_payload is not None, summary=diff_summary, payload=diff_payload),
        output=output,
        error_code=_clean_text(payload.get("error_code")),
        error_message=_clean_text(payload.get("error_message")),
    )


def _clean_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
