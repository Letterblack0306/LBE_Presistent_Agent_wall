"""Gemini generateContent coding-turn event adapter behind LBE authority.

This module only translates Gemini wire objects into the existing
NormalizedModelEvent contract. Workspace/session identity, authorization,
execution, receipts, evidence, validation, and completion remain LBE-owned.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Mapping

from ..professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderProtocolFamily,
)
from ..reasoning_provider import (
    JsonTransport,
    ProviderConfig,
    ProviderError,
    UrllibJsonTransport,
)


class GeminiGenerateContentEventAdapter:
    """Normalize Gemini generateContent text/function-call responses for LBE."""

    def __init__(
        self,
        *,
        config: ProviderConfig,
        transport: JsonTransport | None = None,
    ) -> None:
        if not config.api_key:
            raise ValueError(
                "gemini provider requires a non-empty api_key in its explicit provider config"
            )
        self._config = config
        self._transport = transport or UrllibJsonTransport()

    def complete(
        self,
        *,
        messages: tuple[Mapping[str, Any], ...],
        provider_id: str = "gemini",
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

        system, contents = _gemini_contents(messages)
        payload: dict[str, Any] = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        _gemini_function_declaration(item) for item in tools
                    ]
                }
            ]

        try:
            response = self._transport.post_json(
                endpoint=self._config.endpoint.strip(),
                payload=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self._config.api_key or "",
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

        request_id = _optional_text(response.get("responseId"))
        events: list[NormalizedModelEvent] = [
            self._event(
                ModelEventType.TURN_STARTED,
                provider_id,
                provider_request_id=request_id,
            )
        ]
        candidates = response.get("candidates")
        if (
            not isinstance(candidates, list)
            or len(candidates) != 1
            or not isinstance(candidates[0], Mapping)
        ):
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

        candidate = candidates[0]
        content = candidate.get("content")
        parts = content.get("parts") if isinstance(content, Mapping) else None
        if not isinstance(parts, list):
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
        for part in parts:
            if not isinstance(part, Mapping):
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                text_parts.append(text)

            function_call = part.get("functionCall")
            if not isinstance(function_call, Mapping):
                continue
            provider_call_id = _required_text(
                function_call.get("id"),
                "Gemini functionCall id",
            )
            tool_name = _required_text(
                function_call.get("name"),
                "Gemini functionCall name",
            )
            arguments = function_call.get("args")
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

        usage = response.get("usageMetadata")
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

        finish_reason = _optional_text(candidate.get("finishReason"))
        if tool_seen:
            events.append(
                self._event(
                    ModelEventType.TURN_REQUIRES_TOOL,
                    provider_id,
                    provider_request_id=request_id,
                )
            )
        elif finish_reason in {"MAX_TOKENS", "RECITATION"}:
            events.append(
                self._event(
                    ModelEventType.TURN_INCOMPLETE,
                    provider_id,
                    provider_request_id=request_id,
                    metadata={"finish_reason": finish_reason},
                )
            )
        elif finish_reason in {
            "SAFETY",
            "BLOCKLIST",
            "PROHIBITED_CONTENT",
            "SPII",
        }:
            events.append(
                self._event(
                    ModelEventType.TURN_REFUSED,
                    provider_id,
                    provider_request_id=request_id,
                    metadata={"finish_reason": finish_reason},
                )
            )
        else:
            events.append(
                self._event(
                    ModelEventType.TURN_COMPLETED,
                    provider_id,
                    provider_request_id=request_id,
                    metadata={"finish_reason": finish_reason} if finish_reason else {},
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
            protocol_family=ProviderProtocolFamily.GEMINI_GENERATE_CONTENT,
            **values,
        )


def _gemini_function_declaration(tool: Mapping[str, Any]) -> dict[str, Any]:
    function = tool.get("function")
    if tool.get("type") != "function" or not isinstance(function, Mapping):
        raise ValueError("Gemini tool translation requires function tools")
    name = _required_text(function.get("name"), "tool name")
    parameters = function.get("parameters")
    if not isinstance(parameters, Mapping):
        raise ValueError("tool parameters must be a mapping")
    translated: dict[str, Any] = {
        "name": name,
        "parameters": dict(parameters),
    }
    description = function.get("description")
    if isinstance(description, str) and description.strip():
        translated["description"] = description.strip()
    return translated


def _gemini_contents(
    messages: tuple[Mapping[str, Any], ...],
) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    tool_names: dict[str, str] = {}

    def append(role: str, parts: list[dict[str, Any]]) -> None:
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"].extend(parts)
            return
        contents.append({"role": role, "parts": parts})

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
            tool_name = tool_names.get(tool_call_id)
            if tool_name is None:
                raise ValueError(
                    f"tool result references unknown Gemini function call: {tool_call_id}"
                )
            response: Any = content
            if isinstance(content, str):
                try:
                    decoded = json.loads(content)
                except json.JSONDecodeError:
                    decoded = {"result": content}
                response = decoded
            if not isinstance(response, Mapping):
                response = {"result": response}
            append(
                "user",
                [
                    {
                        "functionResponse": {
                            "id": tool_call_id,
                            "name": tool_name,
                            "response": dict(response),
                        }
                    }
                ],
            )
            continue

        if role == "assistant" and isinstance(message.get("tool_calls"), list):
            parts: list[dict[str, Any]] = []
            if isinstance(content, str) and content:
                parts.append({"text": content})
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
                call_id = _required_text(raw_call.get("id"), "tool call id")
                name = _required_text(function.get("name"), "tool name")
                tool_names[call_id] = name
                parts.append(
                    {
                        "functionCall": {
                            "id": call_id,
                            "name": name,
                            "args": dict(arguments),
                        }
                    }
                )
            append("model", parts)
            continue

        if role in {"user", "assistant"}:
            if not isinstance(content, str):
                raise ValueError(f"{role} message content must be text")
            append(
                "user" if role == "user" else "model",
                [{"text": content}],
            )
            continue

        raise ValueError(f"unsupported normalized provider message role: {role}")

    return "\n\n".join(system_parts), contents


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return _required_text(value, "provider text field")
