from __future__ import annotations

import io
import json
import socket
import urllib.error

import pytest

from lbe_guard_inspector.reasoning_contracts import ExplanationRequest, ReasoningRequest
from lbe_guard_inspector.reasoning_provider import (
    OpenAICompatibleReasoningBackend,
    ProviderConfig,
    ProviderError,
    UrllibJsonTransport,
)


class FakeTransport:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    def post_json(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def planning_request() -> ReasoningRequest:
    return ReasoningRequest(
        problem="inspect package metadata",
        workspace_identity={
            "configured_root_id": "root-1",
            "target_project_root": "C:/repo",
            "workspace_id": "workspace-1",
        },
        workspace_profile={"project_type": "python"},
        approved_guard_ids=("npm.package_metadata",),
        approved_tools=("workspace.read",),
        reference_context=({"source": "verified"},),
    )


def explanation_request() -> ExplanationRequest:
    return ExplanationRequest(
        guard_result={"verdict": "PASS", "governance_state": "OBSERVE"},
        current_workspace_evidence=({"path": "package.json"},),
        validation_evidence=({"status": "confirmed"},),
        governance_state="OBSERVE",
        explanation_focus=("package metadata",),
    )


def choice(value) -> dict:
    return {"choices": [{"message": {"content": json.dumps(value)}}]}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"endpoint": "", "model": "m", "timeout_seconds": 1},
        {"endpoint": "http://example", "model": "", "timeout_seconds": 1},
        {"endpoint": "http://example", "model": "m", "timeout_seconds": 0},
    ],
)
def test_provider_config_requires_explicit_valid_values(kwargs):
    with pytest.raises(ValueError):
        ProviderConfig(**kwargs)


def test_planning_call_uses_explicit_config_and_typed_contract():
    response = choice(
        {
            "interpreted_problem": "inspect package metadata",
            "ambiguities": [],
            "candidate_guard_ids": ["npm.package_metadata"],
            "evidence_requests": [
                {
                    "tool_id": "workspace.read",
                    "path": "package.json",
                    "reason": "inspect metadata",
                }
            ],
            "validation_requests": ["guard_runner.independent_reread"],
            "explanation_focus": ["package metadata"],
        }
    )
    transport = FakeTransport(response)
    backend = OpenAICompatibleReasoningBackend(
        config=ProviderConfig(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="local-model",
            timeout_seconds=12,
            api_key="secret",
        ),
        transport=transport,
    )

    plan = backend.plan(planning_request())

    assert plan.candidate_guard_ids == ("npm.package_metadata",)
    call = transport.calls[0]
    assert call["endpoint"] == "http://127.0.0.1:1234/v1/chat/completions"
    assert call["timeout_seconds"] == 12
    assert call["headers"]["Authorization"] == "Bearer secret"
    assert call["payload"]["model"] == "local-model"
    assert call["payload"]["temperature"] == 0
    response_format = call["payload"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "lbe_planning_response"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "interpreted_problem",
        "ambiguities",
        "candidate_guard_ids",
        "evidence_requests",
        "validation_requests",
        "explanation_focus",
    }
    evidence_schema = schema["properties"]["evidence_requests"]["items"]
    assert evidence_schema["required"] == ["tool_id", "path", "reason"]
    assert evidence_schema["additionalProperties"] is False
    assert "Workspace-relative path only" in evidence_schema["properties"]["path"]["description"]
    user_payload = json.loads(call["payload"]["messages"][1]["content"])
    assert user_payload["stage"] == "planning"
    assert set(user_payload["output_contract"]) == {
        "interpreted_problem",
        "ambiguities",
        "candidate_guard_ids",
        "evidence_requests",
        "validation_requests",
        "explanation_focus",
    }
    assert user_payload["input"]["workspace_identity"] == {
        "configured_root_id": "root-1",
        "workspace_id": "workspace-1",
    }
    assert "C:/repo" not in call["payload"]["messages"][1]["content"]
    system_prompt = call["payload"]["messages"][0]["content"]
    assert "exactly these six keys" in system_prompt
    assert "Do not wrap the object in planning_contract" in system_prompt
    assert "absolute target_project_root is intentionally withheld" in system_prompt


