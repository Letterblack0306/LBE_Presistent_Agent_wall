"""JSON-lines stdio bridge between an LBE terminal client and the LBE runtime.

The Rust client owns the terminal; this process owns the governed session. It
reuses ``terminal_ui`` for session bootstrap, turns and authorization so there
is one runtime path, not a second one.

Client -> bridge (one JSON object per line):
  {"op":"turn","text":"..."}            run a governed turn
  {"op":"mode","mode":"plan|act|audit"} change session mode
  {"op":"decision","decision":"approve|reject"}  resolve the pending gate
  {"op":"cancel"}                       stop the running turn (runtime cancel)
  {"op":"select","model":"<id>"}        select a model from the endpoint catalog
  {"op":"providers"} / {"op":"models"} / {"op":"status"} / {"op":"quit"}

Bridge -> client:
  ready | error | reply | activity | effects | context | permission |
  receipt | mode | providers | models | status | done
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from . import terminal_ui as tui
from .runtime import intent_gate


def _tool_detail(payload: dict[str, Any]) -> str:
    """Short human target for a tool row (path/command), never a turn or call id."""
    sources = [payload]
    for key in ("arguments", "input", "parameters", "request", "output"):
        if isinstance(payload.get(key), dict):
            sources.append(payload[key])
    # The runtime records the written file only in evidence metadata.
    for item in payload.get("evidence") or []:
        if isinstance(item, dict) and isinstance(item.get("metadata"), dict):
            sources.append(item["metadata"])
    for src in sources:
        for key in ("path", "file_path", "relative_path", "proposed_paths", "command", "query", "url", "target"):
            value = src.get(key)
            if isinstance(value, (str, list)) and value:
                text = " ".join(map(str, value)) if isinstance(value, list) else value
                return text if len(text) <= 60 else text[:57] + "..."
    return ""


_OWNER_RULE_CODES = {"OWNER_AUTHORITY_BLOCKER", "OWNER_SCOPE_VIOLATION", intent_gate.INTENT_GATE_BLOCKED}

# Paths of the last write the intent gate stopped; the next `/intent <reason>` answers for them.
_PENDING_INTENT: list[str] = []


# Words the screen spec keeps off the client display. Only the *projected* text changes:
# the persisted event, the receipt and the text the model receives keep the original.
_PLAIN_WORDS = (
    (re.compile(r"owner[- ]authority package", re.IGNORECASE), "owner sign-off file"),
    (re.compile(r"owner authority", re.IGNORECASE), "owner sign-off"),
    (re.compile(r"unproven", re.IGNORECASE), "unconfirmed"),
    (re.compile(r"proven", re.IGNORECASE), "confirmed"),
    (re.compile(r"governed", re.IGNORECASE), "checked"),
    (re.compile(r"authority", re.IGNORECASE), "sign-off"),
)


def _plain_words(text: str) -> str:
    """Display wording for runtime text (keeps the original capitalisation style)."""
    for pattern, plain in _PLAIN_WORDS:
        text = pattern.sub(lambda m, plain=plain: plain.upper() if m.group().isupper() else plain, text)
    return text


def _next_step(payload: dict[str, Any]) -> str:
    """The runtime's own next step for a block, in display wording."""
    output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    return _plain_words(str(payload.get("next_step") or output.get("next_step") or ""))


