from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lbe_guard_inspector.agent_integration import (
    AgentIntegrationError,
    AgentMode,
    AgentRequestEnvelope,
    GovernedAgentGateway,
)
from lbe_guard_inspector.memory import TaskStatus, ValidationStatus
from lbe_guard_inspector.reasoning_contracts import LBEResponse, ReasoningPlan
from lbe_guard_inspector.runtime.completion_gate import CompletionRequirement
from lbe_guard_inspector.runtime.completion_promotion import CompletionProofPromotion
from lbe_guard_inspector.runtime.completion_runtime import CodingCompletionRuntime
from lbe_guard_inspector.runtime.task_completion_policy import TaskCompletionPolicyCatalog
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionResult,
    ToolReceiptStatus,
    ToolRegistry,
    workspace_read_spec,
)
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "tracked.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    return root


class _Controller:
    def __init__(self, outcome: str = "COMPLETED") -> None:
        self.outcome = outcome
        self.requests = []

    def run(self, request):
        self.requests.append(request)
        return LBEResponse(
            task_id=request.task_id,
            workspace_identity={
                "workspace_id": "project-1",
                "target_project_root": str(Path(request.workspace_root).resolve()),
            },
            workspace_profile={},
            plan=None,
            deterministic_result=None,
            explanation=None,
            outcome=self.outcome,
        )


class _MutatingController(_Controller):
    def run(self, request):
        root = Path(request.workspace_root)
        (root / "tracked.txt").write_text("two\n", encoding="utf-8")
        return super().run(request)


def _runtime(
    tmp_path: Path,
    root: Path,
    *,
    mode: str = "audit",
    permission: str | None = None,
    runtime_policy: str | None = None,
) -> SessionMemoryRuntimeBridge:
    if permission is None:
        permission = "write_allowed" if mode == "coding" else "read_only"
    if runtime_policy is None:
        runtime_policy = "permissive" if mode in {"coding", "investigation"} else "audit"
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
        mode=mode,
        permission=permission,
        runtime_policy=runtime_policy,
    )


def _request(root: Path, **overrides) -> AgentRequestEnvelope:
    values = {
        "request_id": "request-1",
        "session_id": "session-1",
        "task_id": "task-1",
        "project_workspace_id": "project-1",
        "workspace_root": root,
        "mode": AgentMode.AUDIT,
        "operation_id": "reasoning.inspect",
        "arguments": {"problem": "Inspect current workspace"},
    }
    values.update(overrides)
    return AgentRequestEnvelope(**values)


