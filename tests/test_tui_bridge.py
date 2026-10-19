"""Protocol tests for the Rust cockpit bridge. No model or provider is contacted."""
from __future__ import annotations

import io
import json
import pytest
from pathlib import Path
from contextlib import redirect_stdout

from lbe_guard_inspector import tui_bridge


def _messages(result):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        pending = tui_bridge._turn_messages(result)
    return pending, [json.loads(line) for line in buffer.getvalue().splitlines()]


def test_reply_effects_and_context_come_from_events():
    result = {"events": [
        {"event_type": "model.message.completed", "payload": {"text": "hello", "usage": {"input_tokens": 12, "context_window": 100}}},
    ]}
    pending, out = _messages(result)
    assert pending is None
    kinds = [m["type"] for m in out]
    assert kinds == ["reply", "effects", "context"]
    assert out[0]["text"] == "hello"
    assert out[1] == {"type": "effects", "executed": 0, "blocked": 0}
    assert out[2]["used"] == 12 and out[2]["total"] == 100


def test_escalation_becomes_permission_and_blocked_activity():
    result = {"events": [{
        "event_type": "tool.escalated",
        "runtime_operation_id": "op-1",
        "payload": {
            "tool_id": "workspace.write",
            "approval_id": "ap-1",
            "authorization": {"capability": "workspace.write", "rationale": "needs approval"},
        },
    }]}
    pending, out = _messages(result)
    assert pending and pending["approval_id"] == "ap-1" and pending["operation_id"] == "op-1"
    assert any(m["type"] == "activity" and m["status"] == "BLOCKED" for m in out)
    perm = [m for m in out if m["type"] == "permission"][0]
    assert perm["id"] == "ap-1" and "workspace.write" in perm["action"]


def test_executed_mutation_is_counted_only_from_evidence():
    result = {"events": [{
        "event_type": "tool.completed",
        "tool_receipt_id": "rcpt-9",
        "payload": {"tool_id": "workspace.write",
                    "evidence": [{"classification": "current_workspace_mutation"}]},
    }]}
    _, out = _messages(result)
    effects = [m for m in out if m["type"] == "effects"][0]
    assert effects["executed"] == 1
    activity = [m for m in out if m["type"] == "activity"][0]
    assert activity["receipt"] == "rcpt-9" and activity["status"] == "OK"


def test_git_state_reports_branch_and_changed_count(tmp_path):
    import subprocess
    from lbe_guard_inspector import tui_bridge
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / "a.txt").write_text("x")
    state = tui_bridge._git_state(tmp_path)
    assert state is not None and state[0] == "main"


def test_provider_rows_carry_auth_mode_install_state_and_engines():
    rows = tui_bridge._provider_rows({
        "auth": {"claude-code": {"mode": "login", "installed": True, "login_hint": "run `claude`"},
                 "lmstudio": {"mode": "none"}},
        "bindings": [{"provider_id": "lmstudio", "engine_id": "native-lbe"},
                     {"provider_id": "lmstudio", "engine_id": "cline"}],
    })
    by_id = {r["id"]: r for r in rows}
    assert by_id["claude-code"] == {"id": "claude-code", "auth": "login", "engines": [],
                                    "installed": True, "login_hint": "run `claude`"}
    assert by_id["lmstudio"]["engines"] == ["cline", "native-lbe"]
    assert "installed" not in by_id["lmstudio"]


def test_capabilities_not_configured_is_its_own_state(monkeypatch):
    monkeypatch.delenv("LBE_CAPABILITY_REGISTRY", raising=False)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        tui_bridge._emit_capabilities()
    assert json.loads(buffer.getvalue()) == {"type": "capabilities", "configured": False, "items": []}


