from __future__ import annotations

from pathlib import Path

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadiness,
    ClineSidecarReadinessStatus,
)
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory, TurnStatus
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.professional_history_runtime import (
    execute_persisted_governed_professional_turn,
    replay_turn_status,
)
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


class _ToolAdapter:
    def __init__(self) -> None:
        self.continuations = []

    def stream_turn(self, request):
        return (
            _event(ModelEventType.TURN_STARTED, provider_request_id="response-1"),
            _event(
                ModelEventType.TOOL_CALL_COMPLETED,
                provider_request_id="response-1",
                provider_item_id="item-native-1",
                provider_tool_call_id="provider-call-1",
                lbe_call_id="lbe-call-1",
                tool_name="workspace.read",
                tool_arguments={"path": "README.md"},
            ),
            _event(
                ModelEventType.TURN_REQUIRES_TOOL,
                provider_request_id="response-1",
                provider_tool_call_id="provider-call-1",
                lbe_call_id="lbe-call-1",
                tool_name="workspace.read",
            ),
        )

    def continue_with_tool_result(self, request, result):
        self.continuations.append(result)
        return (
            _event(ModelEventType.TURN_STARTED, provider_request_id="response-2"),
            _event(ModelEventType.MESSAGE_DELTA, provider_request_id="response-2", text="done"),
            _event(ModelEventType.TURN_COMPLETED, provider_request_id="response-2"),
        )

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


def _request() -> ProviderTurnRequest:
    return ProviderTurnRequest(
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=FAMILY,
        system_prompt="Use governed tools.",
        messages=({"role": "user", "content": "read README"},),
        tool_definitions=(
            ProviderToolDefinition(
                name="workspace.read",
                description="Read workspace file",
                input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            ),
        ),
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


def _context(tmp_path: Path, *, capabilities=("inspect",)) -> ToolExecutionContext:
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode="coding",
            allowed_behaviors=("development_mode_capabilities",),
            capabilities=tuple(capabilities),
            rationale="test",
        ),
        workspace_id="workspace-1",
        workspace_root=tmp_path,
        configured_root_id="dev",
    )


def _orchestrator(handler) -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), handler)
    return GovernedToolOrchestrator(registry=registry)


def test_persists_model_tool_and_continuation_events_in_runtime_order(tmp_path: Path) -> None:
    history = _history(tmp_path)
    adapter = _ToolAdapter()
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(
            lambda request: ToolExecutionResult(
                output={"content": "hello"},
                evidence=({"path": "README.md"},),
            )
        ),
        tool_context=_context(tmp_path),
        operation_id_factory=lambda: "runtime-op-1",
    )

    assert result.operational_turn.status is TurnStatus.COMPLETED
    assert result.replayed_status is TurnStatus.COMPLETED
    events = history.events_for_turn(turn_id=result.operational_turn.turn_id)
    assert [event.event_type for event in events] == [
        "model.turn.started",
        "model.tool_call.completed",
        "model.turn.requires_tool",
        "tool.started",
        "tool.completed",
        "model.turn.started",
        "model.message.delta",
        "model.turn.completed",
    ]
    assert [event.turn_sequence for event in events] == list(range(1, 9))
    assert [event.session_sequence for event in events] == list(range(1, 9))

    tool_completed = events[4]
    assert tool_completed.provider_tool_call_id == "provider-call-1"
    assert tool_completed.lbe_call_id == "lbe-call-1"
    assert tool_completed.runtime_operation_id == "runtime-op-1"
    assert tool_completed.tool_receipt_id == result.runtime_result.tool_receipts[0].receipt_id
    assert len({
        tool_completed.provider_tool_call_id,
        tool_completed.lbe_call_id,
        tool_completed.runtime_operation_id,
        tool_completed.tool_receipt_id,
    }) == 4


def test_replay_reconstructs_finalized_turn_without_reading_turn_status(tmp_path: Path) -> None:
    history = _history(tmp_path)
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(_ToolAdapter()),
        request=_request(),
        orchestrator=_orchestrator(lambda request: ToolExecutionResult(output={"content": "ok"})),
        tool_context=_context(tmp_path),
        operation_id_factory=lambda: "runtime-op-replay",
    )

    assert replay_turn_status(history=history, turn_id=result.operational_turn.turn_id) is TurnStatus.COMPLETED
    assert history.get_turn(turn_id=result.operational_turn.turn_id).status is TurnStatus.COMPLETED


def test_escalation_persists_blocker_and_replays_escalated_without_provider_continuation(tmp_path: Path) -> None:
    history = _history(tmp_path)
    adapter = _ToolAdapter()
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(lambda request: ToolExecutionResult(output={})),
        tool_context=_context(tmp_path, capabilities=("search",)),
        operation_id_factory=lambda: "runtime-op-escalated",
    )

    assert adapter.continuations == []
    assert result.runtime_result.blocked_receipt is not None
    assert result.operational_turn.status is TurnStatus.ESCALATED
    assert result.replayed_status is TurnStatus.ESCALATED
    events = history.events_for_turn(turn_id=result.operational_turn.turn_id)
    assert events[-1].event_type == "tool.escalated"
    assert events[-1].tool_receipt_id == result.runtime_result.blocked_receipt.receipt_id


def test_multiple_operational_turns_keep_session_sequence_monotonic(tmp_path: Path) -> None:
    history = _history(tmp_path)
    for index in (1, 2):
        execute_persisted_governed_professional_turn(
            history=history,
            session_provider=_provider(_ToolAdapter()),
            request=_request(),
            orchestrator=_orchestrator(lambda request: ToolExecutionResult(output={"content": "ok"})),
            tool_context=_context(tmp_path),
            operation_id_factory=lambda index=index: f"runtime-op-{index}",
        )

    events = history.events_for_session(session_id="session-1")
    assert [event.session_sequence for event in events] == list(range(1, len(events) + 1))
    assert len({event.turn_id for event in events}) == 2
