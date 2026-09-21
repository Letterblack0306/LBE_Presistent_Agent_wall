"""Thin CLI control plane for the persistent LBE runtime.

The CLI parses operator input and delegates to existing runtime/data owners. It
must not become a second session controller, provider authority, permission
resolver, tool executor, evidence authority, or completion gate.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

from .agent_integration import AgentMode, AgentRequestEnvelope, GovernedAgentGateway
from .control_protocol import ControlMethod, ControlRequest
from .credential_store import WindowsCredentialStore
from .evidence_service import EvidenceService
from .memory import SessionState, WorkspaceMemoryStore
from .memory.operational_history import SessionOperationalHistory
from .provider_health import check_provider_health
from .provider_registry import default_provider_registry
from .reasoning_config import load_provider_config
from .reasoning_provider import ProviderConfig
from .reasoning_runtime import build_provider_controller
from .runtime.completion_runtime import CodingCompletionRuntime
from .runtime.mode_controller import ModeRequest, resolve_mode
from .session_memory_runtime import SessionMemoryRuntimeBridge
from .session_lifecycle import LbeSessionService
from .user_state import ProviderProfile, UserStateStore


_MODES = ("coding", "audit", "investigation")
_OUTPUT_FORMATS = ("json", "text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lbe",
        description="Persistent LBE runtime control plane",
    )
    parser.add_argument(
        "--format",
        choices=_OUTPUT_FORMATS,
        default="json",
        help="Output format for terminal users or automation",
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
    create.add_argument("--permission", choices=("read_only", "write_allowed", "audit_only", "elevated"), default="read_only")
    create.add_argument("--runtime-policy", choices=("audit", "development", "strict", "permissive"), default="audit")
    create.add_argument("--provider")
    create.add_argument("--model")
    create.add_argument("--engine", help="Reasoning engine binding; defaults to the provider default")
    create.add_argument("--profile")
    create.add_argument("--permission-policy")
    create.add_argument("--evidence-policy")
    create.set_defaults(handler=_session_create)

    list_parser = session_commands.add_parser(
        "list", help="List bounded persisted sessions"
    )
    _add_database_argument(list_parser)
    list_parser.add_argument("--project-workspace-id")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.set_defaults(handler=_session_list)

    continue_parser = session_commands.add_parser(
        "continue", help="Rehydrate an existing persistent session"
    )
    _add_database_argument(continue_parser)
    continue_parser.add_argument("--session-id", required=True)
    continue_parser.add_argument("--task-id")
    continue_parser.add_argument("--provider")
    continue_parser.add_argument("--model")
    continue_parser.add_argument("--engine")
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

    evidence = session_commands.add_parser(
        "evidence", help="Retrieve bounded evidence for an existing session"
    )
    _add_database_argument(evidence)
    evidence.add_argument("--session-id", required=True)
    evidence.add_argument("--task-id", required=True)
    evidence.add_argument("--query", required=True)
    evidence.add_argument("--max-results", type=int, default=10)
    evidence.set_defaults(handler=_session_evidence)

    validate = session_commands.add_parser(
        "validate", help="Evaluate persisted completion evidence for an existing task"
    )
    _add_database_argument(validate)
    validate.add_argument("--session-id", required=True)
    validate.add_argument("--task-id", required=True)
    validate.set_defaults(handler=_session_validate)

    mode_cmd = session_commands.add_parser(
        "mode", help="Update persisted session mode under LBE policy authority"
    )
    _add_database_argument(mode_cmd)
    mode_cmd.add_argument("--session-id", required=True)
    mode_cmd.add_argument("--mode", required=True, choices=_MODES)
    mode_cmd.set_defaults(handler=_session_mode)

    provider = commands.add_parser("provider", help="Inspect or select reasoning providers")
    provider_commands = provider.add_subparsers(dest="provider_command", required=True)
    provider_list = provider_commands.add_parser("list", help="List registered providers")
    provider_list.set_defaults(handler=_provider_list)

    provider_check = provider_commands.add_parser(
        "check", help="Check a provider against the structured reasoning contract"
    )
    provider_check.add_argument("--provider", required=True)
    provider_check.add_argument("--provider-config")
    provider_check.add_argument("--state-root")
    provider_check.add_argument("--profile")
    provider_check.add_argument("--engine")
    provider_check.set_defaults(handler=_provider_check)

    provider_select = provider_commands.add_parser(
        "select", help="Select a provider/model for an existing session"
    )
    _add_database_argument(provider_select)
    provider_select.add_argument("--session-id", required=True)
    provider_select.add_argument("--provider", required=True)
    provider_select.add_argument("--model", required=True)
    provider_select.add_argument("--engine")
    provider_select.set_defaults(handler=_provider_select)

    provider_add = provider_commands.add_parser(
        "add", help="Add or update a per-user provider profile without storing secrets in JSON"
    )
    provider_add.add_argument("--state-root")
    provider_add.add_argument("--name", required=True)
    provider_add.add_argument("--provider", required=True)
    provider_add.add_argument("--model", required=True)
    provider_add.add_argument("--endpoint", required=True)
    provider_add.add_argument("--timeout-seconds", type=float, default=30.0)
    provider_add.add_argument("--credential-id")
    provider_add.add_argument("--use", action="store_true")
    provider_add.set_defaults(handler=_provider_add)

    provider_use = provider_commands.add_parser(
        "use", help="Select an existing per-user provider profile"
    )
    provider_use.add_argument("--state-root")
    provider_use.add_argument("--name", required=True)
    provider_use.set_defaults(handler=_provider_use)

    provider_migrate = provider_commands.add_parser(
        "migrate", help="Migrate one explicit legacy provider config into per-user state"
    )
    provider_migrate.add_argument("--state-root")
    provider_migrate.add_argument("--name", required=True)
    provider_migrate.add_argument("--provider", required=True)
    provider_migrate.add_argument("--provider-config", required=True)
    provider_migrate.add_argument("--credential-id")
    provider_migrate.add_argument("--use", action="store_true")
    provider_migrate.set_defaults(handler=_provider_migrate)

    provider_active = provider_commands.add_parser(
        "active", help="Show the active per-user provider profile without exposing credentials"
    )
    provider_active.add_argument("--state-root")
    provider_active.set_defaults(handler=_provider_active)

    provider_remove = provider_commands.add_parser(
        "remove", help="Remove one per-user provider profile"
    )
    provider_remove.add_argument("--state-root")
    provider_remove.add_argument("--name", required=True)
    provider_remove.set_defaults(handler=_provider_remove)

    _add_mode_command(commands, "code", AgentMode.CODING, "Run a governed coding task")
    _add_mode_command(commands, "audit", AgentMode.AUDIT, "Run a governed read-only audit task")
    _add_mode_command(
        commands,
        "investigate",
        AgentMode.INVESTIGATION,
        "Run a governed investigation task",
    )

    policy = commands.add_parser("policy", help="Inspect active session policy references")
    policy_commands = policy.add_subparsers(dest="policy_command", required=True)
    policy_show = policy_commands.add_parser("show", help="Show active workspace/evidence policy")
    _add_database_argument(policy_show)
    policy_show.add_argument("--session-id", required=True)
    policy_show.set_defaults(handler=_policy_show)

    permissions = commands.add_parser("permissions", help="Inspect active permission policy")
    permission_commands = permissions.add_subparsers(dest="permissions_command", required=True)
    permissions_show = permission_commands.add_parser("show", help="Show active permission policy")
    _add_database_argument(permissions_show)
    permissions_show.add_argument("--session-id", required=True)
    permissions_show.set_defaults(handler=_permissions_show)

    checkpoint = commands.add_parser("checkpoint", help="Inspect persisted LBE checkpoints")
    checkpoint_commands = checkpoint.add_subparsers(dest="checkpoint_command", required=True)
    checkpoint_latest = checkpoint_commands.add_parser(
        "latest", help="Read the latest persisted checkpoint for one session"
    )
    _add_database_argument(checkpoint_latest)
    checkpoint_latest.add_argument("--session-id", required=True)
    checkpoint_latest.set_defaults(handler=_checkpoint_latest)

    checkpoint_compare = checkpoint_commands.add_parser(
        "compare", help="Revalidate one persisted checkpoint against current workspace state"
    )
    _add_database_argument(checkpoint_compare)
    checkpoint_compare.add_argument("--session-id", required=True)
    checkpoint_compare.add_argument("--checkpoint-id", required=True)
    checkpoint_compare.set_defaults(handler=_checkpoint_compare)

    memory = commands.add_parser("memory", help="Read validated LBE session memory projections")
    memory_commands = memory.add_subparsers(dest="memory_command", required=True)
    memory_recall = memory_commands.add_parser(
        "recall", help="Recall validated memory for one persisted session"
    )
    _add_database_argument(memory_recall)
    memory_recall.add_argument("--session-id", required=True)
    memory_recall.add_argument("--query", default="recent")
    memory_recall.add_argument("--limit", type=int, default=10)
    memory_recall.set_defaults(handler=_memory_recall)

    tui = commands.add_parser("tui", help="Open or create a persisted LBE terminal session")
    _add_database_argument(tui)
    tui.add_argument("--session-id", help="Existing session ID; omit with --workspace to create a new terminal session")
    tui.add_argument("--workspace", help="Workspace root for a new terminal session")
    tui.add_argument("--project-workspace-id", help="Project workspace identity for a new terminal session")
    tui.add_argument("--mode", choices=_MODES, help="Session mode for a new terminal session")
    tui.add_argument("--permission", choices=("read_only", "write_allowed", "audit_only", "elevated"), default="read_only")
    tui.add_argument("--runtime-policy", choices=("audit", "development", "strict", "permissive"), default="audit")
    tui.add_argument("--provider", help="Provider identity for a new terminal session")
    tui.add_argument("--model", help="Provider model for a new terminal session")
    tui.add_argument("--engine", help="Reasoning engine binding for a new terminal session")
    tui.add_argument("--profile")
    tui.add_argument("--permission-policy")
    tui.add_argument("--evidence-policy")
    tui.add_argument("--provider-config", help="Explicit provider config for non-streaming turn execution")
    tui.add_argument("--prompt", help="Submit one turn through the existing LBE session/provider runtime")
    tui.add_argument("--wait-timeout", type=float, default=120.0, help=argparse.SUPPRESS)
    tui.set_defaults(handler=_tui)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args)
    except (ValueError, TypeError, FileNotFoundError, RuntimeError) as exc:
        _emit(
            {
                "ok": False,
                "error": type(exc).__name__,
                "message": str(exc),
            },
            args.format,
        )
        return 2
    _emit({"ok": True, **payload}, args.format)
    return 0


def _session_create(args: argparse.Namespace) -> dict[str, Any]:
    workspace = _workspace_root(args.workspace)
    _validate_provider_selection(args.provider, args.model, require_pair=False)
    reasoning_engine = _resolve_engine_selection(args.provider, args.engine)
    state = SessionState(
        session_id=args.session_id,
        project_workspace_id=args.project_workspace_id,
        canonical_workspace_root=workspace,
        mode=args.mode,
        permission=args.permission,
        runtime_policy=args.runtime_policy,
        provider_id=args.provider,
        provider_model=args.model,
        active_profile_id=args.profile,
        permission_policy_id=args.permission_policy,
        evidence_policy_id=args.evidence_policy,
        reasoning_engine=reasoning_engine,
    )
    store = WorkspaceMemoryStore(args.database)
    service = LbeSessionService(
        history=SessionOperationalHistory(store=store),
        provider_registry=default_provider_registry(),
    )
    created = service.create_session(from_state=state, new_session_id=args.session_id)
    return {
        "action": "session.create",
        "session": created.as_dict(),
    }


def _session_list(args: argparse.Namespace) -> dict[str, Any]:
    if args.limit < 1:
        raise ValueError("limit must be a positive integer")
    store = WorkspaceMemoryStore(args.database)
    states = store.list_session_states(
        project_workspace_id=args.project_workspace_id,
        limit=args.limit,
    )
    return {
        "action": "session.list",
        "project_workspace_id": args.project_workspace_id,
        "sessions": [
            {
                **state.as_dict(),
                "status": "idle",
                "origin": "user",
                "parent_session_id": None,
            }
            for state in states
        ],
    }


def _session_continue(args: argparse.Namespace) -> dict[str, Any]:
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    runtime = _runtime_from_state(database=args.database, state=state)
    if args.provider is not None or args.model is not None or args.engine is not None:
        provider_id = state.provider_id if args.provider is None else args.provider
        provider_model = state.provider_model if args.model is None else args.model
        _validate_provider_selection(provider_id, provider_model, require_pair=True)
        state = LbeSessionService(
            history=SessionOperationalHistory(store=store),
            provider_registry=default_provider_registry(),
        ).configure_provider(
            state=state,
            provider_id=provider_id,
            model_id=provider_model,
            engine_id=args.engine if args.engine is not None else state.reasoning_engine,
        )
        runtime = _runtime_from_state(database=args.database, state=state)
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
        "reasoning_engine": state.reasoning_engine,
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


def _session_evidence(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_results < 1:
        raise ValueError("max_results must be a positive integer")
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    retrieval_mode = "investigation" if state.mode == "investigation" else "diagnostic"
    package = EvidenceService().build_evidence_package(
        task_id=args.task_id,
        query=args.query,
        workspace_id=state.project_workspace_id,
        workspace_root=state.canonical_workspace_root,
        max_results=args.max_results,
        roots=[state.project_workspace_id],
        retrieval_mode=retrieval_mode,
    )
    return {
        "action": "session.evidence",
        "session_id": state.session_id,
        "task_id": args.task_id,
        "mode": state.mode,
        "evidence_policy_id": state.evidence_policy_id,
        "package": package,
    }


def _session_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Thin C3 adapter over the existing completion runtime and gate."""
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    runtime = _runtime_from_state(database=args.database, state=state)
    completion_runtime = CodingCompletionRuntime(runtime=runtime)
    contract = completion_runtime.load_contract(task_id=args.task_id)
    if contract is None:
        raise ValueError("persisted task completion contract not found")
    decision, task = completion_runtime.finalize(
        task_id=args.task_id,
        contract=contract,
        evidence=completion_runtime.load_evidence(task_id=args.task_id),
        claimed_complete=True,
    )
    return {
        "action": "session.validate",
        "session_id": state.session_id,
        "task_id": args.task_id,
        "completion": {
            "verdict": decision.verdict.value,
            "satisfied_requirement_ids": list(decision.satisfied_requirement_ids),
            "missing_requirement_ids": list(decision.missing_requirement_ids),
            "failed_requirement_ids": list(decision.failed_requirement_ids),
            "evidence_ids": list(decision.evidence_ids),
            "rationale": decision.rationale,
        },
        "task": _task_payload(task),
    }


