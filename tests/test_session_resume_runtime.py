from __future__ import annotations

import subprocess
from pathlib import Path

from lbe_guard_inspector.memory import TaskStatus, ValidationStatus
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


def runtime(tmp_path: Path, root: Path, **kwargs) -> SessionMemoryRuntimeBridge:
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-r4",
        **kwargs,
    )


def compaction() -> dict[str, object]:
    return {
        "source_message_count": 3,
        "source_prefix_hash": "sha256:" + "a" * 64,
        "source_last_message_key": "id:msg-3",
        "messages": [],
    }


def test_session_contract_survives_runtime_restart(tmp_path: Path) -> None:
    root = repo(tmp_path)
    first = runtime(
        tmp_path,
        root,
        mode="coding",
        provider_id="openai-compatible",
        provider_model="model-a",
        active_profile_id="profile-1",
        permission_policy_id="permissions-1",
        evidence_policy_id="evidence-1",
    )
    first.record_task_status(task_id="task-1", status=TaskStatus.RUNNING)

    second = runtime(tmp_path, root)
    packet = second.start_or_resume(task_id="task-1")

    assert packet["session"]["session_id"] == "session-r4"
    assert packet["session"]["mode"] == "coding"
    assert packet["session"]["provider_id"] == "openai-compatible"
    assert packet["session"]["provider_model"] == "model-a"
    assert packet["session"]["active_profile_id"] == "profile-1"
    assert packet["session"]["permission_policy_id"] == "permissions-1"
    assert packet["session"]["evidence_policy_id"] == "evidence-1"
    assert packet["task"]["task_id"] == "task-1"
    assert packet["task"]["current_status"] == "running"


def test_checkpoint_is_bound_to_session_and_constraints_survive_resume(tmp_path: Path) -> None:
    root = repo(tmp_path)
    first = runtime(tmp_path, root, mode="coding")
    checkpoint_id = first.checkpoint(
        compaction=compaction(),
        active_constraints=["do not commit", "stay inside workspace"],
    )

    second = runtime(tmp_path, root)
    packet = second.start_or_resume()

    assert packet["session"]["checkpoint_id"] == checkpoint_id
    assert packet["checkpoint"]["checkpoint_id"] == checkpoint_id
    assert packet["checkpoint_constraints"] == [
        "do not commit",
        "stay inside workspace",
    ]
    assert packet["checkpoint_revalidation"]["checks"]["branch"] == "MATCH"
    assert packet["checkpoint_revalidation"]["checks"]["head"] == "MATCH"
    assert packet["checkpoint_revalidation"]["reactivation_allowed"] is False
    assert "SOURCE_PREFIX_EVIDENCE_MISSING" in packet["checkpoint_revalidation"]["reasons"]


def test_resume_invalidates_changed_source_fact_and_reports_changed_head(tmp_path: Path) -> None:
    root = repo(tmp_path)
    first = runtime(tmp_path, root, mode="coding")
    memory_id = first.adapter.record_file_hash(relative_path="tracked.txt", task_id="task-1")
    first.record_task_status(task_id="task-1", status=TaskStatus.RUNNING)
    first.checkpoint(compaction=compaction(), active_constraints=["keep constraint"])

    (root / "tracked.txt").write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "change source"], cwd=root, check=True)

    second = runtime(tmp_path, root)
    packet = second.start_or_resume(task_id="task-1")
    stale = second.store.get(memory_id)

    assert stale is not None
    assert stale.validation_status is ValidationStatus.STALE
    assert all(item["memory_id"] != memory_id for item in packet["verified_facts"])
    assert packet["checkpoint_revalidation"]["checks"]["head"] == "MISMATCH"
    assert packet["checkpoint_revalidation"]["status"] == "INELIGIBLE"
    assert packet["task"]["current_status"] == "running"
    assert packet["checkpoint_constraints"] == ["keep constraint"]


def test_provider_change_updates_session_without_changing_workspace_or_task(tmp_path: Path) -> None:
    root = repo(tmp_path)
    first = runtime(
        tmp_path,
        root,
        mode="coding",
        provider_id="provider-a",
        provider_model="model-a",
    )
    first.record_task_status(task_id="task-1", status=TaskStatus.BLOCKED, last_outcome="WAITING")
    first.configure_session(provider_id="provider-b", provider_model="model-b")

    second = runtime(tmp_path, root)
    packet = second.start_or_resume(task_id="task-1")

    assert packet["session"]["provider_id"] == "provider-b"
    assert packet["session"]["provider_model"] == "model-b"
    assert packet["session"]["project_workspace_id"] == "project-1"
    assert packet["task"]["current_status"] == "blocked"
    assert packet["task"]["last_outcome"] == "WAITING"
