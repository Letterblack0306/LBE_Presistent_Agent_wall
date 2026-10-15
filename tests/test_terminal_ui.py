from __future__ import annotations

import json
from types import SimpleNamespace

import lbe_guard_inspector.product_entry as product_entry
import lbe_guard_inspector.terminal_ui as terminal_ui


def test_mode_labels_match_product_modes() -> None:
    assert terminal_ui._mode_label("investigation") == "PLAN"
    assert terminal_ui._mode_label("coding") == "ACT"
    assert terminal_ui._mode_label("audit") == "AUDIT"


def test_payload_text_only_projects_real_payload_content() -> None:
    assert terminal_ui._payload_text({"message": "real output"}) == "real output"
    assert terminal_ui._payload_text({"message": "   "}) is None
    assert terminal_ui._payload_text({}) is None


def test_render_turn_limits_activity_to_latest_three_real_events(capsys) -> None:
    terminal_ui._render_turn(
        {
            "events": [
                {"event_type": "tool.requested", "payload": {}, "runtime_operation_id": "op-1"},
                {"event_type": "tool.started", "payload": {}, "runtime_operation_id": "op-1"},
                {"event_type": "tool.completed", "payload": {}, "runtime_operation_id": "op-1", "tool_receipt_id": "receipt-1"},
                {"event_type": "governed.reasoning.completed", "payload": {}},
                {"event_type": "model.message.completed", "payload": {"text": "authoritative reply"}},
            ]
        }
    )
    out = capsys.readouterr().out
    assert "ACTIVITY" in out
    assert "ACTIVE PROCESS" not in out
    assert "tool.requested" not in out
    assert "tool.started" in out
    assert "receipt receipt-1" in out
    assert "governed.reasoning.completed" in out
    assert "authoritative reply" in out
    assert " · " not in out


def test_header_is_ascii_safe(capsys) -> None:
    terminal_ui._print_header({"mode": "coding", "provider_id": "p", "provider_model": "m", "session_id": "s"}, terminal_ui.Path("C:/work"))
    out = capsys.readouterr().out
    out.encode("ascii")
    assert "LBE | LOCKSTEP BOUNDARY ENGINE" in out
    assert "+-----------+" in out
    assert "|  |[ | ]|  |" in out
    assert "-" * 60 in out


def test_product_entry_bare_command_delegates_to_terminal_client(monkeypatch) -> None:
    called: list[list[str]] = []

    def fake_terminal_main(argv):
        called.append(list(argv))
        return 17

    monkeypatch.setattr(terminal_ui, "main", fake_terminal_main)
    assert product_entry.main([]) == 17
    assert called == [[]]


def test_run_product_json_uses_existing_product_entry(monkeypatch) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"ok": True, "session_id": "sess-1"}),
            stderr="",
        )

    monkeypatch.setattr(terminal_ui.subprocess, "run", fake_run)
    payload = terminal_ui._run_product_json(["session", "status", "--database", "x", "--session-id", "sess-1"])
    assert payload["session_id"] == "sess-1"
    assert observed["command"][:5] == [
        terminal_ui.sys.executable,
        "-m",
        "lbe_guard_inspector.product_entry",
        "--format",
        "json",
    ]


