"""Provider-neutral OpenAI-compatible backend for bounded LBE reasoning."""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol

from .reasoning_contracts import (
    ExplanationRequest,
    ExplanationResult,
    ReasoningPlan,
    ReasoningRequest,
)


@dataclass(frozen=True)
class ProviderConfig:
    endpoint: str
    model: str
    timeout_seconds: float
    api_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, str) or not self.endpoint.strip():
            raise ValueError("provider endpoint must be a non-empty string")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("provider model must be a non-empty string")
        if not isinstance(self.timeout_seconds, (int, float)) or self.timeout_seconds <= 0:
            raise ValueError("provider timeout_seconds must be greater than zero")


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class JsonTransport(Protocol):
    def post_json(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]: ...


class UrllibJsonTransport:
    def post_json(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            raise ProviderError("PROVIDER_HTTP_ERROR", f"HTTP {exc.code}: {detail}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ProviderError("PROVIDER_TIMEOUT", str(exc) or "provider request timed out") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, (TimeoutError, socket.timeout)):
                raise ProviderError("PROVIDER_TIMEOUT", str(reason) or "provider request timed out") from exc
            raise ProviderError("PROVIDER_TRANSPORT_ERROR", str(reason)) from exc
        except OSError as exc:
            raise ProviderError("PROVIDER_TRANSPORT_ERROR", str(exc)) from exc

        if not raw:
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider returned an empty response body")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider returned invalid JSON") from exc
        if not isinstance(decoded, Mapping):
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider response must be a JSON object")
        return decoded


class OpenAICompatibleReasoningBackend:
    def __init__(self, *, config: ProviderConfig, transport: JsonTransport | None = None) -> None:
        self._config = config
        self._transport = transport or UrllibJsonTransport()

    def plan(self, request: ReasoningRequest) -> ReasoningPlan:
        result = self._complete("planning", _PLANNING_SYSTEM_PROMPT, asdict(request))
        try:
            return ReasoningPlan.from_mapping(result)
        except (TypeError, ValueError) as exc:
            raise ProviderError("PROVIDER_SCHEMA_ERROR", f"invalid planning response: {exc}") from exc

    def explain(self, request: ExplanationRequest) -> ExplanationResult:
        result = self._complete("explanation", _EXPLANATION_SYSTEM_PROMPT, asdict(request))
        try:
            return ExplanationResult.from_mapping(result)
        except (TypeError, ValueError) as exc:
            raise ProviderError("PROVIDER_SCHEMA_ERROR", f"invalid explanation response: {exc}") from exc

    def _complete(self, stage: str, system_prompt: str, input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = {
            "model": self._config.model.strip(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"stage": stage, "input": input_payload},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        response = self._transport.post_json(
            endpoint=self._config.endpoint.strip(),
            payload=payload,
            headers=headers,
            timeout_seconds=float(self._config.timeout_seconds),
        )
        content = _extract_message_content(response)
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider message content is not valid JSON") from exc
        if not isinstance(decoded, Mapping):
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider message content must decode to an object")
        return decoded


def _extract_message_content(response: Mapping[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider response must contain exactly one choice")
    choice = choices[0]
    if not isinstance(choice, Mapping):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider choice must be an object")
    message = choice.get("message")
    if not isinstance(message, Mapping):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider choice must contain a message object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider message content must be a non-empty string")
    return content.strip()


_PLANNING_SYSTEM_PROMPT = """You are the bounded planning stage inside LBE. Return one JSON object matching the supplied planning contract exactly. Use only approved guard IDs, approved tool IDs, and workspace-relative paths from the input. Do not return verdicts, authorization, commands, writes, repairs, mutations, policy decisions, or memory-promotion instructions. Do not include prose outside the JSON object."""

_EXPLANATION_SYSTEM_PROMPT = """You are the bounded explanation stage inside LBE. The deterministic result is final. Return one JSON object with exactly one field: explanation. Explain the supplied result and evidence concisely. Do not add or alter verdicts, authority, evidence, governance state, commands, writes, repairs, or policy decisions."""
