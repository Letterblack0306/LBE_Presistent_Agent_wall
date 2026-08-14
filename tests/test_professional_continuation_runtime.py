from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadiness,
    ClineSidecarReadinessStatus,
)
from lbe_guard_inspector.professional_continuation_runtime import (
    ProfessionalContinuationRuntimeError,
    execute_governed_professional_turn,
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
    ToolReceiptStatus,
    ToolRegistry,
    workspace_read_spec,
)


FAMILY = ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT


class _ToolAdapter:
    def __init__(self) -> None:
        self.continuations = []

    def stream_turn(self, request):
        return (
            _event(ModelEventType.TURN_STARTED),
            _event(
                ModelEventType.TOOL_CALL_COMPLETED,
                provider_tool_call_id="provider-call-1",
                lbe_call_id="lbe-call-1",
                tool_name="workspace.read",
                tool_arguments={"path": "README.md"},
            ),
            _event(
                ModelEventType.TURN_REQUIRES_TOOL,
                provider_tool_call_id="provider-call-1",
                lbe_call_id="lbe-call-1",
                tool_name="workspace.read",
            ),
        )

    def continue_with_tool_result(self, request, result):
        self.continuations.append(result)
        return (
            _event(ModelEventType.TURN_STARTED),
            _event(ModelEventType.MESSAGE_DELTA, text="tool result received"),
            _event(ModelEventType.TURN_COMPLETED),
        )

    def cancel(self):
        return None


class _RepeatingToolAdapter(_ToolAdapter):
    def continue_with_tool_result(self, request, result):
        self.continuations.append(result)
        index = len(self.continuations) + 1
        return (
            _event(ModelEventType.TURN_STARTED),
            _event(
                ModelEventType.TOOL_CALL_COMPLETED,
                provider_tool_call_id=f"provider-call-{index}",
                lbe_call_id=f"lbe-call-{index}",
                tool_name="workspace.read",
                tool_arguments={"path": "README.md"},
            ),
            _event(
                ModelEventType.TURN_REQUIRES_TOOL,
                provider_tool_call_id=f"provider-call-{index}",
                lbe_call_id=f"lbe-call-{index}",
                tool_name="workspace.read",
            ),
        )


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
        system_prompt="Use projected tools when necessary.",
        messages=({"role": "user", "content": "read README"},),
        tool_definitions=(
            ProviderToolDefinition(
                name="workspace.read",
                description="Read one workspace file",
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


def _context(tmp_path: Path, *, capabilities=("inspect",), explicitly_forbidden=False) -> ToolExecutionContext:
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
        explicitly_forbidden=explicitly_forbidden,
    )


def _orchestrator(handler) -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), handler)
    return GovernedToolOrchestrator(registry=registry)


def test_executes_authorized_tool_and_continues_with_distinct_receipt_evidence(tmp_path: Path) -> None:
    adapter = _ToolAdapter()
    orchestrator = _orchestrator(
        lambda request: ToolExecutionResult(output={"content": "hello"}, evidence=({"path": "README.md"},))
    )

    result = execute_governed_professional_turn(
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=orchestrator,
        tool_context=_context(tmp_path),
        operation_id_factory=lambda: "runtime-op-1",
    )

    assert result.completed_without_blocker is True
    assert result.final_turn.terminal_event.event_type is ModelEventType.TURN_COMPLETED
    assert len(result.exchanges) == 2
    assert len(result.tool_receipts) == 1
    receipt = result.tool_receipts[0]
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.operation_id == "runtime-op-1"
    assert receipt.receipt_id != receipt.operation_id
    continuation = adapter.continuations[0]
    assert continuation.provider_tool_call_id == "provider-call-1"
    assert continuation.lbe_call_id == "lbe-call-1"
    assert continuation.runtime_operation_id == "runtime-op-1"
    assert continuation.tool_receipt_id == receipt.receipt_id
    assert continuation.output == {"content": "hello"}
    assert continuation.is_error is False


def test_denied_tool_returns_structured_error_to_provider_without_execution(tmp_path: Path) -> None:
    calls = []
    adapter = _ToolAdapter()
    result = execute_governed_professional_turn(
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(lambda request: calls.append(request) or ToolExecutionResult(output={})),
        tool_context=_context(tmp_path, explicitly_forbidden=True),
        operation_id_factory=lambda: "runtime-op-denied",
    )

    assert calls == []
    assert result.tool_receipts[0].status is ToolReceiptStatus.DENIED
    continuation = adapter.continuations[0]
    assert continuation.is_error is True
    assert continuation.output["status"] == "DENIED"
    assert continuation.output["error_code"] == "AUTHORIZATION_DENIED"


def test_escalated_tool_stops_without_provider_continuation(tmp_path: Path) -> None:
    adapter = _ToolAdapter()
    result = execute_governed_professional_turn(
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(lambda request: ToolExecutionResult(output={})),
        tool_context=_context(tmp_path, capabilities=("search",)),
        operation_id_factory=lambda: "runtime-op-escalated",
    )

    assert result.blocked_receipt is not None
    assert result.blocked_receipt.status is ToolReceiptStatus.ESCALATED
    assert result.final_turn.requires_tool is True
    assert adapter.continuations == []


def test_runtime_operation_identity_cannot_reuse_lbe_call_id(tmp_path: Path) -> None:
    with pytest.raises(ProfessionalContinuationRuntimeError, match="distinct from lbe_call_id"):
        execute_governed_professional_turn(
            session_provider=_provider(_ToolAdapter()),
            request=_request(),
            orchestrator=_orchestrator(lambda request: ToolExecutionResult(output={})),
            tool_context=_context(tmp_path),
            operation_id_factory=lambda: "lbe-call-1",
        )


def test_max_tool_hops_fails_closed_on_unbounded_provider_loop(tmp_path: Path) -> None:
    ids = iter(("runtime-op-1", "runtime-op-2"))
    with pytest.raises(ProfessionalContinuationRuntimeError, match="max_tool_hops"):
        execute_governed_professional_turn(
            session_provider=_provider(_RepeatingToolAdapter()),
            request=_request(),
            orchestrator=_orchestrator(lambda request: ToolExecutionResult(output={})),
            tool_context=_context(tmp_path),
            max_tool_hops=1,
            operation_id_factory=lambda: next(ids),
        )
