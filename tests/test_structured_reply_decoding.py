"""Remote models wrap the structured JSON reply in fences or prose; accept it, never invent it."""
import json

import pytest

from lbe_guard_inspector.reasoning_provider import decode_structured_reply

PLAN = {"interpreted_problem": "p", "ambiguities": []}


def test_plain_json_object() -> None:
    assert decode_structured_reply(json.dumps(PLAN)) == PLAN


def test_markdown_fenced_object() -> None:
    assert decode_structured_reply("```json\n" + json.dumps(PLAN) + "\n```") == PLAN


def test_prose_around_object_is_ignored() -> None:
    assert decode_structured_reply("Here is the plan:\n" + json.dumps(PLAN) + "\nThanks!") == PLAN


def test_first_complete_object_wins() -> None:
    assert decode_structured_reply(json.dumps(PLAN) + " {\"other\": 1}") == PLAN


@pytest.mark.parametrize("content", ["no json here", "{broken", ""])
def test_non_objects_still_fail(content) -> None:
    with pytest.raises(json.JSONDecodeError):
        decode_structured_reply(content)


def test_plain_non_object_json_is_returned_unchanged_for_the_schema_gate() -> None:
    # Parity with json.loads: callers (schema/type validation) reject non-objects.
    assert decode_structured_reply("[1, 2, 3]") == [1, 2, 3]


def test_length_truncated_empty_content_is_reported_as_truncation() -> None:
    from lbe_guard_inspector.reasoning_provider import ProviderError, _extract_message_content

    response = {"choices": [{"finish_reason": "length", "message": {"content": None, "reasoning": "thinking..."}}]}
    with pytest.raises(ProviderError) as info:
        _extract_message_content(response)
    assert "finish_reason=length" in str(info.value)


def test_planning_step_budget_leaves_room_for_reasoning_models() -> None:
    from lbe_guard_inspector import reasoning_provider as rp

    assert 2048 <= rp._REASONING_MAX_TOKENS <= rp.LBE_MAX_REQUESTED_OUTPUT_TOKENS
