"""First-party provider envelopes for LBE's existing bounded reasoning contract.

These adapters only translate transport request/response shapes. The shared
ToolAwareOpenAICompatibleReasoningBackend continues to parse and validate the
LBE planning contract; it does not delegate policy, tool execution, or session
authority to a provider.
"""
from __future__ import annotations

import json
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .coding_reasoning_provider import ToolAwareOpenAICompatibleReasoningBackend
from .reasoning_provider import JsonTransport, ProviderConfig, ProviderError


class AnthropicReasoningBackend(ToolAwareOpenAICompatibleReasoningBackend):
    """Translate the shared LBE contract to Anthropic's Messages API."""

    def __init__(self, *, config: ProviderConfig, transport: JsonTransport | None = None) -> None:
        require_api_key(config, "anthropic")
        super().__init__(config=config, transport=transport)

    def _complete(
        self,
        stage: str,
        system_prompt: str,
        output_contract: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        input_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        del output_schema  # LBE validates the decoded response contract itself.
        response = self._transport.post_json(
            endpoint=self._config.endpoint.strip(),
            payload={
                "model": self._config.model.strip(),
                "max_tokens": 2048,
                "temperature": 0,
                "system": system_prompt,
                "messages": [{
                    "role": "user",
                    "content": _contract_input(stage, output_contract, input_payload),
                }],
            },
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._config.api_key or "",
                "anthropic-version": "2023-06-01",
            },
            timeout_seconds=float(self._config.timeout_seconds),
        )
        return _decode_contract_json(_extract_anthropic_text(response), "Anthropic")


class GeminiReasoningBackend(ToolAwareOpenAICompatibleReasoningBackend):
    """Translate the shared LBE contract to Gemini's generateContent API."""

    def __init__(self, *, config: ProviderConfig, transport: JsonTransport | None = None) -> None:
        require_api_key(config, "gemini")
        super().__init__(config=config, transport=transport)

    def _complete(
        self,
        stage: str,
        system_prompt: str,
        output_contract: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        input_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        del output_schema  # LBE validates the decoded response contract itself.
        response = self._transport.post_json(
            endpoint=_gemini_endpoint(self._config.endpoint, self._config.api_key or ""),
            payload={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{
                    "role": "user",
                    "parts": [{"text": _contract_input(stage, output_contract, input_payload)}],
                }],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            },
            headers={"Content-Type": "application/json"},
            timeout_seconds=float(self._config.timeout_seconds),
        )
        return _decode_contract_json(_extract_gemini_text(response), "Gemini")


def require_api_key(config: ProviderConfig, provider_id: str) -> None:
    if not config.api_key:
        raise ValueError(f"{provider_id} provider requires a non-empty api_key in its explicit provider config")


def _contract_input(
    stage: str,
    output_contract: Mapping[str, Any],
    input_payload: Mapping[str, Any],
) -> str:
    return json.dumps(
        {"stage": stage, "output_contract": output_contract, "input": input_payload},
        ensure_ascii=False,
        sort_keys=True,
    )


def _decode_contract_json(content: str, provider_name: str) -> Mapping[str, Any]:
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProviderError("PROVIDER_RESPONSE_ERROR", f"{provider_name} response text is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", f"{provider_name} response text must decode to an object")
    return decoded


def _extract_anthropic_text(response: Mapping[str, Any]) -> str:
    blocks = response.get("content")
    if not isinstance(blocks, list):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "Anthropic response must contain a content array")
    text_blocks = [item.get("text") for item in blocks if isinstance(item, Mapping) and item.get("type") == "text"]
    if len(text_blocks) != 1 or not isinstance(text_blocks[0], str) or not text_blocks[0].strip():
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "Anthropic response must contain exactly one non-empty text block")
    return text_blocks[0].strip()


def _extract_gemini_text(response: Mapping[str, Any]) -> str:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], Mapping):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "Gemini response must contain exactly one candidate")
    content = candidates[0].get("content")
    if not isinstance(content, Mapping):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "Gemini candidate must contain content")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "Gemini candidate content must contain parts")
    texts = [item.get("text") for item in parts if isinstance(item, Mapping) and isinstance(item.get("text"), str)]
    if len(texts) != 1 or not texts[0].strip():
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "Gemini response must contain exactly one non-empty text part")
    return texts[0].strip()


def _gemini_endpoint(endpoint: str, api_key: str) -> str:
    """Append the explicit key without logging or persisting it."""
    parsed = urlsplit(endpoint.strip())
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "key" in query:
        raise ValueError("gemini endpoint must not embed an API key; use the explicit api_key config field")
    query["key"] = api_key
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
