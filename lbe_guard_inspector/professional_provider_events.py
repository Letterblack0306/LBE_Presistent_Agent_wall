"""Normalized P3 provider event and continuation contracts.

This module is the provider/backend boundary for the professional runtime. It
contains no workspace authority, tool dispatcher, session persistence, or
provider-specific transport implementation. Backends such as a future pinned
Cline @cline/llms bridge or a native provider adapter must translate their wire
semantics into these LBE-owned events without fabricating unsupported deltas.

The existing bounded 0.2.1 reasoning providers intentionally do not depend on
this module. Their accepted request/response semantics remain unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping, Protocol

from .provider_capabilities import ProviderProtocolFamily


class ModelEventType(StrEnum):
    """Frozen P0 model/provider event vocabulary used by the professional path."""

    TURN_STARTED = "model.turn.started"
    MESSAGE_DELTA = "model.message.delta"
    MESSAGE_COMPLETED = "model.message.completed"
    REASONING_SUMMARY_DELTA = "model.reasoning_summary.delta"
    REASONING_SUMMARY_COMPLETED = "model.reasoning_summary.completed"
    TOOL_CALL_STARTED = "model.tool_call.started"
    TOOL_CALL_ARGUMENTS_DELTA = "model.tool_call.arguments.delta"
    TOOL_CALL_COMPLETED = "model.tool_call.completed"
    USAGE_UPDATED = "model.usage.updated"
    TURN_REQUIRES_TOOL = "model.turn.requires_tool"
    TURN_REQUIRES_CONTINUATION = "model.turn.requires_continuation"
    TURN_COMPLETED = "model.turn.completed"
    TURN_INCOMPLETE = "model.turn.incomplete"
    TURN_REFUSED = "model.turn.refused"
    CANCELLED = "model.cancelled"
    ERROR = "model.error"


_DELTA_EVENTS = frozenset(
    {
        ModelEventType.MESSAGE_DELTA,
        ModelEventType.REASONING_SUMMARY_DELTA,
        ModelEventType.TOOL_CALL_ARGUMENTS_DELTA,
    }
)
_TOOL_CALL_EVENTS = frozenset(
    {
        ModelEventType.TOOL_CALL_STARTED,
        ModelEventType.TOOL_CALL_ARGUMENTS_DELTA,
        ModelEventType.TOOL_CALL_COMPLETED,
    }
)


@dataclass(frozen=True)
class NormalizedModelEvent:
    """One truthful normalized provider/model event.

    Provider-native identifiers stay distinct from LBE call identity. Runtime
    operation/tool-receipt identity is intentionally absent: it is created only
    after LBE authorization and governed tool execution.
    """

    event_type: ModelEventType
    provider_id: str
    model_id: str
    protocol_family: ProviderProtocolFamily
    provider_request_id: str | None = None
    provider_item_id: str | None = None
    provider_tool_call_id: str | None = None
    lbe_call_id: str | None = None
    text: str | None = None
    tool_name: str | None = None
    tool_arguments: Mapping[str, Any] | None = None
    usage: Mapping[str, int] | None = None
    error_code: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, ModelEventType):
            raise TypeError("event_type must be ModelEventType")
        if not isinstance(self.protocol_family, ProviderProtocolFamily):
            raise TypeError("protocol_family must be ProviderProtocolFamily")
        _require_text(self.provider_id, "provider_id")
        _require_text(self.model_id, "model_id")
        for name in (
            "provider_request_id",
            "provider_item_id",
            "provider_tool_call_id",
            "lbe_call_id",
            "tool_name",
            "error_code",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_text(value, name)

        if self.event_type in _DELTA_EVENTS:
            _require_text(self.text, "text")
        elif self.text is not None and not isinstance(self.text, str):
            raise TypeError("text must be a string when supplied")

        if self.event_type in _TOOL_CALL_EVENTS:
            _require_text(self.provider_tool_call_id, "provider_tool_call_id")
            _require_text(self.lbe_call_id, "lbe_call_id")

        if self.event_type is ModelEventType.TOOL_CALL_COMPLETED:
            _require_text(self.tool_name, "tool_name")
            if self.tool_arguments is None or not isinstance(self.tool_arguments, Mapping):
                raise ValueError("model.tool_call.completed requires tool_arguments mapping")

        if self.event_type is ModelEventType.USAGE_UPDATED:
            if self.usage is None or not isinstance(self.usage, Mapping):
                raise ValueError("model.usage.updated requires usage mapping")
            for key, value in self.usage.items():
                _require_text(key, "usage key")
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ValueError("usage values must be non-negative integers")

        if self.event_type is ModelEventType.ERROR:
            _require_text(self.error_code, "error_code")

        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")


@dataclass(frozen=True)
class ProviderToolDefinition:
    """Provider-visible schema for one already-authorized runtime capability.

    This is descriptive projection only. Possessing a schema does not grant the
    model or transport backend permission to execute the named capability.
    """

    name: str
    description: str
    input_schema: Mapping[str, Any]

    def __post_init__(self) -> None:
        _require_text(self.name, "tool definition name")
        _require_text(self.description, "tool definition description")
        if not isinstance(self.input_schema, Mapping):
            raise TypeError("tool definition input_schema must be a mapping")


@dataclass(frozen=True)
class ProviderTurnRequest:
    """Provider-facing professional turn input without workspace authority."""

    provider_id: str
    model_id: str
    protocol_family: ProviderProtocolFamily
    system_prompt: str
    messages: tuple[Mapping[str, Any], ...]
    tool_definitions: tuple[ProviderToolDefinition, ...] = ()
    provider_options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.provider_id, "provider_id")
        _require_text(self.model_id, "model_id")
        _require_text(self.system_prompt, "system_prompt")
        if not isinstance(self.protocol_family, ProviderProtocolFamily):
            raise TypeError("protocol_family must be ProviderProtocolFamily")
        if not isinstance(self.messages, tuple) or not self.messages:
            raise ValueError("messages must be a non-empty tuple")
        if not all(isinstance(item, Mapping) for item in self.messages):
            raise TypeError("messages must contain mappings")
        if not isinstance(self.tool_definitions, tuple) or not all(
            isinstance(item, ProviderToolDefinition) for item in self.tool_definitions
        ):
            raise TypeError("tool_definitions must be a tuple of ProviderToolDefinition")
        if not isinstance(self.provider_options, Mapping):
            raise TypeError("provider_options must be a mapping")


@dataclass(frozen=True)
class ProviderToolResultContinuation:
    """Evidence-bearing tool result returned to a provider after LBE execution.

    This object cannot authorize or execute a tool. ``runtime_operation_id`` and
    ``tool_receipt_id`` must already exist because the governed runtime produced
    them. ``provider_tool_call_id`` and ``lbe_call_id`` preserve provider/LBE
    correlation without conflating those identities.
    """

    provider_tool_call_id: str
    lbe_call_id: str
    runtime_operation_id: str
    tool_receipt_id: str
    tool_name: str
    output: Any
    is_error: bool = False

    def __post_init__(self) -> None:
        for name in (
            "provider_tool_call_id",
            "lbe_call_id",
            "runtime_operation_id",
            "tool_receipt_id",
            "tool_name",
        ):
            _require_text(getattr(self, name), name)
        if not isinstance(self.is_error, bool):
            raise TypeError("is_error must be bool")


class ProfessionalProviderAdapter(Protocol):
    """Replaceable P3 transport/normalization boundary.

    Implementations may use Cline lower layers or native provider SDKs. They may
    perform provider I/O only. They do not receive workspace roots, permission
    profiles, R6C authority, or a tool dispatcher.
    """

    def stream_turn(self, request: ProviderTurnRequest) -> Iterable[NormalizedModelEvent]: ...

    def continue_with_tool_result(
        self,
        request: ProviderTurnRequest,
        result: ProviderToolResultContinuation,
    ) -> Iterable[NormalizedModelEvent]: ...

    def cancel(self) -> None: ...


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()
