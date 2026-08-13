from __future__ import annotations

import pytest

from lbe_guard_inspector.cline_sidecar_adapter import (
    ClineSidecarProcessError,
    ClineSidecarProviderAdapter,
)
from lbe_guard_inspector.professional_provider_events import (
    ModelEventType,
    ProviderToolResultContinuation,
    ProviderTurnRequest,
)
from lbe_guard_inspector.provider_capabilities import ProviderProtocolFamily


def _request(*, messages=None) -> ProviderTurnRequest:
    return ProviderTurnRequest(
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
        messages=tuple(messages or ({"role": "user", "content": "inspect README"},)),
        tools=(
            {
                "name": "workspace.read",
                "description": "Read one workspace-relative file",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        ),
    )


def _adapter(runner, *, ids=None) -> ClineSidecarProviderAdapter:
    values = iter(ids or ["lbe-call-1", "lbe-call-2"])
    return ClineSidecarProviderAdapter(
        provider_config={
            "providerId": "openai-compatible",
            "modelId": "model-a",
            "baseUrl": "http://127.0.0.1:1234/v1",
        },
        system_prompt="You are a bounded provider transport test.",
        bridge_runner=runner,
        call_id_factory=lambda: next(values),
    )


def test_text_turn_emits_started_delta_and_completed() -> None:
    def runner(payload):
        assert payload["provider_config"]["providerId"] == "openai-compatible"
        assert payload["tools"][0]["name"] == "workspace.read"
        assert "workspace_root" not in payload
        yield {"kind": "chunk", "chunk": {"type": "text", "text": "hello", "id": "resp-1"}}
        yield {"kind": "chunk", "chunk": {"type": "done", "success": True, "id": "resp-1"}}
        yield {"kind": "end"}

    events = tuple(_adapter(runner).stream_turn(_request()))
    assert [event.event_type for event in events] == [
        ModelEventType.TURN_STARTED,
        ModelEventType.MESSAGE_DELTA,
        ModelEventType.TURN_COMPLETED,
    ]


def test_successful_done_after_tool_call_becomes_requires_tool_not_completion() -> None:
    def runner(payload):
        yield {
            "kind": "chunk",
            "chunk": {
                "type": "tool_calls",
                "id": "resp-2",
                "tool_call": {
                    "call_id": "provider-call-7",
                    "function": {
                        "name": "workspace.read",
                        "arguments": {"path": "README.md"},
                    },
                },
            },
        }
        yield {"kind": "chunk", "chunk": {"type": "done", "success": True, "id": "resp-2"}}
        yield {"kind": "end"}

    adapter = _adapter(runner, ids=["lbe-call-7"])
    events = tuple(adapter.stream_turn(_request()))

    assert [event.event_type for event in events] == [
        ModelEventType.TURN_STARTED,
        ModelEventType.TOOL_CALL_COMPLETED,
        ModelEventType.TURN_REQUIRES_TOOL,
    ]
    assert ModelEventType.TURN_COMPLETED not in {event.event_type for event in events}
    assert adapter.pending_tool_call is not None
    assert adapter.pending_tool_call.provider_tool_call_id == "provider-call-7"
    assert adapter.pending_tool_call.lbe_call_id == "lbe-call-7"


def test_continuation_serializes_exact_pending_tool_call_and_lbe_result() -> None:
    payloads = []

    def runner(payload):
        payloads.append(payload)
        if len(payloads) == 1:
            yield {
                "kind": "chunk",
                "chunk": {
                    "type": "tool_calls",
                    "id": "resp-tool",
                    "tool_call": {
                        "call_id": "provider-call-9",
                        "function": {
                            "name": "workspace.read",
                            "arguments": "{\"path\":\"README.md\"}",
                        },
                    },
                },
            }
            yield {"kind": "chunk", "chunk": {"type": "done", "success": True, "id": "resp-tool"}}
            yield {"kind": "end"}
        else:
            yield {"kind": "chunk", "chunk": {"type": "text", "text": "README inspected", "id": "resp-final"}}
            yield {"kind": "chunk", "chunk": {"type": "done", "success": True, "id": "resp-final"}}
            yield {"kind": "end"}

    adapter = _adapter(runner, ids=["lbe-call-9"])
    tuple(adapter.stream_turn(_request()))

    result = ProviderToolResultContinuation(
        provider_tool_call_id="provider-call-9",
        lbe_call_id="lbe-call-9",
        runtime_operation_id="operation-12",
        tool_receipt_id="receipt-13",
        tool_name="workspace.read",
        output={"text": "contents"},
    )
    events = tuple(adapter.continue_with_tool_result(_request(), result))

    continuation_messages = payloads[1]["messages"]
    assistant_tool = continuation_messages[-2]["content"][0]
    user_result = continuation_messages[-1]["content"][0]
    assert assistant_tool == {
        "type": "tool_use",
        "id": "provider-call-9",
        "call_id": "provider-call-9",
        "name": "workspace.read",
        "input": {"path": "README.md"},
    }
    assert user_result["tool_use_id"] == "provider-call-9"
    assert user_result["name"] == "workspace.read"
    assert user_result["content"] == '{"text": "contents"}'
    assert user_result["is_error"] is False
    assert adapter.pending_tool_call is None
    assert events[-1].event_type is ModelEventType.TURN_COMPLETED


def test_continuation_rejects_mismatched_receipt_correlation() -> None:
    def runner(payload):
        yield {
            "kind": "chunk",
            "chunk": {
                "type": "tool_calls",
                "id": "resp-tool",
                "tool_call": {
                    "call_id": "provider-call-1",
                    "function": {"name": "workspace.read", "arguments": {"path": "README.md"}},
                },
            },
        }
        yield {"kind": "chunk", "chunk": {"type": "done", "success": True, "id": "resp-tool"}}
        yield {"kind": "end"}

    adapter = _adapter(runner, ids=["lbe-call-1"])
    tuple(adapter.stream_turn(_request()))

    with pytest.raises(ClineSidecarProcessError, match="lbe_call_id"):
        adapter.continue_with_tool_result(
            _request(),
            ProviderToolResultContinuation(
                provider_tool_call_id="provider-call-1",
                lbe_call_id="wrong-call",
                runtime_operation_id="operation-1",
                tool_receipt_id="receipt-1",
                tool_name="workspace.read",
                output="x",
            ),
        )


def test_new_turn_is_blocked_while_tool_result_is_pending() -> None:
    def runner(payload):
        yield {
            "kind": "chunk",
            "chunk": {
                "type": "tool_calls",
                "id": "resp-tool",
                "tool_call": {
                    "call_id": "provider-call-1",
                    "function": {"name": "workspace.read", "arguments": {"path": "README.md"}},
                },
            },
        }
        yield {"kind": "chunk", "chunk": {"type": "done", "success": True, "id": "resp-tool"}}
        yield {"kind": "end"}

    adapter = _adapter(runner, ids=["lbe-call-1"])
    tuple(adapter.stream_turn(_request()))

    with pytest.raises(ClineSidecarProcessError, match="continuation is pending"):
        tuple(adapter.stream_turn(_request()))


def test_bridge_error_becomes_normalized_error_event() -> None:
    def runner(payload):
        yield {"kind": "error", "code": "PROVIDER_AUTH", "message": "bad key"}
        yield {"kind": "end"}

    events = tuple(_adapter(runner).stream_turn(_request()))
    assert events[-1].event_type is ModelEventType.ERROR
    assert events[-1].error_code == "PROVIDER_AUTH"
    assert events[-1].text == "bad key"


def test_bridge_without_terminal_event_fails_closed() -> None:
    def runner(payload):
        yield {"kind": "chunk", "chunk": {"type": "text", "text": "partial", "id": "resp-1"}}
        yield {"kind": "end"}

    with pytest.raises(ClineSidecarProcessError, match="without a terminal"):
        tuple(_adapter(runner).stream_turn(_request()))


def test_provider_config_and_request_identity_must_match() -> None:
    adapter = _adapter(lambda payload: ())
    wrong = ProviderTurnRequest(
        provider_id="anthropic",
        model_id="model-a",
        protocol_family=ProviderProtocolFamily.ANTHROPIC_MESSAGES,
        messages=({"role": "user", "content": "hello"},),
    )
    with pytest.raises(ClineSidecarProcessError, match="provider_id"):
        tuple(adapter.stream_turn(wrong))
