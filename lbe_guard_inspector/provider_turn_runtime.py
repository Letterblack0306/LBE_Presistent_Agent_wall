"""Runtime-owned non-streaming provider turn over existing adapter and history."""
from __future__ import annotations

import threading
from uuid import uuid4

from .agent_integration import AgentMode, AgentRequestEnvelope, GovernedAgentGateway
from .memory.operational_history import OperationalEvent, SessionOperationalHistory, TurnStatus
from .openai_compatible_event_adapter import OpenAICompatibleEventAdapter
from .professional_provider_events import ModelEventType, NormalizedModelEvent, ProviderProtocolFamily
from .provider_event_history import project_provider_events


class NonStreamingProviderTurnRuntime:
    def __init__(self, *, history: SessionOperationalHistory, adapter: OpenAICompatibleEventAdapter, provider_id: str = "openai-compatible") -> None:
        self.history = history
        self.adapter = adapter
        self.provider_id = provider_id
        self._cancel_lock = threading.Lock()
        self._cancelled_turns: set[str] = set()

    @property
    def supports_cancellation(self) -> bool:
        transport = getattr(getattr(self.adapter, "_transport", None), "supports_cancellation", False)
        return bool(transport)

    def cancel(self, *, turn_id: str) -> None:
        with self._cancel_lock:
            self._cancelled_turns.add(turn_id)
        transport = getattr(getattr(self.adapter, "_transport", None), "cancel", None)
        if transport is not None:
            transport()

    def was_cancelled(self, *, turn_id: str) -> bool:
        with self._cancel_lock:
            return turn_id in self._cancelled_turns

    def run(self, *, turn_id: str, text: str) -> None:
        try:
            events = self.adapter.complete(messages=({"role": "user", "content": text},), provider_id=self.provider_id)
            if self.was_cancelled(turn_id=turn_id):
                return
            project_provider_events(history=self.history, turn_id=turn_id, events=events)
        except Exception as exc:
            if self.was_cancelled(turn_id=turn_id):
                return
            project_provider_events(history=self.history, turn_id=turn_id, events=(NormalizedModelEvent(
                ModelEventType.ERROR, self.provider_id, self.adapter._config.model, ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                error_code="RUNTIME_PROVIDER_PROJECTION_ERROR", metadata={"error_type": type(exc).__name__},
            ),))

    def start(self, *, turn_id: str, text: str) -> None:
        self.run(turn_id=turn_id, text=text)


class GovernedCodingTurnRuntime:
    """Project a TUI coding turn through the same governed gateway as ``lbe code``."""

    supports_cancellation = False

    def __init__(self, *, history: SessionOperationalHistory, gateway: GovernedAgentGateway) -> None:
        self.history = history
        self.gateway = gateway

    def cancel(self, *, turn_id: str) -> None:
        raise RuntimeError("live provider cancellation is not available for governed coding")

    def start(self, *, turn_id: str, text: str) -> None:
        self.run(turn_id=turn_id, text=text)

    def run(self, *, turn_id: str, text: str) -> None:
        turn = self.history.get_turn(turn_id=turn_id)
        if turn is None:
            raise ValueError("turn not found")
        state = self.history.store.load_session_state(session_id=turn.session_id)
        if state is None:
            raise ValueError("session not found")
        self.history.append_event(OperationalEvent(
            session_id=turn.session_id, turn_id=turn_id, event_type="model.turn.started", payload={},
            provider_id=state.provider_id, model_id=state.provider_model,
        ))
        try:
            result = self.gateway.invoke(AgentRequestEnvelope(
                request_id=f"tui-{uuid4().hex}",
                session_id=state.session_id,
                task_id=f"tui-task-{turn_id}",
                project_workspace_id=state.project_workspace_id,
                workspace_root=state.canonical_workspace_root,
                mode=AgentMode.CODING,
                operation_id="reasoning.inspect",
                arguments={"problem": text, "max_results": 10},
            ))
            deterministic = dict(result.response.deterministic_result or {})
            for receipt in deterministic.get("governed_tool_receipts", []):
                if isinstance(receipt, dict):
                    self.history.append_event(OperationalEvent(
                        session_id=turn.session_id, turn_id=turn_id,
                        event_type={"EXECUTED": "tool.completed", "DENIED": "tool.denied", "ESCALATED": "tool.escalated"}.get(str(receipt.get("status")), "tool.failed"),
                        payload=receipt, tool_receipt_id=receipt.get("receipt_id"), runtime_operation_id=receipt.get("operation_id"),
                    ))
            output = deterministic.get("provider_output")
            if isinstance(output, str) and output:
                self.history.append_event(OperationalEvent(
                    session_id=turn.session_id, turn_id=turn_id, event_type="model.message.completed", payload={"text": output},
                    provider_id=state.provider_id, model_id=state.provider_model,
                ))
            if result.outcome == "COMPLETED":
                self.history.append_event(OperationalEvent(session_id=turn.session_id, turn_id=turn_id, event_type="model.turn.completed", payload={"task_id": result.task_id, "outcome": result.outcome}))
                self.history.finalize_turn(turn_id=turn_id, status=TurnStatus.COMPLETED)
                return
            raise RuntimeError(result.response.error.message if result.response.error else result.outcome)
        except Exception as exc:
            self.history.append_event(OperationalEvent(session_id=turn.session_id, turn_id=turn_id, event_type="model.error", payload={"error_code": "GOVERNED_CODING_TURN_ERROR", "error_message": f"{type(exc).__name__}: {exc}"}))
            self.history.finalize_turn(turn_id=turn_id, status=TurnStatus.FAILED)


class BackgroundProviderTurnRuntime:
    """One non-blocking lifecycle around the existing non-streaming runtime."""

    def __init__(self, *, history: SessionOperationalHistory, foreground) -> None:
        self.history = history
        self.foreground = foreground
        self._lock = threading.RLock()
        self._threads: dict[str, threading.Thread] = {}

    @property
    def supports_cancellation(self) -> bool:
        return getattr(self.foreground, "supports_cancellation", False)

    def cancel(self, *, turn_id: str) -> None:
        if self.is_running(turn_id=turn_id):
            self.foreground.cancel(turn_id=turn_id)

    def start(self, *, turn_id: str, text: str) -> None:
        with self._lock:
            if self.is_running(turn_id=turn_id):
                raise ValueError("provider turn is already running")
            turn = self.history.get_turn(turn_id=turn_id)
            if turn is None:
                raise ValueError("turn not found")
            self.history.append_event(OperationalEvent(session_id=turn.session_id, turn_id=turn_id, event_type="runtime.provider.queued", payload={}))
            thread = threading.Thread(target=self._run, kwargs={"turn_id": turn_id, "text": text}, daemon=True)
            self._threads[turn_id] = thread
            thread.start()

    def is_running(self, *, turn_id: str) -> bool:
        with self._lock:
            thread = self._threads.get(turn_id)
            return thread is not None and thread.is_alive()

    def _run(self, *, turn_id: str, text: str) -> None:
        try:
            turn = self.history.get_turn(turn_id=turn_id)
            if turn is not None:
                self.history.append_event(OperationalEvent(session_id=turn.session_id, turn_id=turn_id, event_type="runtime.provider.running", payload={}))
                self.foreground.run(turn_id=turn_id, text=text)
        finally:
            with self._lock:
                self._threads.pop(turn_id, None)