def test_blocked_activity_carries_reason_and_next_and_permission_carries_target():
    result = {"events": [
        {"event_type": "tool.denied", "payload": {
            "tool_id": "workspace.write", "path": "C:/ProgramData/lbe/v.txt",
            "error_message": "not in allowed write paths", "next_step": "write to docs/ instead"}},
        {"event_type": "tool.escalated", "runtime_operation_id": "op-2", "payload": {
            "tool_id": "workspace.write", "path": "tests/t.py", "approval_id": "ap-2",
            "authorization": {"capability": "workspace.write", "rationale": "needs approval"}}},
        {"event_type": "tool.completed", "payload": {"tool_id": "workspace.read", "path": "a.py"}},
    ]}
    pending, out = _messages(result)
    acts = [m for m in out if m["type"] == "activity"]
    denied = acts[0]
    assert denied["status"] == "BLOCKED" and denied["detail"] == "C:/ProgramData/lbe/v.txt"
    assert "allowed write paths" in denied["reason"] and denied["next"] == "write to docs/ instead"
    assert acts[2]["status"] == "OK" and acts[2]["reason"] == ""
    perm = [m for m in out if m["type"] == "permission"][0]
    assert perm["target"] == "tests/t.py"
    assert pending["target"] == "tests/t.py"


def test_activity_carries_the_runtime_rule_id_without_guessing():
    result = {"events": [
        {"event_type": "tool.denied", "payload": {"tool_id": "workspace.write", "audit_status": "NO_SCOPE_FOUND"}},
        {"event_type": "tool.denied", "payload": {"tool_id": "workspace.write", "authorization": {"guard_id": "secret-file-guard"}}},
        {"event_type": "tool.completed", "payload": {"tool_id": "workspace.read", "path": "a.py"}},
    ]}
    _pending, out = _messages(result)
    rules = [m["rule"] for m in out if m["type"] == "activity"]
    assert rules == ["NO_SCOPE_FOUND", "secret-file-guard", ""]


def test_owner_denial_forwards_target_rule_and_next_step_from_the_runtime():
    result = {"events": [
        {"event_type": "tool.denied", "tool_receipt_id": "receipt-1", "payload": {
            "tool_id": "workspace.write_text", "status": "DENIED", "evidence": [],
            "error_code": "OWNER_AUTHORITY_BLOCKER",
            "error_message": "no proven owner evidence package was supplied. Only the owner can supply it.",
            "output": {"proposed_paths": ["hello.txt"], "satisfiable_by": "owner",
                       "next_step": "stop writing and ask the owner to attach an owner-authority package"}}},
        {"event_type": "tool.completed", "tool_receipt_id": "receipt-2", "payload": {
            "tool_id": "workspace.write_text", "status": "EXECUTED",
            "output": {"path": "hello.txt", "created": True},
            "evidence": [{"classification": "current_workspace_mutation",
                          "metadata": {"relative_path": "hello.txt"}}]}},
    ]}
    _pending, out = _messages(result)
    acts = [m for m in out if m["type"] == "activity"]
    assert acts[0]["rule"] == "OWNER_AUTHORITY_BLOCKER"
    assert acts[0]["detail"] == "hello.txt"
    assert acts[0]["next"].startswith("stop writing and ask the owner")
    assert acts[0]["reason"].startswith("no confirmed owner evidence package was supplied")
    assert acts[1]["detail"] == "hello.txt" and acts[1]["rule"] == ""


def _denied_owner_only():
    return {"event_type": "tool.denied", "tool_receipt_id": "r1", "payload": {
        "tool_id": "workspace.write_text", "status": "DENIED", "evidence": [],
        "error_code": "OWNER_AUTHORITY_BLOCKER",
        "error_message": "no proven owner evidence package was supplied.",
        "output": {"satisfiable_by": "owner", "proposed_paths": ["hello.txt"],
                   "next_step": "stop writing and ask the owner to attach an owner-authority package"}}}


def test_owner_only_denial_with_no_model_message_is_relayed_as_the_reply():
    _pending, out = _messages({"events": [_denied_owner_only()]})
    replies = [m for m in out if m["type"] == "reply"]
    assert len(replies) == 1
    assert replies[0]["text"].startswith("LBE blocked this and only you can resolve it")
    assert "attach an owner sign-off file" in replies[0]["text"]


def test_model_message_is_never_replaced_by_the_denial_relay():
    spoke = {"event_type": "model.message.completed", "payload": {"text": "I need an owner package."}}
    _pending, out = _messages({"events": [_denied_owner_only(), spoke]})
    assert [m["text"] for m in out if m["type"] == "reply"] == ["I need an owner package."]


def test_later_tool_result_clears_the_owner_ask():
    ok = {"event_type": "tool.completed", "payload": {"tool_id": "workspace.write_text", "status": "EXECUTED",
          "evidence": [{"classification": "current_workspace_mutation"}], "output": {"path": "hello.txt"}}}
    _pending, out = _messages({"events": [_denied_owner_only(), ok]})
    assert not any(m["type"] == "reply" and "LBE blocked this" in m["text"] for m in out)


