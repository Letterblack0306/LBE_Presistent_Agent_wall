"""Professional turn event entrypoint for the P3 provider path.

This layer binds a composed persistent-session provider to provider turns and
validates the normalized P0 event stream. Tool proposals are not authorized or
executed here. Governed execution is supplied by the continuation runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Iterator

from .professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderToolResultContinuation,
    ProviderTurnRequest,
)
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

ModelEventObserver = Callable[[NormalizedModelEvent], None]


@dataclass(frozen=True)
class ProfessionalTurnResult:
    """Materialized result for one bounded professional provider exchange."""

    events: tuple[NormalizedModelEvent, ...]
    terminal_event: NormalizedModelEvent

    @property
    def requires_tool(self) -> bool:
        return self.terminal_event.event_type is ModelEventType.TURN_REQUIRES_TOOL


def stream_professional_turn(
    *,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
    event_observer: ModelEventObserver | None = None,
) -> Iterable[NormalizedModelEvent]:
    """Stream one normalized provider turn with session/ordering validation.

    ``event_observer`` is called only after each event has passed the P0/session
    validation performed here. The observer receives normalized model events
    only and cannot authorize or execute tools.
    """
    _validate_session_request(session_provider, request)
    _validate_observer(event_observer)
    return _validated_stream(
        session_provider,
        request,
        session_provider.adapter.stream_turn(request),
        event_observer=event_observer,
    )


def execute_professional_turn(
    *,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
    event_observer: ModelEventObserver | None = None,
) -> ProfessionalTurnResult:
    """Materialize one validated provider turn without tool execution."""
    return _materialize(
        stream_professional_turn(
            session_provider=session_provider,
            request=request,
            event_observer=event_observer,
        )
    )


def execute_professional_continuation(
    *,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
    result: ProviderToolResultContinuation,
    event_observer: ModelEventObserver | None = None,
) -> ProfessionalTurnResult:
    """Return one already-executed governed tool result to the provider.

    This function performs provider I/O only. The supplied continuation must
    already contain runtime operation and tool receipt identities produced by
    LBE's governed tool runtime.
    """
    _validate_session_request(session_provider, request)
    _validate_observer(event_observer)
    if not isinstance(result, ProviderToolResultContinuation):
        raise TypeError("result must be ProviderToolResultContinuation")
    stream = session_provider.adapter.continue_with_tool_result(request, result)
    return _materialize(
        _validated_stream(
            session_provider,
            request,
            stream,
            event_observer=event_observer,
        )
    )


def _materialize(events: Iterable[NormalizedModelEvent]) -> ProfessionalTurnResult:
    materialized = tuple(events)
    if not materialized or materialized[-1].event_type not in _TERMINAL_EVENTS:
        raise ProfessionalTurnRuntimeError("professional turn did not end with a terminal model event")
    return ProfessionalTurnResult(events=materialized, terminal_event=materialized[-1])


def _validated_stream(
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
    source: Iterable[NormalizedModelEvent],
    *,
    event_observer: ModelEventObserver | None = None,
) -> Iterator[NormalizedModelEvent]:
    started = False
    terminal_seen = False

    for index, event in enumerate(source):
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
        if event_observer is not None:
            event_observer(event)
        yield event

    if not started:
        raise ProfessionalTurnRuntimeError("professional provider stream was empty")
    if not terminal_seen:
        raise ProfessionalTurnRuntimeError("professional provider stream ended without a terminal model event")


def _validate_observer(observer: ModelEventObserver | None) -> None:
    if observer is not None and not callable(observer):
        raise TypeError("event_observer must be callable")


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
