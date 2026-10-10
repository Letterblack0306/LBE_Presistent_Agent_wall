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
    assert " · " not in out


def test_header_is_ascii_safe(capsys) -> None:
    terminal_ui._print_header({"mode": "coding", "provider_id": "p", "provider_model": "m", "session_id": "s"}, terminal_ui.Path("C:/work"))
    out = capsys.readouterr().out
    out.encode("ascii")
    assert "LBE | LETTERBLACK" in out
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