def test_denial_activity_forwards_who_can_resolve_and_the_paths_the_runtime_returned():
    denied = {"event_type": "tool.denied", "tool_receipt_id": "r1", "payload": {
        "tool_id": "workspace.write_text", "status": "DENIED", "evidence": [],
        "error_code": "OWNER_AUTHORITY_BLOCKER", "error_message": "path is outside allowed_paths.",
        "output": {"satisfiable_by": "agent", "allowed_paths": ["hello.txt"],
                   "proposed_paths": ["hello_from_lbe.txt"], "next_step": "write one of the allowed paths"}}}
    _pending, out = _messages({"events": [denied]})
    act = next(m for m in out if m["type"] == "activity")
    assert act["satisfiable_by"] == "agent"
    assert act["allowed_paths"] == ["hello.txt"]
    assert act["proposed_paths"] == ["hello_from_lbe.txt"]
    assert act["next"] == "write one of the allowed paths"


def test_denial_fields_are_omitted_when_the_runtime_did_not_return_them():
    denied = {"event_type": "tool.denied", "payload": {
        "tool_id": "workspace.read", "status": "DENIED", "evidence": [], "error_message": "denied",
        "output": {"satisfiable_by": "someone-else", "allowed_paths": [], "proposed_paths": "not-a-list"}}}
    _pending, out = _messages({"events": [denied]})
    act = next(m for m in out if m["type"] == "activity")
    assert not {"satisfiable_by", "allowed_paths", "proposed_paths"} & set(act)


def test_successful_tool_result_never_carries_denial_fields():
    ok = {"event_type": "tool.completed", "payload": {
        "tool_id": "workspace.write_text", "status": "EXECUTED", "evidence": [],
        "output": {"satisfiable_by": "owner", "allowed_paths": ["a"], "proposed_paths": ["a"]}}}
    _pending, out = _messages({"events": [ok]})
    act = next(m for m in out if m["type"] == "activity")
    assert not {"satisfiable_by", "allowed_paths", "proposed_paths"} & set(act)


def test_forwarded_path_lists_are_bounded():
    many = [f"dir/file_{i}_" + "x" * 200 for i in range(50)]
    denied = {"event_type": "tool.denied", "payload": {
        "tool_id": "workspace.write_text", "status": "DENIED", "evidence": [], "error_message": "denied",
        "output": {"satisfiable_by": "owner", "allowed_paths": many, "next_step": "ask the owner"}}}
    _pending, out = _messages({"events": [denied]})
    act = next(m for m in out if m["type"] == "activity")
    assert len(act["allowed_paths"]) == 20
    assert all(len(item) <= 120 for item in act["allowed_paths"])


_SCREEN_BANNED = ("authority", "proven", "governed")


def test_display_wording_drops_screen_banned_words_but_not_the_persisted_original():
    original = ("no proven owner evidence package was supplied. Only the owner can supply it: an owner-authority "
                "package (issue_id) attached with LBE_OWNER_AUTHORITY_FILE; other write tools are governed the same way.")
    denied = {"event_type": "tool.denied", "tool_receipt_id": "r1", "payload": {
        "tool_id": "workspace.write_text", "status": "DENIED", "evidence": [],
        "error_code": "OWNER_AUTHORITY_BLOCKER", "error_message": original,
        "output": {"satisfiable_by": "owner", "proposed_paths": ["hello.txt"],
                   "next_step": "stop writing and ask the owner to attach an owner-authority package for hello.txt"}}}
    _pending, out = _messages({"events": [denied]})
    act = next(m for m in out if m["type"] == "activity")
    reply = next(m for m in out if m["type"] == "reply")
    for text in (act["reason"], act["next"], reply["text"]):
        assert not any(word in text.lower() for word in _SCREEN_BANNED), text
    assert "owner sign-off file" in act["next"]
    assert act["rule"] == "OWNER_AUTHORITY_BLOCKER"  # identifiers are not reworded
    assert denied["payload"]["error_message"] == original  # the receipt text is untouched