def _denial_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Denial data the runtime already returns in the receipt output, forwarded as-is.
    A key is present only when the runtime supplied it; nothing is inferred here."""
    output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    fields: dict[str, Any] = {}
    resolver = output.get("satisfiable_by")
    if resolver in {"owner", "agent"}:
        fields["satisfiable_by"] = resolver
    for key in ("allowed_paths", "proposed_paths"):
        value = output.get(key)
        if isinstance(value, (list, tuple)) and value:
            fields[key] = [str(item)[:120] for item in value[:20]]
    for key in _NEEDED_KEYS:  # an intent-gate denial says what was checked, what is missing, what to ask
        value = output.get(key)
        if isinstance(value, str) and value.strip():
            fields[key] = _plain_words(" ".join(value.split()))[:400]
    return fields


_NEEDED_KEYS = ("checked", "missing", "investigate", "ask")
_MAX_REQUEST_CHARS = 1_000_000


def _input_needed_fields(payload: dict[str, Any]) -> dict[str, str]:
    """Split the controller's ``error_details`` (``checked:`` / ``missing:`` / ``investigate:`` /
    ``ask:`` lines) into fields. A key is present only when the runtime sent that line."""
    details = payload.get("error_details")
    if not isinstance(details, list):
        return {}
    fields: dict[str, str] = {}
    for line in details:
        if not isinstance(line, str):
            continue
        key, _sep, value = line.partition(":")
        if key in _NEEDED_KEYS and value.strip() and key not in fields:
            fields[key] = _plain_words(" ".join(value.split()))[:400]
    return fields if "ask" in fields else {}


def _record_intent(workspace: Path, reason: str) -> None:
    """The person's answer to an intent-gate stop, recorded as a PROPOSED intent. It authorizes
    nothing: the existing gate is run again and its verdict is reported as it is."""
    if not _PENDING_INTENT:
        raise RuntimeError("nothing is waiting for an intent: no write was stopped for lack of one")
    paths = tuple(_PENDING_INTENT)
    try:
        record = intent_gate.record_proposed_intent(workspace, reason=reason, paths=paths)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    _PENDING_INTENT.clear()
    block = intent_gate.check_paths(workspace, paths)
    verdict = (
        "The implementation gate now passes for these paths."
        if block is None
        else f"The implementation gate still stops it: missing {block.missing}."
    )
    _emit(type="reply", text=_plain_words(
        f"Recorded as proposed intent {record['intent_id']} in {record['ledger']}. It authorizes nothing. "
        f"{verdict} To authorize it, the owner adds EXISTING_OWNER, sets STATUS to AUTHORIZED, and points "
        "active_intent in .lbe/governance/implementation-gates.json at it. Then ask me to retry."))


def _rule_id(payload: dict[str, Any]) -> str:
    """Governance rule id the runtime returned (audit status, blocker or guard id).
    The client maps it to a plain screen name; unknown ids are never guessed here."""
    sources = [payload]
    for key in ("authorization", "blocker", "audit", "error"):
        if isinstance(payload.get(key), dict):
            sources.append(payload[key])
    for src in sources:
        for key in ("rule_id", "governance_rule", "blocker_id", "blocker_code", "guard_id", "audit_status", "status_code"):
            value = src.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    # Owner-authority denials carry their rule as the receipt error code.
    code = payload.get("error_code")
    if code in _OWNER_RULE_CODES:
        return str(code)
    return ""


def _parse_request(raw: str) -> dict[str, Any] | None:
    """One protocol line from the client; anything that is not a bounded JSON object is reported
    and dropped instead of reaching the dispatcher."""
    raw = raw.strip()
    if not raw:
        return None
    if len(raw) > _MAX_REQUEST_CHARS:
        _emit(type="error", message="bridge request too large; ignored")
        return None
    try:
        request = json.loads(raw)
    except json.JSONDecodeError:
        _emit(type="error", message="bridge received invalid JSON")
        return None
    if not isinstance(request, dict):
        _emit(type="error", message="bridge request must be a JSON object")
        return None
    return request


def _configure_io() -> None:
    """The client speaks UTF-8 JSON lines, never the Windows locale code page: a model reply with
    an em dash or an accented letter would otherwise reach the client as an invalid byte."""
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _emit(**message: Any) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _mode_name(status: dict[str, Any]) -> str:
    return tui._mode_label(status.get("mode")).lower()


def _git_state(workspace: Path) -> tuple[str, int] | None:
    """Branch name and changed-file count for the header; None when not a git checkout."""
    def run(*args: str) -> str | None:
        try:
            done = subprocess.run(["git", "-C", str(workspace), *args], capture_output=True,
                                  text=True, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError):
            return None
        return done.stdout if done.returncode == 0 else None
    branch = run("branch", "--show-current")
    changed = run("status", "--porcelain")
    if branch is None or changed is None:
        return None
    return branch.strip(), len([line for line in changed.splitlines() if line.strip()])


def _emit_git(workspace: Path) -> None:
    state = _git_state(workspace)
    if state:
        _emit(type="git", branch=state[0], diff=state[1])


def _provider_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per provider: how it signs in, whether its CLI is installed, and
    which engines are bound. Only fields the runtime reported are included."""
    auth = payload.get("auth") if isinstance(payload.get("auth"), dict) else {}
    engines: dict[str, list[str]] = {}
    for binding in payload.get("bindings") or []:
        if isinstance(binding, dict) and binding.get("provider_id"):
            engines.setdefault(str(binding["provider_id"]), []).append(str(binding.get("engine_id") or ""))
    ids = sorted(set(auth) | set(engines))
    rows = []
    for pid in ids:
        info = auth.get(pid) if isinstance(auth.get(pid), dict) else {}
        row: dict[str, Any] = {"id": pid, "auth": str(info.get("mode") or ""),
                               "engines": sorted(e for e in engines.get(pid, []) if e)}
        if "installed" in info:
            row["installed"] = bool(info["installed"])
        if info.get("login_hint"):
            row["login_hint"] = str(info["login_hint"])
        rows.append(row)
    return rows


