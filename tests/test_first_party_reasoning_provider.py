from __future__ import annotations

import json

import pytest

from lbe_guard_inspector.first_party_reasoning_provider import (
    AnthropicReasoningBackend,
    GeminiReasoningBackend,
)
from lbe_guard_inspector.reasoning_contracts import ExplanationRequest, ReasoningRequest
from lbe_guard_inspector.reasoning_provider import ProviderConfig, ProviderError


class FakeTransport:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict] = []

    def post_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def _plan() -> dict:
    return {
        "interpreted_problem": "replace the bounded marker",
        "ambiguities": [],
        "candidate_guard_ids": [],
        "evidence_requests": [],
        "validation_requests": [],
        "explanation_focus": [],
        "tool_requests": [
            {
                "tool_id": "workspace.replace_text",
                "path": "README.md",
                "old_text": "BEFORE",
                "new_text": "AFTER",
                "reason": "apply the requested bounded edit",
            }
        ],
    }


def _request() -> ReasoningRequest:
    return ReasoningRequest(
        problem="replace BEFORE with AFTER in README.md",
        workspace_identity={"workspace_id": "controlled"},
        workspace_profile={"project_type": "generic"},
        approved_guard_ids=(),
        approved_tools=("workspace.read", "workspace.replace_text"),
        reference_context=(),
    )


def _config(endpoint: str, *, api_key: str | None = "test-key") -> ProviderConfig:
    return ProviderConfig(endpoint=endpoint, model="test-model", timeout_seconds=15, api_key=api_key)


def test_anthropic_adapter_preserves_lbe_tool_plan_contract() -> None:
    transport = FakeTransport({"content": [{"type": "text", "text": json.dumps(_plan())}]})
    backend = AnthropicReasoningBackend(
        config=_config("https://api.anthropic.com/v1/messages"), transport=transport
    )

    plan = backend.plan(_request())

    assert plan.tool_requests[0].tool_id == "workspace.replace_text"
    call = transport.calls[0]
    assert call["endpoint"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"] == {
        "Content-Type": "application/json",
        "x-api-key": "test-key",
        "anthropic-version": "2023-06-01",
    }
    assert call["payload"]["model"] == "test-model"
    assert call["payload"]["max_tokens"] == 2048
    assert call["payload"]["messages"][0]["role"] == "user"
    body = json.loads(call["payload"]["messages"][0]["content"])
    assert body["stage"] == "planning"
    assert body["output_contract"]["tool_requests"][0]["tool_id"] == "approved tool ID string"


def test_gemini_adapter_preserves_lbe_tool_plan_contract() -> None:
    transport = FakeTransport({"candidates": [{"content": {"parts": [{"text": json.dumps(_plan())}]}}]})
    backend = GeminiReasoningBackend(
        config=_config(
            "https://generativelanguage.googleapis.com/v1beta/models/test-model:generateContent"
        ),
        transport=transport,
    )

    plan = backend.plan(_request())

    assert plan.tool_requests[0].arguments == {
        "path": "README.md", "old_text": "BEFORE", "new_text": "AFTER"
    }
    call = transport.calls[0]
    assert call["endpoint"].endswith(":generateContent?key=test-key")
    assert call["headers"] == {"Content-Type": "application/json"}
    assert call["payload"]["generationConfig"] == {
        "temperature": 0, "responseMimeType": "application/json"
    }
    body = json.loads(call["payload"]["contents"][0]["parts"][0]["text"])
    assert body["stage"] == "planning"
    assert call["payload"]["systemInstruction"]["parts"][0]["text"]


@pytest.mark.parametrize(
    ("backend_type", "endpoint"),
    [
        (AnthropicReasoningBackend, "https://api.anthropic.com/v1/messages"),
        (GeminiReasoningBackend, "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent"),
    ],
)
def test_first_party_adapters_require_explicit_user_owned_key(backend_type, endpoint) -> None:
    with pytest.raises(ValueError, match="requires a non-empty api_key"):
        backend_type(config=_config(endpoint, api_key=None), transport=FakeTransport({}))


@pytest.mark.parametrize(
    ("backend_type", "endpoint", "response"),
    [
        (AnthropicReasoningBackend, "https://api.anthropic.com/v1/messages", {"content": []}),
        (GeminiReasoningBackend, "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent", {"candidates": []}),
    ],
)
def test_first_party_adapters_reject_malformed_provider_envelopes(backend_type, endpoint, response) -> None:
    backend = backend_type(config=_config(endpoint), transport=FakeTransport(response))

    with pytest.raises(ProviderError, match="exactly one") as error:
        backend.plan(_request())

    assert error.value.code == "PROVIDER_RESPONSE_ERROR"


def test_gemini_adapter_refuses_key_embedded_in_endpoint() -> None:
    backend = GeminiReasoningBackend(
        config=_config("https://generativelanguage.googleapis.com/v1beta/models/test:generateContent?key=wrong"),
        transport=FakeTransport({}),
    )

    with pytest.raises(ValueError, match="must not embed an API key"):
        backend.plan(_request())


def test_anthropic_adapter_uses_shared_explanation_contract() -> None:
    transport = FakeTransport({"content": [{"type": "text", "text": '{"explanation":"bounded"}'}]})
    result = AnthropicReasoningBackend(
        config=_config("https://api.anthropic.com/v1/messages"), transport=transport
    ).explain(
        ExplanationRequest(
            guard_result={"verdict": "PASS"},
            current_workspace_evidence=(),
            validation_evidence=(),
            governance_state="OBSERVE",
            explanation_focus=(),
        )
    )

    assert result.explanation == "bounded"
    assert json.loads(transport.calls[0]["payload"]["messages"][0]["content"])["stage"] == "explanation"