def test_status_codes_keep_their_case_when_reworded():
    assert tui_bridge._plain_words("owner status is OWNER_UNPROVEN") == "owner status is OWNER_UNCONFIRMED"
    assert tui_bridge._plain_words("Authority was not proven") == "sign-off was not confirmed"


def _needs_input_error(details):
    return {"event_type": "model.error", "payload": {
        "error_code": "GOVERNED_PROVIDER_TURN_ERROR",
        "error_message": "RuntimeError: GuardPlanner could not select a guard: INSUFFICIENT_EVIDENCE",
        "reason_code": "INSUFFICIENT_EVIDENCE", "error_details": details}}


def test_controller_stop_becomes_one_blocked_activity_with_the_runtime_fields():
    details = ["checked: generic.index_present (needs bounded project metadata)",
               "missing: generic.index_present: bounded project metadata",
               "investigate: read-only look for README.md, package.json",
               "ask: Where is the evidence for this (README.md)? Name the file, or say it does not exist."]
    _pending, out = _messages({"events": [_needs_input_error(details)]})
    acts = [m for m in out if m["type"] == "activity"]
    assert len(acts) == 1
    act = acts[0]
    assert (act["name"], act["event"], act["status"], act["rule"]) == (
        "reasoning.inspect", "reasoning.needs_input", "BLOCKED", "INSUFFICIENT_EVIDENCE")
    assert act["checked"].startswith("generic.index_present")
    assert act["missing"].startswith("generic.index_present")
    assert act["investigate"].startswith("read-only look for")
    assert act["ask"] == act["next"] and act["ask"].startswith("Where is the evidence")
    assert act["reason"].startswith("GuardPlanner could not select a guard")
    assert [m for m in out if m["type"] == "effects"][0]["blocked"] == 1


def test_error_without_a_runtime_question_keeps_the_plain_error_line():
    _pending, out = _messages({"events": [_needs_input_error(["checked: only this"])]})
    act = next(m for m in out if m["type"] == "activity")
    assert act["event"] == "model.error" and "ask" not in act
    _pending, out = _messages({"events": [{"event_type": "model.error", "payload": {"error_message": "boom"}}]})
    assert next(m for m in out if m["type"] == "activity")["event"] == "model.error"


def _intent_denied(paths=("src/a.py",)):
    return {"event_type": "tool.denied", "tool_receipt_id": "r9", "payload": {
        "tool_id": "workspace.write_text", "status": "DENIED", "evidence": [],
        "error_code": "INTENT_GATE_BLOCKED",
        "error_message": "BLOCKED_INTENT_SCOPE_MISMATCH: no valid intent covers src/a.py.",
        "output": {"satisfiable_by": "owner", "proposed_paths": list(paths), "allowed_paths": [],
                   "next_step": "stop writing and ask the owner to authorize an intent that covers src/a.py",
                   "checked": "active intent BASE-1 (ACTIVE) covers docs/",
                   "missing": "an authorized intent that covers src/a.py",
                   "investigate": "docs/governance/PROJECT_INTENT_LEDGER.md (read-only)",
                   "ask": "What is the reason for changing src/a.py? Reply /intent <reason>."}}}


def test_intent_gate_denial_forwards_its_question_and_remembers_the_stopped_paths():
    tui_bridge._PENDING_INTENT.clear()
    _pending, out = _messages({"events": [_intent_denied()]})
    act = next(m for m in out if m["type"] == "activity")
    assert act["rule"] == "INTENT_GATE_BLOCKED" and act["satisfiable_by"] == "owner"
    assert act["ask"].startswith("What is the reason for changing src/a.py?")
    assert act["checked"].startswith("active intent BASE-1") and act["missing"].startswith("an authorized intent")
    assert tui_bridge._PENDING_INTENT == ["src/a.py"]
    ok = {"event_type": "tool.completed", "payload": {"tool_id": "workspace.write_text", "status": "EXECUTED",
          "evidence": [{"classification": "current_workspace_mutation"}], "output": {"path": "src/a.py"}}}
    _messages({"events": [ok]})
    assert tui_bridge._PENDING_INTENT == []


def test_intent_answer_with_nothing_pending_is_refused():
    tui_bridge._PENDING_INTENT.clear()
    buffer = io.StringIO()
    with redirect_stdout(buffer), pytest.raises(RuntimeError, match="nothing is waiting"):
        tui_bridge._record_intent(Path("."), "because")


