from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lbe_guard_inspector.runtime.completion_gate import (
    CompletionRequirement,
    TaskCompletionContract,
)
from lbe_guard_inspector.runtime.completion_runtime import CodingCompletionRuntime
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _runtime(database: Path, root: Path, *, session_id: str = "session-1") -> SessionMemoryRuntimeBridge:
    return SessionMemoryRuntimeBridge(
        database_path=database,
        project_workspace_id="project-1",
        workspace_root=root,
        session_id=session_id,
        mode="coding",
    )


def _contract(*, test_kind: str = "focused_test") -> TaskCompletionContract:
    return TaskCompletionContract(
        requirements=(
            CompletionRequirement("source-change", "source_change", "requested change exists"),
            CompletionRequirement("focused-tests", test_kind, "focused validation passes"),
        )
    )


def test_completion_contract_survives_runtime_restart(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    first = CodingCompletionRuntime(runtime=_runtime(database, root))

    persisted = first.persist_contract(task_id="task-1", contract=_contract())

    second = CodingCompletionRuntime(runtime=_runtime(database, root))
    loaded = second.load_contract(task_id="task-1")

    assert loaded == persisted
    assert loaded == _contract()


def test_identical_completion_contract_persistence_is_idempotent(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    coordinator = CodingCompletionRuntime(runtime=_runtime(database, root))

    first = coordinator.persist_contract(task_id="task-1", contract=_contract())
    second = coordinator.persist_contract(task_id="task-1", contract=_contract())

    assert second == first


def test_completion_contract_cannot_be_replaced_implicitly(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    coordinator = CodingCompletionRuntime(runtime=_runtime(database, root))
    coordinator.persist_contract(task_id="task-1", contract=_contract())

    with pytest.raises(ValueError, match="cannot be replaced implicitly"):
        coordinator.persist_contract(
            task_id="task-1",
            contract=_contract(test_kind="full_suite"),
        )

    assert coordinator.load_contract(task_id="task-1") == _contract()


def test_completion_contract_is_bound_to_session_workspace_identity(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    first = CodingCompletionRuntime(runtime=_runtime(database, root, session_id="session-1"))
    first.persist_contract(task_id="task-1", contract=_contract())

    second = CodingCompletionRuntime(runtime=_runtime(database, root, session_id="session-2"))

    assert second.load_contract(task_id="task-1") is None


def test_new_schema_is_additive_for_existing_database(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    runtime = _runtime(database, root)
    runtime.record_task_status(task_id="task-existing", status="running")

    coordinator = CodingCompletionRuntime(runtime=_runtime(database, root))
    coordinator.persist_contract(task_id="task-new", contract=_contract())

    existing = coordinator._runtime.load_task_status(task_id="task-existing")
    assert existing is not None
    assert existing.status.value == "running"
    assert coordinator.load_contract(task_id="task-new") == _contract()
