"""Tests for the thin governed BirdEye MCP add-on (Cline product surface)."""
from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from lbe_guard_inspector import cli as _cli
from lbe_guard_inspector import product_entry
from lbe_guard_inspector.memory import WorkspaceMemoryStore
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.runtime import cline_governed_birdeye as addon_module
from lbe_guard_inspector.runtime.tool_orchestration import ToolExecutionResult

_READ_CATALOG = [
    {
        "name": "birdeye_search",
        "description": "Rank-indexed search over the live SQLite index.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
    },
    {
        "name": "knowledge_read",
        "description": "Read one GPT-Knowledge document.",
        "inputSchema": {"type": "object", "properties": {"reference": {"type": "string"}}},
    },
]


def _context(workspace: Path) -> SimpleNamespace:
    return SimpleNamespace(
        roots=[SimpleNamespace(path=Path(workspace).resolve(), name="test-root")]
    )


def _write_session(
    store: WorkspaceMemoryStore,
    *,
    workspace: Path,
    session_id: str = "session-addon",
    project_workspace_id: str = "project-addon",
    mode: str = "coding",
    permission: str = "write_allowed",
    runtime_policy: str = "development",
) -> None:
    store.save_session_state(
        SessionState(
            session_id=session_id,
            project_workspace_id=project_workspace_id,
            canonical_workspace_root=str(workspace.resolve()),
            mode=mode,
            permission=permission,
            runtime_policy=runtime_policy,
        )
    )


def _addon(
    store: WorkspaceMemoryStore,
    *,
    session_id: str,
    workspace: Path,
    governed_handler_builder=None,
    read_tools=None,
) -> addon_module.GovernedBirdeyeAddon:
    session = _cli._require_session(store, session_id)
    return addon_module.GovernedBirdeyeAddon(
        store=store,
        session=session,
        workspace_root=workspace,
        context_loader=lambda: _context(workspace),
        read_tools=_READ_CATALOG if read_tools is None else read_tools,
        governed_handler_builder=governed_handler_builder or addon_module.build_birdeye_mcp_handler,
    )


def _call(
    addon: addon_module.GovernedBirdeyeAddon,
    name: str,
    *,
    arguments: dict,
    request_id: int = 1,
) -> dict:
    return addon._dispatch({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    })


def _roundtrip(addon: addon_module.GovernedBirdeyeAddon, messages) -> list[dict]:
    payload = "\n".join(json.dumps(message) for message in messages) + "\n"
    output = io.StringIO()
    addon.serve_stdio(stdin=io.StringIO(payload), stdout=output)
    return [json.loads(line) for line in output.getvalue().splitlines() if line.strip()]


def _governed_count(database: Path) -> int:
    with sqlite3.connect(database) as connection:
        return int(connection.execute(
            "SELECT COUNT(*) FROM governed_operations"
        ).fetchone()[0])


def _patch_executor(workspace: Path, calls: list[str]):
    def fake_patch_handler():
        def handler(request):
            calls.append(request.operation_id)
            content = str(request.arguments["content"])
            (workspace / request.arguments["path"]).write_text(content, encoding="utf-8")
            return ToolExecutionResult(
                output={
                    "path": request.arguments["path"],
                    "created": False,
                    "updated": True,
                    "bytes": len(content.encode("utf-8")),
                    "before_sha256": str(request.arguments["expected_sha256"]),
                    "sha256": "b" * 64,
                    "patch": "-before\n+after",
                },
                evidence=(
                    {
                        "ref": f"workspace:{request.tool_id}:{request.arguments['path']}",
                        "verified": True,
                        "metadata": {
                            "operation_id": request.operation_id,
                            "tool_id": request.tool_id,
                        },
                    },
                ),
            )

        return handler

    return fake_patch_handler


def test_governed_write_requires_approval_then_executes_exact_operation_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "target.txt"
    target.write_text("before", encoding="utf-8")
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace)
    calls: list[str] = []
    monkeypatch.setattr(
        addon_module,
        "build_workspace_patch_handler",
        _patch_executor(workspace, calls),
    )
    addon = _addon(store, session_id="session-addon", workspace=workspace)

    escalated = _call(addon, "lbe_governed_execute", arguments={
        "tool_id": "workspace.patch",
        "arguments": {
            "path": "target.txt",
            "content": "after",
            "expected_sha256": "a" * 64,
        },
        "operation_id": "op-approved-patch",
    })
    payload = json.loads(escalated["result"]["content"][0]["text"])
    assert payload["status"] == "ESCALATED"
    assert payload["approval_id"]
    assert calls == []
    assert target.read_text(encoding="utf-8") == "before"
    assert _governed_count(database) == 1

    approval_id = str(payload["approval_id"])
    assert product_entry.main([
        "authorization", "resolve",
        "--database", str(database),
        "--session-id", "session-addon",
        "--workspace-id", "project-addon",
        "--workspace", str(workspace),
        "--capability", "modify",
        "--operation-id", "op-approved-patch",
        "--approval-id", approval_id,
        "--decision", "approve",
        "--format", "json",
    ]) == 0

    executed = _call(addon, "lbe_governed_execute", arguments={
        "tool_id": "workspace.patch",
        "arguments": {
            "path": "target.txt",
            "content": "after",
            "expected_sha256": "a" * 64,
        },
        "operation_id": "op-approved-patch",
    })
    executed_payload = json.loads(executed["result"]["content"][0]["text"])
    assert executed_payload["status"] == "EXECUTED"
    receipt_id = executed_payload["receipt_id"]
    assert calls == ["op-approved-patch"]
    assert target.read_text(encoding="utf-8") == "after"

    replay = _call(addon, "lbe_governed_execute", arguments={
        "tool_id": "workspace.patch",
        "arguments": {
            "path": "target.txt",
            "content": "after",
            "expected_sha256": "a" * 64,
        },
        "operation_id": "op-approved-patch",
    })
    replay_payload = json.loads(replay["result"]["content"][0]["text"])
    assert replay_payload["status"] == "EXECUTED"
    assert replay_payload["receipt_id"] == receipt_id
    assert calls == ["op-approved-patch"]

    substituted = _call(addon, "lbe_governed_execute", arguments={
        "tool_id": "workspace.patch",
        "arguments": {
            "path": "target.txt",
            "content": "substituted",
            "expected_sha256": "a" * 64,
        },
        "operation_id": "op-approved-patch",
    })
    assert "error" in substituted
    assert substituted["error"]["code"] == -32603
    assert calls == ["op-approved-patch"]


