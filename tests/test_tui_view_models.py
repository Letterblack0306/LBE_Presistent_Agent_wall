from pathlib import Path

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import OperationalEvent
from lbe_guard_inspector.provider_registry import ProviderCapabilities, ProviderDescriptor
from lbe_guard_inspector.runtime.tool_orchestration import (
    ToolAccessClass,
    ToolNetworkBehavior,
    ToolRiskClass,
    ToolSpec,
)
from lbe_guard_inspector.tui_view_models import (
    TuiEventKind,
    TuiState,
    project_tui_capabilities,
    project_tui_event,
    project_tui_provider,
    project_tui_session,
)


def test_session_projection_reuses_persisted_session_owner(tmp_path: Path) -> None:
    state = SessionState(
        "session-1", "workspace-1", tmp_path, "coding",
        "write_allowed", "development", "openai-compatible", "model-1", "profile-1",
    )
    view = project_tui_session(state, active_turn=True)
    assert view.session_id == "session-1"
    assert view.workspace_root == state.canonical_workspace_root
    assert view.provider_id == "openai-compatible"
    assert view.model_id == "model-1"
    assert view.active_turn is True


def test_provider_projection_reuses_descriptor_capabilities() -> None:
    descriptor = ProviderDescriptor(
        "local",
        "model-1",
        ProviderCapabilities(streaming=True, tool_calls=True, structured_output=False, context_limit=8192),
    )
    view = project_tui_provider(descriptor, selected=True, health=TuiState.AVAILABLE)
    assert (view.provider_id, view.model_id, view.selected, view.health) == (
        "local", "model-1", True, TuiState.AVAILABLE,
    )
    assert (view.streaming, view.tool_calls, view.structured_output, view.context_limit) == (
        True, True, False, 8192,
    )


def test_capability_projection_reuses_registered_tool_specs() -> None:
    spec = ToolSpec(
        tool_id="workspace.write",
        capability="write",
        required_arguments=("path",),
        access_class=ToolAccessClass.WRITE,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.HIGH,
    )
    views = project_tui_capabilities((spec,))
    assert len(views) == 1
    assert (views[0].tool_id, views[0].capability, views[0].available) == (
        "workspace.write", "write", True,
    )
    assert (views[0].access_class, views[0].network_behavior, views[0].risk_class) == (
        "write", "none", "high",
    )


def test_tool_view_preserves_authorization_receipt_evidence_and_diff() -> None:
    event = OperationalEvent(
        session_id="s",
        turn_id="t",
        event_type="tool.completed",
        payload={
            "tool_id": "workspace.create_candidate_text",
            "status": "executed",
            "receipt_id": "receipt-1",
            "authorization": {"verdict": "ALLOW", "rationale": "Capability is delegated."},
            "output": {"path": "note.txt", "diff": {"summary": "1 file changed", "files": ["note.txt"]}},
            "evidence": [{"kind": "write"}],
        },
        runtime_operation_id="operation-1",
        tool_receipt_id="receipt-1",
        session_sequence=3,
    )
    view = project_tui_event(event)
    assert view.kind is TuiEventKind.TOOL
    assert view.state is TuiState.COMPLETED
    assert view.receipt is not None
    assert view.receipt.receipt_id == "receipt-1"
    assert view.receipt.operation_id == "operation-1"
    assert view.receipt.authorization is not None
    assert view.receipt.authorization.verdict == "ALLOW"
    assert view.receipt.evidence.count == 1
    assert view.receipt.diff.available is True
    assert view.receipt.diff.summary == "1 file changed"


def test_missing_tool_facts_remain_unknown_or_absent() -> None:
    view = project_tui_event(OperationalEvent(
        session_id="s", turn_id="t", event_type="tool.requested",
        payload={"tool_id": "workspace.read"},
    ))
    assert view.kind is TuiEventKind.TOOL
    assert view.state is TuiState.UNKNOWN
    assert view.receipt is not None
    assert view.receipt.authorization is None
    assert view.receipt.receipt_id is None
    assert view.receipt.evidence.count == 0
    assert view.receipt.diff.available is False
    assert view.receipt.output is None


def test_completion_and_validation_are_typed_from_persisted_events() -> None:
    completed = project_tui_event(OperationalEvent(
        session_id="s", turn_id="t", event_type="model.turn.completed",
        payload={"task_id": "task-1", "outcome": "COMPLETED"},
    ))
    incomplete = project_tui_event(OperationalEvent(
        session_id="s", turn_id="t", event_type="model.turn.incomplete",
        payload={"task_id": "task-2", "outcome": "MISSING_EVIDENCE"},
    ))
    assert (completed.kind, completed.state) == (TuiEventKind.COMPLETION, TuiState.COMPLETED)
    assert completed.validation is not None
    assert completed.validation.task_id == "task-1"
    assert (incomplete.kind, incomplete.state) == (TuiEventKind.VALIDATION, TuiState.FAILED)


def test_failure_cancel_provider_and_unknown_states_stay_truthful() -> None:
    failed = project_tui_event(OperationalEvent(
        session_id="s", turn_id="t", event_type="model.error",
        payload={"error_message": "provider unavailable"},
    ))
    cancelled = project_tui_event(OperationalEvent(
        session_id="s", turn_id="t", event_type="turn.cancelled", payload={},
    ))
    provider = project_tui_event(OperationalEvent(
        session_id="s", turn_id="t", event_type="runtime.provider.started",
        payload={"message": "connecting"}, provider_id="local", model_id="m",
    ))
    unknown = project_tui_event(OperationalEvent(
        session_id="s", turn_id="t", event_type="future.event",
        payload={"outcome": "COMPLETED"},
    ))
    assert (failed.kind, failed.state) == (TuiEventKind.FAILURE, TuiState.FAILED)
    assert (cancelled.kind, cancelled.state) == (TuiEventKind.CONTROL, TuiState.CANCELLED)
    assert (provider.kind, provider.state, provider.provider_id) == (
        TuiEventKind.PROVIDER, TuiState.ACTIVE, "local",
    )
    assert (unknown.kind, unknown.state) == (TuiEventKind.UNKNOWN, TuiState.UNKNOWN)


def test_failed_tool_keeps_structured_error() -> None:
    view = project_tui_event(OperationalEvent(
        session_id="s", turn_id="t", event_type="tool.failed",
        payload={
            "tool_id": "workspace.write",
            "error_code": "WRITE_FAILED",
            "error_message": "disk unavailable",
        },
    ))
    assert view.state is TuiState.FAILED
    assert view.receipt is not None
    assert view.receipt.error_code == "WRITE_FAILED"
    assert view.receipt.error_message == "disk unavailable"
