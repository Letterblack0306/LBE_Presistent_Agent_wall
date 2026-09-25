from __future__ import annotations

import json

from lbe_guard_inspector.professional_provider_events import ModelEventType
from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.runtime.openai_responses_event_adapter import (
    OpenAIResponsesEventAdapter,
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
        endpoint="https://api.openai.com/v1/responses",
        model="gpt-test",
        timeout_seconds=5,
        api_key="secret",
    )


def test_openai_responses_adapter_preserves_call_id_and_previous_response_id():
    transport = _FakeTransport(
        [
            {
                "id": "resp-1",
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "id": "fc-item-1",
                        "call_id": "call-1",
                        "name": "lbe_0_workspace_read",
                        "arguments": json.dumps({"path": "README.md"}),
                    }
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 4,
                    "total_tokens": 14,
                },
            },
            {
                "id": "resp-2",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "id": "msg-2",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "done",
                            }
                        ],
                    }
                ],
            },
        ]
    )
    adapter = OpenAIResponsesEventAdapter(
        config=_config(),
        transport=transport,
    )
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
        provider_id="openai",
        tools=tools,
        lbe_call_id_for_provider_tool_call=lambda call_id: f"lbe-{call_id}",
    )

    call = next(
        event
        for event in events
        if event.event_type is ModelEventType.TOOL_CALL_COMPLETED
    )
    assert call.provider_request_id == "resp-1"
    assert call.provider_item_id == "fc-item-1"
    assert call.provider_tool_call_id == "call-1"
    assert call.lbe_call_id == "lbe-call-1"
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
                        "id": "call-1",
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
                "tool_call_id": "call-1",
                "content": json.dumps({"status": "EXECUTED"}),
            },
        ),
        provider_id="openai",
        tools=tools,
        lbe_call_id_for_provider_tool_call=lambda call_id: f"lbe-{call_id}",
    )

    assert any(
        event.event_type is ModelEventType.MESSAGE_COMPLETED
        and event.text == "done"
        for event in continuation
    )
    assert continuation[-1].event_type is ModelEventType.TURN_COMPLETED

    first_payload = transport.payloads[0]["payload"]
    assert "previous_response_id" not in first_payload
    assert first_payload["input"] == [{"role": "user", "content": "read README"}]

    second_payload = transport.payloads[1]["payload"]
    assert second_payload["previous_response_id"] == "resp-1"
    assert second_payload["input"] == [
        {
            "type": "function_call_output",
            "call_id": "call-1",
            "output": json.dumps({"status": "EXECUTED"}),
        }
    ]