def _session_mode(args: argparse.Namespace) -> dict[str, Any]:
    """Apply a user-requested product mode through existing LBE policy authority.

    The request may change the persisted mode/runtime-policy tuple, but it never
    grants or changes permission. Coding therefore fails closed unless the
    persisted permission already authorizes coding.
    """
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    requested_mode = str(args.mode)
    permission = state.permission or "read_only"

    intent_by_mode = {
        "coding": "fix_issue",
        "investigation": "diagnose_failure",
        "audit": "audit_workspace",
    }
    policy_by_mode = {
        "coding": "permissive",
        "investigation": "permissive",
        "audit": "audit",
    }
    requested_policy = policy_by_mode[requested_mode]
    decision = resolve_mode(
        ModeRequest(
            intent=intent_by_mode[requested_mode],
            permission=permission,
            runtime_policy=requested_policy,
            workspace_root=state.canonical_workspace_root,
        )
    )

    if decision.mode != requested_mode:
        status = (
            "PERMISSION_REQUIRED"
            if requested_mode == "coding" and permission in {"read_only", "audit_only"}
            else "MODE_TRANSITION_DENIED"
        )
        return {
            "action": "session.mode",
            "session_id": state.session_id,
            "accepted": False,
            "status": status,
            "requested_mode": requested_mode,
            "mode": state.mode,
            "permission": state.permission,
            "runtime_policy": state.runtime_policy,
            "resolved_mode": decision.mode,
            "rationale": decision.rationale,
        }

    runtime = _runtime_from_state(database=args.database, state=state)
    updated = runtime.configure_session(
        mode=decision.mode,
        runtime_policy=requested_policy,
    )
    return {
        "action": "session.mode",
        "session_id": updated.session_id,
        "accepted": True,
        "status": "APPLIED",
        "requested_mode": requested_mode,
        "mode": updated.mode,
        "permission": updated.permission,
        "runtime_policy": updated.runtime_policy,
        "resolved_mode": decision.mode,
        "rationale": decision.rationale,
    }


