from __future__ import annotations

import pytest

from lbe_guard_inspector.cline_sidecar_readiness import ClineSidecarReadiness, ClineSidecarReadinessStatus
from lbe_guard_inspector.memory import SessionState
from lbe_guard_inspector.professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderTurnRequest,
)
from lbe_guard_inspector.professional_provider_resolver import ProfessionalTransportRequirements
from lbe_guard_inspector.professional_session_provider import compose_professional_session_provider
from lbe_guard_inspector.professional_turn_runtime import (
    ProfessionalTurnRuntimeError,
    execute_professional_turn,
)
from lbe_guard_inspector.provider_capabilities import (
    CapabilityClaim,
    CapabilitySupport,
    ProviderModelCapabilities,
    ProviderProtocolFamily,
)


_PROTOCOL = ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT


class _Adapter:
    def __init__(self, events):
        self.events = tuple(events)
        self.stream_calls = 0
        self.continuation_calls = 0

    def stream_turn(self, request):
        self.stream_calls += 1
        return self.events

    def continue_with_tool_result(self, request, result):
        self.continuation_calls += 1
        raise AssertionError("P3 turn entrypoint must not execute provider continuation")

    def cancel(self):
        return None


def _event(event_type: ModelEventType, **overrides) -> NormalizedModelEvent:
    values = dict(
        event_type=event_type,
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=_PROTOCOL,
    )
    values.update(overrides)
    return NormalizedModelEvent(**values)


def _request(**overrides) -> ProviderTurnRequest:
    values = dict(
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=_PROTOCOL,
        system_prompt="You are a bounded professional provider transport.",
        messages=({"role": "user", "content": "inspect README"},),
    )
    values.update(overrides)
    return ProviderTurnRequest(**values)


def _ready() -> ClineSidecarReadiness:
    return ClineSidecarReadiness(
        status=ClineSidecarReadinessStatus.READY,
        node_version="v24.15.0",
        bridge_path="C:/bridge/bridge.mjs",
        package_manifest_path="C:/bridge/package.json",
        cline_package_version="0.0.73",
        reason="ready",
    )


def _session_provider(adapter: _Adapter):
    supported = CapabilityClaim(
        support=CapabilitySupport.SUPPORTED,
        reason="test evidence",
        source="test",
    )
    capabilities = ProviderModelCapabilities(
        provider_id="openai-compatible",
        model_id="model-a",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        protocol_family=_PROTOCOL,
        protocol_evidence="test",
        streaming_text=supported,
        client_tool_calls=supported,
    )
    session = SessionState(
        session_id="session-1",
        project_workspace_id="workspace-1",
        canonical_workspace_root="C:/work/example",
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
        provider_id="openai-compatible",
        provider_model="model-a",
    )
    return compose_professional_session_provider(
        session_state=session,
        capabilities=capabilities,
        requirements=ProfessionalTransportRequirements(streaming_text=True),
        provider_config={"providerId": "openai-compatible", "modelId": "model-a"},
        readiness_probe=_ready,
        adapter_factory=lambda: adapter,
    )


def test_completed_turn_stream_is_forwarded_without_runtime_tool_authority() -> None:
    adapter = _Adapter(
        (
            _event(ModelEventType.TURN_STARTED),
            _event(ModelEventType.MESSAGE_DELTA, text="hello"),
            _event(ModelEventType.TURN_COMPLETED),
        )
    )
    result = execute_professional_turn(session_provider=_session_provider(adapter), request=_request())

    assert [event.event_type for event in result.events] == [
        ModelEventType.TURN_STARTED,
        ModelEventType.MESSAGE_DELTA,
        ModelEventType.TURN_COMPLETED,
    ]
    assert result.terminal_event.event_type is ModelEventType.TURN_COMPLETED
    assert result.requires_tool is False
    assert adapter.stream_calls == 1
    assert adapter.continuation_calls == 0


def test_requires_tool_is_terminal_and_does_not_execute_or_continue_tool() -> None:
    adapter = _Adapter(
        (
            _event(ModelEventType.TURN_STARTED),
            _event(
                ModelEventType.TOOL_CALL_COMPLETED,
                provider_tool_call_id="provider-call-1",
                lbe_call_id="lbe-call-1",
                tool_name="workspace.read",
                tool_arguments={"path": "README.md"},
            ),
            _event(
                ModelEventType.TURN_REQUIRES_TOOL,
                provider_tool_call_id="provider-call-1",
                lbe_call_id="lbe-call-1",
                tool_name="workspace.read",
            ),
        )
    )
    result = execute_professional_turn(session_provider=_session_provider(adapter), request=_request())

    assert result.requires_tool is True
    assert result.terminal_event.provider_tool_call_id == "provider-call-1"
    assert result.terminal_event.lbe_call_id == "lbe-call-1"
    assert adapter.continuation_calls == 0


def test_request_provider_identity_must_match_persistent_session() -> None:
    adapter = _Adapter((_event(ModelEventType.TURN_STARTED), _event(ModelEventType.TURN_COMPLETED)))
    with pytest.raises(ProfessionalTurnRuntimeError, match="request does not match the persistent session provider"):
        execute_professional_turn(
            session_provider=_session_provider(adapter),
            request=_request(provider_id="anthropic"),
        )
    assert adapter.stream_calls == 0


def test_event_identity_must_match_persistent_session() -> None:
    adapter = _Adapter(
        (
            _event(ModelEventType.TURN_STARTED),
            _event(ModelEventType.TURN_COMPLETED, model_id="other-model"),
        )
    )
    with pytest.raises(ProfessionalTurnRuntimeError, match="event model_id"):
        execute_professional_turn(session_provider=_session_provider(adapter), request=_request())


def test_stream_must_begin_with_turn_started() -> None:
    adapter = _Adapter((_event(ModelEventType.MESSAGE_DELTA, text="bad"), _event(ModelEventType.TURN_COMPLETED)))
    with pytest.raises(ProfessionalTurnRuntimeError, match="must begin with model.turn.started"):
        execute_professional_turn(session_provider=_session_provider(adapter), request=_request())


def test_duplicate_turn_started_is_rejected() -> None:
    adapter = _Adapter(
        (
            _event(ModelEventType.TURN_STARTED),
            _event(ModelEventType.TURN_STARTED),
            _event(ModelEventType.TURN_COMPLETED),
        )
    )
    with pytest.raises(ProfessionalTurnRuntimeError, match="duplicate model.turn.started"):
        execute_professional_turn(session_provider=_session_provider(adapter), request=_request())


def test_events_after_terminal_are_rejected() -> None:
    adapter = _Adapter(
        (
            _event(ModelEventType.TURN_STARTED),
            _event(ModelEventType.TURN_COMPLETED),
            _event(ModelEventType.MESSAGE_DELTA, text="late"),
        )
    )
    with pytest.raises(ProfessionalTurnRuntimeError, match="after the terminal"):
        execute_professional_turn(session_provider=_session_provider(adapter), request=_request())


def test_stream_without_terminal_event_fails_closed() -> None:
    adapter = _Adapter((_event(ModelEventType.TURN_STARTED), _event(ModelEventType.MESSAGE_DELTA, text="partial")))
    with pytest.raises(ProfessionalTurnRuntimeError, match="without a terminal"):
        execute_professional_turn(session_provider=_session_provider(adapter), request=_request())
