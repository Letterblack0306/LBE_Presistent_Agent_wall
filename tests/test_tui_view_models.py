from lbe_guard_inspector.memory.operational_history import OperationalEvent
from lbe_guard_inspector.tui_view_models import (
    TuiEventKind,
    TuiState,
    project_tui_event,
)


def test_tool_view_preserves_authorization_receipt_and_evidence() -> None:
    event = OperationalEvent(
        session_id="s",
        turn_id="t",
        event_type="tool.completed",
        payload={
            "tool_id": "workspace.create_candidate_text",
            "status": "executed",
            "receipt_id": "receipt-1",
            "authorization": {
                "verdict": "ALLOW",
                "rationale": "Capability is delegated.",
            },
            "output": {"path": "note.txt"},
            "evidence": [{"kind": "write"}],
        },
        runtime_operation_id="operation-1",
        tool_receipt_id="receipt-1",
        session_sequence=3,
    )

    view = project_tui_event(event)

    assert view.kind is TuiEventKind.TOOL
    assert view.state is TuiState.PASS
    assert view.sequence == 3
    assert view.receipt is not None
    assert view.receipt.receipt_id == "receipt-1"
    assert view.receipt.operation_id == "operation-1"
    assert view.receipt.authorization is not None
    assert view.receipt.authorization.verdict == "ALLOW"
    assert view.receipt.authorization.rationale == "Capability is delegated."
    assert view.receipt.evidence.count == 1
    assert view.receipt.output == {"path": "note.txt"}


def test_missing_tool_facts_remain_unknown_or_absent() -> None:
    view = project_tui_event(
        OperationalEvent(
            session_id="s",
            turn_id="t",
            event_type="tool.requested",
            payload={"tool_id": "workspace.read"},
        )
    )

    assert view.kind is TuiEventKind.TOOL
    assert view.state is TuiState.UNKNOWN
    assert view.receipt is not None
    assert view.receipt.authorization is None
    assert view.receipt.receipt_id is None
    assert view.receipt.evidence.count == 0
    assert view.receipt.output is None


def test_unknown_event_is_not_presented_as_success() -> None:
    view = project_tui_event(
        OperationalEvent(
            session_id="s",
            turn_id="t",
            event_type="future.event",
            payload={"outcome": "COMPLETED"},
        )
    )

    assert view.kind is TuiEventKind.UNKNOWN
    assert view.state is TuiState.UNKNOWN
    assert view.title == "future.event"


def test_failed_tool_keeps_structured_error() -> None:
    view = project_tui_event(
        OperationalEvent(
            session_id="s",
            turn_id="t",
            event_type="tool.failed",
            payload={
                "tool_id": "workspace.write",
                "error_code": "WRITE_FAILED",
                "error_message": "disk unavailable",
            },
        )
    )

    assert view.state is TuiState.FAILED
    assert view.receipt is not None
    assert view.receipt.error_code == "WRITE_FAILED"
    assert view.receipt.error_message == "disk unavailable"