def _provider_list(args: argparse.Namespace) -> dict[str, Any]:
    del args
    registry = default_provider_registry()
    return {
        "action": "provider.list",
        "providers": list(registry.provider_ids()),
        "engines": list(registry.engine_ids()),
        "bindings": [
            {
                "provider_id": binding.provider_id,
                "engine_id": binding.engine_id,
                "default": binding.default,
            }
            for binding in registry.bindings()
        ],
    }


def _resolve_user_provider_config(
    *,
    state_root: str | None,
    profile_name: str | None,
    expected_provider_id: str | None = None,
) -> tuple[str, ProviderProfile, ProviderConfig]:
    store = UserStateStore(state_root)
    selected = profile_name or store.active_profile_name()
    if selected is None:
        raise ValueError("no active provider profile is configured")
    profiles = store.profiles()
    profile = profiles.get(selected)
    if profile is None:
        raise ValueError(f"provider profile not found: {selected}")
    if expected_provider_id is not None and profile.provider_id != expected_provider_id:
        raise ValueError(
            "provider profile does not match requested provider: "
            f"{profile.provider_id} != {expected_provider_id}"
        )
    api_key = None
    if profile.credential_id is not None:
        api_key = WindowsCredentialStore().get(profile.credential_id)
    return (
        selected,
        profile,
        ProviderConfig(
            endpoint=profile.endpoint,
            model=profile.model,
            timeout_seconds=profile.timeout_seconds,
            api_key=api_key,
        ),
    )


