from __future__ import annotations

import sys
from pathlib import Path

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadiness,
    ClineSidecarReadinessStatus,
)
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory, TurnStatus
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
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
from lbe_guard_inspector.runtime.professional_command_events import register_live_terminal_exec_backend
from lbe_guard_inspector.runtime.professional_terminal_backend import (
    TerminalCommandPolicy,
    TerminalCommandPolicyCatalog,
)
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolRegistry,
)


FAMILY = ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT


class _TerminalAdapter:
    def __init__(self) -> None:
        self.continuations = []

    def stream_turn(self, request):
        return (
            _event(ModelEventType.TURN_STARTED, provider_request_id="response-1"),
            _event(
                ModelEventType.TOOL_CALL_COMPLETED,
                provider_request_id="response-1",
                provider_item_id="item-terminal-1",
                provider_tool_call_id="provider-call-terminal-1",
                lbe_call_id="lbe-call-terminal-1",
                tool_name="terminal.exec",
                tool_arguments={"command_id": "test.echo"},
            ),
            _event(
                ModelEventType.TURN_REQUIRES_TOOL,
                provider_request_id="response-1",
                provider_tool_call_id="provider-call-terminal-1",
                lbe_call_id="lbe-call-terminal-1",
                tool_name="terminal.exec",
            ),
        )

    def continue_with_tool_result(self, request, result):
        self.continuations.append(result)
        return (
            _event(ModelEventType.TURN_STARTED, provider_request_id="response-2"),
            _event(ModelEventType.MESSAGE_DELTA, provider_request_id="response-2", text="validated"),
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


def _request() -> ProviderTurnRequest:
    return ProviderTurnRequest(
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=FAMILY,
        system_prompt="Use governed tools.",
        messages=({"role": "user", "content": "run validation"},),
        tool_definitions=(
            ProviderToolDefinition(
                name="terminal.exec",
                description="Run one host-registered command",
                input_schema={"type": "object", "properties": {"command_id": {"type": "string"}}},
            ),
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


def _context(tmp_path: Path) -> ToolExecutionContext:
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode="coding",
            allowed_behaviors=("development_mode_capabilities",),
            capabilities=("test_candidate",),
            rationale="test",
        ),
        workspace_id="workspace-1",
        workspace_root=tmp_path,
        configured_root_id="dev",
    )


def _orchestrator() -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    catalog = TerminalCommandPolicyCatalog((
        TerminalCommandPolicy(
            command_id="test.echo",
            argv=(sys.executable, "-c", "import sys; print('hello-live'); print('warn-live', file=sys.stderr)"),
            timeout_seconds=10.0,
        ),
    ))
    register_live_terminal_exec_backend(registry=registry, catalog=catalog)
    return GovernedToolOrchestrator(registry=registry)


def test_live_command_events_persist_inside_governed_tool_item(tmp_path: Path) -> None:
    history = _history(tmp_path)
    adapter = _TerminalAdapter()
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(),
        tool_context=_context(tmp_path),
        operation_id_factory=lambda: "runtime-op-terminal-1",
    )

    assert result.operational_turn.status is TurnStatus.COMPLETED
    receipt = result.runtime_result.tool_receipts[0]
    assert receipt.output is not None
    assert receipt.output["exit_code"] == 0
    assert "hello-live" in receipt.output["stdout"]
    assert "warn-live" in receipt.output["stderr"]

    events = history.events_for_turn(turn_id=result.operational_turn.turn_id)
    event_types = [item.event_type for item in events]
    assert event_types[:4] == [
        "model.turn.started",
        "model.tool_call.completed",
        "model.turn.requires_tool",
        "tool.started",
    ]
    assert "command.started" in event_types
    assert "command.stdout.delta" in event_types
    assert "command.stderr.delta" in event_types
    assert "command.completed" in event_types
    assert event_types.index("command.started") < event_types.index("command.completed") < event_types.index("tool.completed")
    assert event_types[-3:] == ["model.turn.started", "model.message.delta", "model.turn.completed"]

    command_events = [item for item in events if item.event_type.startswith("command.")]
    assert command_events
    assert {item.runtime_operation_id for item in command_events} == {"runtime-op-terminal-1"}
    assert {item.lbe_call_id for item in command_events} == {"lbe-call-terminal-1"}
    assert {item.provider_tool_call_id for item in command_events} == {"provider-call-terminal-1"}

    tool_terminal = next(item for item in events if item.event_type == "tool.completed")
    assert tool_terminal.runtime_operation_id == "runtime-op-terminal-1"
    assert tool_terminal.tool_receipt_id == receipt.receipt_id
    assert len({
        tool_terminal.provider_tool_call_id,
        tool_terminal.lbe_call_id,
        tool_terminal.runtime_operation_id,
        tool_terminal.tool_receipt_id,
    }) == 4

    tool_items = history.items_for_turn(turn_id=result.operational_turn.turn_id)
    tool_item = next(item for item in tool_items if item.kind == "tool.execution")
    assert all(item.item_id == tool_item.item_id for item in events if item.event_type.startswith("command.") or item.event_type.startswith("tool."))


def test_live_command_receipt_continues_provider_with_distinct_receipt_identity(tmp_path: Path) -> None:
    history = _history(tmp_path)
    adapter = _TerminalAdapter()
    result = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(),
        tool_context=_context(tmp_path),
        operation_id_factory=lambda: "runtime-op-terminal-2",
    )

    assert len(adapter.continuations) == 1
    continuation = adapter.continuations[0]
    receipt = result.runtime_result.tool_receipts[0]
    assert continuation.runtime_operation_id == "runtime-op-terminal-2"
    assert continuation.tool_receipt_id == receipt.receipt_id
    assert continuation.lbe_call_id == "lbe-call-terminal-1"
    assert continuation.provider_tool_call_id == "provider-call-terminal-1"
