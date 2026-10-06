"""Receipt-backed provider continuation boundary with no execution authority."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .memory.operational_history import ChildAgentStatus, SessionOperationalHistory
from .runtime.tool_orchestration import ToolReceipt, ToolReceiptStatus


@dataclass(frozen=True)
class ProviderToolContinuation:
    provider_tool_call_id: str
    lbe_call_id: str
    runtime_operation_id: str
    tool_receipt_id: str
    tool_name: str
    output: Mapping[str, Any]
    is_error: bool


def continuation_from_receipt(*, provider_tool_call_id: str, lbe_call_id: str, receipt: ToolReceipt) -> ProviderToolContinuation:
    """Convert an already-governed receipt; this function never invokes a tool."""
    for name, value in (("provider_tool_call_id", provider_tool_call_id), ("lbe_call_id", lbe_call_id)):
        if not isinstance(value, str) or not value.strip(): raise ValueError(f"{name} must be non-empty")
    if not isinstance(receipt, ToolReceipt): raise TypeError("receipt must be ToolReceipt")
    if receipt.status is ToolReceiptStatus.ESCALATED: raise ValueError("escalated receipt must stop for approval, not continue provider")
    output = dict(receipt.output or {}) if receipt.status is ToolReceiptStatus.EXECUTED else {
        "status": receipt.status.value, "error_code": receipt.error_code, "error_message": receipt.error_message,
    }
    return ProviderToolContinuation(provider_tool_call_id.strip(),lbe_call_id.strip(),receipt.operation_id,receipt.receipt_id,receipt.tool_id,output,receipt.status is not ToolReceiptStatus.EXECUTED)


def continuation_from_persisted_child_result(
    *,
    history: SessionOperationalHistory,
    session_id: str,
    turn_id: str,
    child_agent_run_id: str,
) -> ProviderToolContinuation:
    """Reconstruct provider continuation from terminal persisted child + receipt truth."""
    if not isinstance(history, SessionOperationalHistory):
        raise TypeError("history must be SessionOperationalHistory")
    run = history.child_agent_run(
        session_id=session_id,
        turn_id=turn_id,
        child_agent_run_id=child_agent_run_id,
    )
    if run is None:
        raise ValueError("child agent run was not found")
    terminal = {
        ChildAgentStatus.COMPLETED,
        ChildAgentStatus.FAILED,
        ChildAgentStatus.REJECTED,
        ChildAgentStatus.CANCELLED,
    }
    if run.status not in terminal:
        raise ValueError("child agent run is not terminal")
    if not run.receipt_id:
        raise ValueError("terminal child agent run has no correlated receipt")

    matches = tuple(
        event
        for event in history.events_for_turn(turn_id=turn_id)
        if event.tool_receipt_id == run.receipt_id
    )
    if len(matches) != 1:
        raise ValueError("child agent receipt correlation is missing or ambiguous")
    event = matches[0]
    required = {
        "provider_tool_call_id": event.provider_tool_call_id,
        "lbe_call_id": event.lbe_call_id,
        "runtime_operation_id": event.runtime_operation_id,
        "tool_receipt_id": event.tool_receipt_id,
    }
    missing = sorted(name for name, value in required.items() if not str(value or "").strip())
    if missing:
        raise ValueError(f"child agent receipt correlation is incomplete: {missing}")

    payload = dict(event.payload)
    tool_name = str(payload.get("tool_id") or "").strip()
    if not tool_name:
        raise ValueError("child agent receipt payload has no tool_id")
    raw_output = payload.get("output")
    output = dict(raw_output) if isinstance(raw_output, Mapping) else {}
    output["child_agent_run_id"] = run.child_agent_run_id
    output["child_status"] = run.status.value
    if run.child_session_id:
        output["child_session_id"] = run.child_session_id
    if run.evidence_ref:
        output["child_evidence_ref"] = run.evidence_ref

    return ProviderToolContinuation(
        provider_tool_call_id=str(event.provider_tool_call_id),
        lbe_call_id=str(event.lbe_call_id),
        runtime_operation_id=str(event.runtime_operation_id),
        tool_receipt_id=str(event.tool_receipt_id),
        tool_name=tool_name,
        output=output,
        is_error=(run.status is not ChildAgentStatus.COMPLETED or event.event_type != "tool.completed"),
    )


def continue_provider(*, continuation: ProviderToolContinuation, sender: Callable[[ProviderToolContinuation], Any]) -> Any:
    """Send only an existing receipt-backed continuation to a provider adapter."""
    if not isinstance(continuation, ProviderToolContinuation): raise TypeError("continuation must be ProviderToolContinuation")
    if not callable(sender): raise TypeError("sender must be callable")
    return sender(continuation)
