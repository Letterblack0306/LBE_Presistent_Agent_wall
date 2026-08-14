from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadiness,
    ClineSidecarReadinessStatus,
)
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory, TurnStatus
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.professional_continuation_runtime import (
    ProfessionalLoopStopReason,
    ProfessionalUnsupportedCapabilityError,
    execute_governed_professional_turn,
)
from lbe_guard_inspector.professional_history_runtime import execute_persisted_governed_professional_turn
from lbe_guard_inspector.professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderToolDefinition,
    ProviderTurnRequest,
)
from lbe_guard_inspector.professional_provider_resolver import ProfessionalProviderResolution
from lbe_guard_inspector.professional_session_provider import ProfessionalSessionProvider
from lbe_guard_inspector.provider_capabilities import ProviderModelCapabilities, ProviderProtocolFamily
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolRegistry,
    workspace_read_spec,
)


FAMILY = ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT


class _Adapter:
    def __init__(self, events) -> None:
        self.events = tuple(events)
        self.stream_called = False

    def stream_turn(self, request):
        self.stream_called = True
        return self.events

    def continue_with_tool_result(self, request, result):
        raise AssertionError("continuation must not run in stop-boundary tests")

    def cancel(self):
        return None


def _event(event_type, **kwargs):
    return NormalizedModelEvent(
        event_type=event_type,
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=FAMILY,
        **kwargs,
    )


def _provider(adapter) -> ProfessionalSessionProvider:
    capabilities = ProviderModelCapabilities(
        provider_id="openai-compatible",
        model_id="model-a",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        protocol_family=FAMILY,
        protocol_evidence="test",
    )
    readiness = ClineSidecarReadiness(
        status=ClineSidecarReadinessStatus.READY,
        node_version="v24.15.0",
        bridge_path="C:/bridge/bridge.mjs",
        package_manifest_path="C:/bridge/package.json",
        cline_package_version="0.0.73",
        reason="ready",
    )
    return ProfessionalSessionProvider(
        session_id="session-1",
        provider_id="openai-compatible",
        model_id="model-a",
        resolution=ProfessionalProviderResolution(
            backend_id="test",
            adapter=adapter,
            readiness=readiness,
            capabilities=capabilities,
        ),
    )


def _request(*tool_names: str) -> ProviderTurnRequest:
    return ProviderTurnRequest(
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=FAMILY,
        system_prompt="Use only projected tools.",
        messages=({"role": "user", "content": "work"},),
        tool_definitions=tuple(
            ProviderToolDefinition(
                name=name,
                description=f"Projected {name}",
                input_schema={"type": "object", "properties": {}},
            )
            for name in tool_names
        ),
    )


def _context(tmp_path: Path) -> ToolExecutionContext:
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode="coding",
            allowed_behaviors=("development_mode_capabilities",),
            capabilities=("inspect",),
            rationale="test",
        ),
        workspace_id="workspace-1",
        workspace_root=tmp_path,
        configured_root_id="dev",
    )


def _orchestrator(*, handler=None) -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    if handler is not None:
        registry.register(workspace_read_spec(), handler)
    return GovernedToolOrchestrator(registry=registry)


def _history(tmp_path: Path) -> SessionOperationalHistory:
    store = WorkspaceMemoryStore(tmp_path / "memory.sqlite3")
    store.save_session_state(SessionState(
        session_id="session-1",
        project_workspace_id="workspace-1",
        canonical_workspace_root=tmp_path,
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
        provider_id="openai-compatible",
        provider_model="model-a",
    ))
    return SessionOperationalHistory(store=store)


def _unsupported_adapter() -> _Adapter:
    return _Adapter((
        _event(ModelEventType.TURN_STARTED),
        _event(
            ModelEventType.TOOL_CALL_COMPLETED,
            provider_tool_call_id="provider-hidden-1",
            lbe_call_id="lbe-hidden-1",
            tool_name="hidden.tool",
            tool_arguments={},
        ),
        _event(
            ModelEventType.TURN_REQUIRES_TOOL,
            provider_tool_call_id="provider-hidden-1",
            lbe_call_id="lbe-hidden-1",
            tool_name="hidden.tool",
        ),
    ))


def test_unbacked_provider_projection_fails_before_provider_execution(tmp_path: Path) -> None:
    adapter = _Adapter((_event(ModelEventType.TURN_STARTED), _event(ModelEventType.TURN_COMPLETED)))

    with pytest.raises(ProfessionalUnsupportedCapabilityError) as raised:
        execute_governed_professional_turn(
            session_provider=_provider(adapter),
            request=_request("missing.tool"),
            orchestrator=_orchestrator(),
            tool_context=_context(tmp_path),
        )

    assert raised.value.capability_id == "missing.tool"
    assert adapter.stream_called is False


