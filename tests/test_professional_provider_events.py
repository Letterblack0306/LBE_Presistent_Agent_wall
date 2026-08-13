from __future__ import annotations

import pytest

from lbe_guard_inspector.professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProfessionalProviderAdapter,
    ProviderToolDefinition,
    ProviderToolResultContinuation,
    ProviderTurnRequest,
)
from lbe_guard_inspector.provider_capabilities import ProviderProtocolFamily


def _event(event_type: ModelEventType, **kwargs: object) -> NormalizedModelEvent:
    return NormalizedModelEvent(
        event_type=event_type,
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
        **kwargs,
    )


def test_p0_event_vocabulary_is_exactly_frozen_contract() -> None:
    assert {item.value for item in ModelEventType} == {
        "model.turn.started",
        "model.message.delta",
        "model.message.completed",
        "model.reasoning_summary.delta",
        "model.reasoning_summary.completed",
        "model.tool_call.started",
        "model.tool_call.arguments.delta",
        "model.tool_call.completed",
        "model.usage.updated",
        "model.turn.requires_tool",
        "model.turn.requires_continuation",
        "model.turn.completed",
        "model.turn.incomplete",
        "model.turn.refused",
        "model.cancelled",
        "model.error",
    }


def test_incremental_events_require_real_non_empty_delta() -> None:
    with pytest.raises(ValueError, match="text must be a non-empty string"):
        _event(ModelEventType.MESSAGE_DELTA, text="")

    event = _event(ModelEventType.MESSAGE_DELTA, text="actual provider delta")
    assert event.text == "actual provider delta"


def test_one_shot_tool_call_needs_no_fabricated_argument_delta() -> None:
    event = _event(
        ModelEventType.TOOL_CALL_COMPLETED,
        provider_tool_call_id="provider-call-7",
        lbe_call_id="lbe-call-7",
        tool_name="workspace.read",
        tool_arguments={"path": "README.md"},
    )

    assert event.event_type is ModelEventType.TOOL_CALL_COMPLETED
    assert event.tool_arguments == {"path": "README.md"}
    assert event.text is None


def test_tool_call_identity_keeps_provider_and_lbe_ids_distinct() -> None:
    event = _event(
        ModelEventType.TOOL_CALL_STARTED,
        provider_request_id="req-provider-1",
        provider_item_id="item-provider-2",
        provider_tool_call_id="tool-provider-3",
        lbe_call_id="lbe-4",
    )

    assert event.provider_request_id == "req-provider-1"
    assert event.provider_item_id == "item-provider-2"
    assert event.provider_tool_call_id == "tool-provider-3"
    assert event.lbe_call_id == "lbe-4"
    assert not hasattr(event, "runtime_operation_id")
    assert not hasattr(event, "tool_receipt_id")


def test_tool_result_continuation_requires_existing_runtime_evidence_identity() -> None:
    result = ProviderToolResultContinuation(
        provider_tool_call_id="tool-provider-3",
        lbe_call_id="lbe-4",
        runtime_operation_id="operation-5",
        tool_receipt_id="receipt-6",
        tool_name="workspace.read",
        output={"text": "hello"},
    )

    assert result.runtime_operation_id == "operation-5"
    assert result.tool_receipt_id == "receipt-6"

    with pytest.raises(ValueError, match="tool_receipt_id"):
        ProviderToolResultContinuation(
            provider_tool_call_id="tool-provider-3",
            lbe_call_id="lbe-4",
            runtime_operation_id="operation-5",
            tool_receipt_id="",
            tool_name="workspace.read",
            output=None,
        )


def test_provider_turn_request_projects_tool_schema_without_authority() -> None:
    tool = ProviderToolDefinition(
        name="workspace.read",
        description="Read one workspace-relative file.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    )
    request = ProviderTurnRequest(
        provider_id="anthropic",
        model_id="claude-model",
        protocol_family=ProviderProtocolFamily.ANTHROPIC_MESSAGES,
        system_prompt="Use only the projected governed tools when needed.",
        messages=({"role": "user", "content": "inspect this"},),
        tool_definitions=(tool,),
    )

    assert request.tool_definitions == (tool,)
    assert not hasattr(request, "workspace_root")
    assert not hasattr(request, "permission")
    assert not hasattr(request, "authorization")
    assert not hasattr(request, "tool_dispatcher")


def test_usage_event_rejects_fabricated_or_invalid_counts() -> None:
    event = _event(ModelEventType.USAGE_UPDATED, usage={"input_tokens": 10, "output_tokens": 4})
    assert event.usage == {"input_tokens": 10, "output_tokens": 4}

    with pytest.raises(ValueError, match="non-negative integers"):
        _event(ModelEventType.USAGE_UPDATED, usage={"input_tokens": -1})


def test_error_event_requires_provider_error_code() -> None:
    with pytest.raises(ValueError, match="error_code"):
        _event(ModelEventType.ERROR)

    event = _event(ModelEventType.ERROR, error_code="RATE_LIMITED", text="provider rejected request")
    assert event.error_code == "RATE_LIMITED"


def test_professional_adapter_protocol_exposes_only_provider_io_contract() -> None:
    method_names = {
        name
        for name, value in ProfessionalProviderAdapter.__dict__.items()
        if callable(value) and not name.startswith("_")
    }
    assert method_names == {"stream_turn", "continue_with_tool_result", "cancel"}