def resolve_provider_config(
    *,
    provider_config: str | None,
    state_root: str | None = None,
    profile_name: str | None = None,
    expected_provider_id: str | None = None,
) -> tuple[str | None, ProviderConfig]:
    if provider_config is not None:
        return None, load_provider_config(provider_config)
    selected, _profile, config = _resolve_user_provider_config(
        state_root=state_root,
        profile_name=profile_name,
        expected_provider_id=expected_provider_id,
    )
    return selected, config


def _provider_check(args: argparse.Namespace) -> dict[str, Any]:
    profile_name, config = resolve_provider_config(
        provider_config=args.provider_config,
        state_root=args.state_root,
        profile_name=args.profile,
        expected_provider_id=args.provider,
    )
    result = check_provider_health(
        provider_id=args.provider,
        provider_config=config,
        engine_id=args.engine,
    )
    return {
        "action": "provider.check",
        "provider_id": result.provider_id,
        "provider_model": result.model_id,
        "engine_id": result.engine_id,
        "status": result.status,
        "capabilities": asdict(result.capabilities),
        "profile": profile_name,
    }


def _provider_profile_payload(name: str, profile: ProviderProfile) -> dict[str, Any]:
    return {
        "name": name,
        "provider_id": profile.provider_id,
        "model": profile.model,
        "endpoint": profile.endpoint,
        "timeout_seconds": profile.timeout_seconds,
        "credential_id": profile.credential_id,
    }


