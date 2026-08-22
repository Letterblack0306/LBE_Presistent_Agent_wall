from pathlib import Path

import pytest

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore


def test_list_session_states_is_bounded_ordered_and_workspace_scoped(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    store.save_session_state(SessionState("b", "workspace-1", tmp_path, "coding"))
    store.save_session_state(SessionState("a", "workspace-1", tmp_path, "audit"))
    store.save_session_state(SessionState("c", "workspace-2", tmp_path, "investigation"))

    all_states = store.list_session_states(limit=2)
    assert len(all_states) == 2
    assert all(isinstance(state, SessionState) for state in all_states)

    scoped = store.list_session_states(project_workspace_id="workspace-1")
    assert {state.session_id for state in scoped} == {"a", "b"}
    assert all(state.project_workspace_id == "workspace-1" for state in scoped)


def test_list_session_states_rejects_empty_workspace_identity(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    with pytest.raises(ValueError, match="project_workspace_id"):
        store.list_session_states(project_workspace_id=" ")
