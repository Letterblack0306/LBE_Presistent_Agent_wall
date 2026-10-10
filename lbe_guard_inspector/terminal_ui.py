"""LBE-owned terminal product surface.

This module is presentation/input only.  It delegates session creation, mode
changes and provider turns to the existing LBE product-entry/runtime owners.
It never executes workspace tools, grants permission, writes receipts, or
declares completion on its own.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


_MODES = {
    "plan": "investigation",
    "act": "coding",
    "audit": "audit",
}


def _default_install_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "LetterBlack" / "LBE"
    return Path.home() / ".letterblack" / "LBE"


def _run_product_json(arguments: Sequence[str]) -> dict[str, Any]:
    # product_entry accepts a leading --format for both its direct product
    # commands and the legacy CLI command families it delegates to.  Keeping
    # the format flag before the subcommand is therefore valid for start/turn
    # and required for delegated commands such as session status/mode.
    command = [
        sys.executable,
        "-m",
        "lbe_guard_inspector.product_entry",
        "--format",
        "json",
        *arguments,
    ]
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    raw = completed.stdout.strip()
    if not raw:
        detail = completed.stderr.strip() or f"exit {completed.returncode}"
        raise RuntimeError(f"LBE product entry returned no JSON: {detail}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LBE product entry returned invalid JSON: {raw[:400]}") from exc
    if completed.returncode != 0 or not payload.get("ok", True):
        detail = payload.get("message") or payload.get("reason") or payload.get("error") or completed.stderr.strip()
        raise RuntimeError(str(detail or f"LBE command failed with exit {completed.returncode}"))
    return payload


def _workspace_id(workspace: Path) -> str:
    import hashlib
    digest = hashlib.sha256(str(workspace).lower().encode("utf-8")).hexdigest()
    return f"workspace_{digest}"


def _provider_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"provider config missing: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("provider config must contain a JSON object")
    return value


def _ensure_session(args: argparse.Namespace) -> str:
    if args.session:
        return str(args.session)
    provider = _provider_document(args.provider_config)
    model = str(args.model or provider.get("model") or "").strip()
    if not model:
        raise RuntimeError("provider config must declare a model before creating a session")
    provider_id = str(provider.get("provider_id") or args.provider or "openai-compatible")
    mode = _MODES[args.agent]
    permission = "write_allowed" if args.agent == "act" else ("audit_only" if args.agent == "audit" else "read_only")
    runtime_policy = "permissive" if args.agent in {"act", "plan"} else "audit"
    payload = _run_product_json([
        "start",
        "--database", str(args.database),
        "--workspace", str(args.workspace),
        "--project-workspace-id", _workspace_id(args.workspace),
        "--mode", mode,
        "--permission", permission,
        "--runtime-policy", runtime_policy,
        "--provider", provider_id,
        "--model", model,
        "--provider-config", str(args.provider_config),
    ])
    session_id = payload.get("session_id")
    if not session_id:
        raise RuntimeError("LBE session bootstrap did not return a session id")
    return str(session_id)


def _mode_label(mode: str | None) -> str:
    return {
        "investigation": "PLAN",
        "coding": "ACT",
        "audit": "AUDIT",
    }.get(str(mode or ""), str(mode or "UNKNOWN").upper())


def _status(database: Path, session_id: str) -> dict[str, Any]:
    return _run_product_json([
        "session", "status",
        "--database", str(database),
        "--session-id", session_id,
    ])


def _set_mode(database: Path, session_id: str, requested: str) -> dict[str, Any]:
    return _run_product_json([
        "session", "mode",
        "--database", str(database),
        "--session-id", session_id,
        "--mode", requested,
    ])


def _payload_text(payload: dict[str, Any]) -> str | None:
    for key in ("text", "message", "content", "output", "response"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _render_turn(result: dict[str, Any]) -> None:
    events = list(result.get("events") or [])
    activity: list[str] = []
    final_text: str | None = None
    usage: dict[str, Any] | None = None

    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "event")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        text = _payload_text(payload)
        if event_type in {"model.message.completed", "model.output.completed", "assistant.message.completed"} and text:
            final_text = text
        if "usage" in payload and isinstance(payload["usage"], dict):
            usage = payload["usage"]
        receipt = event.get("tool_receipt_id")
        operation = event.get("runtime_operation_id")
        if receipt:
            activity.append(f"{event_type} | receipt {receipt}")
        elif operation and ("tool" in event_type or "operation" in event_type):
            activity.append(f"{event_type} | {operation}")
        elif "error" in event_type:
            detail = text or str(payload.get("error_message") or payload.get("error_code") or "error")
            activity.append(f"{event_type} | {detail}")
        elif "tool" in event_type or event_type.startswith("governed."):
            activity.append(event_type)

    if activity:
        print("")
        print("ACTIVE PROCESS")
        for line in activity[-3:]:
            print(f"  {line}")

    if final_text:
        print("")
        print("Agent")
        print(final_text)
    elif events:
        last = events[-1]
        payload = last.get("payload") if isinstance(last, dict) and isinstance(last.get("payload"), dict) else {}
        fallback = _payload_text(payload)
        if fallback:
            print("")
            print("Agent")
            print(fallback)

    if usage:
        used = usage.get("input_tokens") or usage.get("prompt_tokens")
        total = usage.get("context_window") or usage.get("context_tokens")
        if used is not None:
            if total:
                print(f"CONTEXT {used}/{total}")
            else:
                print(f"CONTEXT {used}")


def _print_header(status: dict[str, Any], workspace: Path) -> None:
    mode = _mode_label(status.get("mode"))
    provider = status.get("provider_id") or "provider?"
    model = status.get("provider_model") or "model?"
    session = status.get("session_id") or "session?"
    print("LBE | LETTERBLACK")
    print(f"{workspace} | {provider}/{model} | {mode}")
    print(f"session {session}")
    print("-" * 60)


def _help() -> None:
    print("/plan  /act  /audit  /status  /help  /quit")
    print("Enter any other text to start a governed LBE turn.")


def build_parser() -> argparse.ArgumentParser:
    root = _default_install_root()
    parser = argparse.ArgumentParser(prog="lbe", description="LBE coding IDE CLI/TUI")
    parser.add_argument("workspace", nargs="?", default=os.environ.get("LBE_TARGET_WORKSPACE") or os.getcwd())
    parser.add_argument("--database", default=os.environ.get("LBE_WALL_DATABASE") or str(root / "state" / "lbe.sqlite3"))
    parser.add_argument("--provider-config", default=os.environ.get("LBE_PROVIDER_CONFIG") or str(root / "config" / "provider-config.json"))
    parser.add_argument("--session", default=os.environ.get("LBE_SESSION_ID"))
    parser.add_argument("--provider", default="openai-compatible")
    parser.add_argument("--model")
    parser.add_argument("--agent", choices=("act", "plan", "audit"), default="act")
    parser.add_argument("--prompt")
    parser.add_argument("--version", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.version:
        from importlib.metadata import version
        try:
            print(f"lbe {version('lbe-guard-inspector')}")
        except Exception:
            print("lbe")
        return 0

    args.workspace = Path(args.workspace).resolve()
    args.database = Path(args.database).resolve()
    args.provider_config = Path(args.provider_config).resolve()
    if not args.workspace.is_dir():
        raise SystemExit(f"workspace missing: {args.workspace}")

    args.database.parent.mkdir(parents=True, exist_ok=True)
    try:
        session_id = _ensure_session(args)
        current = _status(args.database, session_id)
    except RuntimeError as exc:
        print(f"LBE startup failed: {exc}", file=sys.stderr)
        return 2

    os.environ["LBE_SESSION_ID"] = session_id
    os.environ["LBE_TARGET_WORKSPACE"] = str(args.workspace)
    os.environ["LBE_WALL_DATABASE"] = str(args.database)
    os.environ["LBE_PROVIDER_CONFIG"] = str(args.provider_config)

    _print_header(current, args.workspace)

    if args.prompt:
        print(f"> {args.prompt}")
        try:
            result = _run_product_json([
                "turn",
                "--database", str(args.database),
                "--session-id", session_id,
                "--text", args.prompt,
                "--provider-config", str(args.provider_config),
            ])
            _render_turn(result)
            return 0
        except RuntimeError as exc:
            print(f"FAILED | {exc}", file=sys.stderr)
            return 1

    print("Type /help for commands.")
    while True:
        try:
            line = input("[I] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return 0
        if not line:
            continue
        if line in {"/quit", "/exit"}:
            return 0
        if line == "/help":
            _help()
            continue
        if line == "/status":
            try:
                current = _status(args.database, session_id)
                _print_header(current, args.workspace)
            except RuntimeError as exc:
                print(f"FAILED | {exc}")
            continue
        if line in {"/plan", "/act", "/audit"}:
            requested = _MODES[line[1:]]
            try:
                result = _set_mode(args.database, session_id, requested)
                accepted = result.get("accepted", True)
                if not accepted:
                    print(f"DENIED | {result.get('status') or result.get('rationale') or 'mode transition rejected'}")
                else:
                    print(f"MODE | {_mode_label(result.get('mode') or requested)}")
            except RuntimeError as exc:
                print(f"FAILED | {exc}")
            continue

        print(f"> {line}")
        print("[I] working")
        try:
            result = _run_product_json([
                "turn",
                "--database", str(args.database),
                "--session-id", session_id,
                "--text", line,
                "--provider-config", str(args.provider_config),
            ])
            _render_turn(result)
        except RuntimeError as exc:
            print(f"FAILED | {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