def _provider_add(args: argparse.Namespace) -> dict[str, Any]:
    store = UserStateStore(args.state_root)
    profile = ProviderProfile(
        provider_id=args.provider,
        model=args.model,
        endpoint=args.endpoint,
        timeout_seconds=args.timeout_seconds,
        credential_id=args.credential_id,
    )
    store.save_profile(args.name, profile, activate=args.use)
    return {
        "action": "provider.add",
        "profile": _provider_profile_payload(args.name, profile),
        "active_profile": store.active_profile_name(),
    }


def _provider_use(args: argparse.Namespace) -> dict[str, Any]:
    store = UserStateStore(args.state_root)
    profile = store.select_profile(args.name)
    return {
        "action": "provider.use",
        "profile": _provider_profile_payload(args.name, profile),
        "active_profile": store.active_profile_name(),
    }


def _provider_migrate(args: argparse.Namespace) -> dict[str, Any]:
    config = load_provider_config(args.provider_config)
    credential_id = args.credential_id
    if config.api_key is not None:
        if credential_id is None or not str(credential_id).strip():
            raise ValueError(
                "--credential-id is required when the legacy provider config contains api_key"
            )
        WindowsCredentialStore().put(str(credential_id).strip(), config.api_key)
        credential_id = str(credential_id).strip()

    profile = ProviderProfile(
        provider_id=args.provider,
        model=config.model,
        endpoint=config.endpoint,
        timeout_seconds=config.timeout_seconds,
        credential_id=credential_id,
    )
    store = UserStateStore(args.state_root)
    store.save_profile(args.name, profile, activate=args.use)
    return {
        "action": "provider.migrate",
        "profile": _provider_profile_payload(args.name, profile),
        "active_profile": store.active_profile_name(),
        "legacy_config_removal_required": config.api_key is not None,
    }


def _provider_active(args: argparse.Namespace) -> dict[str, Any]:
    store = UserStateStore(args.state_root)
    name = store.active_profile_name()
    if name is None:
        raise ValueError("no active provider profile is configured")
    profile = store.profiles().get(name)
    if profile is None:
        raise ValueError(f"provider profile not found: {name}")
    return {
        "action": "provider.active",
        "profile": _provider_profile_payload(name, profile),
        "active_profile": name,
    }


def _provider_remove(args: argparse.Namespace) -> dict[str, Any]:
    store = UserStateStore(args.state_root)
    removed = store.remove_profile(args.name)
    return {
        "action": "provider.remove",
        "profile": _provider_profile_payload(args.name, removed),
        "active_profile": store.active_profile_name(),
    }


def _provider_select(args: argparse.Namespace) -> dict[str, Any]:
    _validate_provider_selection(args.provider, args.model, require_pair=True)
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    service = LbeSessionService(
        history=SessionOperationalHistory(store=store),
        provider_registry=default_provider_registry(),
    )
    before = state
    updated = service.configure_provider(
        state=state,
        provider_id=args.provider,
        model_id=args.model,
        engine_id=args.engine,
    )
    return {
        "action": "provider.select",
        "session_id": updated.session_id,
        "provider_id": updated.provider_id,
        "provider_model": updated.provider_model,
        "reasoning_engine": updated.reasoning_engine,
        "workspace": updated.canonical_workspace_root,
        "mode": updated.mode,
        "policy_unchanged": {
            "active_profile_id": before.active_profile_id == updated.active_profile_id,
            "permission_policy_id": before.permission_policy_id == updated.permission_policy_id,
            "evidence_policy_id": before.evidence_policy_id == updated.evidence_policy_id,
            "permission": before.permission == updated.permission,
            "runtime_policy": before.runtime_policy == updated.runtime_policy,
        },
    }


