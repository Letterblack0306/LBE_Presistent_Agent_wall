"""JSON-lines stdio bridge between the Rust LBE cockpit and the LBE runtime.

The Rust client owns the terminal; this process owns the governed session. It
reuses ``terminal_ui`` for session bootstrap, turns and authorization so there
is one runtime path, not a second one.

Client -> bridge (one JSON object per line):
  {"op":"turn","text":"..."}            run a governed turn
  {"op":"mode","mode":"plan|act|audit"} change session mode
  {"op":"decision","decision":"approve|reject"}  resolve the pending gate
  {"op":"providers"} / {"op":"models"} / {"op":"status"} / {"op":"quit"}

Bridge -> client:
  ready | error | reply | activity | effects | context | permission |
  receipt | mode | providers | models | status | done
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import terminal_ui as tui


def _emit(**message: Any) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _mode_name(status: dict[str, Any]) -> str:
    return tui._mode_label(status.get("mode")).lower()


def _ready(status: dict[str, Any], session_id: str, workspace: Path) -> None:
    _emit(
        type="ready",
        session_id=session_id,
        mode=_mode_name(status),
        provider=str(status.get("provider_id") or ""),
        model=str(status.get("provider_model") or ""),
        workspace=workspace.name,
    )


def _turn_messages(result: dict[str, Any]) -> dict[str, str] | None:
    """Translate a turn result into protocol messages. Returns pending gate."""
    events = [e for e in (result.get("events") or []) if isinstance(e, dict)]
    final_text: str | None = None
    pending: dict[str, str] | None = None
    executed = blocked = 0
    usage: dict[str, Any] | None = None
    read_only = {"workspace.read", "workspace.list", "workspace.glob", "workspace.search"}

    for event in events:
        etype = str(event.get("event_type") or "event")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
        is_mutation = any(
            isinstance(i, dict) and i.get("classification") == "current_workspace_mutation"
            for i in evidence
        )
        text = tui._payload_text(payload)
        if etype == "tool.completed" and is_mutation:
            executed += 1
        elif etype in {"tool.failed", "tool.denied", "tool.escalated"} and str(
            payload.get("tool_id") or ""
        ) not in read_only:
            blocked += 1
        if etype in {"model.message.completed", "model.output.completed", "assistant.message.completed"} and text:
            final_text = text
        if isinstance(payload.get("usage"), dict):
            usage = payload["usage"]

        receipt = event.get("tool_receipt_id")
        operation = event.get("runtime_operation_id")
        if etype.startswith("tool.") or etype.startswith("governed."):
            tool = str(payload.get("tool_id") or etype)
            status = "BLOCKED" if etype in {"tool.denied", "tool.escalated"} else (
                "FAILED" if etype == "tool.failed" else "OK"
            )
            _emit(type="activity", name=tool, event=etype, status=status,
                  receipt=str(receipt or ""), operation=str(operation or ""))
        elif "error" in etype:
            _emit(type="activity", name=etype, event=etype, status="FAILED",
                  detail=tui._human_error(text or str(payload.get("error_message") or "error")))

        if etype == "tool.escalated":
            auth = payload.get("authorization") if isinstance(payload.get("authorization"), dict) else {}
            approval_id = str(payload.get("approval_id") or "").strip()
            capability = str(auth.get("capability") or "").strip()
            operation_id = str(operation or payload.get("operation_id") or "").strip()
            if approval_id and capability and operation_id:
                pending = {
                    "approval_id": approval_id,
                    "capability": capability,
                    "operation_id": operation_id,
                    "tool_id": str(payload.get("tool_id") or ""),
                    "rationale": str(payload.get("error_message") or auth.get("rationale")
                                     or "Writable operation requires explicit approval."),
                }

    if final_text is None and events:
        last = events[-1].get("payload")
        if isinstance(last, dict):
            final_text = tui._payload_text(last)
    if final_text:
        _emit(type="reply", text=final_text)
    if events:
        _emit(type="effects", executed=executed, blocked=blocked)
    if usage:
        used = usage.get("input_tokens") or usage.get("prompt_tokens")
        total = usage.get("context_window") or usage.get("context_tokens")
        if used is not None:
            _emit(type="context", used=int(used), total=int(total or 0))
    if pending:
        _emit(
            type="permission",
            id=pending["approval_id"],
            action=f"{pending['tool_id'] or 'tool'} ({pending['capability']})",
            scope=pending["rationale"],
        )
    return pending


def serve(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    database = Path(args.database).resolve()
    provider_config = Path(args.provider_config).resolve()
    if not workspace.is_dir():
        _emit(type="error", message=f"workspace missing: {workspace}")
        return 2
    database.parent.mkdir(parents=True, exist_ok=True)
    ns = argparse.Namespace(
        workspace=workspace, database=database, provider_config=provider_config,
        session=args.session, provider=args.provider, model=args.model, agent=args.agent,
    )
    try:
        tui._ensure_workspace_runtime_config(workspace, database)
        session_id = tui._ensure_session(ns)
        status = tui._status(database, session_id)
    except RuntimeError as exc:
        _emit(type="error", message=f"startup failed: {tui._human_error(str(exc))}")
        return 2

    os.environ["LBE_SESSION_ID"] = session_id
    os.environ["LBE_TARGET_WORKSPACE"] = str(workspace)
    os.environ["LBE_WALL_DATABASE"] = str(database)
    os.environ["LBE_PROVIDER_CONFIG"] = str(provider_config)
    _ready(status, session_id, workspace)

    pending: dict[str, str] | None = None
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            _emit(type="error", message="bridge received invalid JSON")
            continue
        op = request.get("op")
        try:
            if op == "quit":
                return 0
            elif op == "turn":
                result = tui._run_product_json([
                    "turn", "--database", str(database), "--session-id", session_id,
                    "--text", str(request.get("text") or ""),
                    "--provider-config", str(provider_config),
                ])
                pending = _turn_messages(result)
            elif op == "mode":
                requested = tui._MODES.get(str(request.get("mode")))
                if requested is None:
                    raise RuntimeError("mode must be plan, act or audit")
                result = tui._set_mode(database, session_id, requested)
                if result.get("accepted", True):
                    _emit(type="mode", mode=_mode_name(result) if result.get("mode") else str(request["mode"]))
                else:
                    raise RuntimeError(f"mode transition rejected: {result.get('status') or result.get('rationale')}")
            elif op == "decision":
                if pending is None:
                    raise RuntimeError("no authorization is pending")
                decision = "approve" if request.get("decision") == "approve" else "reject"
                receipt = tui._resolve_pending_authorization(
                    database=database, session_id=session_id, pending=pending, decision=decision)
                _emit(type="receipt", status=str(receipt.get("status") or "UNKNOWN"),
                      receipt_id=str(receipt.get("receipt_id") or ""),
                      verdict=str((receipt.get("authorization") or {}).get("verdict") or ""))
                if str(receipt.get("status") or "") in {"EXECUTED", "DENIED", "FAILED"}:
                    pending = None
            elif op == "providers":
                payload = tui._providers()
                _emit(type="providers", providers=[str(p) for p in payload.get("providers") or []])
            elif op == "models":
                payload = tui._models(provider_config)
                _emit(type="models", models=[str(m) for m in payload.get("models") or []])
            elif op == "status":
                status = tui._status(database, session_id)
                _ready(status, session_id, workspace)
            else:
                raise RuntimeError(f"unknown op {op!r}")
        except RuntimeError as exc:
            _emit(type="error", message=tui._human_error(str(exc)))
        _emit(type="done")
    return 0


def main(argv: list[str] | None = None) -> int:
    root = tui._default_install_root()
    p = argparse.ArgumentParser(prog="lbe-tui-bridge")
    p.add_argument("--workspace", default=os.environ.get("LBE_TARGET_WORKSPACE") or os.getcwd())
    p.add_argument("--database", default=os.environ.get("LBE_WALL_DATABASE") or str(root / "state" / "lbe.sqlite3"))
    p.add_argument("--provider-config", default=os.environ.get("LBE_PROVIDER_CONFIG") or str(root / "config" / "provider-config.json"))
    p.add_argument("--session", default=os.environ.get("LBE_SESSION_ID"))
    p.add_argument("--provider", default="openai-compatible")
    p.add_argument("--model")
    p.add_argument("--agent", choices=("act", "plan", "audit"), default="act")
    return serve(p.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
