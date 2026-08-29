"""Product-level LBE entry point.

`lbe start` composes the existing CLI/session/TUI owners into one first-run or
resume path. `lbe capabilities` projects persisted installed-integration
metadata without executing adapters. Every other pre-existing CLI command is
delegated to `lbe_guard_inspector.cli.main`; this module does not become a
second session, provider, credential, tool, or completion authority.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from . import cli as _cli
from . import read_only_exports
from .evidence_service import EvidenceService
from .runtime.mode_controller import ModeRequest, resolve_mode
from .runtime.installed_capability_registry import InstalledCapabilityRegistryStore
from .runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolRegistry,
    ToolRequest,
    build_workspace_read_handler,
    workspace_read_spec,
)
from agent import Context


def _build_start_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lbe start",
        description="Create or restore a persisted LBE session and enter the live LBE interface",
    )
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--database", required=True)
    parser.add_argument("--session-id", help="Existing session ID; omit to create a new persisted session")
    parser.add_argument("--workspace", help="Workspace root for a new session")
    parser.add_argument("--project-workspace-id", help="Project workspace identity for a new session")
    parser.add_argument("--mode", choices=("coding", "audit", "investigation"), help="Mode for a new session")
    parser.add_argument(
        "--permission",
        choices=("read_only", "write_allowed", "audit_only", "elevated"),
        default="read_only",
    )
    parser.add_argument(
        "--runtime-policy",
        choices=("audit", "development", "strict", "permissive"),
        default="audit",
    )
    parser.add_argument("--provider", help="Provider identity for a new session")
    parser.add_argument("--model", help="Provider model for a new session")
    parser.add_argument("--profile", help="Existing profile identity persisted on the new session")
    parser.add_argument("--permission-policy")
    parser.add_argument("--evidence-policy")
    parser.add_argument(
        "--provider-config",
        help="Explicit provider configuration used by the existing live turn runtime",
    )
    parser.add_argument(
        "--capability-registry",
        help="Installed capability registry JSON projected read-only in the live LBE interface",
    )
    return parser


def _build_capabilities_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lbe capabilities",
        description="Inspect persisted installed LBE capability configuration without executing adapters",
    )
    parser.add_argument("action", choices=("list", "validate"))
    parser.add_argument("--registry", required=True, help="Path to installed capability registry JSON")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def _build_export_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lbe export",
        description="Read-only Agent Wall projection export",
    )
    parser.add_argument(
        "projection",
        choices=("project_truth", "session_context", "provenance", "validation"),
    )
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--workspace")
    parser.add_argument("--workspace-id")
    parser.add_argument("--database")
    parser.add_argument("--session-id")
    parser.add_argument("--task-id")
    parser.add_argument("--configured-root-id")
    return parser


def _build_tool_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lbe tool",
        description="Invoke one explicitly registered governed LBE capability",
    )
    parser.add_argument("tool_id", choices=("workspace.read",))
    parser.add_argument("--database", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def _start(argv: Sequence[str]) -> int:
    parser = _build_start_parser()
    args = parser.parse_args(list(argv))
    previous_registry = os.environ.get("LBE_CAPABILITY_REGISTRY")
    try:
        if args.session_id is None:
            missing = [
                flag
                for flag, value in (
                    ("--workspace", args.workspace),
                    ("--project-workspace-id", args.project_workspace_id),
                    ("--mode", args.mode),
                )
                if not value
            ]
            if missing:
                raise ValueError("new LBE start requires " + ", ".join(missing))
            _cli._validate_provider_selection(args.provider, args.model, require_pair=False)
        else:
            forbidden = {
                "--workspace": args.workspace,
                "--project-workspace-id": args.project_workspace_id,
                "--mode": args.mode,
                "--provider": args.provider,
                "--model": args.model,
                "--profile": args.profile,
                "--permission-policy": args.permission_policy,
                "--evidence-policy": args.evidence_policy,
            }
            supplied = [name for name, value in forbidden.items() if value is not None]
            if supplied:
                raise ValueError(
                    "existing-session start restores persisted identity; remove "
                    + ", ".join(supplied)
                )

        if args.capability_registry is not None:
            registry_store = InstalledCapabilityRegistryStore(args.capability_registry)
            registry_store.load()
            os.environ["LBE_CAPABILITY_REGISTRY"] = str(registry_store.path)
        else:
            os.environ.pop("LBE_CAPABILITY_REGISTRY", None)

        payload = _cli._tui(args)
    except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError) as exc:
        _cli._emit(
            {"ok": False, "error": type(exc).__name__, "message": str(exc)},
            args.format,
        )
        return 2
    finally:
        if previous_registry is None:
            os.environ.pop("LBE_CAPABILITY_REGISTRY", None)
        else:
            os.environ["LBE_CAPABILITY_REGISTRY"] = previous_registry

    _cli._emit({"ok": True, **payload, "entry": "start"}, args.format)
    return 0


def _capabilities(argv: Sequence[str]) -> int:
    parser = _build_capabilities_parser()
    args = parser.parse_args(list(argv))
    try:
        store = InstalledCapabilityRegistryStore(args.registry)
        registry = store.load()
        statuses = registry.statuses({})
        payload = {
            "action": f"capabilities.{args.action}",
            "schema_version": registry.schema_version,
            "registry": str(store.path),
            "count": len(registry.records),
            "integrations": [status.public_payload() for status in statuses],
            "execution_attempted": False,
        }
    except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError) as exc:
        _cli._emit(
            {"ok": False, "error": type(exc).__name__, "message": str(exc)},
            args.format,
        )
        return 2

    _cli._emit({"ok": True, **payload}, args.format)
    return 0


def _export(argv: Sequence[str]) -> int:
    parser = _build_export_parser()
    args = parser.parse_args(list(argv))
    try:
        if args.projection == "project_truth":
            if not args.workspace:
                raise ValueError("--workspace is required for project_truth export")
            payload = read_only_exports.project_truth(
                workspace_root=args.workspace,
                configured_root_id=args.configured_root_id,
            )
        else:
            if not args.database:
                raise ValueError(f"--database is required for {args.projection} export")
            from .memory import WorkspaceMemoryStore

            store = WorkspaceMemoryStore(args.database)
            if args.projection == "session_context":
                if not args.session_id:
                    raise ValueError("--session-id is required for session_context export")
                payload = read_only_exports.session_context(
                    store=store,
                    session_id=args.session_id,
                    workspace_id=args.workspace_id,
                    workspace_root=args.workspace,
                    task_id=args.task_id,
                )
            elif args.projection == "provenance":
                if not args.workspace_id:
                    raise ValueError("--workspace-id is required for provenance export")
                payload = read_only_exports.provenance(
                    store=store,
                    workspace_id=args.workspace_id,
                    session_id=args.session_id,
                    task_id=args.task_id,
                )
            else:
                if not args.session_id or not args.task_id:
                    raise ValueError("--session-id and --task-id are required for validation export")
                payload = read_only_exports.validation(
                    store=store,
                    session_id=args.session_id,
                    task_id=args.task_id,
                )
    except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError) as exc:
        _cli._emit({"ok": False, "error": type(exc).__name__, "message": str(exc)}, args.format)
        return 2

    _cli._emit(payload, args.format)
    return 0


def _tool(argv: Sequence[str]) -> int:
    parser = _build_tool_parser()
    args = parser.parse_args(list(argv))
    try:
        store = _cli.WorkspaceMemoryStore(args.database)
        state = _cli._require_session(store, args.session_id)
        requested_root = Path(args.workspace).expanduser().resolve()
        persisted_root = Path(state.canonical_workspace_root).expanduser().resolve()
        if state.project_workspace_id != args.workspace_id:
            raise ValueError("workspace id does not match persisted session")
        if requested_root != persisted_root:
            raise ValueError("workspace root does not match persisted session")

        context_config = Context.load()
        configured_root = next(
            (root for root in context_config.roots if root.path == requested_root),
            None,
        )
        if configured_root is None:
            raise ValueError(f"workspace root is not configured for Agent Wall: {requested_root}")

        mode_decision = resolve_mode(ModeRequest(
            intent="inspect_workspace",
            permission=state.permission or "read_only",
            runtime_policy=state.runtime_policy or "audit",
            workspace_root=str(requested_root),
        ))
        context = ToolExecutionContext(
            mode_decision=mode_decision,
            workspace_id=state.project_workspace_id,
            workspace_root=requested_root,
            configured_root_id=configured_root.name,
        )
        registry = ToolRegistry()
        registry.register(workspace_read_spec(), build_workspace_read_handler(EvidenceService()))
        receipt = GovernedToolOrchestrator(registry=registry).invoke(
            ToolRequest(
                operation_id=args.operation_id,
                tool_id=args.tool_id,
                arguments={"path": args.path},
                context=context,
            )
        )
        payload = {
            "ok": True,
            "operation_id": receipt.operation_id,
            "tool_id": receipt.tool_id,
            "status": receipt.status.value,
            "receipt_id": receipt.receipt_id,
            "authorization": None if receipt.authorization is None else {
                "verdict": receipt.authorization.verdict.value,
                "capability": receipt.authorization.capability,
                "rationale": receipt.authorization.rationale,
            },
            "output": dict(receipt.output or {}),
            "evidence": [dict(item) for item in receipt.evidence],
            "error_code": receipt.error_code,
            "error_message": receipt.error_message,
        }
    except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError) as exc:
        _cli._emit({"ok": False, "error": type(exc).__name__, "message": str(exc)}, args.format)
        return 2
    _cli._emit(payload, args.format)
    return 0


def _dispatch_product_command(values: list[str], command: str) -> int:
    command_index = values.index(command)
    prefix = values[:command_index]
    suffix = values[command_index + 1 :]
    if prefix:
        if len(prefix) == 2 and prefix[0] == "--format" and prefix[1] in {"json", "text"}:
            if "--format" not in suffix:
                suffix = ["--format", prefix[1], *suffix]
        else:
            return _cli.main(values)
    if command == "start":
        return _start(suffix)
    if command == "capabilities":
        return _capabilities(suffix)
    if command == "export":
        return _export(suffix)
    if command == "tool":
        return _tool(suffix)
    raise AssertionError(f"unsupported product command: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)

    product_commands = [command for command in ("start", "capabilities", "export", "tool") if command in values]
    if not product_commands:
        return _cli.main(values)
    if len(product_commands) > 1:
        return _cli.main(values)
    return _dispatch_product_command(values, product_commands[0])


if __name__ == "__main__":
    raise SystemExit(main())
