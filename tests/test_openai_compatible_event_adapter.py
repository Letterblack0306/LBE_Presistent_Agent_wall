from __future__ import annotations

from typing import Any, Mapping

import pytest

from lbe_guard_inspector.openai_compatible_event_adapter import OpenAICompatibleEventAdapter
from lbe_guard_inspector.professional_provider_events import ModelEventType
from lbe_guard_inspector.reasoning_provider import (
    LBE_DEFAULT_MAX_OUTPUT_TOKENS,
    LBE_MAX_OUTPUT_TOKENS_CEILING,
    ProviderConfig,
    ProviderError,
)


def _response_with_tool_call() -> Mapping[str, Any]:
    return {
        "id": "chatcmpl-bounded",
        "choices": [{
            "message": {"content": None, "tool_calls": [{
                "id": "provider-call-1",
                "function": {"name": "workspace.read", "arguments": '{"path":"README.md"}'},
            }]},
            "finish_reason": "tool_calls",
        }],
    }


class _Transport:
    def __init__(self, response: Mapping[str, Any] | Exception) -> None:
        self.response = response
        self.requests: list[Mapping[str, Any]] = []

    def post_json(self, **request: Any) -> Mapping[str, Any]:
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    @property
    def payloads(self) -> list[Mapping[str, Any]]:
        return [dict(request.get("payload") or {}) for request in self.requests]


class _StreamTransport(_Transport):
    def stream_json(self, **request: Any):
        self.requests.append(request)
        yield {"id": "chatcmpl-stream", "choices": [{"delta": {"content": "Hel"}}]}
        yield {"choices": [{"delta": {"content": "lo"}}]}
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}


def _adapter(response: Mapping[str, Any] | Exception) -> OpenAICompatibleEventAdapter:
    return OpenAICompatibleEventAdapter(
        config=ProviderConfig(endpoint="http://provider/v1/chat/completions", model="local-model", timeout_seconds=5),
        transport=_Transport(response),
    )