def test_explanation_call_is_separate_and_typed():
    transport = FakeTransport(choice({"explanation": "The deterministic guard passed."}))
    backend = OpenAICompatibleReasoningBackend(
        config=ProviderConfig(endpoint="http://provider", model="model", timeout_seconds=5),
        transport=transport,
    )

    result = backend.explain(explanation_request())

    assert result.explanation == "The deterministic guard passed."
    call = transport.calls[0]
    user_payload = json.loads(call["payload"]["messages"][1]["content"])
    assert user_payload["stage"] == "explanation"
    assert user_payload["output_contract"] == {"explanation": "non-empty string"}
    response_format = call["payload"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "lbe_explanation_response"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"] == {
        "type": "object",
        "properties": {"explanation": {"type": "string", "minLength": 1}},
        "required": ["explanation"],
        "additionalProperties": False,
    }
    assert "exactly one top-level JSON object" in call["payload"]["messages"][0]["content"]


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"choices": []},
        {"choices": [{}, {}]},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": "not json"}}]},
        {"choices": [{"message": {"content": "[]"}}]},
    ],
)
def test_malformed_provider_responses_fail_structurally(response):
    backend = OpenAICompatibleReasoningBackend(
        config=ProviderConfig(endpoint="http://provider", model="model", timeout_seconds=5),
        transport=FakeTransport(response),
    )

    with pytest.raises(ProviderError) as exc:
        backend.plan(planning_request())

    assert exc.value.code == "PROVIDER_RESPONSE_ERROR"


def test_schema_invalid_planning_response_is_rejected():
    backend = OpenAICompatibleReasoningBackend(
        config=ProviderConfig(endpoint="http://provider", model="model", timeout_seconds=5),
        transport=FakeTransport(choice({"verdict": "PASS"})),
    )

    with pytest.raises(ProviderError) as exc:
        backend.plan(planning_request())

    assert exc.value.code == "PROVIDER_SCHEMA_ERROR"


def test_wrapped_planning_contract_is_rejected_instead_of_silently_unwrapped():
    backend = OpenAICompatibleReasoningBackend(
        config=ProviderConfig(endpoint="http://provider", model="model", timeout_seconds=5),
        transport=FakeTransport(choice({"planning_contract": {}})),
    )

    with pytest.raises(ProviderError) as exc:
        backend.plan(planning_request())

    assert exc.value.code == "PROVIDER_SCHEMA_ERROR"
    assert "unsupported planning_contract" in str(exc.value)


def test_injected_transport_failure_is_preserved():
    failure = ProviderError("PROVIDER_TIMEOUT", "timed out")
    backend = OpenAICompatibleReasoningBackend(
        config=ProviderConfig(endpoint="http://provider", model="model", timeout_seconds=5),
        transport=FakeTransport(error=failure),
    )

    with pytest.raises(ProviderError) as exc:
        backend.plan(planning_request())

    assert exc.value is failure


def test_urllib_transport_maps_timeout(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.timeout("late")

    monkeypatch.setattr("urllib.request.urlopen", fail)

    with pytest.raises(ProviderError) as exc:
        UrllibJsonTransport().post_json(
            endpoint="http://provider",
            payload={"x": 1},
            headers={"Content-Type": "application/json"},
            timeout_seconds=1,
        )

    assert exc.value.code == "PROVIDER_TIMEOUT"


def test_urllib_transport_maps_http_error(monkeypatch):
    error = urllib.error.HTTPError(
        "http://provider",
        500,
        "failure",
        hdrs=None,
        fp=io.BytesIO(b"server failed"),
    )

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr("urllib.request.urlopen", fail)

    with pytest.raises(ProviderError) as exc:
        UrllibJsonTransport().post_json(
            endpoint="http://provider",
            payload={"x": 1},
            headers={"Content-Type": "application/json"},
            timeout_seconds=1,
        )

    assert exc.value.code == "PROVIDER_HTTP_ERROR"