def _tui(args: argparse.Namespace) -> dict[str, Any]:
    from .memory.operational_history import SessionOperationalHistory
    from .persistent_turn_control import PersistentTurnControl
    from .provider_turn_runtime import BackgroundProviderTurnRuntime, GovernedCodingTurnRuntime, GovernedProviderTurnRuntime
    from .reasoning_config import load_provider_config
    from .project_profiler import ProjectProfiler
    from .guard_catalog import select_guard_catalog
    from .runtime.agent_guidance import build_agent_guidance
    if args.session_id is None:
        missing = [name for name in ("workspace", "project_workspace_id", "mode") if not getattr(args, name, None)]
        if missing:
            raise ValueError("new terminal session requires " + ", ".join("--" + name.replace("_", "-") for name in missing))
        args.session_id = f"tui-{uuid4().hex}"
        _session_create(args)
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    project_profile = ProjectProfiler().profile(state.canonical_workspace_root)
    guard_catalog = select_guard_catalog(project_profile)
    history = SessionOperationalHistory(store=store)
    provider_runtime = None
    config = None
    if args.provider_config is not None:
        config = load_provider_config(args.provider_config)
        if config.model != state.provider_model:
            raise ValueError("provider config model must match persisted session model")
        if state.mode == AgentMode.CODING.value:
            from .runtime.governed_coding import build_governed_coding_controller
            from .runtime.installed_capability_registry import (
                InstalledCapabilityRegistryStore,
                built_in_adapter_factories,
            )

            runtime = _runtime_from_state(database=args.database, state=state)
            external_capabilities = ()
            registry_path = os.environ.get("LBE_CAPABILITY_REGISTRY")
            if registry_path:
                installed_registry = InstalledCapabilityRegistryStore(registry_path).load()
                external_capabilities = installed_registry.materialize(
                    built_in_adapter_factories(installed_registry)
                )
            controller = build_governed_coding_controller(
                runtime=runtime,
                provider_id=state.provider_id,
                provider_config=config,
                engine_id=state.reasoning_engine,
                external_capabilities=external_capabilities,
            )
            provider_runtime = BackgroundProviderTurnRuntime(
                history=history,
                foreground=GovernedCodingTurnRuntime(
                    history=history,
                    gateway=GovernedAgentGateway(
                        runtime=runtime,
                        reasoning_controller=controller,
                    ),
                ),
            )
        else:
            from .reasoning_runtime import build_provider_controller
            controller, _ = build_provider_controller(
                provider_id=state.provider_id,
                provider_config=config,
                engine_id=state.reasoning_engine,
            )
            intent = "inspect_workspace" if state.mode == AgentMode.AUDIT.value else "diagnose_failure" if state.mode == AgentMode.INVESTIGATION.value else "inspect_workspace"
            guidance = build_agent_guidance(
                mode_decision=resolve_mode(ModeRequest(intent=intent, permission=state.permission, runtime_policy=state.runtime_policy, workspace_root=str(state.canonical_workspace_root))),
                workspace_root=state.canonical_workspace_root,
                tools=(),
            )
            provider_runtime = BackgroundProviderTurnRuntime(history=history, foreground=GovernedProviderTurnRuntime(
                history=history,
                gateway=GovernedAgentGateway(
                    runtime=_runtime_from_state(database=args.database, state=state),
                    reasoning_controller=controller,
                ),
                mode=AgentMode(state.mode),
                guidance=guidance,
            ))
    prompt = getattr(args, "prompt", None)
    wait_timeout = getattr(args, "wait_timeout", 120.0)
    if prompt is not None:
        if provider_runtime is None:
            raise ValueError("--prompt requires --provider-config")
        control = PersistentTurnControl(history=history, provider_runtime=provider_runtime)
        outcome = control.handle(ControlRequest(
            request_id=f"tui-{uuid4().hex}",
            method=ControlMethod.TURN_START,
            params={"session_id": state.session_id, "text": prompt},
        ))
        if not outcome.accepted:
            raise RuntimeError(outcome.reason or "turn submission was rejected")
        turn = history.latest_running_turn(session_id=state.session_id)
        if turn is None:
            raise RuntimeError("turn submission did not create a running turn")
        deadline = time.monotonic() + max(0.1, wait_timeout)
        while provider_runtime.is_running(turn_id=turn.turn_id):
            if time.monotonic() >= deadline:
                control.handle(ControlRequest(
                    request_id=f"tui-cancel-{uuid4().hex}",
                    method=ControlMethod.TURN_CANCEL,
                    params={"session_id": state.session_id, "turn_id": turn.turn_id},
                ))
                raise TimeoutError(f"turn did not complete within {wait_timeout:g} seconds")
            time.sleep(0.05)
        completed = history.get_turn(turn_id=turn.turn_id)
        if completed is None:
            raise RuntimeError("completed turn is missing from operational history")
        return {
            "action": "tui",
            "session_id": state.session_id,
            "turn_id": turn.turn_id,
            "turn_status": completed.status.value,
            "turn_submission": {
                "request_id": outcome.request_id,
                "state": outcome.state,
                "reason": outcome.reason,
            },
            "events": [_serialize_tui_event(event) for event in history.events_for_turn(turn_id=turn.turn_id)],
            "project_profile": project_profile,
            "guard_catalog": guard_catalog,
        }
    # Python/Textual interface removed (LBE-INTENT-CLINE-SURFACE-DIRECTION-001).
    # The Cline CLI/SDK surface replaces it; session setup and provider-config
    # validation above remain the canonical fail-closed entry contract.
    return {
        "action": "tui",
        "session_id": state.session_id,
        "project_profile": project_profile,
        "guard_catalog": guard_catalog,
    }