def test_complete_text_response_emits_no_fabricated_delta_and_preserves_usage() -> None:
    events = _adapter({
        "id": "chatcmpl-1",
        "choices": [{"message": {"content": "complete response"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }).complete(messages=({"role": "user", "content": "hello"},))

    assert [event.event_type for event in events] == [
        ModelEventType.TURN_STARTED,
        ModelEventType.MESSAGE_COMPLETED,
        ModelEventType.USAGE_UPDATED,
        ModelEventType.TURN_COMPLETED,
    ]
    assert events[1].text == "complete response"
    assert events[2].usage == {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
    assert all(event.event_type is not ModelEventType.MESSAGE_DELTA for event in events)


def test_stream_normalizes_progressive_message_deltas_and_terminal_completion() -> None:
    transport = _StreamTransport({})
    adapter = OpenAICompatibleEventAdapter(
        config=ProviderConfig(endpoint="http://provider/v1/chat/completions", model="local-model", timeout_seconds=5),
        transport=transport,
    )

    events = tuple(adapter.stream(messages=({"role": "user", "content": "hello"},)))

    assert [event.event_type for event in events] == [
        ModelEventType.TURN_STARTED,
        ModelEventType.MESSAGE_DELTA,
        ModelEventType.MESSAGE_DELTA,
        ModelEventType.TURN_COMPLETED,
    ]
    assert "".join(event.text or "" for event in events) == "Hello"
    assert transport.requests[0]["payload"]["stream"] is True


def test_complete_tool_call_preserves_distinct_provider_and_lbe_identity() -> None:
    events = _adapter({
        "id": "chatcmpl-2",
        "choices": [{
            "message": {"content": None, "tool_calls": [{
                "id": "provider-call-1",
                "function": {"name": "workspace.read", "arguments": '{"path":"README.md"}'},
            }]},
            "finish_reason": "tool_calls",
        }],
    }).complete(
        messages=({"role": "user", "content": "read"},),
        lbe_call_id_for_provider_tool_call=lambda _: "lbe-call-1",
    )

    assert [event.event_type for event in events] == [
        ModelEventType.TURN_STARTED,
        ModelEventType.TOOL_CALL_STARTED,
        ModelEventType.TOOL_CALL_COMPLETED,
        ModelEventType.TURN_REQUIRES_TOOL,
    ]
    assert events[2].provider_tool_call_id == "provider-call-1"
    assert events[2].lbe_call_id == "lbe-call-1"
    assert events[2].tool_arguments == {"path": "README.md"}


def test_provider_failure_is_a_truthful_error_event() -> None:
    events = _adapter(ProviderError("PROVIDER_TIMEOUT", "timed out")).complete(
        messages=({"role": "user", "content": "hello"},),
    )

    assert len(events) == 1
    assert events[0].event_type is ModelEventType.ERROR
    assert events[0].error_code == "PROVIDER_TIMEOUT"
    assert events[0].metadata["terminal_attribution"] == "http_or_transport_error"
    # The provider's own message must survive normalization: dropping it made every
    # provider rejection (for example an HTTP 402 credit limit) indistinguishable.
    assert events[0].text == "timed out"


def test_tool_call_request_carries_a_bounded_output_limit() -> None:
    """Regression: the coding tool call omitted max_tokens, so the provider substituted
    the model's full output ceiling (OpenRouter asked for 131072 and returned HTTP 402)."""
    transport = _Transport(_response_with_tool_call())
    adapter = OpenAICompatibleEventAdapter(
        config=ProviderConfig(endpoint="http://provider/v1/chat/completions", model="model-a", timeout_seconds=5),
        transport=transport,
    )

    events = adapter.complete(
        messages=({"role": "user", "content": "rename a symbol"},),
        tools=({"type": "function", "function": {"name": "x"}},),
    )

    sent = transport.payloads[0]
    assert sent["max_tokens"] == LBE_DEFAULT_MAX_OUTPUT_TOKENS
    assert sent["max_tokens"] <= LBE_MAX_OUTPUT_TOKENS_CEILING
    assert events[0].metadata["max_output_tokens"] == sent["max_tokens"]


def test_configured_cap_and_request_need_bound_the_tool_call_request() -> None:
    transport = _Transport(_response_with_tool_call())
    config = ProviderConfig(
        endpoint="http://provider/v1/chat/completions",
        model="model-a",
        timeout_seconds=5,
        max_output_tokens=2048,
    )

    OpenAICompatibleEventAdapter(config=config, transport=transport).complete(
        messages=({"role": "user", "content": "rename a symbol"},),
        max_output_tokens=512,
    )

    assert transport.payloads[0]["max_tokens"] == 512


def test_unsupported_configured_cap_fails_before_any_provider_call() -> None:
    transport = _Transport(_response_with_tool_call())
    config = ProviderConfig(
        endpoint="http://provider/v1/chat/completions",
        model="model-a",
        timeout_seconds=5,
        max_output_tokens=LBE_MAX_OUTPUT_TOKENS_CEILING + 1,
    )

    with pytest.raises(ValueError, match="ceiling"):
        OpenAICompatibleEventAdapter(config=config, transport=transport).complete(
            messages=({"role": "user", "content": "rename a symbol"},),
        )

    assert transport.payloads == []


def test_unmapped_provider_tool_call_fails_without_fabricating_requires_tool_state() -> None:
    events = _adapter({
        "id": "chatcmpl-3",
        "choices": [{
            "message": {"tool_calls": [{
                "id": "provider-call-1",
                "function": {"name": "workspace.read", "arguments": '{"path":"README.md"}'},
            }]},
            "finish_reason": "tool_calls",
        }],
    }).complete(messages=({"role": "user", "content": "read"},))

    assert [event.event_type for event in events] == [
        ModelEventType.TURN_STARTED,
        ModelEventType.ERROR,
    ]
    assert events[-1].error_code == "LBE_CALL_ID_REQUIRED"


def test_complete_sends_only_explicitly_declared_lbe_tool_schema() -> None:
    transport = _Transport({
        "id": "chatcmpl-tools",
        "choices": [{"message": {"content": "done"}, "finish_reason": "stop"}],
    })
    adapter = OpenAICompatibleEventAdapter(
        config=ProviderConfig(endpoint="http://provider/v1/chat/completions", model="local-model", timeout_seconds=5),
        transport=transport,
    )

    adapter.complete(
        messages=({"role": "user", "content": "hello"},),
        tools=({"type": "function", "function": {"name": "lbe_0_workspace_read", "parameters": {"type": "object"}}},),
    )

    assert transport.requests[0]["payload"]["tools"] == [
        {"type": "function", "function": {"name": "lbe_0_workspace_read", "parameters": {"type": "object"}}}
    ]
