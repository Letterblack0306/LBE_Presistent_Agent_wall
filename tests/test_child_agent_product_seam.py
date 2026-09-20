import json

from lbe_guard_inspector import product_entry
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore


def _seam_call(db, turn_id, argv):
    return product_entry.main(["child-agent", *argv, "--database", str(db), "--session-id", "s1", "--turn-id", turn_id])


def _new_run(db, turn_id, correlation_id, capsys):
    code = _seam_call(
        db,
        turn_id,
        ["create", "--correlation-id", correlation_id, "--parent-agent", "parent-1", "--child-tools", json.dumps(["workspace.read"])],
    )
    assert code == 0
    return json.loads(capsys.readouterr().out)["child_agent"]


def test_child_agent_product_seam_drives_created_started_complete_failed_cancel(tmp_path, capsys):
    db = tmp_path / "state.sqlite3"
    store = WorkspaceMemoryStore(db)
    store.save_session_state(SessionState(session_id="s1", project_workspace_id="w1", canonical_workspace_root=tmp_path, mode="coding"))
    turn = SessionOperationalHistory(store=store).start_turn(session_id="s1")

    created = _new_run(db, turn.turn_id, "corr-create", capsys)
    assert created["status"] == "pending" and created["correlation_id"] == "corr-create"
    run_id = created["child_agent_run_id"]

    assert _seam_call(db, turn.turn_id, ["started", "--child-agent-run-id", run_id, "--child-session-id", "child-s1"]) == 0
    started = json.loads(capsys.readouterr().out)
    assert started["child_agent"]["status"] == "running" and started["child_agent"]["child_session_id"] == "child-s1"

    assert _seam_call(db, turn.turn_id, ["complete", "--child-agent-run-id", run_id, "--receipt-id", "receipt-1"]) == 0
    completed = json.loads(capsys.readouterr().out)
    assert completed["child_agent"]["status"] == "completed" and completed["child_agent"]["receipt_id"] == "receipt-1"

    failed = _new_run(db, turn.turn_id, "corr-failed", capsys)
    assert _seam_call(db, turn.turn_id, ["failed", "--child-agent-run-id", failed["child_agent_run_id"], "--evidence-ref", "ev-1"]) == 0
    assert json.loads(capsys.readouterr().out)["child_agent"]["status"] == "failed"

    cancelled = _new_run(db, turn.turn_id, "corr-cancel", capsys)
    assert _seam_call(db, turn.turn_id, ["cancel", "--child-agent-run-id", cancelled["child_agent_run_id"]]) == 0
    assert json.loads(capsys.readouterr().out)["child_agent"]["status"] == "cancelled"

    history = SessionOperationalHistory(store=WorkspaceMemoryStore(db))
    reruns = history.child_agent_runs_for_turn(turn_id=turn.turn_id)
    assert [r.correlation_id for r in reruns] == ["corr-create", "corr-failed", "corr-cancel"]
    assert {r.status.value for r in reruns} == {"completed", "failed", "cancelled"}


def test_child_agent_product_seam_rejects_missing_run_identity(tmp_path, capsys):
    db = tmp_path / "state.sqlite3"
    store = WorkspaceMemoryStore(db)
    store.save_session_state(SessionState(session_id="s1", project_workspace_id="w1", canonical_workspace_root=tmp_path, mode="coding"))
    turn = SessionOperationalHistory(store=store).start_turn(session_id="s1")
    assert _seam_call(db, turn.turn_id, ["complete", "--child-agent-run-id", "does-not-exist"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and payload["error"] == "KeyError"