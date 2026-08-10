from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lbe_guard_inspector.memory.completion_evidence import TaskCompletionEvidencePersistence
from lbe_guard_inspector.runtime.completion_gate import CompletionEvidenceStatus
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


def _save(
    persistence: TaskCompletionEvidencePersistence,
    runtime: SessionMemoryRuntimeBridge,
    *,
    evidence_id: str = "evidence-1",
    kind: str = "focused_test",
    status: str = "PASS",
    operation_id: str = "validation-1",
):
    return persistence.save(
        session_id=runtime.session_id,
        task_id="task-1",
        project_workspace_id=runtime.project_workspace_id,
        canonical_workspace_root=str(runtime.workspace_root),
        evidence_id=evidence_id,
        kind=kind,
        status=status,
        source="validator:test-runner",
        producer_id="validation.test-runner",
        operation_id=operation_id,
        details={"exit_code": 0},
    )


def test_completion_evidence_survives_runtime_restart(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    first_runtime = _runtime(database, root)
    persistence = TaskCompletionEvidencePersistence(first_runtime.store)
    stored = _save(persistence, first_runtime)

    second = CodingCompletionRuntime(runtime=_runtime(database, root))
    loaded = second.load_evidence(task_id="task-1")

    assert len(loaded) == 1
    assert loaded[0].evidence_id == stored.evidence_id
    assert loaded[0].kind == "focused_test"
    assert loaded[0].status is CompletionEvidenceStatus.PASS
    assert loaded[0].source == "validator:test-runner"
    assert loaded[0].details == {
        "exit_code": 0,
        "producer_id": "validation.test-runner",
        "operation_id": "validation-1",
    }


def test_identical_completion_evidence_persistence_is_idempotent(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path / "memory.sqlite", root)
    persistence = TaskCompletionEvidencePersistence(runtime.store)

    first = _save(persistence, runtime)
    second = _save(persistence, runtime)

    assert second == first


def test_completion_evidence_cannot_be_relabelled_implicitly(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path / "memory.sqlite", root)
    persistence = TaskCompletionEvidencePersistence(runtime.store)
    _save(persistence, runtime)

    with pytest.raises(ValueError, match="cannot be replaced implicitly"):
        _save(persistence, runtime, kind="full_suite")

    loaded = persistence.load(
        session_id=runtime.session_id,
        task_id="task-1",
        project_workspace_id=runtime.project_workspace_id,
    )
    assert len(loaded) == 1
    assert loaded[0].kind == "focused_test"


def test_completion_evidence_requires_producer_and_operation_identity(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path / "memory.sqlite", root)
    persistence = TaskCompletionEvidencePersistence(runtime.store)

    with pytest.raises(ValueError, match="producer_id must not be empty"):
        persistence.save(
            session_id=runtime.session_id,
            task_id="task-1",
            project_workspace_id=runtime.project_workspace_id,
            canonical_workspace_root=str(runtime.workspace_root),
            evidence_id="evidence-1",
            kind="focused_test",
            status="PASS",
            source="validator:test-runner",
            producer_id="",
            operation_id="validation-1",
        )


def test_completion_evidence_is_bound_to_session_identity(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    first_runtime = _runtime(database, root, session_id="session-1")
    _save(TaskCompletionEvidencePersistence(first_runtime.store), first_runtime)

    second = CodingCompletionRuntime(runtime=_runtime(database, root, session_id="session-2"))

    assert second.load_evidence(task_id="task-1") == ()