def test_provider_cannot_execute_tool_outside_effective_projection(tmp_path: Path) -> None:
    calls = []
    result = execute_governed_professional_turn(
        session_provider=_provider(_unsupported_adapter()),
        request=_request("workspace.read"),
        orchestrator=_orchestrator(
            handler=lambda request: calls.append(request) or ToolExecutionResult(output={"unexpected": True})
        ),
        tool_context=_context(tmp_path),
    )

    assert calls == []
    assert result.tool_receipts == ()
    assert result.unsupported_capability == "hidden.tool"
    assert result.stop_reason is ProfessionalLoopStopReason.UNSUPPORTED_CAPABILITY
    assert result.completed_without_blocker is False


def test_unprojected_tool_stop_is_persisted_without_fabricated_tool_receipt(tmp_path: Path) -> None:
    history = _history(tmp_path)
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(_unsupported_adapter()),
        request=_request("workspace.read"),
        orchestrator=_orchestrator(handler=lambda request: ToolExecutionResult(output={})),
        tool_context=_context(tmp_path),
    )

    assert result.operational_turn.status is TurnStatus.INCOMPLETE
    assert result.replayed_status is TurnStatus.INCOMPLETE
    events = history.events_for_turn(turn_id=result.operational_turn.turn_id)
    assert events[-1].event_type == "runtime.unsupported_capability"
    assert events[-1].payload["capability_id"] == "hidden.tool"
    assert not any(item.event_type.startswith("tool.") for item in events)


def test_preflight_unsupported_projection_closes_started_history_turn(tmp_path: Path) -> None:
    history = _history(tmp_path)
    adapter = _Adapter((_event(ModelEventType.TURN_STARTED), _event(ModelEventType.TURN_COMPLETED)))

    with pytest.raises(ProfessionalUnsupportedCapabilityError):
        execute_persisted_governed_professional_turn(
            history=history,
            session_provider=_provider(adapter),
            request=_request("missing.tool"),
            orchestrator=_orchestrator(),
            tool_context=_context(tmp_path),
        )

    assert adapter.stream_called is False
    events = history.events_for_session(session_id="session-1")
    assert len(events) == 1
    assert events[0].event_type == "runtime.unsupported_capability"
    assert events[0].payload["phase"] == "provider_projection_preflight"


@pytest.mark.parametrize("error_code", ["CREDENTIAL_REQUIRED", "MANUAL_ACTION_REQUIRED"])
def test_provider_manual_blocker_is_distinct_from_generic_error(tmp_path: Path, error_code: str) -> None:
    adapter = _Adapter((
        _event(ModelEventType.TURN_STARTED),
        _event(ModelEventType.ERROR, error_code=error_code, text="human dependency"),
    ))
    result = execute_governed_professional_turn(
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(),
        tool_context=_context(tmp_path),
    )

    assert result.stop_reason is ProfessionalLoopStopReason.CREDENTIAL_MANUAL_BLOCKER
    assert result.completed_without_blocker is False


def test_manual_blocker_persists_as_incomplete_not_failed(tmp_path: Path) -> None:
    history = _history(tmp_path)
    adapter = _Adapter((
        _event(ModelEventType.TURN_STARTED),
        _event(ModelEventType.ERROR, error_code="CREDENTIAL_REQUIRED", text="login required"),
    ))
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(),
        tool_context=_context(tmp_path),
    )

    assert result.runtime_result.stop_reason is ProfessionalLoopStopReason.CREDENTIAL_MANUAL_BLOCKER
    assert result.operational_turn.status is TurnStatus.INCOMPLETE
    assert result.replayed_status is TurnStatus.INCOMPLETE


def test_ordinary_provider_error_remains_failed(tmp_path: Path) -> None:
    history = _history(tmp_path)
    adapter = _Adapter((
        _event(ModelEventType.TURN_STARTED),
        _event(ModelEventType.ERROR, error_code="PROVIDER_FAILURE", text="boom"),
    ))
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(),
        tool_context=_context(tmp_path),
    )

    assert result.runtime_result.stop_reason is ProfessionalLoopStopReason.ERROR
    assert result.operational_turn.status is TurnStatus.FAILED
    assert result.replayed_status is TurnStatus.FAILED
