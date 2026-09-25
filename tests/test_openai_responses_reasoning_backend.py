from __future__ import annotations

import json

from lbe_guard_inspector.reasoning_contracts import ReasoningRequest
from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.runtime.openai_responses_reasoning_backend import (
    OpenAIResponsesReasoningBackend,
)


class _FakeTransport:
    supports_cancellation = False

    def __init__(self, response):
        self.response = response
        self.calls = []

    def post_json(self, *, endpoint, payload, headers, timeout_seconds):
        self.calls.append(
            {
                "endpoint": endpoint,
                "payload": payload,
                "headers": dict(headers),
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response

    def cancel(self):
        raise AssertionError("cancel must not be called")

    def stream_json(self, **_kwargs):
        raise AssertionError("streaming is not used")


def test_openai_responses_reasoning_uses_json_schema_contract():
    response_plan = {
        "interpreted_problem": "inspect the workspace",
        "ambiguities": [],
        "candidate_guard_ids": [],
        "evidence_requests": [],
        "validation_requests": [],
        "explanation_focus": [],
        "tool_requests": [],
    }
    transport = _FakeTransport(
        {
            "id": "resp-1",
            "status": "completed",
            "output_text": json.dumps(response_plan),
            "output": [],
        }
    )
    backend = OpenAIResponsesReasoningBackend(
        config=ProviderConfig(
            endpoint="https://api.openai.com/v1/responses",
            model="gpt-test",
            timeout_seconds=5,
            api_key="secret",
        ),
        transport=transport,
    )

    plan = backend.plan(
        ReasoningRequest(
            problem="inspect the workspace",
            workspace_identity={
                "workspace_id": "w",
                "configured_root_id": "w",
                "target_project_root": "/secret/host/path",
            },
            workspace_profile={"mode": "audit"},
            approved_guard_ids=(),
            approved_tools=(),
            reference_context=(),
        )
    )

    assert plan.interpreted_problem == "inspect the workspace"
    assert plan.tool_requests == ()

    payload = transport.calls[0]["payload"]
    assert payload["model"] == "gpt-test"
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    decoded_input = json.loads(payload["input"])
    assert decoded_input["stage"] == "planning"
    assert "target_project_root" not in decoded_input["input"]["workspace_identity"]
    assert transport.calls[0]["headers"]["Authorization"] == "Bearer secret"
