"""OpenAI Responses backend for LBE's bounded reasoning contract.

This backend translates only the provider request/response envelope. LBE keeps
workspace/session authority, deterministic authorization, tool execution,
receipts/evidence, validation, and completion.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Mapping

from ..coding_reasoning_provider import (
    ToolAwareReasoningPlan,
    _TOOL_AWARE_PLANNING_SYSTEM_PROMPT,
    _planning_input_payload,
    _tool_aware_output_contract,
    _tool_aware_schema,
)
from ..reasoning_contracts import (
    ExplanationRequest,
    ExplanationResult,
    ReasoningRequest,
)
from ..reasoning_provider import (
    JsonTransport,
    ProviderConfig,
    ProviderError,
    UrllibJsonTransport,
    _EXPLANATION_JSON_SCHEMA,
    _EXPLANATION_OUTPUT_CONTRACT,
    _EXPLANATION_SYSTEM_PROMPT,
    _require_relative_evidence_paths,
)


class OpenAIResponsesReasoningBackend:
    """Bounded plan/explain backend over the OpenAI Responses API."""

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

    def plan(self, request: ReasoningRequest) -> ToolAwareReasoningPlan:
        result = self._complete(
            "planning",
            _TOOL_AWARE_PLANNING_SYSTEM_PROMPT,
            _tool_aware_output_contract(),
            _tool_aware_schema(),
            _planning_input_payload(request),
        )
        try:
            plan = ToolAwareReasoningPlan.from_mapping(result)
            _require_relative_evidence_paths(plan)
            return plan
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                "PROVIDER_SCHEMA_ERROR",
                f"invalid planning response: {exc}",
            ) from exc

    def explain(self, request: ExplanationRequest) -> ExplanationResult:
        result = self._complete(
            "explanation",
            _EXPLANATION_SYSTEM_PROMPT,
            _EXPLANATION_OUTPUT_CONTRACT,
            _EXPLANATION_JSON_SCHEMA,
            asdict(request),
        )
        try:
            return ExplanationResult.from_mapping(result)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                "PROVIDER_SCHEMA_ERROR",
                f"invalid explanation response: {exc}",
            ) from exc

    def _complete(
        self,
        stage: str,
        system_prompt: str,
        output_contract: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        input_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        payload = {
            "model": self._config.model.strip(),
            "instructions": system_prompt,
            "input": json.dumps(
                {
                    "stage": stage,
                    "output_contract": output_contract,
                    "input": input_payload,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": f"lbe_{stage}_response",
                    "strict": True,
                    "schema": output_schema,
                }
            },
        }
        response = self._transport.post_json(
            endpoint=self._config.endpoint.strip(),
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._config.api_key}",
            },
            timeout_seconds=float(self._config.timeout_seconds),
        )
        status = response.get("status")
        if isinstance(status, str) and status != "completed":
            raise ProviderError(
                "PROVIDER_RESPONSE_ERROR",
                f"OpenAI Responses reasoning ended with status {status}",
            )
        content = _responses_output_text(response)
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                "PROVIDER_RESPONSE_ERROR",
                "OpenAI Responses output_text is not valid JSON",
            ) from exc
        if not isinstance(decoded, Mapping):
            raise ProviderError(
                "PROVIDER_RESPONSE_ERROR",
                "OpenAI Responses output_text must decode to an object",
            )
        return decoded


def _responses_output_text(response: Mapping[str, Any]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = response.get("output")
    if not isinstance(output, list):
        raise ProviderError(
            "PROVIDER_RESPONSE_ERROR",
            "OpenAI Responses payload does not contain output text",
        )
    texts: list[str] = []
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, Mapping) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                texts.append(text)
    if not texts:
        raise ProviderError(
            "PROVIDER_RESPONSE_ERROR",
            "OpenAI Responses payload does not contain output_text content",
        )
    return "".join(texts).strip()