def test_gateway_routes_agent_request_to_existing_runtime_and_reasoning_owner(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
    controller = _Controller()
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    result = gateway.invoke(_request(root))

    assert len(controller.requests) == 1
    assert controller.requests[0].problem == "Inspect current workspace"
    assert controller.requests[0].task_id == "task-1"
    assert Path(controller.requests[0].workspace_root).resolve() == root.resolve()
    assert result.request_id == "request-1"
    assert result.session_id == "session-1"
    assert result.task_id == "task-1"
    assert result.operation_id == "reasoning.inspect"
    assert result.status is TaskStatus.COMPLETED
    assert result.outcome == "COMPLETED"
    assert result.response is not None
    state = runtime.load_task_status(task_id="task-1")
    assert state is not None
    assert state.last_outcome == "COMPLETED"


def test_coding_gateway_keeps_provider_completion_provisional_until_gate_and_fails_closed(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(
        tmp_path,
        root,
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
    )
    controller = _Controller("COMPLETED")
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    result = gateway.invoke(_request(root, mode=AgentMode.CODING))

    assert result.response.outcome == "COMPLETED"
    assert result.outcome == "VALIDATION_FAILED"
    assert result.status is TaskStatus.FAILED
    state = runtime.load_task_status(task_id="task-1")
    assert state is not None
    assert state.status is TaskStatus.FAILED
    assert state.last_outcome == "VALIDATION_FAILED"
    assert CodingCompletionRuntime(runtime=runtime).load_contract(task_id="task-1").requirements == (
        CompletionRequirement("source-change", "source_change"),
        CompletionRequirement("focused-tests", "focused_test"),
        CompletionRequirement("git-state", "git_status"),
    )
    proof = CompletionProofPromotion(runtime=runtime).load(task_id="task-1")
    assert proof is not None
    assert proof.validation_status is ValidationStatus.UNVERIFIED
    assert proof.value["proof_state"] == "TEMP"
    assert proof.value["lbe_completion_verdict"] is None


def test_coding_gateway_auto_finalizes_ready_and_promotes_same_completion_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")
    controller = _MutatingController("COMPLETED")
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    monkeypatch.setattr(
        "lbe_guard_inspector.runtime.completion_evidence_producers._run_validation_command",
        lambda **kwargs: subprocess.CompletedProcess(kwargs["command"], 0, stdout="ok", stderr=""),
    )

    result = gateway.invoke(_request(root, mode=AgentMode.CODING))

    assert len(controller.requests) == 1
    assert result.response.outcome == "COMPLETED"
    assert result.status is TaskStatus.COMPLETED
    assert result.outcome == "VALIDATED_COMPLETION"
    proof = CompletionProofPromotion(runtime=runtime).load(task_id="task-1")
    assert proof is not None
    assert proof.validation_status is ValidationStatus.VERIFIED
    assert proof.value["proof_state"] == "VERIFIED"
    assert proof.value["lbe_completion_verdict"] == "READY"
    assert set(proof.value["satisfied_requirement_ids"]) == {
        "source-change",
        "focused-tests",
        "git-state",
    }
    evidence = CodingCompletionRuntime(runtime=runtime).load_evidence(task_id="task-1")
    assert [(item.kind, item.status.value) for item in evidence] == [
        ("source_change", "PASS"),
        ("focused_test", "PASS"),
        ("git_status", "PASS"),
    ]


def test_noncompleted_coding_provider_never_creates_completion_proof(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")
    gateway = GovernedAgentGateway(
        runtime=runtime,
        reasoning_controller=_Controller("INSUFFICIENT_EVIDENCE"),
    )

    result = gateway.invoke(_request(root, mode=AgentMode.CODING))

    assert result.status is TaskStatus.BLOCKED
    assert result.outcome == "INSUFFICIENT_EVIDENCE"
    assert CompletionProofPromotion(runtime=runtime).load(task_id="task-1") is None


def test_coding_validation_recovery_retries_safe_producer_but_never_reasoning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lbe_guard_inspector.runtime.completion_evidence_producers import CompletionEvidenceProducers

    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")
    controller = _Controller("COMPLETED")
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)
    original = CompletionEvidenceProducers.produce_source_change
    calls = {"count": 0}

    def flaky(self, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("temporary validation timeout")
        return original(self, **kwargs)

    monkeypatch.setattr(CompletionEvidenceProducers, "produce_source_change", flaky)

    result = gateway.invoke(_request(root, mode=AgentMode.CODING))

    assert result.status is TaskStatus.FAILED
    assert len(controller.requests) == 1
    assert calls["count"] == 2
    validation_state = runtime.load_recovery_state(
        task_id="task-1",
        operation_id="reasoning.inspect:request-1:validation:source_change",
    )
    assert validation_state is not None
    assert validation_state.attempt_count == 2
    assert validation_state.terminal is True
    assert validation_state.succeeded is True
    reasoning_state = runtime.load_recovery_state(
        task_id="task-1",
        operation_id="reasoning.inspect:request-1:reasoning",
    )
    assert reasoning_state is not None
    assert reasoning_state.attempt_count == 1
    assert reasoning_state.terminal is True
    assert reasoning_state.succeeded is True


def test_coding_exact_request_replay_is_blocked_without_second_reasoning_execution(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")
    controller = _Controller("COMPLETED")
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)
    request = _request(root, mode=AgentMode.CODING)

    gateway.invoke(request)
    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(request)

    assert exc.value.code == "duplicate_operation"
    assert len(controller.requests) == 1


def test_coding_gateway_fails_closed_when_no_lbe_completion_policy_matches(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")
    gateway = GovernedAgentGateway(
        runtime=runtime,
        reasoning_controller=_Controller(),
        completion_policy_catalog=TaskCompletionPolicyCatalog(()),
    )

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(_request(root, mode=AgentMode.CODING))

    assert exc.value.code == "completion_policy_missing"
    assert runtime.load_task_status(task_id="task-1") is None


def test_coding_provider_switch_reuses_existing_completion_contract(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=_Controller())
    gateway.invoke(_request(root, mode=AgentMode.CODING))
    initial = CodingCompletionRuntime(runtime=runtime).load_contract(task_id="task-1")
    assert initial is not None

    runtime.configure_session(provider_id="provider-b", provider_model="model-b")
    resumed = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
    )
    resumed_gateway = GovernedAgentGateway(runtime=resumed, reasoning_controller=_Controller())
    resumed_gateway.invoke(_request(root, mode=AgentMode.CODING, request_id="request-2"))

    assert CodingCompletionRuntime(runtime=resumed).load_contract(task_id="task-1") == initial
    recovered = resumed.load_recovery_state(
        task_id="task-1",
        operation_id="reasoning.inspect:request-1:reasoning",
    )
    assert recovered is not None
    assert recovered.terminal is True
    assert recovered.succeeded is True


def test_provider_plan_cannot_widen_lbe_completion_requirements(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")

    class _ProviderPlanController(_Controller):
        def run(self, request):
            response = super().run(request)
            return LBEResponse(
                task_id=response.task_id,
                workspace_identity=response.workspace_identity,
                workspace_profile=response.workspace_profile,
                plan=ReasoningPlan(
                    interpreted_problem="provider attempt",
                    ambiguities=(),
                    candidate_guard_ids=(),
                    evidence_requests=(),
                    validation_requests=("provider-selected-validation",),
                    explanation_focus=(),
                ),
                deterministic_result=None,
                explanation=None,
                outcome=response.outcome,
            )

    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=_ProviderPlanController())
    gateway.invoke(_request(root, mode=AgentMode.CODING))

    contract = CodingCompletionRuntime(runtime=runtime).load_contract(task_id="task-1")
    assert contract is not None
    assert tuple(item.evidence_kind for item in contract.requirements) == (
        "source_change",
        "focused_test",
        "git_status",
    )


def test_provider_completion_cannot_manufacture_live_repository_evidence(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=_Controller("COMPLETED"))

    result = gateway.invoke(_request(root, mode=AgentMode.CODING))

    assert result.status is TaskStatus.FAILED
    assert result.outcome == "VALIDATION_FAILED"
    evidence = CodingCompletionRuntime(runtime=runtime).load_evidence(task_id="task-1")
    assert [(item.kind, item.status.value) for item in evidence] == [
        ("source_change", "FAIL"),
        ("focused_test", "FAIL"),
        ("git_status", "FAIL"),
    ]
    proof = CompletionProofPromotion(runtime=runtime).load(task_id="task-1")
    assert proof is not None
    assert proof.validation_status is ValidationStatus.UNVERIFIED


def test_gateway_rejects_legacy_session_missing_authoritative_typed_policy(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
    with runtime.store._connect() as connection:
        connection.execute(
            "UPDATE session_state SET permission=NULL, runtime_policy=NULL WHERE session_id=?",
            (runtime.session_id,),
        )
    runtime = _runtime(tmp_path, root)
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=_Controller())

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(_request(root))

    assert exc.value.code == "policy_state_missing"


def test_gateway_rejects_resolved_mode_contradiction(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(
        tmp_path,
        root,
        mode="coding",
        permission="read_only",
        runtime_policy="permissive",
    )
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=_Controller())

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(_request(root, mode=AgentMode.CODING))

    assert exc.value.code == "resolved_mode_mismatch"


def test_opaque_permission_policy_id_cannot_widen_r6b_authority(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
        mode="audit",
        permission="read_only",
        runtime_policy="permissive",
        permission_policy_id="write_allowed",
    )
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=_Controller())

    decision = gateway.resolve_runtime_mode(_request(root))

    assert decision.mode == "audit"
    assert "propose" not in decision.capabilities


def test_gateway_uses_r6b_decision_for_existing_r6e_context(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, permission="read_only", runtime_policy="audit")
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=_Controller())
    context = gateway.tool_execution_context(_request(root))
    registry = ToolRegistry()
    calls = []
    registry.register(
        workspace_read_spec(),
        lambda request: calls.append(request) or ToolExecutionResult(output={"ok": True}),
    )

    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        gateway.tool_request(
            request=_request(root),
            tool_id="workspace.read",
            arguments={"path": "README.md"},
        )
    )

    assert context.mode_decision.mode == "audit"
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.authorization is not None
    assert calls[0].context.mode_decision == context.mode_decision


