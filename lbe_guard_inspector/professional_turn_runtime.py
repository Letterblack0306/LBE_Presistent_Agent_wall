"""Professional turn event entrypoint for the P3 provider path.

This layer binds a composed persistent-session provider to one provider turn and
validates the normalized P0 event stream. It does not authorize or execute model
tool proposals. ``model.turn.requires_tool`` remains an outward terminal for
this P3 entrypoint; governed tool execution belongs to the later continuation
loop through LBE runtime/tool_orchestration.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from .professional_provider_events import ModelEventType, NormalizedModelEvent, ProviderTurnRequest
from .professional_session_provider import ProfessionalSessionProvider


class ProfessionalTurnRuntimeError(RuntimeError):
    """Raised when a professional provider stream violates the P0 turn contract."""


_TERMINAL_EVENTS = frozenset(
    {
        ModelEventType.TURN_REQUIRES_TOOL,
        ModelEventType.TURN_REQUIRES_CONTINUATION,
        ModelEventType.TURN_COMPLETED,
        ModelEventType.TURN_INCOMPLETE,
        ModelEventType.TURN_REFUSED,
        ModelEventType.CANCELLED,
        ModelEventType.ERROR,
    }
)


@dataclass(frozen=True)
class ProfessionalTurnResult:
    """Materialized result for clients that need one bounded P3 provider turn."""

    events: tuple[NormalizedModelEvent, ...]
    terminal_event: NormalizedModelEvent

    @property
    def requires_tool(self) -> bool:
        return self.terminal_event.event_type is ModelEventType.TURN_REQUIRES_TOOL


def stream_professional_turn(
    *,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
) -> Iterable[NormalizedModelEvent]:
    """Stream one normalized provider turn with session/ordering validation.

    The function is intentionally authority-free. It forwards normalized model
    events only and stops at the provider terminal contract. Tool proposals are
    never dispatched here.
    """
    _validate_session_request(session_provider, request)
    return _validated_stream(session_provider, request)


def execute_professional_turn(
    *,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
) -> ProfessionalTurnResult:
    """Materialize one validated P3 turn without performing tool execution."""
    events = tuple(stream_professional_turn(session_provider=session_provider, request=request))
    if not events or events[-1].event_type not in _TERMINAL_EVENTS:
        raise ProfessionalTurnRuntimeError("professional turn did not end with a terminal model event")
    return ProfessionalTurnResult(events=events, terminal_event=events[-1])


def _validated_stream(
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
) -> Iterator[NormalizedModelEvent]:
    started = False
    terminal_seen = False

    for index, event in enumerate(session_provider.adapter.stream_turn(request)):
        if not isinstance(event, NormalizedModelEvent):
            raise ProfessionalTurnRuntimeError("professional provider emitted a non-NormalizedModelEvent")
        if terminal_seen:
            raise ProfessionalTurnRuntimeError("professional provider emitted events after the terminal model event")
        if event.provider_id != session_provider.provider_id:
            raise ProfessionalTurnRuntimeError("model event provider_id does not match the persistent session provider")
        if event.model_id != session_provider.model_id:
            raise ProfessionalTurnRuntimeError("model event model_id does not match the persistent session model")
        if event.protocol_family is not request.protocol_family:
            raise ProfessionalTurnRuntimeError("model event protocol_family does not match the provider turn request")

        if index == 0:
            if event.event_type is not ModelEventType.TURN_STARTED:
                raise ProfessionalTurnRuntimeError("professional provider stream must begin with model.turn.started")
            started = True
        elif event.event_type is ModelEventType.TURN_STARTED:
            raise ProfessionalTurnRuntimeError("professional provider emitted duplicate model.turn.started")

        if event.event_type in _TERMINAL_EVENTS:
            terminal_seen = True
        yield event

    if not started:
        raise ProfessionalTurnRuntimeError("professional provider stream was empty")
    if not terminal_seen:
        raise ProfessionalTurnRuntimeError("professional provider stream ended without a terminal model event")


def _validate_session_request(
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
) -> None:
    if not isinstance(session_provider, ProfessionalSessionProvider):
        raise TypeError("session_provider must be ProfessionalSessionProvider")
    if not isinstance(request, ProviderTurnRequest):
        raise TypeError("request must be ProviderTurnRequest")
    if request.provider_id != session_provider.provider_id:
        raise ProfessionalTurnRuntimeError("provider turn request does not match the persistent session provider")
    if request.model_id != session_provider.model_id:
        raise ProfessionalTurnRuntimeError("provider turn request does not match the persistent session model")