def test_provider_helpers_delegate_to_existing_product_entry(monkeypatch, tmp_path) -> None:
    calls: list[list[str]] = []

    def fake_run(arguments):
        calls.append(list(arguments))
        if arguments[:2] == ["provider", "list"]:
            return {"providers": ["openai-compatible"], "engines": ["native"], "bindings": []}
        if arguments[:2] == ["provider", "models"]:
            return {"models": ["model-a"], "is_local": True}
        if arguments[:2] == ["provider", "select"]:
            return {"provider_id": "openai-compatible", "provider_model": "model-a"}
        raise AssertionError(arguments)

    monkeypatch.setattr(terminal_ui, "_run_product_json", fake_run)
    provider_config = tmp_path / "provider.json"
    provider_config.write_text("{}", encoding="utf-8")

    assert terminal_ui._providers()["providers"] == ["openai-compatible"]
    assert terminal_ui._models(provider_config)["models"] == ["model-a"]
    selected = terminal_ui._select_model(
        database=tmp_path / "lbe.sqlite3",
        session_id="sess-1",
        provider_id="openai-compatible",
        model_id="model-a",
    )
    assert selected["provider_model"] == "model-a"
    assert calls[0] == ["provider", "list"]
    assert calls[1] == ["provider", "models", "--provider-config", str(provider_config)]
    assert calls[2][:2] == ["provider", "select"]
    assert "--database" in calls[2]
    assert "--session-id" in calls[2]
    assert "--provider" in calls[2]
    assert "--model" in calls[2]


def test_provider_rendering_projects_registry_without_inventing_state(capsys) -> None:
    terminal_ui._render_providers(
        {
            "providers": ["openai-compatible", "anthropic"],
            "engines": ["native", "cline"],
            "bindings": [
                {"provider_id": "openai-compatible", "engine_id": "native"},
                {"provider_id": "anthropic", "engine_id": "cline"},
            ],
        }
    )
    terminal_ui._render_models(
        {"models": ["model-a", "model-b"], "is_local": True},
        selected="model-b",
    )
    out = capsys.readouterr().out
    assert "openai-compatible | engines: native" in out
    assert "anthropic | engines: cline" in out
    assert "ENGINES | native, cline" in out
    assert "  model-a" in out
    assert "* model-b" in out
    assert "SOURCE | local endpoint" in out


def test_render_turn_projects_runtime_approval_gate(capsys) -> None:
    pending = terminal_ui._render_turn(
        {
            "events": [
                {
                    "event_type": "tool.escalated",
                    "runtime_operation_id": "op-approval-1",
                    "payload": {
                        "tool_id": "workspace.patch",
                        "approval_id": "approval-1",
                        "error_code": "AUTHORIZATION_REQUIRED",
                        "error_message": "Needs approval",
                        "authorization": {
                            "verdict": "ESCALATE",
                            "capability": "modify",
                            "rationale": "Needs approval",
                        },
                    },
                }
            ]
        }
    )
    assert pending == {
        "approval_id": "approval-1",
        "capability": "modify",
        "operation_id": "op-approval-1",
        "tool_id": "workspace.patch",
        "rationale": "Needs approval",
    }
    out = capsys.readouterr().out
    assert "ACTION GATE" in out
    assert "approval-1" in out
    assert "/approve or /deny" in out


def test_resolve_pending_authorization_reuses_runtime_identities(monkeypatch, tmp_path) -> None:
    calls: list[list[str]] = []

    def fake_run(arguments):
        calls.append(list(arguments))
        if arguments[:2] == ["operation", "inspect"]:
            return {
                "ok": True,
                "operation_id": "op-1",
                "tool_id": "workspace.patch",
                "capability": "modify",
                "approval_id": "approval-1",
                "decision": "pending",
                "workspace_id": "workspace-1",
                "workspace": str(tmp_path),
            }
        if arguments[:2] == ["authorization", "resolve"]:
            return {
                "ok": True,
                "operation_id": "op-1",
                "capability": "modify",
                "approval_id": "approval-1",
                "verdict": "ALLOW",
            }
        if arguments[:2] == ["operation", "resume"]:
            return {
                "ok": True,
                "operation_id": "op-1",
                "tool_id": "workspace.patch",
                "status": "EXECUTED",
                "receipt_id": "receipt-1",
                "evidence": [{"ref": "workspace:workspace-1:target.txt"}],
            }
        raise AssertionError(arguments)

    monkeypatch.setattr(terminal_ui, "_run_product_json", fake_run)
    receipt = terminal_ui._resolve_pending_authorization(
        database=tmp_path / "lbe.sqlite",
        session_id="session-1",
        pending={
            "approval_id": "approval-1",
            "capability": "modify",
            "operation_id": "op-1",
            "tool_id": "workspace.patch",
            "rationale": "Needs approval",
        },
        decision="approve",
    )
    assert receipt["status"] == "EXECUTED"
    assert [call[:2] for call in calls] == [
        ["operation", "inspect"],
        ["authorization", "resolve"],
        ["operation", "resume"],
    ]
    resolve_call = calls[1]
    assert resolve_call[resolve_call.index("--workspace-id") + 1] == "workspace-1"
    assert resolve_call[resolve_call.index("--approval-id") + 1] == "approval-1"


