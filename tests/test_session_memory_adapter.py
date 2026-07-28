from __future__ import annotations

import subprocess
from pathlib import Path

from lbe_guard_inspector.memory import (
    SessionMemoryAdapter,
    ValidationStatus,
    WorkspaceMemoryStore,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "tracked.txt").write_text("one", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    return repo


def _adapter(tmp_path: Path, repo: Path) -> SessionMemoryAdapter:
    store = WorkspaceMemoryStore(tmp_path / "state" / "memory.db")
    return SessionMemoryAdapter(
        store=store,
        project_workspace_id="project-1",
        workspace_root=repo,
    )


def test_adapter_records_deterministic_git_state(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = _adapter(tmp_path, repo)
    ids = adapter.record_git_state(source_message_id="msg-git")
    assert len(ids) == 3
    records = adapter.store.query(project_workspace_id="project-1")
    assert {item.predicate for item in records} == {
        "git_branch",
        "git_head",
        "changed_files",
    }
    assert all(item.validation_status is ValidationStatus.VERIFIED for item in records)


def test_adapter_records_command_exit_code_only_as_deterministic_result(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    adapter = _adapter(tmp_path, repo)
    memory_id = adapter.record_command_result(
        command="python -m pytest -q",
        cwd=repo,
        exit_code=1,
        stdout="1 failed",
        stderr="",
        source_message_id="msg-command",
    )
    record = adapter.store.get(memory_id)
    assert record is not None
    assert record.predicate == "command_exit_code"
    assert record.value["exit_code"] == 1
    assert record.validation_status is ValidationStatus.VERIFIED


def test_adapter_hashes_only_files_inside_workspace(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = _adapter(tmp_path, repo)
    memory_id = adapter.record_file_hash(
        relative_path="tracked.txt",
        source_message_id="msg-file",
    )
    record = adapter.store.get(memory_id)
    assert record is not None
    assert record.source_path == "tracked.txt"
    assert record.source_hash == record.value


def test_adapter_rejects_path_traversal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = _adapter(tmp_path, repo)
    try:
        adapter.record_file_hash(relative_path="../outside.txt")
    except ValueError as exc:
        assert "inside the workspace" in str(exc)
    else:
        raise AssertionError("path traversal was accepted")


def test_assistant_observation_remains_unverified(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = _adapter(tmp_path, repo)
    memory_id = adapter.record_assistant_observation(
        subject="agent.py",
        predicate="is_broken",
        value=True,
        source_message_id="msg-assistant",
    )
    record = adapter.store.get(memory_id)
    assert record is not None
    assert record.validation_status is ValidationStatus.UNVERIFIED
    assert adapter.store.query(project_workspace_id="project-1") == []


def test_compaction_checkpoint_and_rehydration(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = _adapter(tmp_path, repo)
    adapter.record_git_state(source_message_id="msg-git")
    checkpoint_id = adapter.checkpoint_compaction(
        session_id="session-1",
        compaction={
            "source_message_count": 12,
            "source_prefix_hash": "sha256:" + "a" * 64,
            "source_last_message_key": "id:msg-12",
            "messages": [],
        },
        active_constraints=["do not commit"],
    )
    packet = adapter.rehydrate(
        session_id="session-1",
        recent_messages=[{"role": "user", "content": "continue"}],
    )
    assert packet["checkpoint"]["checkpoint_id"] == checkpoint_id
    assert packet["checkpoint"]["active_constraints"] == ["do not commit"]
    assert packet["workspace"]["project_workspace_id"] == "project-1"
    assert packet["recent_messages"] == [{"role": "user", "content": "continue"}]
