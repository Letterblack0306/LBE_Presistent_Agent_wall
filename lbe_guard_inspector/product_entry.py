"""Product-level LBE entry point.

`lbe start` composes the existing CLI/session/TUI owners into one first-run or
resume path. `lbe capabilities` projects persisted installed-integration
metadata without executing adapters. Every other pre-existing CLI command is
delegated to `lbe_guard_inspector.cli.main`; this module does not become a
second session, provider, credential, tool, or completion authority.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import hashlib
import time
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from . import cli as _cli
from .control_protocol import ControlMethod, ControlRequest
from .agent_integration import AgentMode, GovernedAgentGateway
from . import read_only_exports
from .evidence_service import EvidenceService
from .runtime.mode_controller import ModeRequest, resolve_mode
from .runtime.external_capabilities import (
    birdeye_mcp_tool_spec,
    build_birdeye_mcp_handler,
)
from .runtime.authorization_resolver import AuthorizationRequest, resolve_authorization, AuthorizationVerdict
from .runtime.installed_capability_registry import InstalledCapabilityRegistryStore
from .runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolRegistry,
    ToolRequest,
    build_workspace_list_handler,
    build_workspace_glob_handler,
    build_workspace_search_handler,
    build_workspace_read_handler,
    workspace_glob_spec,
    workspace_search_spec,
    workspace_list_spec,
    workspace_read_spec,
)
from .runtime.governed_coding import (
    build_process_run_registered_handler,
    build_workspace_patch_handler,
    process_run_registered_spec,
    workspace_patch_spec,
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


def _build_turn_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lbe turn",
        description="Start one conversational turn through the persisted LBE runtime",
    )
    parser.add_argument("--database", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--provider-config", required=True)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def _build_control_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lbe control",
        description="Apply a persisted turn control operation",
    )
    parser.add_argument("action", choices=("cancel", "interrupt"))
    parser.add_argument("--database", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--turn-id", required=True)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def _serialize_operational_event(event: object) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "session_id": event.session_id,
        "turn_id": event.turn_id,
        "event_type": event.event_type,
        "payload": dict(event.payload),
        "provider_id": event.provider_id,
        "model_id": event.model_id,
        "provider_request_id": event.provider_request_id,
        "provider_item_id": event.provider_item_id,
        "provider_tool_call_id": event.provider_tool_call_id,
        "lbe_call_id": event.lbe_call_id,
        "runtime_operation_id": event.runtime_operation_id,
        "tool_receipt_id": event.tool_receipt_id,
        "created_at": event.created_at,
        "session_sequence": event.session_sequence,
        "turn_sequence": event.turn_sequence,
    }


def _turn(argv: Sequence[str]) -> int:
    parser = _build_turn_parser()
    args = parser.parse_args(list(argv))
    try:
        from .memory.operational_history import SessionOperationalHistory
        from .persistent_turn_control import PersistentTurnControl
        from .provider_turn_runtime import GovernedCodingTurnRuntime, GovernedProviderTurnRuntime
        from .reasoning_runtime import build_provider_controller
        from .runtime.governed_coding import GovernedProviderReasoningController

        store = _cli.WorkspaceMemoryStore(args.database)
        state = _cli._require_session(store, args.session_id)
        config = _cli.load_provider_config(args.provider_config)
        if config.model != state.provider_model:
            raise ValueError("provider config model must match persisted session model")
        history = SessionOperationalHistory(store=store)
        runtime = _cli._runtime_from_state(database=args.database, state=state)
        if state.mode == "coding" and state.permission not in {"read_only", "audit_only"}:
            controller = GovernedProviderReasoningController(
                runtime=runtime, provider_id=state.provider_id, provider_config=config
            )
            provider_runtime = GovernedCodingTurnRuntime(
                history=history,
                gateway=GovernedAgentGateway(runtime=runtime, reasoning_controller=controller),
            )
        else:
            controller, _ = build_provider_controller(
                provider_id=state.provider_id,
                provider_config=config,
            )
            provider_runtime = GovernedProviderTurnRuntime(
                history=history,
                gateway=GovernedAgentGateway(runtime=runtime, reasoning_controller=controller),
                mode=AgentMode(state.mode),
            )
        control = PersistentTurnControl(history=history, provider_runtime=provider_runtime)
        outcome = control.handle(ControlRequest(
            request_id=f"bridge-{uuid4().hex}",
            method=ControlMethod.TURN_START,
            params={"session_id": state.session_id, "text": args.text},
        ))
        if outcome.accepted:
            deadline = time.monotonic() + float(config.timeout_seconds) + 5.0
            while time.monotonic() < deadline:
                running = history.latest_running_turn(session_id=state.session_id)
                if running is None:
                    break
                time.sleep(0.05)
        turn = history.latest_running_turn(session_id=state.session_id)
        if turn is None:
            turns = history.events_for_session(session_id=state.session_id)
            turn_id = turns[-1].turn_id if turns else None
        else:
            turn_id = turn.turn_id
        events = history.events_for_turn(turn_id=turn_id) if turn_id else ()
        payload = {
            "ok": outcome.accepted,
            "request_id": outcome.request_id,
            "state": outcome.state,
            "reason": outcome.reason,
            "session_id": state.session_id,
            "turn_id": turn_id,
            "mode": state.mode,
            "events": [_serialize_operational_event(event) for event in events],
        }
        if not outcome.accepted:
            payload["error"] = "TURN_START_REJECTED"
    except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError, KeyError) as exc:
        _cli._emit({"ok": False, "error": type(exc).__name__, "message": str(exc)}, args.format)
        return 2
    _cli._emit(payload, args.format)
    return 0


def _control(argv: Sequence[str]) -> int:
    parser = _build_control_parser()
    args = parser.parse_args(list(argv))
    try:
        from .memory.operational_history import SessionOperationalHistory
        from .persistent_turn_control import PersistentTurnControl

        store = _cli.WorkspaceMemoryStore(args.database)
        history = SessionOperationalHistory(store=store)
        outcome = PersistentTurnControl(history=history).handle(ControlRequest(
            request_id=f"control-{uuid4().hex}",
            method=ControlMethod.TURN_CANCEL if args.action == "cancel" else ControlMethod.TURN_INTERRUPT,
            params={"session_id": args.session_id, "turn_id": args.turn_id},
        ))
        payload = {
            "ok": outcome.accepted,
            "action": f"turn.{args.action}",
            "request_id": outcome.request_id,
            "state": outcome.state,
            "reason": outcome.reason,
            "session_id": args.session_id,
            "turn_id": args.turn_id,
        }
        if not outcome.accepted:
            payload["error"] = "TURN_CONTROL_REJECTED"
    except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError, KeyError) as exc:
        _cli._emit({"ok": False, "error": type(exc).__name__, "message": str(exc)}, args.format)
        return 2
    _cli._emit(payload, args.format)
    return 0


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
    parser.add_argument("tool_id")
    parser.add_argument("--database", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--content")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--command-id")
    parser.add_argument("--arguments", help="JSON object for external capability arguments")
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def _build_authorization_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lbe authorization")
    parser.add_argument("action", choices=("evaluate", "resolve"))
    parser.add_argument("--database", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--capability", required=True)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--approval-id")
    parser.add_argument("--decision", choices=("approve", "reject"))
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
            intent="fix_issue" if args.tool_id == "workspace.patch" else "inspect_workspace",
            permission=state.permission or "read_only",
            runtime_policy=state.runtime_policy or "audit",
            workspace_root=str(requested_root),
        ))
        context = ToolExecutionContext(
            mode_decision=mode_decision,
            workspace_id=state.project_workspace_id,
            workspace_root=requested_root,
            configured_root_id=configured_root.name,
            explicitly_forbidden=(
                args.tool_id in {"workspace.patch", "process.run_registered"}
                and (state.permission or "read_only") in {"read_only", "audit_only"}
            ),
        )
        registry = ToolRegistry()
        registry.register(workspace_read_spec(), build_workspace_read_handler(EvidenceService()))
        registry.register(workspace_list_spec(), build_workspace_list_handler())
        registry.register(workspace_glob_spec(), build_workspace_glob_handler())
        registry.register(workspace_search_spec(), build_workspace_search_handler(EvidenceService()))
        registry.register(workspace_patch_spec(), build_workspace_patch_handler())
        registry.register(process_run_registered_spec(), build_process_run_registered_handler())
        if args.tool_id.startswith("mcp.birdeye."):
            birdeye_tool = args.tool_id.removeprefix("mcp.birdeye.")
            registry.register(birdeye_mcp_tool_spec(birdeye_tool), build_birdeye_mcp_handler(birdeye_tool))
        if args.tool_id.startswith("mcp.birdeye."):
            if args.arguments is None:
                raise ValueError("--arguments is required for BirdEye MCP tools")
            arguments = {"arguments": json.loads(args.arguments)}
        elif args.tool_id == "workspace.glob":
            arguments = {"pattern": args.path}
        elif args.tool_id == "workspace.search":
            arguments = {"query": args.path}
        elif args.tool_id == "workspace.patch":
            arguments = {
                "path": args.path,
                "content": args.content,
                "expected_sha256": args.expected_sha256,
            }
        elif args.tool_id == "process.run_registered":
            arguments = {"command_id": args.command_id}
        else:
            arguments = {"path": args.path}
        receipt = GovernedToolOrchestrator(registry=registry).invoke(
            ToolRequest(
                operation_id=args.operation_id,
                tool_id=args.tool_id,
                arguments=arguments,
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


def _authorization(argv: Sequence[str]) -> int:
    parser = _build_authorization_parser()
    args = parser.parse_args(list(argv))
    try:
        store = _cli.WorkspaceMemoryStore(args.database)
        state = _cli._require_session(store, args.session_id)
        requested_root = Path(args.workspace).expanduser().resolve()
        if state.project_workspace_id != args.workspace_id:
            raise ValueError("workspace id does not match persisted session")
        if requested_root != Path(state.canonical_workspace_root).expanduser().resolve():
            raise ValueError("workspace root does not match persisted session")
        intent = "fix_issue" if args.capability in {"modify", "test_candidate", "validate_proposal"} else "inspect_workspace"
        mode = resolve_mode(ModeRequest(
            intent=intent,
            permission=state.permission or "read_only",
            runtime_policy=state.runtime_policy or "audit",
            workspace_root=str(requested_root),
        ))
        approval_id = "approval-" + hashlib.sha256(
            f"{args.operation_id}:{args.capability}:{state.project_workspace_id}".encode()
        ).hexdigest()[:24]
        explicitly_forbidden = (
            args.capability in {"modify", "test_candidate", "validate_proposal"}
            and (state.permission or "read_only") in {"read_only", "audit_only"}
        )
        if args.action == "evaluate":
            decision = resolve_authorization(AuthorizationRequest(
                mode_decision=mode,
                capability=args.capability,
                explicitly_forbidden=explicitly_forbidden,
            ))
            verdict = "REQUIRE_APPROVAL" if decision.verdict is AuthorizationVerdict.ESCALATE else decision.verdict.value
            payload = {
                "ok": True,
                "operation_id": args.operation_id,
                "capability": args.capability,
                "verdict": verdict,
                "rationale": decision.rationale,
                "approval_id": approval_id if verdict == "REQUIRE_APPROVAL" else None,
            }
        else:
            if args.approval_id != approval_id:
                raise ValueError("approval id does not match Agent Wall authorization request")
            if args.decision is None:
                raise ValueError("decision is required for authorization resolution")
            if args.decision == "reject":
                payload = {
                    "ok": True,
                    "operation_id": args.operation_id,
                    "capability": args.capability,
                    "verdict": "DENY",
                    "rationale": "User rejected the Agent Wall approval request.",
                    "approval_id": approval_id,
                }
            else:
                decision = resolve_authorization(AuthorizationRequest(
                    mode_decision=mode,
                    capability=args.capability,
                    approval_granted=True,
                    explicitly_forbidden=explicitly_forbidden,
                ))
                payload = {
                    "ok": True,
                    "operation_id": args.operation_id,
                    "capability": args.capability,
                    "verdict": decision.verdict.value,
                    "rationale": decision.rationale,
                    "approval_id": approval_id,
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
    if command == "turn":
        return _turn(suffix)
    if command == "control":
        return _control(suffix)
    if command == "start":
        return _start(suffix)
    if command == "capabilities":
        return _capabilities(suffix)
    if command == "export":
        return _export(suffix)
    if command == "tool":
        return _tool(suffix)
    if command == "authorization":
        return _authorization(suffix)
    raise AssertionError(f"unsupported product command: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)

    product_commands = [command for command in ("turn", "control", "start", "capabilities", "export", "tool", "authorization") if command in values]
    if not product_commands:
        return _cli.main(values)
    if len(product_commands) > 1:
        return _cli.main(values)
    return _dispatch_product_command(values, product_commands[0])


if __name__ == "__main__":
    raise SystemExit(main())