def test_intent_answer_is_recorded_as_proposed_and_the_gate_still_decides(tmp_path):
    import shutil
    import subprocess
    root = tmp_path / "ws"
    (root / "scripts").mkdir(parents=True)
    (root / ".lbe" / "governance").mkdir(parents=True)
    (root / "docs" / "governance").mkdir(parents=True)
    (root / "src").mkdir()
    shutil.copy(Path(__file__).resolve().parents[1] / "scripts" / "check-implementation-gate.py", root / "scripts")
    index = "index: `docs/` `src/`\n"
    (root / "PROJECT_INDEX.md").write_text(index, encoding="utf-8")
    (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "docs" / "governance" / "PROJECT_INTENT_LEDGER.md").write_text(
        "## INTENT BASE-1\n\nSTATUS: ACTIVE\nMACHINE_SLICE: S\nEXISTING_OWNER: o\nEXPECTED_PATH_PREFIXES: docs/\n", encoding="utf-8")
    import hashlib
    (root / ".lbe" / "governance" / "implementation-gates.json").write_text(json.dumps({
        "status": "OPEN", "active_slice": "S", "implementation_allowed": True, "active_plan": "p", "active_phase": "ph",
        "intent_and_structure_governance": {"required": True, "intent_required_before_mutation": True, "enforce_before_write": True,
                                            "root_index": "PROJECT_INDEX.md", "intent_ledger": "docs/governance/PROJECT_INTENT_LEDGER.md"},
        "active_intent": {"intent_id": "BASE-1", "index_revision": hashlib.sha256(index.encode()).hexdigest().upper()},
    }), encoding="utf-8")
    for args in (("init", "-q", "-b", "scratch"), ("config", "user.email", "t@t"), ("config", "user.name", "t"),
                 ("add", "-A"), ("commit", "-qm", "base")):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

    tui_bridge._PENDING_INTENT[:] = ["src/a.py"]
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        tui_bridge._record_intent(root, "fix the parser bug in a.py")
    reply = json.loads(buffer.getvalue().splitlines()[-1])
    assert reply["type"] == "reply" and "Recorded as proposed intent LBE-INTENT-PROPOSED-" in reply["text"]
    assert "authorizes nothing" in reply["text"] and "still stops it" in reply["text"]
    assert "STATUS: PROPOSED" in (root / "docs" / "governance" / "PROJECT_INTENT_LEDGER.md").read_text(encoding="utf-8")
    assert tui_bridge._PENDING_INTENT == []


def test_bridge_output_is_utf8_even_when_the_locale_code_page_is_not():
    """A model reply with an em dash reached the Rust client as a cp1252 byte and closed the connection."""
    import os
    import subprocess
    import sys
    code = (
        "from lbe_guard_inspector import tui_bridge as b; b._configure_io(); "
        "b._emit(type='reply', text='a \u2014 b \u201cq\u201d \u00e9')"
    )
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env,
                         cwd=str(Path(__file__).resolve().parents[1]), check=True).stdout
    assert json.loads(out.decode("utf-8"))["text"] == "a — b “q” é"


def test_malformed_protocol_lines_are_reported_and_dropped():
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        assert tui_bridge._parse_request("null") is None
        assert tui_bridge._parse_request("[1, 2]") is None
        assert tui_bridge._parse_request("{broken") is None
        assert tui_bridge._parse_request("   ") is None
        assert tui_bridge._parse_request("x" * (tui_bridge._MAX_REQUEST_CHARS + 1)) is None
        assert tui_bridge._parse_request('{"op": "status"}') == {"op": "status"}
    messages = [json.loads(line)["message"] for line in buffer.getvalue().splitlines()]
    assert messages == ["bridge request must be a JSON object", "bridge request must be a JSON object",
                        "bridge received invalid JSON", "bridge request too large; ignored"]


def test_an_answer_only_applies_to_the_latest_turns_stopped_write():
    tui_bridge._PENDING_INTENT[:] = ["old/stale.py"]
    _messages({"events": [{"event_type": "model.message.completed", "payload": {"text": "nothing blocked this time"}}]})
    assert tui_bridge._PENDING_INTENT == []
    _messages({"events": [_intent_denied(("src/a.py",))]})
    assert tui_bridge._PENDING_INTENT == ["src/a.py"]
