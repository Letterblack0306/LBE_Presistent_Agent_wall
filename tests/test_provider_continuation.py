import pytest
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import ChildAgentStatus, SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.provider_continuation import (
    continue_provider,
    continuation_from_persisted_child_result,
    continuation_from_receipt,
)
from lbe_guard_inspector.runtime.tool_orchestration import ToolReceipt, ToolReceiptStatus

def _receipt(status=ToolReceiptStatus.EXECUTED): return ToolReceipt(operation_id='op1',tool_id='workspace.read',status=status,authorization=None,output={'text':'ok'} if status is ToolReceiptStatus.EXECUTED else None,error_code='DENIED' if status is not ToolReceiptStatus.EXECUTED else None)
def test_continuation_requires_governed_receipt_and_preserves_all_identities():
    result=continuation_from_receipt(provider_tool_call_id='provider1',lbe_call_id='lbe1',receipt=_receipt())
    assert result.runtime_operation_id=='op1' and result.tool_receipt_id.startswith('receipt-') and result.output=={'text':'ok'}
def test_escalation_stops_before_provider_continuation():
    with pytest.raises(ValueError,match='stop'): continuation_from_receipt(provider_tool_call_id='provider1',lbe_call_id='lbe1',receipt=_receipt(ToolReceiptStatus.ESCALATED))
def test_sender_receives_only_receipt_backed_continuation():
    item=continuation_from_receipt(provider_tool_call_id='provider1',lbe_call_id='lbe1',receipt=_receipt())
    assert continue_provider(continuation=item,sender=lambda value:value.tool_receipt_id)==item.tool_receipt_id


def _child_history(tmp_path):
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    store.save_session_state(SessionState(
        session_id="parent-session",
        project_workspace_id="workspace",
        canonical_workspace_root=tmp_path,
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
        provider_id="openai-compatible",
        provider_model="model-1",
    ))
    return SessionOperationalHistory(store=store)


def _persist_completed_child(history, *, correlated: bool = True):
    turn = history.start_turn(session_id="parent-session")
    child = history.create_child_agent_run(
        session_id="parent-session",
        turn_id=turn.turn_id,
        correlation_id="provider-call-1",
        parent_agent="parent-agent",
        child_tools=("workspace.read",),
    )
    history.start_child_agent_run(
        session_id="parent-session",
        turn_id=turn.turn_id,
        child_agent_run_id=child.child_agent_run_id,
        child_session_id="child-session-1",
    )
    receipt = ToolReceipt(
        operation_id="parent-turn:lbe-call-1",
        tool_id="subagent.delegate",
        status=ToolReceiptStatus.EXECUTED,
        authorization=None,
        output={"text": "child result"},
    )
    history.project_tool_receipt(
        session_id="parent-session",
        turn_id=turn.turn_id,
        item_id=child.child_agent_run_id,
        receipt=receipt,
        provider_tool_call_id="provider-call-1" if correlated else None,
        lbe_call_id="lbe-call-1" if correlated else None,
    )
    history.finalize_child_agent_run(
        session_id="parent-session",
        turn_id=turn.turn_id,
        child_agent_run_id=child.child_agent_run_id,
        status=ChildAgentStatus.COMPLETED,
        receipt_id=receipt.receipt_id,
        evidence_ref="evidence-child-1",
    )
    return turn, child, receipt


def test_persisted_child_result_reconstructs_correlated_parent_continuation(tmp_path):
    history = _child_history(tmp_path)
    turn, child, receipt = _persist_completed_child(history)

    continuation = continuation_from_persisted_child_result(
        history=history,
        session_id="parent-session",
        turn_id=turn.turn_id,
        child_agent_run_id=child.child_agent_run_id,
    )

    assert continuation.provider_tool_call_id == "provider-call-1"
    assert continuation.lbe_call_id == "lbe-call-1"
    assert continuation.runtime_operation_id == "parent-turn:lbe-call-1"
    assert continuation.tool_receipt_id == receipt.receipt_id
    assert continuation.tool_name == "subagent.delegate"
    assert continuation.output["text"] == "child result"
    assert continuation.output["child_agent_run_id"] == child.child_agent_run_id
    assert continuation.output["child_status"] == "completed"
    assert continuation.output["child_session_id"] == "child-session-1"
    assert continuation.output["child_evidence_ref"] == "evidence-child-1"
    assert continuation.is_error is False


def test_persisted_child_result_fails_closed_without_provider_lbe_correlation(tmp_path):
    history = _child_history(tmp_path)
    turn, child, _ = _persist_completed_child(history, correlated=False)

    with pytest.raises(ValueError, match="correlation is incomplete"):
        continuation_from_persisted_child_result(
            history=history,
            session_id="parent-session",
            turn_id=turn.turn_id,
            child_agent_run_id=child.child_agent_run_id,
        )
