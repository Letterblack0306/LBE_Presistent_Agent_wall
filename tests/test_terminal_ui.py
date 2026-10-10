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
    assert "ACTIVE PROCESS" in out
    assert "tool.requested" not in out
    assert "tool.started" in out
    assert "receipt receipt-1" in out
    assert "governed.reasoning.completed" in out
    assert "authoritative reply" in out


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
    assert observed["command"][:3] == [
        terminal_ui.sys.executable,
        "-m",
        "lbe_guard_inspector.product_entry",
    ]
