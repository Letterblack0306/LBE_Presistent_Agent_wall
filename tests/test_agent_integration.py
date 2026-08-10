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
from lbe_guard_inspector.memory import TaskStatus
from lbe_guard_inspector.reasoning_contracts import LBEResponse
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


def _runtime(tmp_path: Path, root: Path) -> SessionMemoryRuntimeBridge:
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
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
    runtime = _runtime(tmp_path, root)
    controller = _Controller()
    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)

    with pytest.raises(AgentIntegrationError) as exc:
        gateway.invoke(_request(root, operation_id="shell.execute", mode=AgentMode.CODING))

    assert exc.value.code == "unsupported_operation"
    assert controller.requests == []
    assert runtime.load_task_status(task_id="task-1") is None


def test_gateway_preserves_blocked_outcome_as_persisted_lifecycle_state(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
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