def _serialize_tui_event(event: object) -> dict[str, object]:
    """Project persisted operational history without creating a second event owner."""
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


def _code(args: argparse.Namespace) -> dict[str, Any]:
    return _run_mode_command(args, AgentMode.CODING, action="code")


def _audit(args: argparse.Namespace) -> dict[str, Any]:
    return _run_mode_command(args, AgentMode.AUDIT, action="audit")


def _investigate(args: argparse.Namespace) -> dict[str, Any]:
    return _run_mode_command(args, AgentMode.INVESTIGATION, action="investigate")


def _run_mode_command(
    args: argparse.Namespace,
    mode: AgentMode,
    *,
    action: str,
) -> dict[str, Any]:
    if args.max_results < 1:
        raise ValueError("max_results must be a positive integer")
    state = _require_session(WorkspaceMemoryStore(args.database), args.session_id)
    if not state.provider_id or not state.provider_model:
        raise ValueError("persisted session does not have a selected provider/model")

    provider_config = load_provider_config(args.provider_config)
    if provider_config.model.strip() != state.provider_model:
        raise ValueError("provider config model does not match persisted session provider model")

    runtime = _runtime_from_state(database=args.database, state=state)
    controller, handle = build_provider_controller(
        provider_id=state.provider_id,
        provider_config=provider_config,
        engine_id=state.reasoning_engine,
    )
    if handle.descriptor.provider_id != state.provider_id:
        raise ValueError("provider adapter identity does not match persisted session provider")
    if mode is AgentMode.CODING:
        from .runtime.governed_coding import build_governed_coding_controller

        controller = build_governed_coding_controller(
            runtime=runtime,
            provider_id=state.provider_id,
            provider_config=provider_config,
            engine_id=state.reasoning_engine,
        )

    gateway = GovernedAgentGateway(runtime=runtime, reasoning_controller=controller)
    request_id = args.request_id.strip() if args.request_id else f"request-{uuid4()}"
    result = gateway.invoke(
        AgentRequestEnvelope(
            request_id=request_id,
            session_id=state.session_id,
            task_id=args.task_id,
            project_workspace_id=state.project_workspace_id,
            workspace_root=state.canonical_workspace_root,
            mode=mode,
            operation_id="reasoning.inspect",
            arguments={
                "problem": args.problem,
                "max_results": args.max_results,
            },
        )
    )
    return {
        "action": action,
        "request_id": result.request_id,
        "session_id": result.session_id,
        "task_id": result.task_id,
        "mode": result.mode.value,
        "mode_decision": asdict(result.mode_decision),
        "status": result.status.value,
        "outcome": result.outcome,
        "response": asdict(result.response),
    }


def _checkpoint_latest(args: argparse.Namespace) -> dict[str, Any]:
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    runtime = _runtime_from_state(database=args.database, state=state)
    packet = runtime.start_or_resume()
    return {
        "action": "checkpoint.latest",
        "session_id": state.session_id,
        "project_workspace_id": state.project_workspace_id,
        "checkpoint": packet.get("checkpoint"),
        "checkpoint_revalidation": packet.get("checkpoint_revalidation"),
    }


def _checkpoint_compare(args: argparse.Namespace) -> dict[str, Any]:
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    runtime = _runtime_from_state(database=args.database, state=state)
    packet = runtime.start_or_resume()
    checkpoint = packet.get("checkpoint")
    if checkpoint is None:
        raise ValueError("no persisted checkpoint exists for session")
    if checkpoint.get("checkpoint_id") != args.checkpoint_id:
        raise ValueError("requested checkpoint is not the latest persisted checkpoint")
    revalidation = packet.get("checkpoint_revalidation")
    if revalidation is None:
        raise ValueError("checkpoint revalidation evidence is unavailable")
    return {
        "action": "checkpoint.compare",
        "session_id": state.session_id,
        "project_workspace_id": state.project_workspace_id,
        "checkpoint_id": args.checkpoint_id,
        "revalidation": revalidation,
    }


def _memory_recall(args: argparse.Namespace) -> dict[str, Any]:
    if args.limit < 1:
        raise ValueError("limit must be a positive integer")
    store = WorkspaceMemoryStore(args.database)
    state = _require_session(store, args.session_id)
    runtime = _runtime_from_state(database=args.database, state=state)
    packet = runtime.start_or_resume()
    records = [
        *packet.get("verified_facts", []),
        *packet.get("active_constraints", []),
        *packet.get("recent_failures", []),
    ]
    query = str(args.query or "recent").strip().lower()
    if query and query != "recent":
        records = [
            record
            for record in records
            if query in json.dumps(record, ensure_ascii=False, sort_keys=True).lower()
        ]
    records = records[: min(int(args.limit), 100)]
    return {
        "action": "memory.recall",
        "session_id": state.session_id,
        "project_workspace_id": state.project_workspace_id,
        "query": args.query,
        "records": records,
        "checkpoint": packet.get("checkpoint"),
        "checkpoint_revalidation": packet.get("checkpoint_revalidation"),
    }


