"""Owner authority must reach governed coding turns started from the terminal."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from lbe_guard_inspector import product_entry, terminal_ui
from lbe_guard_inspector.provider_turn_runtime import GovernedCodingTurnRuntime


def _package(**overrides):
    value = {
        "issue_id": "ISSUE-1",
        "owner_file_or_module": "hello.txt",
        "owner_reason": "owner of the file under change",
        "owner_evidence": ["user request"],
        "owner_status": "OWNER_PROVEN",
        "allowed_paths": ["hello.txt"],
        "validation_command": "python -m pytest -q",
    }
    value.update(overrides)
    return value


@pytest.fixture(autouse=True)
def _reset_authority(monkeypatch):
    monkeypatch.setattr(terminal_ui, "_OWNER_AUTHORITY_FILE", None)


def test_turn_parser_accepts_owner_authority_file() -> None:
    args = product_entry._build_turn_parser().parse_args([
        "--database", "d.sqlite3", "--session-id", "s", "--text", "t",
        "--owner-authority-file", "pkg.json",
    ])
    assert args.owner_authority_file == "pkg.json"


def test_authority_flag_is_added_only_to_turn_commands(monkeypatch) -> None:
    monkeypatch.setattr(terminal_ui, "_OWNER_AUTHORITY_FILE", "C:/pkg.json")
    assert terminal_ui._with_owner_authority(["turn", "--text", "x"])[-2:] == ["--owner-authority-file", "C:/pkg.json"]
    assert terminal_ui._with_owner_authority(["provider", "list"]) == ["provider", "list"]


def test_no_authority_attached_means_no_flag() -> None:
    assert terminal_ui._with_owner_authority(["turn", "--text", "x"]) == ["turn", "--text", "x"]


def test_authority_command_attaches_valid_package_and_clears(tmp_path: Path, capsys) -> None:
    path = tmp_path / "pkg.json"
    path.write_text(json.dumps(_package()), encoding="utf-8")
    terminal_ui._handle_authority_command(f"/authority {path}")
    out = capsys.readouterr().out
    assert "attached ISSUE-1 [OWNER_PROVEN]" in out and "hello.txt" in out
    assert terminal_ui._OWNER_AUTHORITY_FILE == str(path.resolve())
    terminal_ui._handle_authority_command("/authority clear")
    assert terminal_ui._OWNER_AUTHORITY_FILE is None


def test_authority_command_rejects_package_the_contract_refuses(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    bad = _package()
    bad.pop("allowed_paths")
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises((ValueError, KeyError)):
        terminal_ui._handle_authority_command(f"/authority {path}")
    assert terminal_ui._OWNER_AUTHORITY_FILE is None


def test_coding_turn_envelope_carries_the_owner_authority_package() -> None:
    captured = {}

    class Gateway:
        def invoke(self, envelope):
            captured["arguments"] = dict(envelope.arguments)
            return SimpleNamespace(
                outcome="COMPLETED", task_id="t",
                response=SimpleNamespace(deterministic_result={}, error=None),
            )

    events = []
    turn = SimpleNamespace(session_id="s")
    state = SimpleNamespace(
        provider_id="p", provider_model="m", session_id="s",
        project_workspace_id="w", canonical_workspace_root="C:/w",
    )
    history = SimpleNamespace(
        get_turn=lambda turn_id: turn,
        store=SimpleNamespace(load_session_state=lambda session_id: state),
        append_event=events.append,
        events_for_turn=lambda turn_id: (),
        finalize_turn=lambda **kwargs: None,
    )
    package = {"owner_authority": _package()}
    runtime = GovernedCodingTurnRuntime(history=history, gateway=Gateway(), reference_context=(package,))
    runtime.run(turn_id="turn-1", text="create hello.txt")
    assert captured["arguments"]["reference_context"] == (package,)
    assert captured["arguments"]["problem"] == "create hello.txt"


def test_default_runtime_has_empty_reference_context() -> None:
    runtime = GovernedCodingTurnRuntime(history=SimpleNamespace(), gateway=SimpleNamespace())
    assert runtime.reference_context == ()


def _turn(*events):
    return {"events": [dict(e) for e in events]}


def test_render_turn_reports_effects_from_receipts_not_model_text(capsys) -> None:
    terminal_ui._render_turn(_turn(
        {"event_type": "tool.completed", "payload": {"tool_id": "workspace.read", "evidence": []}},
        {"event_type": "model.message.completed", "payload": {"text": "hello.txt has been overwritten"}},
    ))
    out = capsys.readouterr().out
    assert "hello.txt has been overwritten" in out  # the model's words are shown as-is
    assert "governed workspace changes executed: 0" in out
    assert "blocked or failed: 0" in out


def test_render_turn_counts_executed_mutation_and_blocked_write(capsys) -> None:
    terminal_ui._render_turn(_turn(
        {"event_type": "tool.completed", "payload": {
            "tool_id": "workspace.create_candidate_text",
            "evidence": [{"classification": "current_workspace_mutation"}]}},
        {"event_type": "tool.failed", "payload": {"tool_id": "workspace.write_text", "evidence": []}},
    ))
    out = capsys.readouterr().out
    assert "changes executed: 1" in out and "blocked or failed: 1" in out
