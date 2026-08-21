from pathlib import Path

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import OperationalEvent, SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.terminal_projection import project_terminal_timeline, render_terminal_timeline


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