def test_gateway_rejects_request_mode_that_differs_from_persisted_session(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="audit")
    controller = _Controller()
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(_request(root, mode=AgentMode.CODING))

    assert exc.value.code == "mode_mismatch"
    assert controller.requests == []
    assert runtime.load_task_status(task_id="task-1") is None


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("session_id", "other-session", "session_mismatch"),
        ("project_workspace_id", "other-project", "workspace_mismatch"),
    ],
)
def test_gateway_rejects_identity_mismatch_before_reasoning(tmp_path: Path, field, value, code) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
    controller = _Controller()
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(_request(root, **{field: value}))

    assert exc.value.code == code
    assert controller.requests == []
    assert runtime.load_task_status(task_id="task-1") is None


def test_gateway_rejects_workspace_root_mismatch_before_reasoning(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    runtime = _runtime(tmp_path, root)
    controller = _Controller()
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(_request(other))

    assert exc.value.code == "workspace_mismatch"
    assert controller.requests == []


def test_gateway_does_not_treat_terminal_capability_as_authority(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="coding")
    controller = _Controller()
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(_request(root, operation_id="shell.execute", mode=AgentMode.CODING))

    assert exc.value.code == "unsupported_operation"
    assert controller.requests == []
    assert runtime.load_task_status(task_id="task-1") is None


def test_gateway_preserves_blocked_outcome_as_persisted_lifecycle_state(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root, mode="investigation")
    gateway = GovernedAgentGateway(
        runtime=runtime,
        reasoning_controller=_Controller("INSUFFICIENT_EVIDENCE"),
    )

    result = gateway.invoke(_request(root, mode=AgentMode.INVESTIGATION))

    assert result.status is TaskStatus.BLOCKED
    assert result.outcome == "INSUFFICIENT_EVIDENCE"
    state = runtime.load_task_status(task_id="task-1")
    assert state is not None
    assert state.status is TaskStatus.BLOCKED
    assert state.last_outcome == "INSUFFICIENT_EVIDENCE"


def test_gateway_rejects_unregistered_arguments_instead_of_reinterpreting_them(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
    controller = _Controller()
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(
            _request(
                root,
                arguments={
                    "problem": "Inspect",
                    "command": "git status",
                },
            )
        )

    assert exc.value.code == "invalid_request"
    assert controller.requests == []
