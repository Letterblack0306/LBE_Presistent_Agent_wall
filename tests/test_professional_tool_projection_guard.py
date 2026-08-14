from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadiness,
    ClineSidecarReadinessStatus,
)
from lbe_guard_inspector.professional_continuation_runtime import (
    ProfessionalContinuationRuntimeError,
    ProfessionalLoopStopReason,
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
    ToolRegistry,
    workspace_read_spec,
)


FAMILY = ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT


class _Adapter:
    def __init__(self, *, tool_name: str = "workspace.read") -> None:
        self.tool_name = tool_name
        self.stream_calls = 0
        self.continuations = []

    def stream_turn(self, request):
        self.stream_calls += 1
        return (
            _event(ModelEventType.TURN_STARTED),
            _event(
                ModelEventType.TOOL_CALL_COMPLETED,
                provider_tool_call_id="provider-call-1",
                lbe_call_id="lbe-call-1",
                tool_name=self.tool_name,
                tool_arguments={"path": "README.md"},
            ),
            _event(
                ModelEventType.TURN_REQUIRES_TOOL,
                provider_tool_call_id="provider-call-1",
                lbe_call_id="lbe-call-1",
                tool_name=self.tool_name,
            ),
        )

    def continue_with_tool_result(self, request, result):
        self.continuations.append(result)
        return (
            _event(ModelEventType.TURN_STARTED),
            _event(ModelEventType.TURN_COMPLETED),
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


def _request(*tool_names: str) -> ProviderTurnRequest:
    return ProviderTurnRequest(
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=FAMILY,
        system_prompt="Use projected tools only.",
        messages=({"role": "user", "content": "inspect workspace"},),
        tool_definitions=tuple(
            ProviderToolDefinition(
                name=name,
                description="projected test tool",
                input_schema={"type": "object"},
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


def _orchestrator(handler=None) -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    if handler is not None:
        registry.register(workspace_read_spec(), handler)
    return GovernedToolOrchestrator(registry=registry)


def test_projection_preflight_rejects_provider_visible_tool_without_runtime_backend(tmp_path: Path) -> None:
    adapter = _Adapter()
    with pytest.raises(ProfessionalContinuationRuntimeError, match="no registered runtime backend"):
        execute_governed_professional_turn(
            session_provider=_provider(adapter),
            request=_request("workspace.read"),
            orchestrator=_orchestrator(),
            tool_context=_context(tmp_path),
        )
    assert adapter.stream_calls == 0


def test_provider_proposal_outside_request_projection_stops_before_tool_execution(tmp_path: Path) -> None:
    adapter = _Adapter(tool_name="workspace.read")
    calls = []
    result = execute_governed_professional_turn(
        session_provider=_provider(adapter),
        request=_request(),
        orchestrator=_orchestrator(lambda request: calls.append(request) or ToolExecutionResult(output={})),
        tool_context=_context(tmp_path),
        operation_id_factory=lambda: "runtime-op-should-not-run",
    )
    assert result.stop_reason is ProfessionalLoopStopReason.UNSUPPORTED_CAPABILITY
    assert result.completed_without_blocker is False
    assert result.tool_receipts == ()
    assert adapter.stream_calls == 1
    assert calls == []
    assert adapter.continuations == []


def test_projected_registered_tool_still_defers_authority_to_r6c(tmp_path: Path) -> None:
    adapter = _Adapter()
    calls = []
    result = execute_governed_professional_turn(
        session_provider=_provider(adapter),
        request=_request("workspace.read"),
        orchestrator=_orchestrator(lambda request: calls.append(request) or ToolExecutionResult(output={"ok": True})),
        tool_context=_context(tmp_path),
        operation_id_factory=lambda: "runtime-op-1",
    )
    assert len(calls) == 1
    assert result.tool_receipts[0].output == {"ok": True}
    assert len(adapter.continuations) == 1
