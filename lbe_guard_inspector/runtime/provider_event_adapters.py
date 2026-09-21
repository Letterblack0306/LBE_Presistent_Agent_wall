"""Provider-native coding event adapters behind LBE authority.

These adapters translate provider wire formats into the existing
NormalizedModelEvent contract. They do not own workspace/session identity,
authorization, tool execution, receipts, evidence, validation, or completion.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Mapping

from ..openai_compatible_event_adapter import OpenAICompatibleEventAdapter
from ..professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderProtocolFamily,
)
from ..provider_capability_discovery import detect_protocol_family
from .gemini_event_adapter import GeminiGenerateContentEventAdapter
from ..reasoning_provider import (
    JsonTransport,
    ProviderConfig,
    ProviderError,
    UrllibJsonTransport,
)


class AnthropicMessagesEventAdapter:
    """Normalize Anthropic Messages text/tool-use responses for LBE."""

    def __init__(
        self,
        *,
        config: ProviderConfig,
        transport: JsonTransport | None = None,
    ) -> None:
        if not config.api_key:
            raise ValueError(
                "anthropic provider requires a non-empty api_key in its explicit provider config"
            )
        self._config = config
        self._transport = transport or UrllibJsonTransport()

    def complete(
        self,
        *,
        messages: tuple[Mapping[str, Any], ...],
        provider_id: str = "anthropic",
        lbe_call_id_for_provider_tool_call: Callable[[str], str] | None = None,
        tools: tuple[Mapping[str, Any], ...] = (),
    ) -> tuple[NormalizedModelEvent, ...]:
        if not isinstance(messages, tuple) or not messages:
            raise ValueError("messages must be a non-empty tuple of mappings")
        if not all(isinstance(item, Mapping) for item in messages):
            raise TypeError("messages must contain only mappings")
        if not isinstance(tools, tuple) or not all(
            isinstance(item, Mapping) for item in tools
        ):
            raise TypeError("tools must be a tuple of mappings")

        system, wire_messages = _anthropic_messages(messages)
        payload: dict[str, Any] = {
            "model": self._config.model.strip(),
            "max_tokens": 4096,
            "messages": wire_messages,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [_anthropic_tool(item) for item in tools]

        try:
            response = self._transport.post_json(
                endpoint=self._config.endpoint.strip(),
                payload=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self._config.api_key or "",
                    "anthropic-version": "2023-06-01",
                },
                timeout_seconds=float(self._config.timeout_seconds),
            )
        except ProviderError as exc:
            return (
                self._event(
                    ModelEventType.ERROR,
                    provider_id,
                    error_code=exc.code,
                    metadata={"terminal_attribution": "http_or_transport_error"},
                ),
            )

        request_id = _optional_text(response.get("id"))
        events: list[NormalizedModelEvent] = [
            self._event(
                ModelEventType.TURN_STARTED,
                provider_id,
                provider_request_id=request_id,
            )
        ]
        content = response.get("content")
        if not isinstance(content, list):
            return tuple(
                events
                + [
                    self._event(
                        ModelEventType.ERROR,
                        provider_id,
                        provider_request_id=request_id,
                        error_code="PROVIDER_RESPONSE_ERROR",
                        metadata={"terminal_attribution": "provider_native"},
                    )
                ]
            )

        tool_seen = False
        text_parts: list[str] = []
        for block in content:
            if not isinstance(block, Mapping):
                continue
            block_type = block.get("type")
            if block_type == "text":
                text = block.get("text")
                if isinstance(text, str) and text:
                    text_parts.append(text)
                continue
            if block_type != "tool_use":
                continue
            provider_call_id = _required_text(block.get("id"), "tool_use id")
            tool_name = _required_text(block.get("name"), "tool_use name")
            arguments = block.get("input")
            if not isinstance(arguments, Mapping):
                return tuple(
                    events
                    + [
                        self._event(
                            ModelEventType.ERROR,
                            provider_id,
                            provider_request_id=request_id,
                            error_code="PROVIDER_RESPONSE_ERROR",
                            metadata={"terminal_attribution": "provider_native"},
                        )
                    ]
                )
            if lbe_call_id_for_provider_tool_call is None:
                return tuple(
                    events
                    + [
                        self._event(
                            ModelEventType.ERROR,
                            provider_id,
                            provider_request_id=request_id,
                            error_code="LBE_CALL_ID_REQUIRED",
                            metadata={"terminal_attribution": "runtime_policy"},
                        )
                    ]
                )
            lbe_call_id = _required_text(
                lbe_call_id_for_provider_tool_call(provider_call_id),
                "lbe_call_id",
            )
            tool_seen = True
            events.extend(
                (
                    self._event(
                        ModelEventType.TOOL_CALL_STARTED,
                        provider_id,
                        provider_request_id=request_id,
                        provider_tool_call_id=provider_call_id,
                        lbe_call_id=lbe_call_id,
                    ),
                    self._event(
                        ModelEventType.TOOL_CALL_COMPLETED,
                        provider_id,
                        provider_request_id=request_id,
                        provider_tool_call_id=provider_call_id,
                        lbe_call_id=lbe_call_id,
                        tool_name=tool_name,
                        tool_arguments=dict(arguments),
                    ),
                )
            )

        if text_parts:
            events.append(
                self._event(
                    ModelEventType.MESSAGE_COMPLETED,
                    provider_id,
                    provider_request_id=request_id,
                    text="".join(text_parts),
                )
            )

        usage = response.get("usage")
        if isinstance(usage, Mapping):
            normalized = {
                str(key): value
                for key, value in usage.items()
                if isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
            }
            if normalized:
                events.append(
                    self._event(
                        ModelEventType.USAGE_UPDATED,
                        provider_id,
                        provider_request_id=request_id,
                        usage=normalized,
                    )
                )

        stop_reason = _optional_text(response.get("stop_reason"))
        if tool_seen or stop_reason == "tool_use":
            events.append(
                self._event(
                    ModelEventType.TURN_REQUIRES_TOOL,
                    provider_id,
                    provider_request_id=request_id,
                )
            )
        elif stop_reason == "max_tokens":
            events.append(
                self._event(
                    ModelEventType.TURN_INCOMPLETE,
                    provider_id,
                    provider_request_id=request_id,
                    metadata={"stop_reason": stop_reason},
                )
            )
        elif stop_reason == "refusal":
            events.append(
                self._event(
                    ModelEventType.TURN_REFUSED,
                    provider_id,
                    provider_request_id=request_id,
                    metadata={"stop_reason": stop_reason},
                )
            )
        else:
            events.append(
                self._event(
                    ModelEventType.TURN_COMPLETED,
                    provider_id,
                    provider_request_id=request_id,
                    metadata={"stop_reason": stop_reason} if stop_reason else {},
                )
            )
        return tuple(events)

    def _event(
        self,
        event_type: ModelEventType,
        provider_id: str,
        **values: Any,
    ) -> NormalizedModelEvent:
        return NormalizedModelEvent(
            event_type=event_type,
            provider_id=provider_id,
            model_id=self._config.model.strip(),
            protocol_family=ProviderProtocolFamily.ANTHROPIC_MESSAGES,
            **values,
        )


def build_native_provider_event_adapter(
    *,
    provider_id: str,
    config: ProviderConfig,
    transport: JsonTransport | None = None,
):
    """Build only a provider transport that LBE actually implements.

    No provider/engine fallback occurs here. Unsupported protocol families fail
    explicitly before any network request or governed mutation.
    """
    family, evidence = detect_protocol_family(
        provider_id=provider_id,
        endpoint=config.endpoint,
    )
    if family is ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT:
        return OpenAICompatibleEventAdapter(config=config, transport=transport)
    if family is ProviderProtocolFamily.ANTHROPIC_MESSAGES:
        return AnthropicMessagesEventAdapter(config=config, transport=transport)
    if family is ProviderProtocolFamily.GEMINI_GENERATE_CONTENT:
        return GeminiGenerateContentEventAdapter(config=config, transport=transport)
    raise ValueError(
        "native-lbe governed coding transport is not implemented for "
        f"{provider_id} protocol {family.value}: {evidence}. "
        "Select an explicitly supported reasoning engine; LBE will not silently "
        "route this provider through a different transport."
    )


def _anthropic_tool(tool: Mapping[str, Any]) -> dict[str, Any]:
    function = tool.get("function")
    if tool.get("type") != "function" or not isinstance(function, Mapping):
        raise ValueError("Anthropic tool translation requires function tools")
    name = _required_text(function.get("name"), "tool name")
    parameters = function.get("parameters")
    if not isinstance(parameters, Mapping):
        raise ValueError("tool parameters must be a mapping")
    translated: dict[str, Any] = {
        "name": name,
        "input_schema": dict(parameters),
    }
    description = function.get("description")
    if isinstance(description, str) and description.strip():
        translated["description"] = description.strip()
    return translated


def _anthropic_messages(
    messages: tuple[Mapping[str, Any], ...],
) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    wire: list[dict[str, Any]] = []

    def append(role: str, content: Any) -> None:
        if wire and wire[-1]["role"] == role:
            existing = wire[-1]["content"]
            if isinstance(existing, list) and isinstance(content, list):
                existing.extend(content)
                return
        wire.append({"role": role, "content": content})

    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role == "system":
            if isinstance(content, str) and content.strip():
                system_parts.append(content.strip())
            continue
        if role == "tool":
            tool_call_id = _required_text(
                message.get("tool_call_id"),
                "tool_call_id",
            )
            append(
                "user",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": content if isinstance(content, str) else json.dumps(content),
                    }
                ],
            )
            continue
        if role == "assistant" and isinstance(message.get("tool_calls"), list):
            blocks: list[dict[str, Any]] = []
            if isinstance(content, str) and content:
                blocks.append({"type": "text", "text": content})
            for raw_call in message["tool_calls"]:
                if not isinstance(raw_call, Mapping):
                    raise ValueError("assistant tool call must be a mapping")
                function = raw_call.get("function")
                if not isinstance(function, Mapping):
                    raise ValueError("assistant tool call function must be a mapping")
                raw_arguments = function.get("arguments")
                if not isinstance(raw_arguments, str):
                    raise ValueError("assistant tool call arguments must be JSON text")
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "assistant tool call arguments must be valid JSON"
                    ) from exc
                if not isinstance(arguments, Mapping):
                    raise ValueError(
                        "assistant tool call arguments must decode to an object"
                    )
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": _required_text(raw_call.get("id"), "tool call id"),
                        "name": _required_text(function.get("name"), "tool name"),
                        "input": dict(arguments),
                    }
                )
            append("assistant", blocks)
            continue
        if role in {"user", "assistant"}:
            if not isinstance(content, str):
                raise ValueError(f"{role} message content must be text")
            append(str(role), content)
            continue
        raise ValueError(f"unsupported normalized provider message role: {role}")

    return "\n\n".join(system_parts), wire


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return _required_text(value, "provider text field")
