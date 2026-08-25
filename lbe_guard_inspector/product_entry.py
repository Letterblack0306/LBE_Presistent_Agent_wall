"""Product-level LBE entry point.

`lbe start` composes the existing CLI/session/TUI owners into one first-run or
resume path. Every pre-existing CLI command is delegated byte-for-byte in
behavior to `lbe_guard_inspector.cli.main`; this module does not become a second
session, provider, credential, tool, or completion authority.
"""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import cli as _cli


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
            # Restoring an existing session must not silently replace its persisted
            # workspace/provider/profile/policy identity with caller-supplied values.
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


def main(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)

    # Preserve all historical CLI behavior unless the explicit product-level
    # `start` command is selected. Support the existing global --format option
    # before `start` as well as `lbe start --format ...`.
    start_index = next((index for index, value in enumerate(values) if value == "start"), None)
    if start_index is None:
        return _cli.main(values)

    prefix = values[:start_index]
    suffix = values[start_index + 1 :]
    if prefix:
        if len(prefix) == 2 and prefix[0] == "--format" and prefix[1] in {"json", "text"}:
            if "--format" not in suffix:
                suffix = ["--format", prefix[1], *suffix]
        else:
            # Let the legacy parser produce its normal deterministic error for
            # malformed global command structure rather than reinterpret it.
            return _cli.main(values)
    return _start(suffix)


if __name__ == "__main__":
    raise SystemExit(main())
