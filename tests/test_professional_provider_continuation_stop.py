from __future__ import annotations

from pathlib import Path

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadiness,
    ClineSidecarReadinessStatus,
)
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory, TurnStatus
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.professional_continuation_runtime import (
    ProfessionalLoopStopReason,
    execute_governed_professional_turn,
)
from lbe_guard_inspector.professional_history_runtime import (
    execute_persisted_governed_professional_turn,
)
from lbe_guard_inspector.professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderTurnRequest,
)
from lbe_guard_inspector.professional_provider_resolver import ProfessionalProviderResolution
from lbe_guard_inspector.professional_session_provider import ProfessionalSessionProvider
from lbe_guard_inspector.provider_capabilities import ProviderModelCapabilities, ProviderProtocolFamily
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolRegistry,
)


FAMILY = ProviderProtocolFamily.ANTHROPIC_MESSAGES


class _ProviderContinuationAdapter:
    def stream_turn(self, request):
        return (
            _event(ModelEventType.TURN_STARTED, provider_request_id="msg-1"),
            _event(
                ModelEventType.TURN_REQUIRES_CONTINUATION,
                provider_request_id="msg-1",
                metadata={
                    "provider_stop_reason": "pause_turn",
                    "provider_state_metadata_ref": "provider-state-1",
                },
            ),
        )

    def continue_with_tool_result(self, request, result):
        raise AssertionError("provider continuation stop must not be serialized as a tool result")

    def cancel(self):
        return None


def _event(event_type, **kwargs):
    return NormalizedModelEvent(
        event_type=event_type,
        provider_id="anthropic",
        model_id="model-a",
        protocol_family=FAMILY,
        **kwargs,
    )


def _request() -> ProviderTurnRequest:
    return ProviderTurnRequest(
        provider_id="anthropic",
        model_id="model-a",
        protocol_family=FAMILY,
        system_prompt="Continue provider-side work truthfully.",
        messages=({"role": "user", "content": "continue"},),
    )


def _provider() -> ProfessionalSessionProvider:
    capabilities = ProviderModelCapabilities(
        provider_id="anthropic",
        model_id="model-a",
        endpoint="https://api.anthropic.com/v1/messages",
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
        provider_id="anthropic",
        model_id="model-a",
        resolution=ProfessionalProviderResolution(
            backend_id="test",
            adapter=_ProviderContinuationAdapter(),
            readiness=readiness,
            capabilities=capabilities,
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


def _orchestrator() -> GovernedToolOrchestrator:
    return GovernedToolOrchestrator(registry=ToolRegistry())


def _history(tmp_path: Path) -> SessionOperationalHistory:
    store = WorkspaceMemoryStore(tmp_path / "memory.sqlite3")
    store.save_session_state(SessionState(
        session_id="session-1",
        project_workspace_id="workspace-1",
        canonical_workspace_root=tmp_path,
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
        provider_id="anthropic",
        provider_model="model-a",
    ))
    return SessionOperationalHistory(store=store)


def test_provider_continuation_required_is_not_reported_as_completion(tmp_path: Path) -> None:
    result = execute_governed_professional_turn(
        session_provider=_provider(),
        request=_request(),
        orchestrator=_orchestrator(),
        tool_context=_context(tmp_path),
    )

    assert result.tool_receipts == ()
    assert result.blocked_receipt is None
    assert result.stop_reason is ProfessionalLoopStopReason.PROVIDER_CONTINUATION_REQUIRED
    assert result.completed_without_blocker is False
    assert result.final_turn.terminal_event.event_type is ModelEventType.TURN_REQUIRES_CONTINUATION


def test_provider_continuation_required_is_persisted_without_tool_result_fabrication(tmp_path: Path) -> None:
    history = _history(tmp_path)
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(),
        request=_request(),
        orchestrator=_orchestrator(),
        tool_context=_context(tmp_path),
    )

    assert result.runtime_result.stop_reason is ProfessionalLoopStopReason.PROVIDER_CONTINUATION_REQUIRED
    assert result.operational_turn.status is TurnStatus.INCOMPLETE
    assert result.replayed_status is TurnStatus.INCOMPLETE
    events = history.events_for_turn(turn_id=result.operational_turn.turn_id)
    terminal = events[-1]
    assert terminal.event_type == ModelEventType.TURN_REQUIRES_CONTINUATION.value
    assert terminal.provider_state_metadata_ref == "provider-state-1"
    assert terminal.payload["metadata"]["provider_stop_reason"] == "pause_turn"
    assert not any(item.event_type.startswith("tool.") for item in events)
