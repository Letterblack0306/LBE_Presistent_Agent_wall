from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from lbe_guard_inspector.memory import ValidationStatus, WorkspaceMemoryStore
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "tracked.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    return root


def bridge(tmp_path: Path, root: Path) -> SessionMemoryRuntimeBridge:
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
    )


def test_bridge_initializes_store_and_adapter(tmp_path: Path) -> None:
    root = repo(tmp_path)
    runtime = bridge(tmp_path, root)

    assert isinstance(runtime.store, WorkspaceMemoryStore)
    assert runtime.project_workspace_id == "project-1"
    assert runtime.workspace_root == root.resolve()


def test_deterministic_command_and_tool_results_are_verified(tmp_path: Path) -> None:
    root = repo(tmp_path)
    runtime = bridge(tmp_path, root)

    command_id = runtime.ingest_command_result(
        command="python -m pytest -q",
        cwd=root,
        exit_code=1,
        stdout="1 failed",
        task_id="task-1",
    )
    tool_id = runtime.ingest_tool_result(
        tool_name="workspace.read_file",
        result={"path": "tracked.txt", "sha256": "abc"},
        success=True,
        task_id="task-1",
    )

    command = runtime.store.get(command_id)
    tool = runtime.store.get(tool_id)
    assert command is not None and command.validation_status is ValidationStatus.VERIFIED
    assert tool is not None and tool.validation_status is ValidationStatus.VERIFIED
    assert command.task_id == "task-1"
    assert tool.task_id == "task-1"


def test_model_observation_is_not_promoted_by_runtime_bridge(tmp_path: Path) -> None:
    root = repo(tmp_path)
    runtime = bridge(tmp_path, root)

    observation_id = runtime.adapter.record_assistant_observation(
        subject="tracked.txt",
        predicate="is_broken",
        value=True,
    )

    observation = runtime.store.get(observation_id)
    assert observation is not None
    assert observation.validation_status is ValidationStatus.UNVERIFIED
    assert runtime.store.query(project_workspace_id="project-1") == []


def test_checkpoint_rehydrate_preserves_constraints_as_history(tmp_path: Path) -> None:
    root = repo(tmp_path)
    runtime = bridge(tmp_path, root)
    runtime.adapter.record_git_state(task_id="task-1")

    checkpoint_id = runtime.checkpoint(
        compaction={
            "source_message_count": 4,
            "source_prefix_hash": "sha256:" + "a" * 64,
            "source_last_message_key": "id:msg-4",
            "messages": [],
        },
        active_constraints=["do not commit"],
    )
    packet = runtime.start_or_resume(task_id="task-1")

    assert packet["checkpoint"]["checkpoint_id"] == checkpoint_id
    assert packet["checkpoint"]["active_constraints"] == ["do not commit"]


def test_current_source_invalidates_stale_source_backed_memory(tmp_path: Path) -> None:
    root = repo(tmp_path)
    runtime = bridge(tmp_path, root)
    memory_id = runtime.adapter.record_file_hash(relative_path="tracked.txt")
    original = runtime.store.get(memory_id)
    assert original is not None
    assert original.source_hash == hashlib.sha256(b"one\n").hexdigest()

    (root / "tracked.txt").write_text("two\n", encoding="utf-8")
    runtime.start_or_resume()

    stale = runtime.store.get(memory_id)
    assert stale is not None
    assert stale.validation_status is ValidationStatus.STALE


def test_registry_receipt_remains_separate_but_correlated(tmp_path: Path) -> None:
    root = repo(tmp_path)
    runtime = bridge(tmp_path, root)

    correlation = runtime.correlate_registry_receipt(
        module_id="module.registry",
        receipt_sequence=7,
        task_id="task-1",
    )

    assert correlation == {
        "project_workspace_id": "project-1",
        "session_id": "session-1",
        "task_id": "task-1",
        "module_id": "module.registry",
        "receipt_sequence": 7,
        "memory_evidence_stored": False,
    }
    assert runtime.store.query(project_workspace_id="project-1") == []
