from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.runtime.authorization_resolver import AuthorizationVerdict
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolAccessClass,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolNetworkBehavior,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
    ToolRiskClass,
    ToolSpec,
    build_workspace_read_handler,
    workspace_read_spec,
)


def _mode(*capabilities: str) -> ModeDecision:
    return ModeDecision(
        mode="coding",
        allowed_behaviors=("development_mode_capabilities",),
        capabilities=tuple(capabilities),
        rationale="test",
    )


def _context(tmp_path: Path, *capabilities: str, **overrides) -> ToolExecutionContext:
    values = {
        "mode_decision": _mode(*capabilities),
        "workspace_id": "workspace-1",
        "workspace_root": tmp_path,
        "configured_root_id": "dev",
    }
    values.update(overrides)
    return ToolExecutionContext(**values)


def _request(tmp_path: Path, *, operation_id="op-1", tool_id="workspace.read", arguments=None, capabilities=("inspect",), **context_overrides) -> ToolRequest:
    return ToolRequest(
        operation_id=operation_id,
        tool_id=tool_id,
        arguments=arguments if arguments is not None else {"path": "README.md"},
        context=_context(tmp_path, *capabilities, **context_overrides),
    )


def _registry(handler) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), handler)
    return registry


def test_workspace_read_spec_declares_required_governance_metadata() -> None:
    spec = workspace_read_spec()
    assert spec.tool_id == "workspace.read"
    assert spec.capability == "inspect"
    assert spec.required_arguments == ("path",)
    assert spec.access_class is ToolAccessClass.READ
    assert spec.network_behavior is ToolNetworkBehavior.NONE
    assert spec.risk_class is ToolRiskClass.LOW
    assert spec.timeout_seconds > 0
    assert spec.retry_policy
    assert spec.preconditions
    assert spec.expected_evidence
    assert spec.failure_modes


def test_registry_rejects_duplicate_tool_id() -> None:
    registry = ToolRegistry()
    spec = workspace_read_spec()
    registry.register(spec, lambda request: ToolExecutionResult(output={}))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec, lambda request: ToolExecutionResult(output={}))


def test_unregistered_tool_cannot_execute(tmp_path: Path) -> None:
    orchestrator = GovernedToolOrchestrator(registry=ToolRegistry())
    receipt = orchestrator.invoke(_request(tmp_path, tool_id="shell.execute"))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "UNREGISTERED_TOOL"
    assert receipt.authorization is None


def test_authorized_registered_tool_executes_and_captures_evidence(tmp_path: Path) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return ToolExecutionResult(
            output={"ok": True},
            evidence=({"ref": "workspace:1:README.md", "verified": True},),
        )

    orchestrator = GovernedToolOrchestrator(registry=_registry(handler))
    receipt = orchestrator.invoke(_request(tmp_path))
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.ALLOW
    assert receipt.output == {"ok": True}
    assert receipt.evidence == ({"ref": "workspace:1:README.md", "verified": True},)
    assert len(calls) == 1


def test_missing_mode_capability_escalates_without_execution(tmp_path: Path) -> None:
    calls = []
    orchestrator = GovernedToolOrchestrator(
        registry=_registry(lambda request: calls.append(request) or ToolExecutionResult(output={}))
    )
    receipt = orchestrator.invoke(_request(tmp_path, capabilities=("search",)))
    assert receipt.status is ToolReceiptStatus.ESCALATED
    assert receipt.error_code == "AUTHORIZATION_REQUIRED"
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.ESCALATE
    assert calls == []


def test_explicit_forbidden_policy_denies_without_execution(tmp_path: Path) -> None:
    calls = []
    orchestrator = GovernedToolOrchestrator(
        registry=_registry(lambda request: calls.append(request) or ToolExecutionResult(output={}))
    )
    receipt = orchestrator.invoke(_request(tmp_path, explicitly_forbidden=True))
    assert receipt.status is ToolReceiptStatus.DENIED
    assert receipt.error_code == "AUTHORIZATION_DENIED"
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.DENY
    assert calls == []


def test_workspace_scope_expansion_escalates_before_execution(tmp_path: Path) -> None:
    calls = []
    orchestrator = GovernedToolOrchestrator(
        registry=_registry(lambda request: calls.append(request) or ToolExecutionResult(output={}))
    )
    receipt = orchestrator.invoke(_request(tmp_path, within_workspace_scope=False))
    assert receipt.status is ToolReceiptStatus.ESCALATED
    assert calls == []


def test_invalid_arguments_fail_before_authorization_or_execution(tmp_path: Path) -> None:
    calls = []
    orchestrator = GovernedToolOrchestrator(
        registry=_registry(lambda request: calls.append(request) or ToolExecutionResult(output={}))
    )
    receipt = orchestrator.invoke(_request(tmp_path, arguments={"unknown": True}))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "INVALID_TOOL_ARGUMENTS"
    assert receipt.authorization is None
    assert calls == []


def test_duplicate_operation_id_returns_original_receipt_without_reexecution(tmp_path: Path) -> None:
    calls = []

    def handler(request):
        calls.append(request.operation_id)
        return ToolExecutionResult(output={"count": len(calls)})

    orchestrator = GovernedToolOrchestrator(registry=_registry(handler))
    request = _request(tmp_path, operation_id="op-repeat")
    first = orchestrator.invoke(request)
    second = orchestrator.invoke(request)
    assert second is first
    assert first.output == {"count": 1}
    assert calls == ["op-repeat"]
    assert orchestrator.receipt("op-repeat") is first


def test_handler_failure_becomes_structured_receipt(tmp_path: Path) -> None:
    def handler(request):
        raise OSError("read failed")

    receipt = GovernedToolOrchestrator(registry=_registry(handler)).invoke(_request(tmp_path))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"
    assert "read failed" in receipt.error_message
    assert receipt.authorization is not None
    assert receipt.authorization.verdict is AuthorizationVerdict.ALLOW


class FakeEvidenceService(EvidenceService):
    def __init__(self, evidence=None):
        self.calls = []
        self.evidence = evidence or [{"ref": "workspace:workspace-1:README.md", "verified": True}]

    def build_evidence_package(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "current_workspace_evidence": list(self.evidence),
            "missing_evidence": [],
        }


def test_workspace_read_handler_delegates_to_existing_evidence_service(tmp_path: Path) -> None:
    service = FakeEvidenceService()
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), build_workspace_read_handler(service))
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        _request(tmp_path, arguments={"path": "docs/README.md"})
    )
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output == {
        "path": "docs/README.md",
        "evidence_count": 1,
        "missing_evidence": [],
    }
    assert receipt.evidence == ({"ref": "workspace:workspace-1:README.md", "verified": True},)
    assert len(service.calls) == 1
    call = service.calls[0]
    assert call["workspace_id"] == "workspace-1"
    assert call["workspace_root"] == str(tmp_path.resolve())
    assert call["roots"] == ["dev"]
    assert call["retrieval_mode"] == "guard"
    assert call["rule_id"] == "workspace.read"
    assert call["path_patterns"] == ["docs/README.md"]


def test_workspace_read_handler_rejects_path_escape_before_evidence_read(tmp_path: Path) -> None:
    service = FakeEvidenceService()
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), build_workspace_read_handler(service))
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        _request(tmp_path, arguments={"path": "../outside.txt"})
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"
    assert service.calls == []
