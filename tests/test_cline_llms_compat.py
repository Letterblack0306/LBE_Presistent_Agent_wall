from __future__ import annotations

import pytest

from lbe_guard_inspector.cline_llms_compat import (
    CLINE_LLMS_PACKAGE,
    CLINE_LLMS_VERSION,
    CLINE_SOURCE_COMMIT,
    ClineCompatibilityError,
    normalize_cline_stream_chunk,
)
from lbe_guard_inspector.professional_provider_events import ModelEventType
from lbe_guard_inspector.provider_capabilities import ProviderProtocolFamily


_COMMON = {
    "provider_id": "openai-compatible",
    "model_id": "model-a",
    "protocol_family": ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
}


def test_cline_compatibility_evidence_is_pinned() -> None:
    assert CLINE_LLMS_PACKAGE == "@cline/llms"
    assert CLINE_LLMS_VERSION == "0.0.73"
    assert CLINE_SOURCE_COMMIT == "e6b1c3fbc8c1d76ce2e3f6c61d46e1d63468a6b8"


def test_text_chunk_maps_to_real_message_delta_with_backend_provenance() -> None:
    events = normalize_cline_stream_chunk(
        {"type": "text", "text": "hello", "id": "response-1"},
        **_COMMON,
    )

    assert len(events) == 1
    event = events[0]
    assert event.event_type is ModelEventType.MESSAGE_DELTA
    assert event.text == "hello"
    assert event.provider_request_id == "response-1"
    assert event.metadata["backend"] == "@cline/llms"
    assert event.metadata["backend_version"] == "0.0.73"


def test_reasoning_chunk_fails_closed_without_summary_semantic_proof() -> None:
    with pytest.raises(ClineCompatibilityError, match="reasoning summary"):
        normalize_cline_stream_chunk(
            {"type": "reasoning", "reasoning": "private reasoning", "id": "response-1"},
            **_COMMON,
        )

    events = normalize_cline_stream_chunk(
        {"type": "reasoning", "reasoning": "provider summary", "id": "response-1"},
        reasoning_is_summary=True,
        **_COMMON,
    )
    assert events[0].event_type is ModelEventType.REASONING_SUMMARY_DELTA
    assert events[0].text == "provider summary"


def test_usage_chunk_preserves_only_reported_token_counts() -> None:
    event = normalize_cline_stream_chunk(
        {
            "type": "usage",
            "inputTokens": 20,
            "outputTokens": 5,
            "cacheReadTokens": 3,
            "id": "response-2",
        },
        **_COMMON,
    )[0]

    assert event.event_type is ModelEventType.USAGE_UPDATED
    assert event.usage == {
        "input_tokens": 20,
        "output_tokens": 5,
        "cache_read_tokens": 3,
    }
    assert "cache_write_tokens" not in event.usage


def test_complete_cline_tool_call_maps_to_one_completed_lbe_tool_proposal() -> None:
    events = normalize_cline_stream_chunk(
        {
            "type": "tool_calls",
            "id": "response-3",
            "tool_call": {
                "call_id": "provider-call-9",
                "function": {
                    "name": "workspace.read",
                    "arguments": '{"path":"README.md"}',
                },
            },
        },
        lbe_call_id="lbe-call-9",
        **_COMMON,
    )

    assert [event.event_type for event in events] == [ModelEventType.TOOL_CALL_COMPLETED]
    event = events[0]
    assert event.provider_tool_call_id == "provider-call-9"
    assert event.lbe_call_id == "lbe-call-9"
    assert event.tool_name == "workspace.read"
    assert event.tool_arguments == {"path": "README.md"}


def test_cline_tool_call_never_fabricates_partial_argument_events() -> None:
    with pytest.raises(ClineCompatibilityError, match="will not fabricate argument deltas"):
        normalize_cline_stream_chunk(
            {
                "type": "tool_calls",
                "id": "response-4",
                "tool_call": {
                    "call_id": "provider-call-10",
                    "function": {
                        "name": "workspace.read",
                        "arguments": '{"path":',
                    },
                },
            },
            lbe_call_id="lbe-call-10",
            **_COMMON,
        )


def test_cline_tool_call_requires_host_supplied_durable_lbe_identity() -> None:
    with pytest.raises(ClineCompatibilityError, match="host-supplied durable lbe_call_id"):
        normalize_cline_stream_chunk(
            {
                "type": "tool_calls",
                "id": "response-5",
                "tool_call": {
                    "call_id": "provider-call-11",
                    "function": {"name": "workspace.read", "arguments": {"path": "README.md"}},
                },
            },
            **_COMMON,
        )


def test_done_chunk_distinguishes_completed_incomplete_and_error() -> None:
    completed = normalize_cline_stream_chunk(
        {"type": "done", "success": True, "id": "response-6"},
        **_COMMON,
    )[0]
    incomplete = normalize_cline_stream_chunk(
        {
            "type": "done",
            "success": False,
            "incompleteReason": "max_output_tokens",
            "id": "response-7",
        },
        **_COMMON,
    )[0]
    failed = normalize_cline_stream_chunk(
        {"type": "done", "success": False, "error": "transport failed", "id": "response-8"},
        **_COMMON,
    )[0]

    assert completed.event_type is ModelEventType.TURN_COMPLETED
    assert incomplete.event_type is ModelEventType.TURN_INCOMPLETE
    assert incomplete.text == "max_output_tokens"
    assert failed.event_type is ModelEventType.ERROR
    assert failed.error_code == "CLINE_STREAM_ERROR"


def test_unknown_cline_chunk_type_fails_closed() -> None:
    with pytest.raises(ClineCompatibilityError, match="unsupported Cline stream chunk type"):
        normalize_cline_stream_chunk(
            {"type": "mystery", "id": "response-9"},
            **_COMMON,
        )