def _emit_capabilities() -> None:
    """Project the installed capability registry read-only. Not configured is a
    state of its own, never an empty list."""
    path = os.environ.get("LBE_CAPABILITY_REGISTRY")
    if not path:
        _emit(type="capabilities", configured=False, items=[])
        return
    from .runtime.installed_capability_registry import (
        InstalledCapabilityRegistryStore,
        built_in_adapter_factories,
    )
    try:
        registry = InstalledCapabilityRegistryStore(path).load()
        statuses = registry.statuses(built_in_adapter_factories(registry))
    except (ValueError, TypeError, OSError, KeyError, RuntimeError) as exc:
        _emit(type="capabilities", configured=True, items=[], error=tui._human_error(str(exc)))
        return
    keep = ("integration_id", "kind", "enabled", "availability", "rationale", "risk_class", "access_class")
    _emit(type="capabilities", configured=True,
          items=[{k: v for k, v in s.public_payload().items() if k in keep} for s in statuses])


def _ready(status: dict[str, Any], session_id: str, workspace: Path) -> None:
    _emit(
        type="ready",
        session_id=session_id,
        mode=_mode_name(status),
        provider=str(status.get("provider_id") or ""),
        model=str(status.get("provider_model") or ""),
        workspace=workspace.name,
        permission=str(status.get("permission_mode") or status.get("permission") or ""),
        policy=str(status.get("runtime_policy") or status.get("policy") or ""),
    )


def _turn_messages(result: dict[str, Any]) -> dict[str, str] | None:
    """Translate a turn result into protocol messages. Returns pending gate."""
    events = [e for e in (result.get("events") or []) if isinstance(e, dict)]
    _PENDING_INTENT.clear()  # only the latest turn's stopped write can be answered
    final_text: str | None = None
    pending: dict[str, str] | None = None
    executed = blocked = 0
    usage: dict[str, Any] | None = None
    model_spoke = False
    owner_ask = ""  # set by an owner-only denial, cleared by any later tool result
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
            model_spoke = True
        if isinstance(payload.get("usage"), dict):
            usage = payload["usage"]

        receipt = event.get("tool_receipt_id")
        operation = event.get("runtime_operation_id")
        if etype == "tool.denied" and payload.get("error_code") == intent_gate.INTENT_GATE_BLOCKED:
            stopped = (payload.get("output") or {}).get("proposed_paths") if isinstance(payload.get("output"), dict) else None
            _PENDING_INTENT[:] = [str(p) for p in stopped or []][:20]
        elif etype == "tool.completed" and is_mutation:
            _PENDING_INTENT.clear()
        if etype in {"tool.completed", "tool.failed", "tool.denied", "tool.escalated"}:
            tool = str(payload.get("tool_id") or etype)
            status = "BLOCKED" if etype in {"tool.denied", "tool.escalated"} else (
                "FAILED" if etype == "tool.failed" else "OK"
            )
            reason = ""
            if status != "OK":
                reason = _plain_words(tui._human_error(str(payload.get("error_message") or text or "")))
            output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
            owner_ask = (
                f"LBE blocked this and only you can resolve it: {reason} Next: {_next_step(payload)}"
                if output.get("satisfiable_by") == "owner" and _next_step(payload)
                else ""
            )
            denial = _denial_fields(payload) if status != "OK" else {}
            _emit(type="activity", name=tool, event=etype, status=status,
                  receipt=str(receipt or ""), detail=_tool_detail(payload),
                  reason=reason, next=denial.get("ask") or _next_step(payload),
                  rule=_rule_id(payload), **denial)
        elif "error" in etype and _input_needed_fields(payload):
            # The controller stopped for lack of evidence and said what it would need.
            fields = _input_needed_fields(payload)
            message = str(payload.get("error_message") or "").removeprefix("RuntimeError: ")
            _emit(type="activity", name="reasoning.inspect", event="reasoning.needs_input", status="BLOCKED",
                  receipt="", detail="", reason=_plain_words(tui._human_error(message)),
                  next=fields.get("ask", ""), rule=str(payload.get("reason_code") or ""), **fields)
            blocked += 1
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
                    "target": _tool_detail(payload),
                    "rationale": str(payload.get("error_message") or auth.get("rationale")
                                     or "Writable operation requires explicit approval."),
                }

    if final_text is None and events:
        last = events[-1].get("payload")
        if isinstance(last, dict):
            final_text = tui._payload_text(last)
    if owner_ask and not model_spoke:
        # The turn ended on an owner-only denial and the model said nothing: relay the
        # runtime's own explanation so the ask still reaches the user as a reply.
        final_text = owner_ask
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
            target=pending.get("target", ""),
        )
    return pending


