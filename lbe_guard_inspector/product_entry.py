"""Product-level LBE entry point.

`lbe start` composes the existing CLI/session/TUI owners into one first-run or
resume path. `lbe capabilities` projects persisted installed-integration
metadata without executing adapters. Every other pre-existing CLI command is
delegated to `lbe_guard_inspector.cli.main`; this module does not become a
second session, provider, credential, tool, or completion authority.
"""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import cli as _cli
from .runtime.installed_capability_registry import InstalledCapabilityRegistryStore


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


def _start(argv: Sequence[str]) -> int:
    parser = _build_start_parser()
    args = parser.parse_args(list(argv))
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

        payload = _cli._tui(args)
    except (ValueError, TypeError, FileNotFoundError, RuntimeError) as exc:
        _cli._emit(
            {"ok": False, "error": type(exc).__name__, "message": str(exc)},
            args.format,
        )
        return 2

    _cli._emit({"ok": True, **payload, "entry": "start"}, args.format)
    return 0


def _capabilities(argv: Sequence[str]) -> int:
    parser = _build_capabilities_parser()
    args = parser.parse_args(list(argv))
    try:
        registry = InstalledCapabilityRegistryStore(args.registry).load()
        statuses = registry.statuses({})
        payload = {
            "action": f"capabilities.{args.action}",
            "schema_version": registry.schema_version,
            "registry": str(InstalledCapabilityRegistryStore(args.registry).path),
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
    raise AssertionError(f"unsupported product command: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)

    product_commands = [command for command in ("start", "capabilities") if command in values]
    if not product_commands:
        return _cli.main(values)
    if len(product_commands) > 1:
        return _cli.main(values)
    return _dispatch_product_command(values, product_commands[0])


if __name__ == "__main__":
    raise SystemExit(main())
