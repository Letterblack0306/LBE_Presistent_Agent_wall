from __future__ import annotations

import json

import pytest

from lbe_guard_inspector.runtime.cline_stdio_bridge import GovernedClineWorker
from lbe_guard_inspector.runtime.cline_stdio_protocol import (
    PROTOCOL_VERSION,
    BridgeFrame,
    ProtocolError,
    parse_frame,
)


def _frame(
    message_type: str,
    message_id: str = "py-1",
    payload: dict | None = None,
) -> BridgeFrame:
    return BridgeFrame(
        protocol_version=PROTOCOL_VERSION,
        message_id=message_id,
        message_type=message_type,
        session_id="session-1",
        turn_id="turn-1",
        payload=payload or {},
    )


def test_valid_protocol_frame_round_trips() -> None:
    frame = _frame("runtime.start", payload={"allowed_tools": []})
    parsed = parse_frame(
        frame.to_json_line(), expected_direction="python_to_node"
    )
    assert parsed == frame


@pytest.mark.parametrize(
    "raw, message",
    [
        ("not-json", "malformed JSON frame"),
        (
            json.dumps(
                {
                    "protocol_version": "wrong",
                    "message_id": "1",
                    "message_type": "runtime.ready",
                    "session_id": "s",
                    "turn_id": "t",
                }
            ),
            "unsupported protocol_version",
        ),
        (
            json.dumps(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "message_id": "1",
                    "message_type": "unknown",
                    "session_id": "s",
                    "turn_id": "t",
                }
            ),
            "unknown message_type",
        ),
    ],
)
def test_protocol_rejects_malformed_or_unknown_frames(
    raw: str, message: str
) -> None:
    with pytest.raises(ProtocolError, match=message):
        parse_frame(raw)


def test_protocol_preserves_tool_identity_chain() -> None:
    frame = BridgeFrame(
        protocol_version=PROTOCOL_VERSION,
        message_id="node-1",
        message_type="tool.proposed",
        session_id="session-1",
        turn_id="turn-1",
        payload={"tool_id": "workspace.read", "arguments": {"path": "README.md"}},
        cline_tool_call_id="cline-call-1",
        lbe_call_id="lbe-call-1",
        operation_id="operation-1",
    )
    parsed = parse_frame(
        frame.to_json_line(), expected_direction="node_to_python"
    )
    assert parsed.cline_tool_call_id == "cline-call-1"
    assert parsed.lbe_call_id == "lbe-call-1"
    assert parsed.operation_id == "operation-1"


def test_real_worker_startup_and_shutdown_reports_pinned_cline_runtime() -> None:
    worker = GovernedClineWorker()
    ready = worker.start(
        _frame(
            "runtime.start",
            payload={"allowed_tools": [{"tool_id": "workspace.read"}]},
        )
    )
    assert ready.message_type == "runtime.ready"
    assert ready.payload["cline_agents_version"] == "0.0.75"
    assert ready.payload["agent_runtime_export"] is True
    assert ready.payload["create_agent_runtime_export"] is True
    assert ready.payload["allowed_tool_ids"] == ["workspace.read"]
    assert ready.payload["native_mutation_tools_registered"] is False

    completed = worker.shutdown(
        _frame("runtime.shutdown", message_id="py-2")
    )
    assert completed.message_type == "turn.completed"
    assert completed.payload == {"shutdown": True}
    assert not worker.is_running


def test_worker_exposes_only_explicit_allowlist() -> None:
    worker = GovernedClineWorker()
    ready = worker.start(
        _frame("runtime.start", payload={"allowed_tools": []})
    )
    assert ready.payload["allowed_tool_ids"] == []
    assert ready.payload["native_mutation_tools_registered"] is False
    worker.shutdown(_frame("runtime.shutdown", message_id="py-2"))


def test_foundation_turn_execution_fails_truthfully_without_fake_continuation() -> None:
    worker = GovernedClineWorker()
    worker.start(_frame("runtime.start", payload={"allowed_tools": []}))
    worker.send(
        _frame(
            "turn.execute",
            message_id="py-2",
            payload={"text": "hello"},
        )
    )
    result = worker.read()
    assert result.message_type == "turn.failed"
    assert result.payload["code"] == "FOUNDATION_CONTINUATION_UNVERIFIED"
    worker.shutdown(_frame("runtime.shutdown", message_id="py-3"))