def serve(args: argparse.Namespace) -> int:
    _configure_io()
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
    _emit_git(workspace)

    pending: dict[str, str] | None = None
    cancel = threading.Event()
    ops: "queue.Queue[dict[str, Any] | None]" = queue.Queue()

    def read_stdin() -> None:
        # Cancel must be seen while a turn blocks the worker, so read here.
        for raw in sys.stdin:
            request = _parse_request(raw)
            if request is None:
                continue
            if request.get("op") == "cancel":
                cancel.set()
            else:
                ops.put(request)
        ops.put(None)

    threading.Thread(target=read_stdin, daemon=True).start()

    while True:
        request = ops.get()
        if request is None:
            return 0
        op = request.get("op")
        try:
            if op == "quit":
                return 0
            elif op == "turn":
                if cancel.is_set():
                    # Stop was pressed while this turn was still queued behind another op.
                    cancel.clear()
                    _emit(type="error", message="stopped before the task started; nothing ran")
                    _emit_git(workspace)
                    _emit(type="done")
                    continue
                result = tui._run_cancellable_turn(
                    ["turn", "--database", str(database), "--session-id", session_id,
                     "--text", str(request.get("text") or ""),
                     "--provider-config", str(provider_config)],
                    cancel,
                    database=database,
                    session_id=session_id,
                )
                pending = _turn_messages(result)
                cancel.clear()
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
                _emit(type="providers", providers=_provider_rows(tui._providers()))
            elif op == "models":
                payload = tui._models(provider_config)
                _emit(type="models", models=[str(m) for m in payload.get("models") or []])
            elif op == "select":
                model_id = str(request.get("model") or "").strip()
                if not model_id:
                    raise RuntimeError("usage: /model <model-id>")
                current = tui._status(database, session_id)
                catalog = [str(m) for m in tui._models(provider_config).get("models") or []]
                if model_id not in catalog:
                    raise RuntimeError(f"model is not in the configured endpoint catalog: {model_id}")
                tui._select_model(database=database, session_id=session_id,
                                  provider_id=str(current.get("provider_id") or ""), model_id=model_id)
                _ready(tui._status(database, session_id), session_id, workspace)
            elif op == "intent":
                _record_intent(workspace, str(request.get("text") or ""))
            elif op == "capabilities":
                _emit_capabilities()
            elif op == "status":
                status = tui._status(database, session_id)
                _ready(status, session_id, workspace)
            else:
                raise RuntimeError(f"unknown op {op!r}")
        except RuntimeError as exc:
            _emit(type="error", message=tui._human_error(str(exc)))
        _emit_git(workspace)
        _emit(type="done")


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
