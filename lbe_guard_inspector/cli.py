"""Thin CLI control plane for the persistent LBE runtime.

The CLI parses operator input and delegates to existing runtime/data owners. It
must not become a second session controller, provider authority, permission
resolver, tool executor, or completion gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .memory import WorkspaceMemoryStore
from .provider_registry import default_provider_registry
from .session_memory_runtime import SessionMemoryRuntimeBridge


_MODES = ("coding", "audit", "investigation")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lbe",
        description="Persistent LBE runtime control plane",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    session = commands.add_parser("session", help="Manage persistent sessions")
    session_commands = session.add_subparsers(dest="session_command", required=True)

    create = session_commands.add_parser("create", help="Create a persistent session")
    _add_database_argument(create)
    create.add_argument("--workspace", required=True)
    create.add_argument("--project-workspace-id", required=True)
    create.add_argument("--session-id", required=True)
    create.add_argument("--mode", required=True, choices=_MODES)
    create.add_argument("--provider")
    create.add_argument("--model")
    create.add_argument("--profile")
    create.add_argument("--permission-policy")
    create.add_argument("--evidence-policy")
    create.set_defaults(handler=_session_create)

    continue_parser = session_commands.add_parser(
        "continue", help="Rehydrate an existing persistent session"
    )
    _add_database_argument(continue_parser)
    continue_parser.add_argument("--session-id", required=True)
    continue_parser.add_argument("--task-id")
    continue_parser.set_defaults(handler=_session_continue)

    status = session_commands.add_parser("status", help="Read persisted session status")
    _add_database_argument(status)
    status.add_argument("--session-id", required=True)
    status.add_argument("--task-id")
    status.set_defaults(handler=_session_status)

    inspect_parser = session_commands.add_parser(
        "inspect", help="Inspect persisted session identity and lifecycle state"
    )
    _add_database_argument(inspect_parser)
    inspect_parser.add_argument("--session-id", required=True)
    inspect_parser.add_argument("--task-id")
    inspect_parser.set_defaults(handler=_session_inspect)

    provider = commands.add_parser("provider", help="Inspect reasoning providers")
    provider_commands = provider.add_subparsers(dest="provider_command", required=True)
    provider_list = provider_commands.add_parser("list", help="List registered providers")
    provider_list.set_defaults(handler=_provider_list)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args)
    except (ValueError, TypeError, FileNotFoundError, RuntimeError) as exc:
        _emit({
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        })
        return 2
    _emit({"ok": True, **payload})
    return 0


def _session_create(args: argparse.Namespace) -> dict[str, Any]:
    workspace = _workspace_root(args.workspace)
    runtime = SessionMemoryRuntimeBridge(
        database_path=args.database,
        project_workspace_id=args.project_workspace_id,
        workspace_root=workspace,
        session_id=args.session_id,
        mode=args.mode,
        provider_id=args.provider,
        provider_model=args.model,
        active_profile_id=args.profile,
        permission_policy_id=args.permission_policy,
        evidence_policy_id=args.evidence_policy,
    )
    return {
        "action": "session.create",
        "session": runtime.session_state.as_dict(),
    }


def _session_continue(args: argparse.Namespace) -> dict[str, Any]:
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    runtime = SessionMemoryRuntimeBridge(
        database_path=args.database,
        project_workspace_id=state.project_workspace_id,
        workspace_root=state.canonical_workspace_root,
        session_id=state.session_id,
        mode=state.mode,
        provider_id=state.provider_id,
        provider_model=state.provider_model,
        active_profile_id=state.active_profile_id,
        permission_policy_id=state.permission_policy_id,
        evidence_policy_id=state.evidence_policy_id,
    )
    packet = runtime.start_or_resume(task_id=args.task_id)
    return {
        "action": "session.continue",
        "session": runtime.session_state.as_dict(),
        "context": packet,
    }


def _session_status(args: argparse.Namespace) -> dict[str, Any]:
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    payload: dict[str, Any] = {
        "action": "session.status",
        "session_id": state.session_id,
        "mode": state.mode,
        "workspace": state.canonical_workspace_root,
        "provider_id": state.provider_id,
        "provider_model": state.provider_model,
        "checkpoint_id": state.checkpoint_id,
    }
    if args.task_id:
        task = store.load_session_task(
            session_id=state.session_id,
            task_id=args.task_id,
            project_workspace_id=state.project_workspace_id,
        )
        payload["task"] = _task_payload(task)
    return payload


def _session_inspect(args: argparse.Namespace) -> dict[str, Any]:
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    payload: dict[str, Any] = {
        "action": "session.inspect",
        "session": state.as_dict(),
    }
    if args.task_id:
        task = store.load_session_task(
            session_id=state.session_id,
            task_id=args.task_id,
            project_workspace_id=state.project_workspace_id,
        )
        payload["task"] = _task_payload(task)
    return payload


def _provider_list(args: argparse.Namespace) -> dict[str, Any]:
    del args
    registry = default_provider_registry()
    return {
        "action": "provider.list",
        "providers": list(registry.provider_ids()),
    }


def _require_session(store: WorkspaceMemoryStore, session_id: str):
    clean_id = str(session_id).strip()
    if not clean_id:
        raise ValueError("session_id must not be empty")
    state = store.load_session_state(session_id=clean_id)
    if state is None:
        raise FileNotFoundError(f"persistent session not found: {clean_id}")
    return state


def _workspace_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"workspace does not exist or is not a directory: {root}")
    return root


def _task_payload(task: Any) -> dict[str, Any] | None:
    if task is None:
        return None
    return {
        "session_id": task.session_id,
        "task_id": task.task_id,
        "project_workspace_id": task.project_workspace_id,
        "canonical_workspace_root": task.canonical_workspace_root,
        "status": task.status.value,
        "last_outcome": task.last_outcome,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _add_database_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--database",
        required=True,
        help="Path to the persistent LBE SQLite database",
    )


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