def _policy_show(args: argparse.Namespace) -> dict[str, Any]:
    state = _require_session(WorkspaceMemoryStore(args.database), args.session_id)
    return {
        "action": "policy.show",
        "session_id": state.session_id,
        "workspace": state.canonical_workspace_root,
        "mode": state.mode,
        "active_profile_id": state.active_profile_id,
        "evidence_policy_id": state.evidence_policy_id,
    }


def _permissions_show(args: argparse.Namespace) -> dict[str, Any]:
    state = _require_session(WorkspaceMemoryStore(args.database), args.session_id)
    return {
        "action": "permissions.show",
        "session_id": state.session_id,
        "workspace": state.canonical_workspace_root,
        "mode": state.mode,
        "permission_policy_id": state.permission_policy_id,
    }


def _runtime_from_state(*, database: str | Path, state: Any) -> SessionMemoryRuntimeBridge:
    return SessionMemoryRuntimeBridge(
        database_path=database,
        project_workspace_id=state.project_workspace_id,
        workspace_root=state.canonical_workspace_root,
        session_id=state.session_id,
        mode=state.mode,
        permission=state.permission,
        runtime_policy=state.runtime_policy,
        provider_id=state.provider_id,
        provider_model=state.provider_model,
        active_profile_id=state.active_profile_id,
        permission_policy_id=state.permission_policy_id,
        evidence_policy_id=state.evidence_policy_id,
        reasoning_engine=state.reasoning_engine,
    )


def _resolve_engine_selection(provider_id: str | None, engine_id: str | None) -> str | None:
    if provider_id is None:
        if engine_id is not None:
            raise ValueError("reasoning engine requires a provider selection")
        return None
    registry = default_provider_registry()
    clean_provider = str(provider_id).strip()
    if clean_provider not in registry.provider_ids():
        raise ValueError(f"provider is not registered: {clean_provider}")
    selected = (
        registry.default_engine_for_provider(clean_provider)
        if engine_id is None
        else str(engine_id).strip()
    )
    if not selected:
        raise ValueError(f"provider has no default reasoning engine: {clean_provider}")
    if selected not in registry.engines_for_provider(clean_provider):
        raise ValueError(
            f"reasoning engine is not registered for provider: {selected}/{clean_provider}"
        )
    return selected


def _validate_provider_selection(
    provider_id: str | None,
    provider_model: str | None,
    *,
    require_pair: bool,
) -> None:
    if provider_id is None and provider_model is None and not require_pair:
        return
    if not provider_id or not str(provider_id).strip():
        raise ValueError("provider_id must be supplied with provider model")
    if not provider_model or not str(provider_model).strip():
        raise ValueError("provider model must be supplied with provider_id")
    registry = default_provider_registry()
    clean_provider = str(provider_id).strip()
    if clean_provider not in registry.provider_ids():
        raise ValueError(f"provider is not registered: {clean_provider}")


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


def _add_mode_command(
    commands: argparse._SubParsersAction,
    name: str,
    mode: AgentMode,
    help_text: str,
) -> None:
    command = commands.add_parser(name, help=help_text)
    _add_database_argument(command)
    command.add_argument("--session-id", required=True)
    command.add_argument("--task-id", required=True)
    command.add_argument("--provider-config", required=True)
    command.add_argument("--problem", required=True)
    command.add_argument("--request-id")
    command.add_argument("--max-results", type=int, default=10)
    command.set_defaults(
        handler={
            AgentMode.CODING: _code,
            AgentMode.AUDIT: _audit,
            AgentMode.INVESTIGATION: _investigate,
        }[mode]
    )


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
        return
    for line in _human_lines(payload):
        print(line)


def _human_lines(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    action = payload.get("action")
    if action:
        lines.append(str(action))
    if payload.get("ok") is False:
        lines.append(f"error: {payload.get('error')}: {payload.get('message')}")
        return lines
    for key, value in payload.items():
        if key in {"ok", "action"}:
            continue
        _append_human_value(lines, key, value, indent=0)
    return lines or ["ok"]


def _append_human_value(lines: list[str], key: str, value: Any, *, indent: int) -> None:
    prefix = "  " * indent
    if isinstance(value, dict):
        lines.append(f"{prefix}{key}:")
        for nested_key, nested_value in value.items():
            _append_human_value(lines, str(nested_key), nested_value, indent=indent + 1)
        return
    if isinstance(value, list):
        lines.append(f"{prefix}{key}: {', '.join(str(item) for item in value)}")
        return
    lines.append(f"{prefix}{key}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
