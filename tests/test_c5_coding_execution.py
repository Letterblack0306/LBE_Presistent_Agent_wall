from __future__ import annotations

import json
from pathlib import Path

import pytest

import lbe_guard_inspector.agent_integration as agent_integration
from lbe_guard_inspector.agent_integration import AgentMode, AgentRequestEnvelope, GovernedAgentGateway
from lbe_guard_inspector.coding_reasoning_provider import (
    PlannedToolRequest,
    ToolAwareOpenAICompatibleReasoningBackend,
    ToolAwareReasoningPlan,
)
from lbe_guard_inspector.reasoning_contracts import LBEResponse, ReasoningRequest
from lbe_guard_inspector.reasoning_provider import ProviderConfig, ProviderError
from lbe_guard_inspector.runtime.mode_controller import ModeRequest, resolve_mode
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
    build_workspace_replace_text_handler,
    workspace_replace_text_spec,
)
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


class FakeTransport:
    def __init__(self, content: dict):
        self.content = content
        self.payloads = []

    def post_json(self, **kwargs):
        self.payloads.append(kwargs)
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(self.content),
                    }
                }
            ]
        }


def _provider_plan() -> dict:
    return {
        "interpreted_problem": "replace the bounded marker",
        "ambiguities": [],
        "candidate_guard_ids": [],
        "evidence_requests": [],
        "validation_requests": [],
        "explanation_focus": [],
        "tool_requests": [
            {
                "tool_id": "workspace.replace_text",
                "path": "README.md",
                "old_text": "C5_BEFORE",
                "new_text": "C5_AFTER",
                "reason": "apply the exact requested controlled edit",
            }
        ],
    }


def _reasoning_request(*approved_tools: str) -> ReasoningRequest:
    return ReasoningRequest(
        problem="replace C5_BEFORE with C5_AFTER in README.md",
        workspace_identity={"configured_root_id": "dev", "workspace_id": "workspace-1"},
        workspace_profile={},
        approved_guard_ids=(),
        approved_tools=approved_tools,
        reference_context=(),
    )


def test_tool_aware_provider_accepts_one_approved_bounded_replace_request() -> None:
    transport = FakeTransport(_provider_plan())
    backend = ToolAwareOpenAICompatibleReasoningBackend(
        config=ProviderConfig(endpoint="http://provider.invalid/v1/chat/completions", model="test", timeout_seconds=1),
        transport=transport,
    )
    plan = backend.plan(_reasoning_request("workspace.read", "workspace.replace_text"))
    assert isinstance(plan, ToolAwareReasoningPlan)
    assert len(plan.tool_requests) == 1
    assert plan.tool_requests[0].arguments == {
        "path": "README.md",
        "old_text": "C5_BEFORE",
        "new_text": "C5_AFTER",
    }


def test_tool_aware_provider_rejects_unapproved_replace_request() -> None:
    backend = ToolAwareOpenAICompatibleReasoningBackend(
        config=ProviderConfig(endpoint="http://provider.invalid/v1/chat/completions", model="test", timeout_seconds=1),
        transport=FakeTransport(_provider_plan()),
    )
    with pytest.raises(ProviderError, match="not approved"):
        backend.plan(_reasoning_request("workspace.read"))


def test_coding_mode_exposes_modify_but_audit_does_not() -> None:
    coding = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="permissive"))
    audit = resolve_mode(ModeRequest(intent="inspect_workspace", permission="read_only", runtime_policy="permissive"))
    assert coding.mode == "coding"
    assert "modify" in coding.capabilities
    assert audit.mode == "audit"
    assert "modify" not in audit.capabilities


def _tool_request(tmp_path: Path, *, mode, path="README.md", old="C5_BEFORE", new="C5_AFTER") -> ToolRequest:
    return ToolRequest(
        operation_id="op-1",
        tool_id="workspace.replace_text",
        arguments={"path": path, "old_text": old, "new_text": new},
        context=ToolExecutionContext(
            mode_decision=mode,
            workspace_id="workspace-1",
            workspace_root=tmp_path,
            configured_root_id="dev",
        ),
    )


def _replace_orchestrator() -> GovernedToolOrchestrator:
    registry = ToolRegistry()
    registry.register(workspace_replace_text_spec(), build_workspace_replace_text_handler())
    return GovernedToolOrchestrator(registry=registry)


def test_workspace_replace_text_executes_exactly_once_under_coding_authority(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("alpha\nC5_BEFORE\nomega\n", encoding="utf-8")
    coding = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="permissive"))
    receipt = _replace_orchestrator().invoke(_tool_request(tmp_path, mode=coding))
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert target.read_text(encoding="utf-8") == "alpha\nC5_AFTER\nomega\n"
    assert receipt.output["replacement_count"] == 1
    assert receipt.output["before_sha256"] != receipt.output["after_sha256"]