def test_interactive_commands_include_existing_runtime_routes() -> None:
    assert {"/help", "/status", "/models", "/approve", "/deny", "/quit"}.issubset(
        set(terminal_ui._TERMINAL_COMMANDS)
    )

def test_fullscreen_uses_actual_product_runtime_and_no_second_executor(monkeypatch, tmp_path) -> None:
    """A TTY launch routes to the UI while preserving existing product entry."""
    monkeypatch.setattr(terminal_ui.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(terminal_ui.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(terminal_ui, "_ensure_session", lambda args: "session-1")
    monkeypatch.setattr(terminal_ui, "_status", lambda database, session: {
        "session_id": session, "provider_id": "local",
        "provider_model": "model-1", "mode": "audit"
    })
    seen = {}
    def fake_full_screen(args, session_id, status):
        seen.update({"session_id": session_id, "model": status["provider_model"]})
        return 0
    monkeypatch.setattr(terminal_ui, "_run_full_screen", fake_full_screen)
    config = tmp_path / "provider.json"
    config.write_text('{"model":"model-1"}', encoding="utf-8")
    assert terminal_ui.main([str(tmp_path), "--database", str(tmp_path / "state.sqlite3"),
                             "--provider-config", str(config), "--agent", "audit"]) == 0
    assert seen == {"session_id": "session-1", "model": "model-1"}


def test_cancellable_turn_preserves_json_product_result(monkeypatch):
    import threading
    from types import SimpleNamespace
    class Finished:
        returncode = 0
        def communicate(self):
            return ('{"ok":true,"events":[]}', "")
    monkeypatch.setattr(terminal_ui.subprocess, "Popen", lambda *args, **kwargs: Finished())
    assert terminal_ui._run_cancellable_turn(["turn"], threading.Event())["ok"] is True


def test_cancellable_turn_does_not_claim_rollback(monkeypatch):
    import threading
    import time
    class Running:
        returncode = -15
        def __init__(self):
            self.stopped = threading.Event()
        def communicate(self):
            self.stopped.wait(timeout=3)
            return ("", "")
        def terminate(self):
            self.stopped.set()
        def kill(self):
            self.stopped.set()
    process = Running()
    monkeypatch.setattr(terminal_ui.subprocess, "Popen", lambda *args, **kwargs: process)
    cancellation = threading.Event()
    cancellation.set()
    import pytest
    with pytest.raises(RuntimeError, match="already executed tool effects"):
        terminal_ui._run_cancellable_turn(["turn"], cancellation)
    assert process.stopped.is_set()


def test_live_turn_events_are_delivered_once_in_session_order(monkeypatch, tmp_path):
    import threading
    from types import SimpleNamespace

    event = SimpleNamespace(session_sequence=8, event_type="tool.completed",
                            payload={"tool_id": "workspace.read"}, tool_receipt_id="rcpt-live")
    old = SimpleNamespace(session_sequence=7, event_type="user.message", payload={})
    class History:
        reads = 0
        def __init__(self, *, store):
            pass
        def events_for_session(self, *, session_id):
            self.reads += 1
            return (old,) if self.reads == 1 else (old, event, event)
    class Process:
        returncode = 0
        def communicate(self):
            return ('{"ok":true,"events":[]}', "")
    import lbe_guard_inspector.memory.operational_history as history_module
    monkeypatch.setattr(history_module, "SessionOperationalHistory", History)
    monkeypatch.setattr(terminal_ui.subprocess, "Popen", lambda *args, **kwargs: Process())
    seen = []
    result = terminal_ui._run_cancellable_turn(
        ["turn"], threading.Event(), on_event=seen.append,
        database=tmp_path / "test.sqlite3", session_id="test-session")
    assert result["ok"] is True
    assert [e.tool_receipt_id for e in seen] == ["rcpt-live"]


def test_resume_transcript_replays_real_session_events(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from lbe_guard_inspector.memory import operational_history
    class History:
        def __init__(self, *, store):
            pass
        def events_for_session(self, *, session_id):
            assert session_id == "same-session"
            return [
                SimpleNamespace(event_type="user.message", payload={"text": "check status"}, tool_receipt_id=None, runtime_operation_id=None),
                SimpleNamespace(event_type="tool.completed", payload={}, tool_receipt_id="receipt-1", runtime_operation_id=None),
                SimpleNamespace(event_type="model.message.completed", payload={"text": "Done"}, tool_receipt_id=None, runtime_operation_id=None),
            ]
    monkeypatch.setattr(operational_history, "SessionOperationalHistory", History)
    result=terminal_ui._resume_transcript(tmp_path/"db.sqlite3", "same-session")
    assert "you > check status" in result
    assert "receipt-1" in result
    assert "agent" in result and "Done" in result


def test_fullscreen_is_frameless_conversation_first_layout(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from prompt_toolkit.application import Application
    from prompt_toolkit.output import DummyOutput
    import prompt_toolkit.application.application as app_module
    from prompt_toolkit.input import DummyInput
    monkeypatch.setattr(app_module, "get_app_session", lambda: SimpleNamespace(output=DummyOutput(), input=DummyInput()))
    from prompt_toolkit.layout.containers import HSplit

    db = tmp_path / "state.sqlite3"
    monkeypatch.setattr(terminal_ui, "_resume_transcript", lambda database, sid: "you > recovered turn")
    captured = {}

    def inspect(self, *args, **kwargs):
        captured["root"] = self.layout.container
        return 0
    monkeypatch.setattr(Application, "run", inspect)
    args = SimpleNamespace(database=db, workspace=tmp_path, provider_config=tmp_path / "provider.json")
    status = {"provider_id": "openai-compatible", "provider_model": "model-a", "mode": "audit"}
    assert terminal_ui._run_full_screen(args, "same-session", status) == 0
    root = captured["root"]
    assert isinstance(root, HSplit)
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.layout import walk
    from prompt_toolkit.layout.controls import BufferControl

    windows = [c for c in walk(root) if isinstance(c, Window) and isinstance(c.content, BufferControl)]
    assert len(windows) == 2  # transcript + composer
    transcript, composer = windows
    assert "recovered turn" in transcript.content.buffer.text
    assert transcript.content.buffer.read_only() and not composer.content.buffer.read_only()
    # top bar, rule, transcript, rule, composer, rule, status: no boxed frames
    assert len(root.get_children()) == 7


def test_transcript_styles_come_from_what_each_line_is() -> None:
    lines = [
        "you  > create hello.txt",
        "ACTIVITY",
        "  tool.completed | receipt r-1",
        "  model.error | boom",
        "Agent",
        "done",
        "EFFECTS | governed workspace changes executed: 1 | blocked or failed: 0  (from receipts, not model text)",
        "EFFECTS | governed workspace changes executed: 0 | blocked or failed: 1  (from receipts, not model text)",
        "EFFECTS | governed workspace changes executed: 0 | blocked or failed: 0  (from receipts, not model text)",
        "ACTION GATE",
        "  tool       | workspace.patch",
        "after the gate",
    ]
    styles = terminal_ui._classify_transcript(lines)
    assert styles == [
        "class:user", "class:label", "class:muted", "class:error", "class:label", "class:text",
        "class:ok", "class:warn", "class:muted", "class:warn", "class:warn", "class:text",
    ]


def test_green_is_only_for_executed_effects_never_for_model_words() -> None:
    styles = terminal_ui._classify_transcript(["Agent", "All changes were applied successfully"])
    assert "class:ok" not in styles


def test_no_color_style_keeps_non_color_cues() -> None:
    style = terminal_ui._ui_style(False)
    attrs = {name: style.get_attrs_for_style_str("class:" + name) for name in ("user", "error", "warn")}
    assert all(a.bold for a in attrs.values())
    assert terminal_ui._PALETTE["signal"] == "#ef4b4b"  # logo red, from lbe-logo.svg


def test_ascii_mode_when_requested(monkeypatch) -> None:
    monkeypatch.setenv("LBE_ASCII", "1")
    assert terminal_ui._ascii_only() is True


def test_human_error_is_one_readable_line() -> None:
    raw = ("CalledProcessError: Command '['git', '-C', 'C:\\w', 'rev-parse', 'HEAD']' "
           "returned non-zero exit status 128.")
    out = terminal_ui._human_error(raw)
    assert out == "command failed (exit 128): rev-parse HEAD"
    assert len(terminal_ui._human_error("x" * 500)) <= 180


def test_help_lists_one_command_per_row(capsys) -> None:
    terminal_ui._help()
    rows = capsys.readouterr().out.splitlines()
    assert rows[0] == "COMMANDS"
    assert all(len(r) < 100 for r in rows)
    assert any(r.strip().startswith("/providers") for r in rows)


def test_providers_marks_the_active_one(capsys) -> None:
    terminal_ui._render_providers(
        {"providers": ["a", "b"], "engines": [], "bindings": []}, active="b")
    out = capsys.readouterr().out
    assert "* b" in out and "  a" in out and "* a" not in out


def test_fullscreen_slash_menu_filters_actual_commands(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from prompt_toolkit.application import Application
    from prompt_toolkit.output import DummyOutput
    from prompt_toolkit.input import DummyInput
    import prompt_toolkit.application.application as app_module
    from prompt_toolkit.document import Document
    import prompt_toolkit.widgets as widgets
    monkeypatch.setattr(app_module, "get_app_session", lambda: SimpleNamespace(
        input=DummyInput(), output=DummyOutput()))
    monkeypatch.setattr(terminal_ui, "_resume_transcript", lambda database, session: "")
    text_areas = []
    original = widgets.TextArea
    def record(*args, **kwargs):
        item = original(*args, **kwargs)
        text_areas.append(item)
        return item
    monkeypatch.setattr(widgets, "TextArea", record)
    monkeypatch.setattr(Application, "run", lambda self: 0)
    args = SimpleNamespace(database=tmp_path/"state.sqlite3", workspace=tmp_path,
                           provider_config=tmp_path/"provider.json")
    terminal_ui._run_full_screen(args, "test-session", {"mode":"audit"})
    menu = next(area.completer for area in text_areas if area.completer is not None)
    values = [c.text for c in menu.get_completions(Document("/mo"), None)]
    assert "/model" in values and "/models" in values
    assert "/quit" not in values
    assert list(menu.get_completions(Document("ordinary task"), None)) == []


def test_long_workspace_path_keeps_its_tail_and_never_overflows() -> None:
    path = "C:\\Users\\someone\\Projects\\a-very-long-name\\my-project"
    shown = terminal_ui._fit_path(path, 24)
    assert len(shown) <= 24 and shown.endswith("my-project") and shown.startswith("\u2026")
    assert terminal_ui._fit_path(path, 200) == path
    assert terminal_ui._fit_path(path, 4) == ""
