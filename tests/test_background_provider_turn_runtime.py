import threading
import time
from pathlib import Path

from lbe_guard_inspector.control_protocol import ControlMethod, ControlRequest
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.openai_compatible_event_adapter import OpenAICompatibleEventAdapter
from lbe_guard_inspector.persistent_turn_control import PersistentTurnControl
from lbe_guard_inspector.provider_turn_runtime import BackgroundProviderTurnRuntime, NonStreamingProviderTurnRuntime
from lbe_guard_inspector.reasoning_provider import ProviderConfig


class _BlockingTransport:
    def __init__(self) -> None:
        self.started = threading.Event(); self.release = threading.Event()
    def post_json(self, **_: object) -> dict[str, object]:
        self.started.set(); self.release.wait(timeout=5)
        return {"id": "req", "choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]}


def test_background_runtime_leaves_control_responsive_and_rejects_unavailable_live_cancel(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    store.save_session_state(SessionState("s", "w", tmp_path, "coding", "read_only", "development", "openai-compatible", "m"))
    history = SessionOperationalHistory(store=store)
    transport = _BlockingTransport()
    foreground = NonStreamingProviderTurnRuntime(history=history, adapter=OpenAICompatibleEventAdapter(config=ProviderConfig("http://provider.invalid/v1/chat/completions", "m", 5), transport=transport))
    control = PersistentTurnControl(history=history, provider_runtime=BackgroundProviderTurnRuntime(history=history, foreground=foreground))
    started = control.handle(ControlRequest("start", ControlMethod.TURN_START, {"session_id": "s", "text": "go"}))
    assert started.accepted and transport.started.wait(timeout=1)
    turn = history.latest_running_turn(session_id="s")
    assert turn is not None
    assert control.handle(ControlRequest("steer", ControlMethod.TURN_STEER, {"session_id": "s", "turn_id": turn.turn_id, "text": "focus"})).accepted
    cancelled = control.handle(ControlRequest("cancel", ControlMethod.TURN_CANCEL, {"session_id": "s", "turn_id": turn.turn_id}))
    assert not cancelled.accepted and "cancellation" in (cancelled.reason or "")
    transport.release.set()
    for _ in range(100):
        if history.get_turn(turn_id=turn.turn_id).status.value == "completed": break
        time.sleep(.01)
    assert history.get_turn(turn_id=turn.turn_id).status.value == "completed"