def test_workspace_replace_text_escalates_in_audit_without_mutation(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("C5_BEFORE\n", encoding="utf-8")
    audit = resolve_mode(ModeRequest(intent="inspect_workspace", permission="read_only", runtime_policy="permissive"))
    receipt = _replace_orchestrator().invoke(_tool_request(tmp_path, mode=audit))
    assert receipt.status is ToolReceiptStatus.ESCALATED
    assert target.read_text(encoding="utf-8") == "C5_BEFORE\n"


def test_workspace_replace_text_rejects_escape_and_ambiguous_match(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("C5_BEFORE C5_BEFORE\n", encoding="utf-8")
    coding = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="permissive"))
    ambiguous = _replace_orchestrator().invoke(_tool_request(tmp_path, mode=coding))
    assert ambiguous.status is ToolReceiptStatus.FAILED
    assert target.read_text(encoding="utf-8") == "C5_BEFORE C5_BEFORE\n"

    outside = _replace_orchestrator().invoke(
        _tool_request(tmp_path, mode=coding, path="../outside.txt")
    )
    assert outside.status is ToolReceiptStatus.FAILED


class FakeController:
    def __init__(self, plan: ToolAwareReasoningPlan):
        self.plan = plan

    def run(self, request):
        return LBEResponse(
            task_id=request.task_id,
            workspace_identity={"workspace_id": "workspace-1"},
            workspace_profile={},
            plan=self.plan,
            deterministic_result={"verdict": "FAIL"},
            explanation=None,
            outcome="COMPLETED",
        )


class FakeCompletionEvidenceProducers:
    def __init__(self, *, runtime):
        self.runtime = runtime

    def capture_workspace_snapshot(self):
        return object()

    def produce_source_change(self, **kwargs):
        return None

    def produce_focused_test(self, **kwargs):
        return None

    def produce_git_status(self, **kwargs):
        return None


def _runtime(tmp_path: Path, *, mode="coding", permission="write_allowed") -> SessionMemoryRuntimeBridge:
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "runtime.sqlite3",
        project_workspace_id="workspace-1",
        workspace_root=tmp_path,
        session_id=f"session-{mode}",
        mode=mode,
        permission=permission,
        runtime_policy="permissive",
        provider_id="openai-compatible",
        provider_model="test-model",
    )


def _plan() -> ToolAwareReasoningPlan:
    return ToolAwareReasoningPlan(
        interpreted_problem="replace marker",
        ambiguities=(),
        candidate_guard_ids=("test.guard",),
        evidence_requests=(),
        validation_requests=(),
        explanation_focus=(),
        tool_requests=(
            PlannedToolRequest(
                tool_id="workspace.replace_text",
                path="README.md",
                old_text="C5_BEFORE",
                new_text="C5_AFTER",
                reason="controlled proof",
            ),
        ),
    )


def test_gateway_executes_planned_replace_only_in_coding_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(agent_integration, "CompletionEvidenceProducers", FakeCompletionEvidenceProducers)
    target = tmp_path / "README.md"
    target.write_text("C5_BEFORE\n", encoding="utf-8")
    runtime = _runtime(tmp_path)
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=FakeController(_plan()))
    result = gateway.invoke(
        AgentRequestEnvelope(
            request_id="request-1",
            session_id=runtime.session_id,
            task_id="task-1",
            project_workspace_id=runtime.project_workspace_id,
            workspace_root=tmp_path,
            mode=AgentMode.CODING,
            operation_id="reasoning.inspect",
            arguments={"problem": "replace C5_BEFORE with C5_AFTER"},
        )
    )
    assert target.read_text(encoding="utf-8") == "C5_AFTER\n"
    assert result.status.value == "running"
    assert runtime.load_task_status(task_id="task-1").last_outcome == "AWAITING_VALIDATION"


def test_gateway_never_executes_planned_replace_in_audit_mode(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("C5_BEFORE\n", encoding="utf-8")
    runtime = _runtime(tmp_path, mode="audit", permission="read_only")
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=FakeController(_plan()))
    gateway.invoke(
        AgentRequestEnvelope(
            request_id="request-audit",
            session_id=runtime.session_id,
            task_id="task-audit",
            project_workspace_id=runtime.project_workspace_id,
            workspace_root=tmp_path,
            mode=AgentMode.AUDIT,
            operation_id="reasoning.inspect",
            arguments={"problem": "inspect only"},
        )
    )
    assert target.read_text(encoding="utf-8") == "C5_BEFORE\n"