def test_read_tool_is_read_only_and_writes_no_wall_rows(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace)

    def fake_builder(name: str):
        def handler(request):
            return ToolExecutionResult(
                output={"name": name, "query": request.arguments["arguments"], "evidence": []},
                evidence=(),
            )

        return handler

    addon = _addon(
        store,
        session_id="session-addon",
        workspace=workspace,
        governed_handler_builder=fake_builder,
    )
    assert _governed_count(database) == 0

    result = _call(addon, "birdeye_search", arguments={"query": "govern"},
                   request_id=2)
    assert result["result"]["content"][0]["type"] == "text"
    payload = json.loads(result["result"]["content"][0]["text"])
    assert payload["read_only"] is True
    assert payload["governed"] is False
    assert payload["name"] == "birdeye_search"
    assert _governed_count(database) == 0


def test_session_status_is_read_only_projection(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace)
    addon = _addon(store, session_id="session-addon", workspace=workspace)

    result = _call(addon, "lbe_session_status", arguments={})
    payload = json.loads(result["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["session_id"] == "session-addon"
    assert payload["workspace_id"] == "project-addon"
    assert payload["workspace_root"] == str(workspace.resolve())
    assert payload["mode"] == "coding"
    assert payload["permission"] == "write_allowed"
    assert payload["runtime_policy"] == "development"
    assert payload["database"] == str(database)
    assert _governed_count(database) == 0


def test_read_only_session_denies_write_before_executor(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace, permission="read_only", runtime_policy="audit")
    calls: list[str] = []
    addon = _addon(
        store,
        session_id="session-addon",
        workspace=workspace,
        governed_handler_builder=_patch_executor(workspace, calls),
    )

    denied = _call(addon, "lbe_governed_execute", arguments={
        "tool_id": "workspace.patch",
        "arguments": {
            "path": "target.txt",
            "content": "after",
            "expected_sha256": "a" * 64,
        },
        "operation_id": "op-denied-patch",
    })
    payload = json.loads(denied["result"]["content"][0]["text"])
    assert payload["status"] == "DENIED"
    assert payload["error_code"] == "AUTHORIZATION_DENIED"
    assert calls == []
    assert _governed_count(database) == 0


def test_unknown_tool_is_rejected(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace)
    addon = _addon(store, session_id="session-addon", workspace=workspace)

    rejected = _call(addon, "lbe_governed_execute", arguments={
        "tool_id": "workspace.delete",
        "arguments": {"path": "x.txt"},
    })
    assert "error" in rejected
    assert "tool is not registered: workspace.delete" in rejected["error"]["message"]


def test_tools_list_advertises_read_catalog_and_governed_surface(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace)
    addon = _addon(store, session_id="session-addon", workspace=workspace)

    listed = addon._dispatch({
        "jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {},
    })
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert "birdeye_search" in names
    assert "knowledge_read" in names
    assert "lbe_session_status" in names
    assert "lbe_governed_execute" in names
    search = next(tool for tool in listed["result"]["tools"] if tool["name"] == "birdeye_search")
    assert "read-only" in search["description"].lower()


def test_constructor_fails_closed_on_workspace_root_mismatch(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace)

    with pytest.raises(ValueError, match="workspace root does not match persisted session"):
        _addon(store, session_id="session-addon", workspace=other)


def test_env_fails_closed_when_session_database_or_workspace_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="LBE_SESSION_ID"):
        addon_module.build_addon_from_environment(environ={})

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace)

    with pytest.raises(ValueError, match="LBE_TARGET_WORKSPACE"):
        addon_module.build_addon_from_environment(environ={
            "LBE_SESSION_ID": "session-addon",
            "LBE_WALL_DATABASE": str(database),
        })

    with pytest.raises(FileNotFoundError):
        addon_module.build_addon_from_environment(environ={
            "LBE_SESSION_ID": "missing-session",
            "LBE_WALL_DATABASE": str(database),
            "LBE_TARGET_WORKSPACE": str(workspace),
        })


def test_serve_stdio_round_trips_initialize_list_and_ping(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    database = tmp_path / "lbe.sqlite"
    store = WorkspaceMemoryStore(database)
    _write_session(store, workspace=workspace)
    addon = _addon(store, session_id="session-addon", workspace=workspace)

    responses = _roundtrip(addon, [
        {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "cline", "version": "test"},
        }},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ])
    initialize = next(item for item in responses if item.get("id") == 0)
    assert initialize["result"]["protocolVersion"] == "2024-11-05"
    assert initialize["result"]["serverInfo"]["name"] == "lbe-birdeye"
    names = [tool["name"] for tool in next(
        item for item in responses if item.get("id") == 2
    )["result"]["tools"]]
    assert "lbe_governed_execute" in names
    pinged = next(item for item in responses if item.get("id") == 1)
    assert pinged["result"] == {}