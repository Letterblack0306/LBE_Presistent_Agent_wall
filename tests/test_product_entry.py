from __future__ import annotations

import json
from pathlib import Path

import pytest

from lbe_guard_inspector import product_entry
from lbe_guard_inspector.memory import WorkspaceMemoryStore


def _disable_live_ui(monkeypatch) -> None:
    # The Python/Textual UI has been removed; no live UI launches from `start`.
    return None


def _last_json(capsys) -> dict[str, object]:
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    return json.loads(lines[-1])


def test_start_creates_one_persisted_session_and_enters_existing_tui_owner(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _disable_live_ui(monkeypatch)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"

    code = product_entry.main(
        [
            "start",
            "--database",
            str(database),
            "--workspace",
            str(workspace),
            "--project-workspace-id",
            "project-1",
            "--mode",
            "coding",
            "--permission",
            "write_allowed",
            "--runtime-policy",
            "development",
            "--provider",
            "openai-compatible",
            "--model",
            "model-a",
            "--profile",
            "profile-a",
        ]
    )

    assert code == 0
    payload = _last_json(capsys)
    assert payload["ok"] is True
    assert payload["action"] == "tui"
    assert payload["entry"] == "start"
    session_id = str(payload["session_id"])

    state = WorkspaceMemoryStore(database).load_session_state(session_id=session_id)
    assert state is not None
    assert state.session_id == session_id
    assert state.project_workspace_id == "project-1"
    assert Path(state.canonical_workspace_root).resolve() == workspace.resolve()
    assert state.mode == "coding"
    assert state.permission == "write_allowed"
    assert state.runtime_policy == "development"
    assert state.provider_id == "openai-compatible"
    assert state.provider_model == "model-a"
    assert state.active_profile_id == "profile-a"


def test_start_existing_session_restores_same_persisted_identity(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _disable_live_ui(monkeypatch)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"

    assert product_entry.main(
        [
            "start",
            "--database",
            str(database),
            "--workspace",
            str(workspace),
            "--project-workspace-id",
            "project-1",
            "--mode",
            "audit",
        ]
    ) == 0
    created = _last_json(capsys)
    session_id = str(created["session_id"])
    before = WorkspaceMemoryStore(database).load_session_state(session_id=session_id)
    assert before is not None

    assert product_entry.main(
        ["start", "--database", str(database), "--session-id", session_id]
    ) == 0
    restored = _last_json(capsys)
    assert restored["session_id"] == session_id
    after = WorkspaceMemoryStore(database).load_session_state(session_id=session_id)
    assert after is not None
    assert after.as_dict() == before.as_dict()


def test_existing_session_start_rejects_identity_override_before_tui(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    called = False

    def fail_tui(_args):
        nonlocal called
        called = True
        raise AssertionError("TUI must not run")

    monkeypatch.setattr(product_entry._cli, "_tui", fail_tui)
    code = product_entry.main(
        [
            "start",
            "--database",
            str(tmp_path / "lbe.sqlite"),
            "--session-id",
            "existing",
            "--provider",
            "openai-compatible",
        ]
    )
    assert code == 2
    assert called is False
    payload = _last_json(capsys)
    assert payload["ok"] is False
    assert "restores persisted identity" in str(payload["message"])


def test_new_start_requires_workspace_project_identity_and_mode(tmp_path: Path, capsys) -> None:
    code = product_entry.main(["start", "--database", str(tmp_path / "lbe.sqlite")])
    assert code == 2
    payload = _last_json(capsys)
    assert payload["ok"] is False
    assert "--workspace" in str(payload["message"])
    assert "--project-workspace-id" in str(payload["message"])
    assert "--mode" in str(payload["message"])


def test_new_start_rejects_unpaired_provider_selection(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    code = product_entry.main(
        [
            "start",
            "--database",
            str(tmp_path / "lbe.sqlite"),
            "--workspace",
            str(workspace),
            "--project-workspace-id",
            "project-1",
            "--mode",
            "coding",
            "--provider",
            "openai-compatible",
        ]
    )
    assert code == 2
    payload = _last_json(capsys)
    assert payload["ok"] is False
    assert "provider model" in str(payload["message"])


def test_start_provider_config_mismatch_fails_closed_before_live_turn_runtime(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _disable_live_ui(monkeypatch)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"
    config = tmp_path / "provider.json"
    config.write_text(
        json.dumps(
            {
                "endpoint": "http://127.0.0.1:1234/v1/chat/completions",
                "model": "different-model",
                "timeout_seconds": 5,
            }
        ),
        encoding="utf-8",
    )

    code = product_entry.main(
        [
            "start",
            "--database",
            str(database),
            "--workspace",
            str(workspace),
            "--project-workspace-id",
            "project-1",
            "--mode",
            "coding",
            "--permission",
            "write_allowed",
            "--runtime-policy",
            "development",
            "--provider",
            "openai-compatible",
            "--model",
            "model-a",
            "--provider-config",
            str(config),
        ]
    )
    assert code == 2
    payload = _last_json(capsys)
    assert payload["ok"] is False
    assert "must match persisted session model" in str(payload["message"])


def test_non_start_commands_delegate_to_legacy_cli(monkeypatch) -> None:
    observed: list[list[str]] = []

    def fake_main(argv):
        observed.append(list(argv))
        return 17

    monkeypatch.setattr(product_entry._cli, "main", fake_main)
    assert product_entry.main(["provider", "list"]) == 17
    assert observed == [["provider", "list"]]


def test_global_format_before_start_is_preserved(tmp_path: Path, monkeypatch, capsys) -> None:
    _disable_live_ui(monkeypatch)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    code = product_entry.main(
        [
            "--format",
            "text",
            "start",
            "--database",
            str(tmp_path / "lbe.sqlite"),
            "--workspace",
            str(workspace),
            "--project-workspace-id",
            "project-1",
            "--mode",
            "audit",
        ]
    )
    assert code == 0
    output = capsys.readouterr().out
    assert "tui" in output
    assert "entry: start" in output



def test_product_entry_approval_bridge_executes_exact_operation_once(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from types import SimpleNamespace

    from lbe_guard_inspector.memory.models import SessionState
    from lbe_guard_inspector.runtime.tool_orchestration import ToolExecutionResult

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "target.txt"
    target.write_text("before", encoding="utf-8")
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    store.save_session_state(
        SessionState(
            session_id="session-approval",
            project_workspace_id="project-approval",
            canonical_workspace_root=str(workspace.resolve()),
            mode="coding",
            permission="write_allowed",
            runtime_policy="development",
        )
    )

    monkeypatch.setattr(
        product_entry.Context,
        "load",
        staticmethod(
            lambda: SimpleNamespace(
                roots=[SimpleNamespace(path=workspace.resolve(), name="test-root")]
            )
        ),
    )
    calls: list[str] = []

    def fake_patch_handler():
        def handler(request):
            calls.append(request.operation_id)
            content = str(request.arguments["content"])
            target.write_text(content, encoding="utf-8")
            return ToolExecutionResult(
                output={
                    "path": "target.txt",
                    "created": False,
                    "updated": True,
                    "bytes": len(content.encode("utf-8")),
                    "before_sha256": str(request.arguments["expected_sha256"]),
                    "sha256": "b" * 64,
                    "patch": "-before\n+after",
                },
                evidence=(
                    {
                        "ref": "workspace:project-approval:target.txt",
                        "verified": True,
                        "metadata": {
                            "operation_id": request.operation_id,
                            "tool_id": request.tool_id,
                        },
                    },
                ),
            )

        return handler

    monkeypatch.setattr(
        product_entry,
        "build_workspace_patch_handler",
        fake_patch_handler,
    )

    base = [
        "tool",
        "workspace.patch",
        "--database",
        str(database),
        "--session-id",
        "session-approval",
        "--workspace-id",
        "project-approval",
        "--workspace",
        str(workspace),
        "--path",
        "target.txt",
        "--content",
        "after",
        "--expected-sha256",
        "a" * 64,
        "--operation-id",
        "op-approved-patch",
        "--format",
        "json",
    ]

    assert product_entry.main(base) == 0
    escalated = _last_json(capsys)
    assert escalated["status"] == "ESCALATED"
    assert escalated["approval_id"]
    assert calls == []
    assert target.read_text(encoding="utf-8") == "before"

    approval_id = str(escalated["approval_id"])
    assert product_entry.main(
        [
            "authorization",
            "resolve",
            "--database",
            str(database),
            "--session-id",
            "session-approval",
            "--workspace-id",
            "project-approval",
            "--workspace",
            str(workspace),
            "--capability",
            "modify",
            "--operation-id",
            "op-approved-patch",
            "--approval-id",
            approval_id,
            "--decision",
            "approve",
            "--format",
            "json",
        ]
    ) == 0
    approved = _last_json(capsys)
    assert approved["verdict"] == "ALLOW"

    assert product_entry.main(base) == 0
    executed = _last_json(capsys)
    assert executed["status"] == "EXECUTED"
    receipt_id = executed["receipt_id"]
    assert calls == ["op-approved-patch"]
    assert target.read_text(encoding="utf-8") == "after"

    assert product_entry.main(base) == 0
    replay = _last_json(capsys)
    assert replay["status"] == "EXECUTED"
    assert replay["receipt_id"] == receipt_id
    assert calls == ["op-approved-patch"]

    changed = base.copy()
    changed[changed.index("after")] = "substituted"
    assert product_entry.main(changed) == 2
    rejected = _last_json(capsys)
    assert rejected["ok"] is False
    assert "payload" in str(rejected["message"]).lower()
    assert calls == ["op-approved-patch"]
