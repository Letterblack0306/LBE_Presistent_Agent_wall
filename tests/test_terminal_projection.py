from pathlib import Path

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import OperationalEvent, SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.terminal_projection import (
    project_terminal_activity,
    project_terminal_timeline,
    render_terminal_activity,
    render_terminal_event_detail,
    render_terminal_timeline,
)


def test_terminal_projection_renders_persisted_governed_receipt_without_inferring_authority(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    store.save_session_state(SessionState("s", "w", tmp_path, "coding", "write_allowed", "development", "openai-compatible", "m"))
    history = SessionOperationalHistory(store=store)
    turn = history.start_turn(session_id="s")
    history.append_event(OperationalEvent(session_id="s", turn_id=turn.turn_id, event_type="user.message", payload={"text": "Create a file"}))
    history.append_event(OperationalEvent(session_id="s", turn_id=turn.turn_id, event_type="tool.completed", payload={"tool_id": "workspace.create_candidate_text", "status": "executed", "receipt_id": "receipt-1", "output": {"path": "note.txt"}, "evidence": [{"kind": "write"}]}, runtime_operation_id="op-1", tool_receipt_id="receipt-1"))
    history.append_event(OperationalEvent(session_id="s", turn_id=turn.turn_id, event_type="model.turn.completed", payload={"task_id": "task-1", "outcome": "COMPLETED"}))

    cells = project_terminal_timeline(history=history, session_id="s")
    assert [(cell.title, cell.tone) for cell in cells] == [("OBJECTIVE", "objective"), ("TOOL COMPLETED", "success"), ("VALIDATED RESULT", "success")]
    rendered = render_terminal_timeline(history=history, session_id="s")
    assert "tool: workspace.create_candidate_text" in rendered
    assert "receipt: receipt-1" in rendered
    assert "operation: op-1" in rendered
    assert "authorization" not in rendered



def test_structured_activity_and_detail_preserve_persisted_tool_facts(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "details.sqlite3")
    store.save_session_state(SessionState(
        "details", "w", tmp_path, "coding", "write_allowed", "development",
        "openai-compatible", "m",
    ))
    history = SessionOperationalHistory(store=store)
    turn = history.start_turn(session_id="details")
    history.append_event(OperationalEvent(
        session_id="details",
        turn_id=turn.turn_id,
        event_type="tool.completed",
        payload={
            "tool_id": "workspace.create_candidate_text",
            "status": "executed",
            "receipt_id": "receipt-detail",
            "authorization": {"verdict": "ALLOW", "rationale": "delegated"},
            "output": {"path": "note.txt", "diff": {"summary": "1 file changed"}},
            "evidence": [{"kind": "write", "path": "note.txt"}],
        },
        runtime_operation_id="operation-detail",
        tool_receipt_id="receipt-detail",
    ))

    rows = project_terminal_activity(history=history, session_id="details")
    assert len(rows) == 1
    assert (rows[0].kind, rows[0].receipt, rows[0].state) == (
        "tool", "receipt-detail", "completed",
    )
    activity = render_terminal_activity(history=history, session_id="details")
    assert "workspace.create_candidate_text" in activity
    assert "receipt-detail" in activity
    assert "\"authorization\"" not in activity

    detail = render_terminal_event_detail(
        history=history,
        session_id="details",
        sequence=rows[0].sequence,
    )
    assert "authorization=ALLOW rationale=delegated" in detail
    assert "receipt=receipt-detail operation=operation-detail" in detail
    assert "evidence_count=1" in detail
    assert "diff=available summary=1 file changed" in detail


def test_structured_detail_reports_missing_and_unknown_truthfully(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "unknown.sqlite3")
    store.save_session_state(SessionState(
        "unknown", "w", tmp_path, "audit", "read_only", "audit", None, None,
    ))
    history = SessionOperationalHistory(store=store)
    empty = render_terminal_event_detail(history=history, session_id="unknown")
    assert empty == "DETAIL\nunavailable: no persisted runtime events"

    turn = history.start_turn(session_id="unknown")
    history.append_event(OperationalEvent(
        session_id="unknown",
        turn_id=turn.turn_id,
        event_type="tool.requested",
        payload={"tool_id": "workspace.read"},
    ))
    detail = render_terminal_event_detail(history=history, session_id="unknown")
    assert "state=unknown" in detail
    assert "receipt=unavailable" in detail
    assert "authorization=unavailable" in detail
    assert "diff=unavailable summary=unavailable" in detail
    missing = render_terminal_event_detail(
        history=history,
        session_id="unknown",
        sequence=999,
    )
    assert "unavailable: event sequence 999 not found" in missing
