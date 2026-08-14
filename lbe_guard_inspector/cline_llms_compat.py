"""Compatibility mapper for the evaluated Cline ``@cline/llms`` stream contract.

Evidence pin used for this adapter contract:

- package: ``@cline/llms@0.0.73``
- Cline source commit: ``e6b1c3fbc8c1d76ce2e3f6c61d46e1d63468a6b8``
- public stream type: ``sdk/packages/llms/src/providers/stream.ts``

This is deliberately a *shape mapper*, not a Node process launcher and not a
tool executor. A later transport bridge may serialize Cline ``ApiStreamChunk``
objects to this boundary. LBE remains responsible for provider selection truth,
tool authorization/execution, durable session state, evidence, and completion.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from .professional_provider_events import ModelEventType, NormalizedModelEvent
from .provider_capabilities import ProviderProtocolFamily


CLINE_LLMS_PACKAGE = "@cline/llms"
CLINE_LLMS_VERSION = "0.0.73"
CLINE_SOURCE_COMMIT = "e6b1c3fbc8c1d76ce2e3f6c61d46e1d63468a6b8"


class ClineCompatibilityError(ValueError):
    """Raised when a Cline chunk cannot be represented truthfully by LBE P0."""



def normalize_cline_stream_chunk(
    chunk: Mapping[str, Any],
    *,
    provider_id: str,
    model_id: str,
    protocol_family: ProviderProtocolFamily,
    lbe_call_id: str | None = None,
    reasoning_is_summary: bool = False,
) -> tuple[NormalizedModelEvent, ...]:
    """Map one pinned Cline ``ApiStreamChunk`` to zero or more LBE P0 events.

    The function refuses to invent semantics that the public Cline chunk does
    not expose. In particular, Cline's public ``tool_calls`` chunk has no field
    declaring argument-fragment/delta semantics, so it maps to one completed
    tool-call event only when complete arguments can be decoded. No synthetic
    ``tool_call.started`` or ``tool_call.arguments.delta`` events are emitted.

    Cline labels its reasoning chunk simply as reasoning. LBE's public contract
    is specifically a reasoning *summary*. Therefore callers must explicitly
    prove that the selected provider/backend projection supplies summary-safe
    content before such a chunk can be exposed as ``reasoning_summary.delta``.
    """

    if not isinstance(chunk, Mapping):
        raise TypeError("Cline stream chunk must be a mapping")
    chunk_type = _required_text(chunk.get("type"), "Cline chunk type")
    common = {
        "provider_id": provider_id,
        "model_id": model_id,
        "protocol_family": protocol_family,
        "provider_request_id": _optional_text(chunk.get("id"), "Cline response id"),
        "metadata": {
            "backend": CLINE_LLMS_PACKAGE,
            "backend_version": CLINE_LLMS_VERSION,
            "backend_source_commit": CLINE_SOURCE_COMMIT,
        },
    }

    if chunk_type == "text":
        return (
            NormalizedModelEvent(
                event_type=ModelEventType.MESSAGE_DELTA,
                text=_required_text(chunk.get("text"), "Cline text chunk"),
                **common,
            ),
        )

    if chunk_type == "reasoning":
        if not reasoning_is_summary:
            raise ClineCompatibilityError(
                "Cline reasoning chunk cannot be exposed as LBE reasoning summary without explicit semantic proof"
            )
        return (
            NormalizedModelEvent(
                event_type=ModelEventType.REASONING_SUMMARY_DELTA,
                text=_required_text(chunk.get("reasoning"), "Cline reasoning chunk"),
                **common,
            ),
        )

    if chunk_type == "usage":
        usage = {
            "input_tokens": _non_negative_int(chunk.get("inputTokens"), "inputTokens"),
            "output_tokens": _non_negative_int(chunk.get("outputTokens"), "outputTokens"),
        }
        for source_name, target_name in (
            ("cacheWriteTokens", "cache_write_tokens"),
            ("cacheReadTokens", "cache_read_tokens"),
            ("thoughtsTokenCount", "reasoning_tokens"),
        ):
            value = chunk.get(source_name)
            if value is not None:
                usage[target_name] = _non_negative_int(value, source_name)
        return (
            NormalizedModelEvent(
                event_type=ModelEventType.USAGE_UPDATED,
                usage=usage,
                **common,
            ),
        )

    if chunk_type == "tool_calls":
        if lbe_call_id is None:
            raise ClineCompatibilityError("Cline tool call requires host-supplied durable lbe_call_id")
        raw_tool_call = chunk.get("tool_call")
        if not isinstance(raw_tool_call, Mapping):
            raise ClineCompatibilityError("Cline tool_calls chunk requires tool_call mapping")
        raw_function = raw_tool_call.get("function")
        if not isinstance(raw_function, Mapping):
            raise ClineCompatibilityError("Cline tool call requires function mapping")
        provider_tool_call_id = _first_text(raw_tool_call.get("call_id"), raw_function.get("id"))
        if provider_tool_call_id is None:
            raise ClineCompatibilityError("Cline tool call does not expose a provider-native call id")
        tool_name = _required_text(raw_function.get("name"), "Cline tool name")
        tool_arguments = _decode_complete_arguments(raw_function.get("arguments"))
        return (
            NormalizedModelEvent(
                event_type=ModelEventType.TOOL_CALL_COMPLETED,
                provider_tool_call_id=provider_tool_call_id,
                lbe_call_id=lbe_call_id,
                tool_name=tool_name,
                tool_arguments=tool_arguments,
                **common,
            ),
        )

    if chunk_type == "done":
        success = chunk.get("success")
        if not isinstance(success, bool):
            raise ClineCompatibilityError("Cline done chunk requires boolean success")
        if success:
            return (NormalizedModelEvent(event_type=ModelEventType.TURN_COMPLETED, **common),)
        incomplete_reason = chunk.get("incompleteReason")
        if isinstance(incomplete_reason, str) and incomplete_reason.strip():
            return (
                NormalizedModelEvent(
                    event_type=ModelEventType.TURN_INCOMPLETE,
                    text=incomplete_reason.strip(),
                    **common,
                ),
            )
        error = chunk.get("error")
        if isinstance(error, str) and error.strip():
            return (
                NormalizedModelEvent(
                    event_type=ModelEventType.ERROR,
                    error_code="CLINE_STREAM_ERROR",
                    text=error.strip(),
                    **common,
                ),
            )
        raise ClineCompatibilityError("failed Cline done chunk exposes neither incompleteReason nor error")

    raise ClineCompatibilityError(f"unsupported Cline stream chunk type: {chunk_type}")


def _decode_complete_arguments(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ClineCompatibilityError(
                "Cline tool argument string is not complete JSON; LBE will not fabricate argument deltas"
            ) from exc
        if isinstance(decoded, Mapping):
            return dict(decoded)
        raise ClineCompatibilityError("Cline tool arguments must decode to a JSON object")
    raise ClineCompatibilityError("Cline tool call requires complete object arguments")


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClineCompatibilityError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _non_negative_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ClineCompatibilityError(f"Cline {name} must be a non-negative integer")
    return value
