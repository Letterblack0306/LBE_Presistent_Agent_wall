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



def _run_cancellable_turn(arguments: Sequence[str], cancel_event: Any, *,
                          on_event: Any = None, database: Path | None = None,
                          session_id: str | None = None) -> dict[str, Any]:
    """Interrupt the local turn process, not committed remote/workspace effects."""
    import subprocess as _subprocess

    command = [sys.executable, "-m", "lbe_guard_inspector.product_entry",
               "--format", "json", *arguments]
    process = _subprocess.Popen(
        command, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    history = None
    last_sequence = 0
    if on_event is not None and database is not None and session_id:
        from .cli import WorkspaceMemoryStore
        from .memory.operational_history import SessionOperationalHistory
        history = SessionOperationalHistory(store=WorkspaceMemoryStore(str(database)))
        old = history.events_for_session(session_id=session_id)
        last_sequence = max((event.session_sequence for event in old), default=0)

    def deliver_new_events():
        nonlocal last_sequence
        if history is None:
            return
        for event in history.events_for_session(session_id=session_id):
            if event.session_sequence <= last_sequence:
                continue
            last_sequence = event.session_sequence
            if event.event_type.startswith(("tool.", "runtime.provider.", "model.error")):
                on_event(event)

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(process.communicate)
        while True:
            try:
                stdout, stderr = future.result(timeout=0.15)
                deliver_new_events()
                break
            except FutureTimeout:
                deliver_new_events()
                if cancel_event.is_set():
                    # Request cancellation from the persisted LBE turn owner
                    # before stopping the waiting CLI transport.
                    if history is not None:
                        running = history.latest_running_turn(session_id=session_id)
                        if running is not None:
                            try:
                                _run_product_json([
                                    "control", "cancel", "--database", str(database),
                                    "--session-id", str(session_id),
                                    "--turn-id", running.turn_id,
                                ])
                            except RuntimeError:
                                pass  # local interruption is not proof of runtime cancellation
                    process.terminate()
                    try:
                        future.result(timeout=2)
                    except FutureTimeout:
                        process.kill()
                        future.result(timeout=5)
                    raise RuntimeError(
                        "Turn interrupted locally; already executed tool effects "
                        "must be checked in the LBE receipts."
                    )
    raw = stdout.strip()
    if not raw:
        raise RuntimeError(stderr.strip() or f"LBE turn exited {process.returncode} without JSON")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LBE turn returned invalid JSON: {raw[:400]}") from exc
    if process.returncode != 0 or not payload.get("ok", True):
        raise RuntimeError(str(payload.get("message") or payload.get("reason") or
                               payload.get("error") or stderr.strip() or process.returncode))
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


def _render_turn(result: dict[str, Any]) -> dict[str, str] | None:
    events = list(result.get("events") or [])
    activity: list[str] = []
    final_text: str | None = None
    usage: dict[str, Any] | None = None
    pending: dict[str, str] | None = None

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
        if event_type == "tool.escalated":
            authorization = payload.get("authorization") if isinstance(payload.get("authorization"), dict) else {}
            approval_id = str(payload.get("approval_id") or "").strip()
            capability = str(authorization.get("capability") or "").strip()
            operation_id = str(operation or payload.get("operation_id") or "").strip()
            tool_id = str(payload.get("tool_id") or "").strip()
            if approval_id and capability and operation_id:
                pending = {
                    "approval_id": approval_id,
                    "capability": capability,
                    "operation_id": operation_id,
                    "tool_id": tool_id,
                    "rationale": str(
                        payload.get("error_message")
                        or authorization.get("rationale")
                        or "Writable operation requires explicit Agent Wall approval."
                    ),
                }
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

    if pending is not None:
        print("")
        print("ACTION GATE")
        print(f"  tool       | {pending.get('tool_id') or 'unknown'}")
        print(f"  operation  | {pending['operation_id']}")
        print(f"  capability | {pending['capability']}")
        print(f"  approval   | {pending['approval_id']}")
        print(f"  reason     | {pending['rationale']}")
        print("  decision   | /approve or /deny")
    return pending


# Monochrome terminal projection of docs/reference/ui/lbe-logo.svg.
# Frame, opposing brackets and center bar preserve existing brand geometry.
_LBE_LOGO_TERMINAL = (
    "+-----------+",
    "|  +-----+  |",
    "|  |[ | ]|  |",
    "|  |[ | ]|  |",
    "|  +-----+  |",
    "+-----------+",
)

_TERMINAL_COMMANDS = (
    "/help", "/status", "/providers", "/provider", "/agents", "/models", "/model ",
    "/plan", "/act", "/audit", "/approve", "/deny",
    "/quit", "/exit",
)


def _interactive_reader(database: Path, session_id: str):
    """Editable terminal composer; keep the standard-input fallback dependency-free."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import WordCompleter
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.styles import Style
    except ImportError:
        return lambda: input("[I] > ")

    session = PromptSession(
        history=InMemoryHistory(),
        completer=WordCompleter(_TERMINAL_COMMANDS, sentence=True),
        complete_while_typing=False,
        style=Style.from_dict({
            "bottom-toolbar": "bg:#15171c #a6aab2",
            "prompt": "#e8555a bold",
        }),
    )

    def footer():
        try:
            state = _status(database, session_id)
            model = str(state.get("provider_model") or "model?")
            provider = str(state.get("provider_id") or "provider?")
            mode = _mode_label(state.get("mode"))
        except RuntimeError:
            provider, model, mode = "provider?", "model?", "UNKNOWN"
        return (
            f" {provider}/{model}  |  {mode}  |  "
            "/help  /providers  /models  /plan  /act  /audit  /quit "
        )

    return lambda: session.prompt(
        "LBE > ",
        bottom_toolbar=footer,
        complete_in_thread=False,
    )

def _landing_rows(status: dict[str, Any], workspace: Path) -> tuple[str, ...]:
    """Snapshot real session fields; unknown state is never shown as healthy."""
    provider = str(status.get("provider_id") or "not configured")
    model = str(status.get("provider_model") or "not selected")
    mode = _mode_label(status.get("mode"))
    session = str(status.get("session_id") or "not started")
    return (
        "  LBE  /  LOCKSTEP BOUNDARY ENGINE",
        "  " + "-" * 55,
        f"  Workspace  {workspace}",
        f"  Provider   {provider}",
        f"  Model      {model}",
        f"  Session    {session}",
        f"  Mode       {mode}",
        "  " + "-" * 55,
        "  /providers  list available providers  /models  inspect model catalog",
        "  /model ID   select model          /plan /act /audit  switch mode",
        "  /status     refresh session       /help   commands and keys",
        "  Enter task to start a governed turn.  Tab: commands  Up/Down: history",
    )


def _select_from_catalog(title: str, values: list[str]) -> str | None:
    """Native keyboard picker; never use static example provider/model lists."""
    unique = list(dict.fromkeys(str(v) for v in values if str(v).strip()))
    if not unique:
        return None
    try:
        from prompt_toolkit.shortcuts import radiolist_dialog
        return radiolist_dialog(
            title=title,
            text="Arrow keys: choose  |  Enter: confirm  |  Tab: buttons  |  Esc: cancel",
            values=[(item, item) for item in unique],
        ).run()
    except (ImportError, EOFError, KeyboardInterrupt):
        for index, value in enumerate(unique, 1):
            print(f"  {index:>2}. {value}")
        try:
            reply = input("Choose number (blank cancels): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        return unique[int(reply)-1] if reply.isdigit() and 1 <= int(reply) <= len(unique) else None

def _print_header(status: dict[str, Any], workspace: Path) -> None:
    mode = _mode_label(status.get("mode"))
    provider = status.get("provider_id") or "provider?"
    model = status.get("provider_model") or "model?"
    session = status.get("session_id") or "session?"
    for line in _LBE_LOGO_TERMINAL:
        print(line)
    print("LBE | LOCKSTEP BOUNDARY ENGINE")
    print(f"{workspace} | {provider}/{model} | {mode}")
    print(f"session {session}")
    print("-" * 60)


def _help() -> None:
    print("/plan  /act  /audit  /status  /provider  /providers  /agents  /models  /model <id>  /approve  /deny  /help  /quit")
    print("Provider/model and approval commands delegate to existing LBE runtime owners.")
    print("Enter any other text to start a governed LBE turn.")


def _render_agents() -> None:
    """Read-only catalog of external agent platforms (no model is run)."""
    from .agent_platforms import discover_agent_platforms

    print("AGENT PLATFORMS (catalog only; discovery runs --version, never a model)")
    for row in discover_agent_platforms():
        flags = ", ".join(
            name for name, on in (
                ("mcp", row["mcp_client"]),
                ("hooks", row["hooks"]),
                ("acp", bool(row["acp_args"])),
            ) if on
        ) or "-"
        state = row["version"] or ("installed" if row["installed"] else "not installed")
        print(f"  {row['platform_id']:<13} {row['display_name']:<20} {state:<28} {flags}")


def _providers() -> dict[str, Any]:
    return _run_product_json(["provider", "list"])


def _models(provider_config: Path) -> dict[str, Any]:
    return _run_product_json([
        "provider", "models",
        "--provider-config", str(provider_config),
    ])


def _select_model(
    *,
    database: Path,
    session_id: str,
    provider_id: str,
    model_id: str,
) -> dict[str, Any]:
    return _run_product_json([
        "provider", "select",
        "--database", str(database),
        "--session-id", session_id,
        "--provider", provider_id,
        "--model", model_id,
    ])


def _render_providers(payload: dict[str, Any]) -> None:
    providers = [str(item) for item in payload.get("providers") or []]
    engines = [str(item) for item in payload.get("engines") or []]
    bindings = [item for item in payload.get("bindings") or [] if isinstance(item, dict)]
    print("PROVIDERS")
    for provider in providers:
        related = [
            str(item.get("engine_id"))
            for item in bindings
            if item.get("provider_id") == provider and item.get("engine_id")
        ]
        suffix = f" | engines: {', '.join(related)}" if related else ""
        print(f"  {provider}{suffix}")
    if engines:
        print(f"ENGINES | {', '.join(engines)}")


def _render_models(payload: dict[str, Any], selected: str | None = None) -> None:
    models = [str(item) for item in payload.get("models") or []]
    print("MODELS")
    for model in models:
        marker = "*" if selected and model == selected else " "
        print(f"{marker} {model}")
    if payload.get("is_local") is True:
        print("SOURCE | local endpoint")


def _resolve_pending_authorization(
    *,
    database: Path,
    session_id: str,
    pending: dict[str, str],
    decision: str,
) -> dict[str, Any]:
    inspected = _run_product_json([
        "operation", "inspect",
        "--database", str(database),
        "--session-id", session_id,
        "--operation-id", pending["operation_id"],
    ])
    if str(inspected.get("approval_id") or "") != pending["approval_id"]:
        raise RuntimeError("pending approval identity changed in the LBE runtime")
    if str(inspected.get("capability") or "") != pending["capability"]:
        raise RuntimeError("pending capability identity changed in the LBE runtime")
    resolved = _run_product_json([
        "authorization", "resolve",
        "--database", str(database),
        "--session-id", session_id,
        "--workspace-id", str(inspected["workspace_id"]),
        "--workspace", str(inspected["workspace"]),
        "--capability", pending["capability"],
        "--operation-id", pending["operation_id"],
        "--approval-id", pending["approval_id"],
        "--decision", decision,
    ])
    expected = "ALLOW" if decision == "approve" else "DENY"
    if str(resolved.get("verdict") or "") != expected:
        raise RuntimeError(
            f"LBE authorization resolution returned {resolved.get('verdict')!r}, expected {expected}"
        )
    return _run_product_json([
        "operation", "resume",
        "--database", str(database),
        "--session-id", session_id,
        "--operation-id", pending["operation_id"],
    ])


def _render_governed_receipt(payload: dict[str, Any]) -> None:
    status = str(payload.get("status") or "UNKNOWN")
    print(f"AUTHORIZATION | {status}")
    receipt_id = payload.get("receipt_id")
    if receipt_id:
        print(f"RECEIPT | {receipt_id}")
    authorization = payload.get("authorization")
    if isinstance(authorization, dict) and authorization.get("verdict"):
        print(f"VERDICT | {authorization['verdict']}")
    evidence = payload.get("evidence")
    if isinstance(evidence, list):
        for item in evidence[:3]:
            if isinstance(item, dict) and item.get("ref"):
                print(f"EVIDENCE | {item['ref']}")


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





def _resume_transcript(database: Path, session_id: str) -> str:
    """Project persisted conversational history without creating another store."""
    from .cli import WorkspaceMemoryStore
    from .memory.operational_history import SessionOperationalHistory
    history = SessionOperationalHistory(store=WorkspaceMemoryStore(str(database)))
    lines = []
    for event in history.events_for_session(session_id=session_id):
        payload = event.payload if isinstance(event.payload, dict) else {}
        message = _payload_text(payload)
        if event.event_type == "user.message" and message:
            lines.append("you > " + message)
        elif event.event_type in {"model.message.completed", "model.output.completed", "assistant.message.completed"} and message:
            lines.append("agent\n" + message)
        elif event.event_type in {"tool.completed", "tool.failed", "tool.denied", "tool.escalated"}:
            reference = str(event.tool_receipt_id or event.runtime_operation_id or "")
            lines.append("  " + event.event_type + (" | " + reference if reference else ""))
    return "\n\n".join(lines[-150:])


def _run_full_screen(args: argparse.Namespace, session_id: str, initial: dict[str, Any]) -> int:
    """Terminal view only: all state transitions remain owned by product_entry."""
    import io
    import threading
    cancel_turn = threading.Event()
    from contextlib import redirect_stdout
    from prompt_toolkit.application import Application
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.layout import HSplit, Layout, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.widgets import Frame, TextArea
    from prompt_toolkit.styles import Style

    state = dict(initial)
    pending: dict[str, str] | None = None
    busy = False
    activity_state = "IDLE"
    previous = _resume_transcript(args.database, session_id)
    transcript = TextArea(text=(previous + "\n\n" if previous else
                                "LBE | LOCKSTEP BOUNDARY ENGINE\nWhat can I do for you?\n\n"),
                          read_only=True, scrollbar=True, wrap_lines=True, focusable=True)
    class SlashCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/") or "\n" in text or " " in text:
                return
            for command in _TERMINAL_COMMANDS:
                candidate = command.strip()
                if candidate.startswith(text) and candidate != text:
                    yield Completion(candidate, start_position=-len(text),
                                     display=candidate)

    composer = TextArea(multiline=True, height=3, prompt="> ",
                        scrollbar=False, wrap_lines=True,
                        completer=SlashCompleter(),
                        complete_while_typing=True)
    status = FormattedTextControl(text=lambda: [
        ("class:accent", " LBE  "),
        ("class:status", "  |  " + str(state.get("provider_id") or "?") + "/" +
         str(state.get("provider_model") or "?") + "  |  " +
         _mode_label(state.get("mode")) +
         ("  |  CANCELLING" if busy and cancel_turn.is_set() else "  |  " + activity_state if busy else "  |  READY") +
         ("  |  APPROVAL REQUIRED" if pending else "")),
    ])
    keys = KeyBindings()
    app = None

    def append(text: str):
        if not text:
            return

        def render():
            transcript.buffer.read_only = False
            transcript.text = (transcript.text + text + "\n")[-60000:]
            transcript.buffer.read_only = True
            transcript.buffer.cursor_position = len(transcript.text)
            if app is not None:
                app.invalidate()

        # Prompt-toolkit buffers belong to the UI event loop, not the provider worker.
        loop = getattr(app, "loop", None) if app is not None else None
        if loop is not None and threading.current_thread() is not threading.main_thread():
            loop.call_soon_threadsafe(render)
        else:
            render()

    def run_command(line: str):
        nonlocal busy, pending, state, activity_state
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                if line in {"/help", "?"}:
                    _help()
                elif line == "/status":
                    state = _status(args.database, session_id)
                    for row in _landing_rows(state, args.workspace):
                        print(row)
                elif line == "/providers":
                    _render_providers(_providers())
                elif line == "/agents":
                    _render_agents()
                elif line == "/provider":
                    _render_providers(_providers())
                    print("Choose a compatible configured provider through its runtime binding; selection alone does not grant authorization.")
                elif line == "/models":
                    _render_models(_models(args.provider_config), str(state.get("provider_model") or ""))
                elif line.startswith("/model "):
                    model_id = line[7:].strip()
                    catalog = _models(args.provider_config)
                    options = [str(x) for x in catalog.get("models") or []]
                    if model_id not in options:
                        print("DENIED | model not in the active endpoint catalog")
                    else:
                        result = _select_model(
                            database=args.database, session_id=session_id,
                            provider_id=str(state.get("provider_id") or ""),
                            model_id=model_id)
                        state = _status(args.database, session_id)
                        print("MODEL | " + str(result.get("provider_model") or model_id))
                elif line in {"/plan", "/act", "/audit"}:
                    result = _set_mode(args.database, session_id, _MODES[line[1:]])
                    if result.get("accepted", True):
                        state = _status(args.database, session_id)
                        print("MODE | " + _mode_label(state.get("mode")))
                    else:
                        print("DENIED | " + str(result.get("rationale") or result.get("status") or "mode transition"))
                elif line in {"/approve", "/deny"}:
                    if pending is None:
                        print("DENIED | no operation requires approval")
                    else:
                        receipt = _resolve_pending_authorization(
                            database=args.database, session_id=session_id, pending=pending,
                            decision="approve" if line == "/approve" else "reject")
                        _render_governed_receipt(receipt)
                        if str(receipt.get("status") or "") in {"EXECUTED", "DENIED", "FAILED"}:
                            pending = None
                elif line == "/model":
                    _render_models(_models(args.provider_config), str(state.get("provider_model") or ""))
                    print("Use /model <id> to select a model.")
                else:
                    def show_event(event):
                        nonlocal activity_state
                        event_type = str(event.event_type)
                        activity_state = event_type
                        detail = str(event.payload.get("tool_id") or event.runtime_operation_id or "")
                        receipt = str(event.tool_receipt_id or "")
                        append("  " + event_type +
                               ("  " + detail if detail else "") +
                               ("  receipt " + receipt if receipt else ""))
                        if app is not None:
                            app.invalidate()
                    result = _run_cancellable_turn([
                        "turn", "--database", str(args.database),
                        "--session-id", session_id, "--text", line,
                        "--provider-config", str(args.provider_config)], cancel_turn,
                        on_event=show_event, database=args.database, session_id=session_id)
                    new_pending = _render_turn(result)
                    if new_pending is not None:
                        pending = new_pending
        except Exception as exc:
            out.write("FAILED | " + str(exc) + "\n")
        finally:
            content = out.getvalue().strip()
            append(content or "No displayable result; inspect runtime status with /status")
            busy = False
            activity_state = "IDLE"
            if app is not None:
                app.invalidate()

    @keys.add("enter", filter=Condition(lambda: app is not None and app.layout.current_window == composer.window))
    def submit(event):
        nonlocal busy, activity_state
        if busy:
            return
        line = composer.text.strip()
        if not line:
            return
        composer.text = ""
        if line in {"/quit", "/exit"}:
            event.app.exit(result=0)
            return
        append("you  > " + line)
        cancel_turn.clear()
        busy = True
        activity_state = "STARTING"
        event.app.invalidate()
        threading.Thread(target=run_command, args=(line,), daemon=True).start()

    @keys.add("tab", filter=Condition(lambda: app is not None and app.layout.current_window == composer.window))
    def command_completion(event):
        if composer.buffer.complete_state:
            composer.buffer.complete_next()
        elif composer.text.startswith("/"):
            composer.buffer.start_completion(select_first=False)

    @keys.add("c-j", filter=Condition(lambda: app is not None and app.layout.current_window == composer.window))
    def newline(event):
        event.current_buffer.insert_text("\n")

    @keys.add("f3")
    def open_model_catalog(event):
        # Keep the choice in the composer; submission owns the actual mutation.
        import threading
        def load():
            try:
                catalog = _models(args.provider_config)
                options = [str(x) for x in catalog.get("models") or []]
                if not options:
                    append("No models reported by the configured endpoint.")
                else:
                    append("AVAILABLE MODELS\n" + "\n".join(
                        "  /model " + x for x in options))
                    append("Type /model <id> to select through LBE.")
            except RuntimeError as exc:
                append("MODEL CATALOG | " + str(exc))
        threading.Thread(target=load, daemon=True).start()

    @keys.add("f2")
    def open_provider_catalog(event):
        import threading
        def load():
            try:
                catalog = _providers()
                choices = [str(x) for x in catalog.get("providers") or []]
                append("AVAILABLE PROVIDERS\n" + "\n".join("  " + x for x in choices))
                append("Use /providers for provider details.")
            except RuntimeError as exc:
                append("PROVIDER CATALOG | " + str(exc))
        threading.Thread(target=load, daemon=True).start()

    @keys.add("pageup")
    def scroll_up(event):
        event.app.layout.focus(transcript)
        transcript.window.vertical_scroll = max(0, transcript.window.vertical_scroll - 12)
        event.app.invalidate()

    @keys.add("pagedown")
    def scroll_down(event):
        transcript.window.vertical_scroll += 12
        event.app.invalidate()

    @keys.add("escape")
    def focus_input(event):
        event.app.layout.focus(composer)

    @keys.add("c-c")
    def quit_app(event):
        if busy:
            cancel_turn.set()
            append("LBE | cancellation requested; checking local turn process")
        else:
            event.app.exit(result=0)

    style = Style.from_dict({
        "frame.border": "#34383f",
        "frame.label": "#d6d7dd",
        "accent": "bold #ef4b4b",
        "status": "bg:#17191e #c4c8d0",
    })
    root = HSplit([
        Window(height=1, content=FormattedTextControl(
            text=" LBE  |  LOCKSTEP BOUNDARY ENGINE  |  " + str(args.workspace)), style="class:status"),
        Frame(transcript, title="Conversation / tools"),
        Frame(composer, title="Task  |  Enter send  |  Ctrl+J newline  |  PgUp/PgDn scroll", height=6),
        Window(height=1, content=status, style="class:status"),
    ])
    app = Application(layout=Layout(root, focused_element=composer),
                      key_bindings=keys, style=style, full_screen=True,
                      mouse_support=True)
    return int(app.run() or 0)


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

    if not args.prompt and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            import prompt_toolkit  # noqa: F401
        except ImportError:
            pass
        else:
            return _run_full_screen(args, session_id, current)

    _print_header(current, args.workspace)
    for row in _landing_rows(current, args.workspace):
        print(row)
    pending_authorization: dict[str, str] | None = None

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

    print("Enter a task, or /help for controls. Tab completes commands; Up/Down recalls history.")
    read_line = _interactive_reader(args.database, session_id)
    while True:
        try:
            line = read_line().strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return 0
        if not line:
            continue
        if line in {"/quit", "/exit"}:
            return 0
        if line in {"/help", "?"}:
            _help()
            continue
        if line == "/status":
            try:
                current = _status(args.database, session_id)
                _print_header(current, args.workspace)
            except RuntimeError as exc:
                print(f"FAILED | {exc}")
            continue
        if line in {"/approve", "/deny"}:
            if pending_authorization is None:
                print("DENIED | no Agent Wall authorization is pending")
                continue
            try:
                decision = "approve" if line == "/approve" else "reject"
                receipt = _resolve_pending_authorization(
                    database=args.database,
                    session_id=session_id,
                    pending=pending_authorization,
                    decision=decision,
                )
                _render_governed_receipt(receipt)
                if str(receipt.get("status") or "") in {"EXECUTED", "DENIED", "FAILED"}:
                    pending_authorization = None
            except RuntimeError as exc:
                print(f"FAILED | {exc}")
            continue
        if line == "/provider":
            try:
                catalog = _providers()
                raw = catalog.get("providers") or []
                names = [
                    str(item.get("provider_id") or item.get("id") or item.get("name") or "")
                    if isinstance(item, dict) else str(item) for item in raw
                ]
                selected_provider = _select_from_catalog("LBE providers", names)
                if selected_provider:
                    print(f"PROVIDER | {selected_provider} (catalog choice; use /models to inspect endpoint models)")
                    print("Provider switching requires a compatible configured session binding; no silent provider mutation.")
            except RuntimeError as exc:
                print(f"FAILED | {exc}")
            continue
        if line == "/agents":
            _render_agents()
            continue
        if line == "/providers":
            try:
                _render_providers(_providers())
            except RuntimeError as exc:
                print(f"FAILED | {exc}")
            continue
        if line == "/models":
            try:
                current = _status(args.database, session_id)
                _render_models(_models(args.provider_config), str(current.get("provider_model") or ""))
            except RuntimeError as exc:
                print(f"FAILED | {exc}")
            continue
        if line == "/model":
            try:
                current = _status(args.database, session_id)
                available = _models(args.provider_config)
                choices = [
                    str(item.get("id") or item.get("model") or "")
                    if isinstance(item, dict) else str(item)
                    for item in (available.get("models") or [])
                ]
                chosen = _select_from_catalog("LBE models", choices)
                if chosen:
                    selected = _select_model(
                        database=args.database,
                        session_id=session_id,
                        provider_id=str(current.get("provider_id") or ""),
                        model_id=chosen,
                    )
                    print(f"MODEL | {selected.get('provider_id')}/{selected.get('provider_model')}")
            except RuntimeError as exc:
                print(f"FAILED | {exc}")
            continue
        if line.startswith("/model "):
            model_id = line[len("/model "):].strip()
            if not model_id:
                print("FAILED | usage: /model <model-id>")
                continue
            try:
                current = _status(args.database, session_id)
                provider_id = str(current.get("provider_id") or "").strip()
                if not provider_id:
                    raise RuntimeError("active session has no provider id")
                available = _models(args.provider_config)
                model_ids = [str(item) for item in available.get("models") or []]
                if model_id not in model_ids:
                    print(f"DENIED | model is not present in the configured endpoint catalog: {model_id}")
                    continue
                selected = _select_model(
                    database=args.database,
                    session_id=session_id,
                    provider_id=provider_id,
                    model_id=model_id,
                )
                print(f"MODEL | {selected.get('provider_id')}/{selected.get('provider_model')}")
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
            new_pending = _render_turn(result)
            if new_pending is not None:
                pending_authorization = new_pending
        except RuntimeError as exc:
            print(f"FAILED | {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
