from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.cline_sidecar_readiness import ClineSidecarReadiness, ClineSidecarReadinessStatus
from lbe_guard_inspector.memory import TaskStatus
from lbe_guard_inspector.memory.completion_evidence import TaskCompletionEvidencePersistence
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory
from lbe_guard_inspector.professional_completion_runtime import (
    ProfessionalCompletionRuntimeError,
    execute_completion_gated_persisted_professional_turn,
)
from lbe_guard_inspector.professional_provider_events import ModelEventType, NormalizedModelEvent, ProviderTurnRequest
from lbe_guard_inspector.professional_provider_resolver import ProfessionalProviderResolution
from lbe_guard_inspector.professional_session_provider import ProfessionalSessionProvider
from lbe_guard_inspector.provider_capabilities import ProviderModelCapabilities, ProviderProtocolFamily
from lbe_guard_inspector.runtime.completion_gate import CompletionRequirement, CompletionVerdict, TaskCompletionContract
from lbe_guard_inspector.runtime.completion_runtime import CodingCompletionRuntime
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import GovernedToolOrchestrator, ToolExecutionContext, ToolRegistry
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


FAMILY = ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT


class _TerminalAdapter:
    def __init__(self, terminal: ModelEventType = ModelEventType.TURN_COMPLETED) -> None:
        self.terminal = terminal
        self.calls = 0

    def stream_turn(self, request):
        self.calls += 1
        return (
            _event(ModelEventType.TURN_STARTED),
            _event(ModelEventType.MESSAGE_DELTA, text="candidate result"),
            _event(self.terminal),
        )

    def continue_with_tool_result(self, request, result):
        raise AssertionError("no tool continuation expected")

    def cancel(self):
        return None


def _event(event_type: ModelEventType, **kwargs) -> NormalizedModelEvent:
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
        system_prompt="Complete the governed task.",
        messages=({"role": "user", "content": "finish task"},),
    )


def _provider(adapter) -> ProfessionalSessionProvider:
    return ProfessionalSessionProvider(
        session_id="session-1",
        provider_id="openai-compatible",
        model_id="model-a",
        resolution=ProfessionalProviderResolution(
            backend_id="test",
            adapter=adapter,
            readiness=ClineSidecarReadiness(
                status=ClineSidecarReadinessStatus.READY,
                node_version="v24.15.0",
                bridge_path="C:/bridge/bridge.mjs",
                package_manifest_path="C:/bridge/package.json",
                cline_package_version="0.0.73",
                reason="ready",
            ),
            capabilities=ProviderModelCapabilities(
                provider_id="openai-compatible",
                model_id="model-a",
                endpoint="http://127.0.0.1:1234/v1/chat/completions",
                protocol_family=FAMILY,
                protocol_evidence="test",
            ),
        ),
    )


def _runtime(tmp_path: Path) -> SessionMemoryRuntimeBridge:
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite3",
        project_workspace_id="workspace-1",
        workspace_root=tmp_path,
        session_id="session-1",
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
        provider_id="openai-compatible",
        provider_model="model-a",
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


def _contract() -> TaskCompletionContract:
    return TaskCompletionContract(
        requirements=(CompletionRequirement("focused-tests", "focused_test"),)
    )


def _persist_evidence(runtime: SessionMemoryRuntimeBridge, *, status: str) -> None:
    TaskCompletionEvidencePersistence(runtime.store).save(
        session_id=runtime.session_id,
        task_id="task-1",
        project_workspace_id=runtime.project_workspace_id,
        canonical_workspace_root=str(runtime.workspace_root),
        evidence_id=f"ev-focused-{status.lower()}",
        kind="focused_test",
        status=status,
        source="test-producer",
        producer_id="test.producer.v1",
        operation_id="reasoning.inspect",
        details={"proof": status},
    )


def _execute(tmp_path: Path, *, evidence_status: str | None = None, terminal=ModelEventType.TURN_COMPLETED):
    runtime = _runtime(tmp_path)
    completion = CodingCompletionRuntime(runtime=runtime)
    completion.persist_contract(task_id="task-1", contract=_contract())
    runtime.record_task_status(task_id="task-1", status=TaskStatus.RUNNING)
    if evidence_status is not None:
        _persist_evidence(runtime, status=evidence_status)
    adapter = _TerminalAdapter(terminal)
    result = execute_completion_gated_persisted_professional_turn(
        history=SessionOperationalHistory(store=runtime.store),
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=GovernedToolOrchestrator(registry=ToolRegistry()),
        tool_context=_context(tmp_path),
        completion_runtime=completion,
        task_id="task-1",
    )
    return runtime, adapter, result


def test_model_completed_without_required_evidence_is_blocked(tmp_path: Path) -> None:
    runtime, adapter, result = _execute(tmp_path)

    assert adapter.calls == 1
    assert result.completion_decision is not None
    assert result.completion_decision.verdict is CompletionVerdict.BLOCKED
    assert result.validated_complete is False
    assert result.task_state is not None
    assert result.task_state.status is TaskStatus.BLOCKED
    assert runtime.load_task_status(task_id="task-1").last_outcome == "VALIDATION_INCOMPLETE"


def test_model_completed_with_passing_persisted_evidence_promotes_task(tmp_path: Path) -> None:
    runtime, _, result = _execute(tmp_path, evidence_status="PASS")

    assert result.completion_decision is not None
    assert result.completion_decision.verdict is CompletionVerdict.READY
    assert result.validated_complete is True
    assert result.task_state is not None
    assert result.task_state.status is TaskStatus.COMPLETED
    assert runtime.load_task_status(task_id="task-1").last_outcome == "VALIDATED_COMPLETION"


def test_model_completed_with_failed_persisted_evidence_fails_task(tmp_path: Path) -> None:
    runtime, _, result = _execute(tmp_path, evidence_status="FAIL")

    assert result.completion_decision is not None
    assert result.completion_decision.verdict is CompletionVerdict.FAILED
    assert result.validated_complete is False
    assert result.task_state is not None
    assert result.task_state.status is TaskStatus.FAILED
    assert runtime.load_task_status(task_id="task-1").last_outcome == "VALIDATION_FAILED"


def test_non_completion_terminal_does_not_invoke_completion_promotion(tmp_path: Path) -> None:
    runtime, _, result = _execute(tmp_path, evidence_status="PASS", terminal=ModelEventType.TURN_INCOMPLETE)

    assert result.completion_decision is None
    assert result.task_state is None
    persisted = runtime.load_task_status(task_id="task-1")
    assert persisted is not None
    assert persisted.status is TaskStatus.RUNNING


def test_missing_completion_contract_fails_before_provider_execution(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    adapter = _TerminalAdapter()

    with pytest.raises(ProfessionalCompletionRuntimeError, match="completion contract"):
        execute_completion_gated_persisted_professional_turn(
            history=SessionOperationalHistory(store=runtime.store),
            session_provider=_provider(adapter),
            request=_request(),
            orchestrator=GovernedToolOrchestrator(registry=ToolRegistry()),
            tool_context=_context(tmp_path),
            completion_runtime=CodingCompletionRuntime(runtime=runtime),
            task_id="task-1",
        )

    assert adapter.calls == 0
