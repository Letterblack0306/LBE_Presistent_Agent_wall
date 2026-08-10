from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lbe_guard_inspector.cli import main
from lbe_guard_inspector.memory import TaskStatus, WorkspaceMemoryStore
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


def _json_output(capsys):
    output = capsys.readouterr().out.strip()
    return json.loads(output)


def test_session_create_persists_explicit_runtime_contract(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"

    code = main([
        "session", "create",
        "--database", str(database),
        "--workspace", str(root),
        "--project-workspace-id", "project-1",
        "--session-id", "session-1",
        "--mode", "coding",
        "--provider", "openai-compatible",
        "--model", "model-a",
        "--profile", "profile-a",
        "--permission-policy", "permissions-a",
        "--evidence-policy", "evidence-a",
    ])

    payload = _json_output(capsys)
    assert code == 0
    assert payload["ok"] is True
    assert payload["action"] == "session.create"
    assert payload["session"]["session_id"] == "session-1"
    assert payload["session"]["mode"] == "coding"
    assert payload["session"]["provider_id"] == "openai-compatible"
    assert payload["session"]["provider_model"] == "model-a"
    assert payload["session"]["permission_policy_id"] == "permissions-a"

    stored = WorkspaceMemoryStore(database).load_session_state(session_id="session-1")
    assert stored is not None
    assert stored.project_workspace_id == "project-1"
    assert Path(stored.canonical_workspace_root).resolve() == root.resolve()


def test_session_status_reads_existing_state_without_reconfiguring_it(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    runtime = SessionMemoryRuntimeBridge(
        database_path=database,
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
        mode="audit",
        provider_id="openai-compatible",
        provider_model="model-a",
        permission_policy_id="read-policy",
    )
    before = runtime.store.load_session_state(session_id="session-1")
    assert before is not None

    code = main([
        "session", "status",
        "--database", str(database),
        "--session-id", "session-1",
    ])

    payload = _json_output(capsys)
    assert code == 0
    assert payload == {
        "action": "session.status",
        "checkpoint_id": before.checkpoint_id,
        "mode": "audit",
        "ok": True,
        "provider_id": "openai-compatible",
        "provider_model": "model-a",
        "session_id": "session-1",
        "workspace": before.canonical_workspace_root,
    }
    after = runtime.store.load_session_state(session_id="session-1")
    assert after is not None
    assert after.permission_policy_id == "read-policy"
    assert after.mode == before.mode
    assert after.provider_id == before.provider_id


def test_session_status_can_include_canonical_task_state(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    runtime = SessionMemoryRuntimeBridge(
        database_path=database,
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
        mode="coding",
    )
    runtime.record_task_status(
        task_id="task-1",
        status=TaskStatus.BLOCKED,
        last_outcome="VALIDATION_REQUIRED",
    )

    code = main([
        "session", "status",
        "--database", str(database),
        "--session-id", "session-1",
        "--task-id", "task-1",
    ])

    payload = _json_output(capsys)
    assert code == 0
    assert payload["task"]["task_id"] == "task-1"
    assert payload["task"]["status"] == "blocked"
    assert payload["task"]["last_outcome"] == "VALIDATION_REQUIRED"


def test_session_inspect_returns_persisted_contract_not_model_inference(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    SessionMemoryRuntimeBridge(
        database_path=database,
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
        mode="investigation",
        active_profile_id="profile-a",
        evidence_policy_id="evidence-a",
    )

    code = main([
        "session", "inspect",
        "--database", str(database),
        "--session-id", "session-1",
    ])

    payload = _json_output(capsys)
    assert code == 0
    assert payload["action"] == "session.inspect"
    assert payload["session"]["mode"] == "investigation"
    assert payload["session"]["active_profile_id"] == "profile-a"
    assert payload["session"]["evidence_policy_id"] == "evidence-a"


def test_session_continue_rehydrates_existing_runtime_identity(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    database = tmp_path / "memory.sqlite"
    runtime = SessionMemoryRuntimeBridge(
        database_path=database,
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
        mode="audit",
        provider_id="openai-compatible",
        provider_model="model-a",
    )
    runtime.checkpoint(
        compaction={
            "source_message_count": 1,
            "source_prefix_hash": "sha256:" + "a" * 64,
            "source_last_message_key": "id:msg-1",
            "messages": [],
        },
        active_constraints=["do not mutate"],
    )

    code = main([
        "session", "continue",
        "--database", str(database),
        "--session-id", "session-1",
    ])

    payload = _json_output(capsys)
    assert code == 0
    assert payload["action"] == "session.continue"
    assert payload["session"]["session_id"] == "session-1"
    assert payload["session"]["mode"] == "audit"
    assert payload["session"]["provider_id"] == "openai-compatible"
    assert payload["context"]["checkpoint"]["active_constraints"] == ["do not mutate"]


def test_provider_list_reads_registered_adapters_without_building_provider(capsys) -> None:
    code = main(["provider", "list"])

    payload = _json_output(capsys)
    assert code == 0
    assert payload == {
        "action": "provider.list",
        "ok": True,
        "providers": ["openai-compatible"],
    }


def test_missing_session_returns_structured_error(tmp_path: Path, capsys) -> None:
    code = main([
        "session", "status",
        "--database", str(tmp_path / "memory.sqlite"),
        "--session-id", "missing",
    ])

    payload = _json_output(capsys)
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"] == "FileNotFoundError"
    assert "persistent session not found: missing" in payload["message"]


def test_session_create_rejects_missing_workspace(tmp_path: Path, capsys) -> None:
    code = main([
        "session", "create",
        "--database", str(tmp_path / "memory.sqlite"),
        "--workspace", str(tmp_path / "missing"),
        "--project-workspace-id", "project-1",
        "--session-id", "session-1",
        "--mode", "coding",
    ])

    payload = _json_output(capsys)
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"] == "FileNotFoundError"
