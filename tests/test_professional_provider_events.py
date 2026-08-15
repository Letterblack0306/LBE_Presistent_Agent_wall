import pytest

from lbe_guard_inspector.professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderProtocolFamily,
)


def _event(**values):
    defaults = {
        "event_type": ModelEventType.MESSAGE_DELTA,
        "provider_id": "openai-compatible",
        "model_id": "model-a",
        "protocol_family": ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
        "text": "hello",
        "provider_request_id": "provider-request-1",
    }
    defaults.update(values)
    return NormalizedModelEvent(**defaults)


def test_message_delta_preserves_provider_identity_without_runtime_receipt_identity() -> None:
    event = _event()
    assert event.provider_request_id == "provider-request-1"
    assert event.provider_tool_call_id is None
    assert event.lbe_call_id is None
    assert not hasattr(event, "runtime_operation_id")
    assert not hasattr(event, "tool_receipt_id")


def test_tool_completion_requires_distinct_provider_and_lbe_call_identity() -> None:
    event = _event(
        event_type=ModelEventType.TOOL_CALL_COMPLETED,
        text=None,
        provider_tool_call_id="provider-tool-1",
        lbe_call_id="lbe-call-1",
        tool_name="workspace.read",
        tool_arguments={"path": "README.md"},
    )
    assert event.provider_tool_call_id == "provider-tool-1"
    assert event.lbe_call_id == "lbe-call-1"


def test_invalid_normalized_event_fails_closed() -> None:
    with pytest.raises(ValueError, match="provider_tool_call_id"):
        _event(event_type=ModelEventType.TOOL_CALL_STARTED, text=None, lbe_call_id="lbe-call-1")
    with pytest.raises(ValueError, match="error_code"):
        _event(event_type=ModelEventType.ERROR, text=None)
    with pytest.raises(ValueError, match="usage"):
        _event(event_type=ModelEventType.USAGE_UPDATED, text=None)
