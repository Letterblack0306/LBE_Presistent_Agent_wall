from __future__ import annotations

import json

from lbe_guard_inspector.professional_provider_events import ModelEventType
from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.runtime.provider_event_adapters import (
    AnthropicMessagesEventAdapter,
)


class _FakeTransport:
    supports_cancellation = False

    def __init__(self, responses):
        self.responses = list(responses)
        self.payloads = []

    def post_json(self, *, endpoint, payload, headers, timeout_seconds):
        self.payloads.append(
            {
                "endpoint": endpoint,
                "payload": payload,
                "headers": dict(headers),
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.responses.pop(0)

    def cancel(self):
        raise AssertionError("cancel must not be called")

    def stream_json(self, **_kwargs):
        raise AssertionError("streaming is not used by this adapter")


def _config():
    return ProviderConfig(
        endpoint="https://api.anthropic.com/v1/messages",
        model="claude-test",
        timeout_seconds=5,
        api_key="secret",
    )


def test_anthropic_messages_adapter_normalizes_tool_use_and_continuation():
    transport = _FakeTransport(
        [
            {
                "id": "msg-1",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu-1",
                        "name": "lbe_0_workspace_read",
                        "input": {"path": "README.md"},
                    }
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
            {
                "id": "msg-2",
                "content": [{"type": "text", "text": "done"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 20, "output_tokens": 3},
            },
        ]
    )
    adapter = AnthropicMessagesEventAdapter(config=_config(), transport=transport)
    tools = (
        {
            "type": "function",
            "function": {
                "name": "lbe_0_workspace_read",
                "description": "read",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
    )

    events = adapter.complete(
        messages=(
            {"role": "system", "content": "system"},
            {"role": "user", "content": "read README"},
        ),
        provider_id="anthropic",
        tools=tools,
        lbe_call_id_for_provider_tool_call=lambda call_id: f"lbe-{call_id}",
    )

    call = next(
        event
        for event in events
        if event.event_type is ModelEventType.TOOL_CALL_COMPLETED
    )
    assert call.provider_tool_call_id == "toolu-1"
    assert call.lbe_call_id == "lbe-toolu-1"
    assert call.tool_name == "lbe_0_workspace_read"
    assert call.tool_arguments == {"path": "README.md"}
    assert events[-1].event_type is ModelEventType.TURN_REQUIRES_TOOL

    continuation = adapter.complete(
        messages=(
            {"role": "system", "content": "system"},
            {"role": "user", "content": "read README"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "toolu-1",
                        "type": "function",
                        "function": {
                            "name": "lbe_0_workspace_read",
                            "arguments": json.dumps({"path": "README.md"}),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "toolu-1",
                "content": json.dumps({"status": "EXECUTED"}),
            },
        ),
        provider_id="anthropic",
        tools=tools,
        lbe_call_id_for_provider_tool_call=lambda call_id: f"lbe-{call_id}",
    )

    assert any(
        event.event_type is ModelEventType.MESSAGE_COMPLETED
        and event.text == "done"
        for event in continuation
    )
    assert continuation[-1].event_type is ModelEventType.TURN_COMPLETED

    second_payload = transport.payloads[1]["payload"]
    assistant = next(
        message for message in second_payload["messages"]
        if message["role"] == "assistant"
    )
    tool_use = next(
        block for block in assistant["content"]
        if block["type"] == "tool_use"
    )
    assert tool_use["id"] == "toolu-1"
    tool_result_message = second_payload["messages"][-1]
    assert tool_result_message["role"] == "user"
    assert tool_result_message["content"][0]["type"] == "tool_result"
    assert tool_result_message["content"][0]["tool_use_id"] == "toolu-1"
