"""Governed provider continuation loop.

This is the first boundary that connects a professional model tool proposal to
LBE's existing governed tool orchestrator. The provider never receives the
orchestrator, workspace context, authorization resolver, or handler registry.
Only a receipt-backed ProviderToolResultContinuation crosses back to provider
transport after LBE has produced the tool result.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable

from .professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderToolResultContinuation,
    ProviderTurnRequest,
)
from .professional_session_provider import ProfessionalSessionProvider
from .professional_turn_runtime import (
    ProfessionalTurnResult,
    execute_professional_continuation,
    execute_professional_turn,
)
from .runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolReceipt,
    ToolReceiptStatus,
    ToolRequest,
)


class ProfessionalContinuationRuntimeError(RuntimeError):
    """Raised when provider/tool correlation cannot be proven safely."""


OperationIdFactory = Callable[[], str]


@dataclass(frozen=True)
class ProfessionalGovernedTurnResult:
    exchanges: tuple[ProfessionalTurnResult, ...]
    tool_receipts: tuple[ToolReceipt, ...]
    final_turn: ProfessionalTurnResult
    blocked_receipt: ToolReceipt | None = None

    @property
    def completed_without_blocker(self) -> bool:
        return self.blocked_receipt is None and not self.final_turn.requires_tool


def execute_governed_professional_turn(
    *,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
    orchestrator: GovernedToolOrchestrator,
    tool_context: ToolExecutionContext,
    max_tool_hops: int = 8,
    operation_id_factory: OperationIdFactory | None = None,
) -> ProfessionalGovernedTurnResult:
    """Run provider → governed tool → provider continuation until terminal.

    ESCALATED receipts stop the loop and remain outward blockers. EXECUTED,
    DENIED, and FAILED receipts are returned to the provider as truthful tool
    results/errors so the model may continue without being granted authority.
    """
    if not isinstance(session_provider, ProfessionalSessionProvider):
        raise TypeError("session_provider must be ProfessionalSessionProvider")
    if not isinstance(request, ProviderTurnRequest):
        raise TypeError("request must be ProviderTurnRequest")
    if not isinstance(orchestrator, GovernedToolOrchestrator):
        raise TypeError("orchestrator must be GovernedToolOrchestrator")
    if not isinstance(tool_context, ToolExecutionContext):
        raise TypeError("tool_context must be ToolExecutionContext")
    if not isinstance(max_tool_hops, int) or isinstance(max_tool_hops, bool) or max_tool_hops < 1:
        raise ValueError("max_tool_hops must be a positive integer")

    make_operation_id = operation_id_factory or (lambda: f"runtime-op-{uuid.uuid4().hex}")
    if not callable(make_operation_id):
        raise TypeError("operation_id_factory must be callable")

    turn = execute_professional_turn(session_provider=session_provider, request=request)
    exchanges = [turn]
    receipts: list[ToolReceipt] = []
    hops = 0

    while turn.requires_tool:
        if hops >= max_tool_hops:
            raise ProfessionalContinuationRuntimeError("professional tool continuation exceeded max_tool_hops")

        proposal = _find_terminal_tool_proposal(turn)
        operation_id = make_operation_id()
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ProfessionalContinuationRuntimeError("operation_id_factory returned an empty operation id")
        operation_id = operation_id.strip()
        if operation_id == proposal.lbe_call_id:
            raise ProfessionalContinuationRuntimeError("runtime operation identity must remain distinct from lbe_call_id")

        receipt = orchestrator.invoke(ToolRequest(
            operation_id=operation_id,
            tool_id=proposal.tool_name or "",
            arguments=dict(proposal.tool_arguments or {}),
            context=tool_context,
        ))
        receipts.append(receipt)

        if receipt.status is ToolReceiptStatus.ESCALATED:
            return ProfessionalGovernedTurnResult(
                exchanges=tuple(exchanges),
                tool_receipts=tuple(receipts),
                final_turn=turn,
                blocked_receipt=receipt,
            )

        continuation = ProviderToolResultContinuation(
            provider_tool_call_id=proposal.provider_tool_call_id or "",
            lbe_call_id=proposal.lbe_call_id or "",
            runtime_operation_id=receipt.operation_id,
            tool_receipt_id=receipt.receipt_id,
            tool_name=receipt.tool_id,
            output=_provider_tool_output(receipt),
            is_error=receipt.status is not ToolReceiptStatus.EXECUTED,
        )
        turn = execute_professional_continuation(
            session_provider=session_provider,
            request=request,
            result=continuation,
        )
        exchanges.append(turn)
        hops += 1

    return ProfessionalGovernedTurnResult(
        exchanges=tuple(exchanges),
        tool_receipts=tuple(receipts),
        final_turn=turn,
    )


def _find_terminal_tool_proposal(turn: ProfessionalTurnResult) -> NormalizedModelEvent:
    terminal = turn.terminal_event
    if terminal.event_type is not ModelEventType.TURN_REQUIRES_TOOL:
        raise ProfessionalContinuationRuntimeError("turn does not require a tool")
    if not terminal.provider_tool_call_id or not terminal.lbe_call_id or not terminal.tool_name:
        raise ProfessionalContinuationRuntimeError("model.turn.requires_tool lacks tool correlation identity")

    matches = tuple(
        event
        for event in turn.events
        if event.event_type is ModelEventType.TOOL_CALL_COMPLETED
        and event.provider_tool_call_id == terminal.provider_tool_call_id
        and event.lbe_call_id == terminal.lbe_call_id
        and event.tool_name == terminal.tool_name
    )
    if len(matches) != 1:
        raise ProfessionalContinuationRuntimeError(
            "model.turn.requires_tool must correlate to exactly one completed tool proposal"
        )
    return matches[0]


def _provider_tool_output(receipt: ToolReceipt) -> object:
    if receipt.status is ToolReceiptStatus.EXECUTED:
        return dict(receipt.output or {})
    return {
        "status": receipt.status.value,
        "error_code": receipt.error_code,
        "error_message": receipt.error_message,
    }
