"""OpenAI Responses coding-turn event adapter behind LBE authority.

The adapter preserves Responses API call_id / previous_response_id semantics
while normalizing provider observations into LBE model events. It does not own
authorization, execution, receipts, evidence, session state, or completion.
"""
from __future__ import annotations

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


class OpenAIResponsesEventAdapter:
    """Normalize non-streaming OpenAI Responses function calls for LBE."""

    def __init__(
        self,
        *,
        config: ProviderConfig,
        transport: JsonTransport | None = None,
    ) -> None:
        if not config.api_key:
            raise ValueError(
                "openai responses provider requires a non-empty api_key in its explicit provider config"
            )
        self._config = config
        self._transport = transport or UrllibJsonTransport()
        self._previous_response_id: str | None = None
        self._consumed_tool_outputs = 0

    def complete(
        self,
        *,
        messages: tuple[Mapping[str, Any], ...],
        provider_id: str = "openai",
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

        instructions = _responses_instructions(messages)
        tool_outputs = _responses_tool_outputs(messages)
        payload: dict[str, Any] = {
            "model": self._config.model.strip(),
        }
        if instructions:
            payload["instructions"] = instructions
        if tools:
            payload["tools"] = [_responses_tool(item) for item in tools]

        if self._previous_response_id is None:
            payload["input"] = _responses_initial_input(messages)
        else:
            pending = tool_outputs[self._consumed_tool_outputs :]
            if not pending:
                raise ValueError(
                    "Responses continuation requires a new function_call_output"
                )
            payload["previous_response_id"] = self._previous_response_id
            payload["input"] = pending

        try:
            response = self._transport.post_json(
                endpoint=self._config.endpoint.strip(),
                payload=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._config.api_key}",
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

        response_id = _required_text(response.get("id"), "response id")
        events: list[NormalizedModelEvent] = [
            self._event(
                ModelEventType.TURN_STARTED,
                provider_id,
                provider_request_id=response_id,
            )
        ]
        output = response.get("output")
        if not isinstance(output, list):
            return tuple(
                events
                + [
                    self._event(
                        ModelEventType.ERROR,
                        provider_id,
                        provider_request_id=response_id,
                        error_code="PROVIDER_RESPONSE_ERROR",
                        metadata={"terminal_attribution": "provider_native"},
                    )
                ]
            )

        tool_seen = False
        refusal_seen = False
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, Mapping):
                continue
            item_type = item.get("type")
            if item_type == "function_call":
                call_id = _required_text(item.get("call_id"), "function call_id")
                name = _required_text(item.get("name"), "function name")
                raw_arguments = item.get("arguments")
                if not isinstance(raw_arguments, str):
                    return tuple(
                        events
                        + [
                            self._event(
                                ModelEventType.ERROR,
                                provider_id,
                                provider_request_id=response_id,
                                error_code="PROVIDER_RESPONSE_ERROR",
                                metadata={"terminal_attribution": "provider_native"},
                            )
                        ]
                    )
                import json

                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    return tuple(
                        events
                        + [
                            self._event(
                                ModelEventType.ERROR,
                                provider_id,
                                provider_request_id=response_id,
                                error_code="PROVIDER_RESPONSE_ERROR",
                                metadata={"terminal_attribution": "provider_native"},
                            )
                        ]
                    )
                if not isinstance(arguments, Mapping):
                    return tuple(
                        events
                        + [
                            self._event(
                                ModelEventType.ERROR,
                                provider_id,
                                provider_request_id=response_id,
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
                                provider_request_id=response_id,
                                error_code="LBE_CALL_ID_REQUIRED",
                                metadata={"terminal_attribution": "runtime_policy"},
                            )
                        ]
                    )
                lbe_call_id = _required_text(
                    lbe_call_id_for_provider_tool_call(call_id),
                    "lbe_call_id",
                )
                tool_seen = True
                events.extend(
                    (
                        self._event(
                            ModelEventType.TOOL_CALL_STARTED,
                            provider_id,
                            provider_request_id=response_id,
                            provider_item_id=_optional_text(item.get("id")),
                            provider_tool_call_id=call_id,
                            lbe_call_id=lbe_call_id,
                        ),
                        self._event(
                            ModelEventType.TOOL_CALL_COMPLETED,
                            provider_id,
                            provider_request_id=response_id,
                            provider_item_id=_optional_text(item.get("id")),
                            provider_tool_call_id=call_id,
                            lbe_call_id=lbe_call_id,
                            tool_name=name,
                            tool_arguments=dict(arguments),
                        ),
                    )
                )
                continue

            if item_type != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, Mapping):
                    continue
                part_type = part.get("type")
                if part_type == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text:
                        text_parts.append(text)
                elif part_type == "refusal":
                    refusal = part.get("refusal")
                    if isinstance(refusal, str) and refusal:
                        refusal_seen = True
                        text_parts.append(refusal)

        if text_parts:
            events.append(
                self._event(
                    ModelEventType.MESSAGE_COMPLETED,
                    provider_id,
                    provider_request_id=response_id,
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
                        provider_request_id=response_id,
                        usage=normalized,
                    )
                )

        status = _optional_text(response.get("status"))
        self._previous_response_id = response_id
        self._consumed_tool_outputs = len(tool_outputs)

        if tool_seen:
            events.append(
                self._event(
                    ModelEventType.TURN_REQUIRES_TOOL,
                    provider_id,
                    provider_request_id=response_id,
                )
            )
        elif refusal_seen:
            events.append(
                self._event(
                    ModelEventType.TURN_REFUSED,
                    provider_id,
                    provider_request_id=response_id,
                )
            )
        elif status == "incomplete":
            events.append(
                self._event(
                    ModelEventType.TURN_INCOMPLETE,
                    provider_id,
                    provider_request_id=response_id,
                    metadata={
                        "incomplete_details": response.get("incomplete_details")
                    },
                )
            )
        elif status == "cancelled":
            events.append(
                self._event(
                    ModelEventType.CANCELLED,
                    provider_id,
                    provider_request_id=response_id,
                )
            )
        elif status == "failed":
            error = response.get("error")
            code = "PROVIDER_RESPONSE_ERROR"
            if isinstance(error, Mapping) and isinstance(error.get("code"), str):
                code = error["code"]
            events.append(
                self._event(
                    ModelEventType.ERROR,
                    provider_id,
                    provider_request_id=response_id,
                    error_code=code,
                    metadata={"terminal_attribution": "provider_native"},
                )
            )
        else:
            events.append(
                self._event(
                    ModelEventType.TURN_COMPLETED,
                    provider_id,
                    provider_request_id=response_id,
                    metadata={"status": status} if status else {},
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
            protocol_family=ProviderProtocolFamily.OPENAI_RESPONSES,
            **values,
        )


def _responses_instructions(messages: tuple[Mapping[str, Any], ...]) -> str:
    return "\n\n".join(
        content.strip()
        for message in messages
        if message.get("role") == "system"
        and isinstance((content := message.get("content")), str)
        and content.strip()
    )


def _responses_initial_input(
    messages: tuple[Mapping[str, Any], ...],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"}:
            continue
        if not isinstance(content, str):
            continue
        items.append(
            {
                "role": role,
                "content": content,
            }
        )
    if not items:
        raise ValueError("Responses initial turn requires user/assistant text input")
    return items


def _responses_tool_outputs(
    messages: tuple[Mapping[str, Any], ...],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") != "tool":
            continue
        call_id = _required_text(message.get("tool_call_id"), "tool_call_id")
        content = message.get("content")
        if not isinstance(content, str):
            raise ValueError("Responses tool output must be text")
        items.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": content,
            }
        )
    return items


def _responses_tool(tool: Mapping[str, Any]) -> dict[str, Any]:
    function = tool.get("function")
    if tool.get("type") != "function" or not isinstance(function, Mapping):
        raise ValueError("Responses tool translation requires function tools")
    parameters = function.get("parameters")
    if not isinstance(parameters, Mapping):
        raise ValueError("tool parameters must be a mapping")
    translated: dict[str, Any] = {
        "type": "function",
        "name": _required_text(function.get("name"), "tool name"),
        "parameters": dict(parameters),
    }
    description = function.get("description")
    if isinstance(description, str) and description.strip():
        translated["description"] = description.strip()
    return translated


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return _required_text(value, "provider text field")
