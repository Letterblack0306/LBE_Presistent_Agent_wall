"""Runtime-owned non-streaming provider turn over existing adapter and history."""
from __future__ import annotations

from .memory.operational_history import SessionOperationalHistory
from .openai_compatible_event_adapter import OpenAICompatibleEventAdapter
from .professional_provider_events import ModelEventType, NormalizedModelEvent, ProviderProtocolFamily
from .provider_event_history import project_provider_events


class NonStreamingProviderTurnRuntime:
    def __init__(self, *, history: SessionOperationalHistory, adapter: OpenAICompatibleEventAdapter, provider_id: str = "openai-compatible") -> None:
        self.history = history
        self.adapter = adapter
        self.provider_id = provider_id

    def run(self, *, turn_id: str, text: str) -> None:
        try:
            events = self.adapter.complete(messages=({"role": "user", "content": text},), provider_id=self.provider_id)
            project_provider_events(history=self.history, turn_id=turn_id, events=events)
        except Exception as exc:
            project_provider_events(history=self.history, turn_id=turn_id, events=(NormalizedModelEvent(
                ModelEventType.ERROR, self.provider_id, self.adapter._config.model, ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                error_code="RUNTIME_PROVIDER_PROJECTION_ERROR", metadata={"error_type": type(exc).__name__},
            ),))
