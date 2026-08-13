"""Governed provider continuation loop.

This is the boundary that connects a professional model tool proposal to LBE's
existing governed tool orchestrator. The provider never receives the
orchestrator, workspace context, authorization resolver, or handler registry.
Only a receipt-backed ProviderToolResultContinuation crosses back to provider
transport after LBE has produced the tool result.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from .professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderToolResultContinuation,
    ProviderTurnRequest,
)
from .professional_session_provider import ProfessionalSessionProvider
from .professional_turn_runtime import (
    ModelEventObserver,
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


class ProfessionalUnsupportedCapabilityError(ProfessionalContinuationRuntimeError):
    """Raised before provider execution when a projected capability has no backend."""

    def __init__(self, capability_id: str, message: str) -> None:
        self.capability_id = str(capability_id).strip()
        super().__init__(message)


class ProfessionalLoopStopReason(StrEnum):
    """Why the governed provider loop stopped at its current boundary.

    This is a runtime decision projection, not a provider event replacement and
    not a client-control protocol. P8 may later act on interrupt/cancel/steering
    controls, while this P7 type truthfully classifies the outcome already
    observed from the provider/tool loop.
    """

    TERMINAL_COMPLETION = "terminal_completion"
    PROVIDER_CONTINUATION_REQUIRED = "provider_continuation_required"
    APPROVAL_ESCALATION_REQUIRED = "approval_escalation_required"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    CREDENTIAL_MANUAL_BLOCKER = "credential_manual_blocker"
    TERMINAL_INCOMPLETE = "terminal_incomplete"
    TERMINAL_REFUSAL = "terminal_refusal"
    CANCELLED = "cancelled"
    ERROR = "error"


_MANUAL_BLOCKER_CODES = frozenset({"CREDENTIAL_REQUIRED", "MANUAL_ACTION_REQUIRED"})


OperationIdFactory = Callable[[], str]
ToolStartedObserver = Callable[[NormalizedModelEvent, str], None]
ToolReceiptObserver = Callable[[NormalizedModelEvent, ToolReceipt], None]


@dataclass(frozen=True)
class ProfessionalGovernedTurnResult:
    exchanges: tuple[ProfessionalTurnResult, ...]
    tool_receipts: tuple[ToolReceipt, ...]
    final_turn: ProfessionalTurnResult
    blocked_receipt: ToolReceipt | None = None
    unsupported_capability: str | None = None

    @property
    def stop_reason(self) -> ProfessionalLoopStopReason:
        if self.unsupported_capability is not None:
            return ProfessionalLoopStopReason.UNSUPPORTED_CAPABILITY
        if self.blocked_receipt is not None:
            if self.blocked_receipt.status is not ToolReceiptStatus.ESCALATED:
                raise ProfessionalContinuationRuntimeError(
                    "blocked professional turn must carry an escalated receipt"
                )
            if _is_manual_blocker_code(self.blocked_receipt.error_code):
                return ProfessionalLoopStopReason.CREDENTIAL_MANUAL_BLOCKER
            return ProfessionalLoopStopReason.APPROVAL_ESCALATION_REQUIRED
        terminal_event = self.final_turn.terminal_event
        terminal = terminal_event.event_type
        if terminal is ModelEventType.ERROR and _is_manual_blocker_code(terminal_event.error_code):
            return ProfessionalLoopStopReason.CREDENTIAL_MANUAL_BLOCKER
        mapping = {
            ModelEventType.TURN_COMPLETED: ProfessionalLoopStopReason.TERMINAL_COMPLETION,
            ModelEventType.TURN_REQUIRES_CONTINUATION: ProfessionalLoopStopReason.PROVIDER_CONTINUATION_REQUIRED,
            ModelEventType.TURN_INCOMPLETE: ProfessionalLoopStopReason.TERMINAL_INCOMPLETE,
            ModelEventType.TURN_REFUSED: ProfessionalLoopStopReason.TERMINAL_REFUSAL,
            ModelEventType.CANCELLED: ProfessionalLoopStopReason.CANCELLED,
            ModelEventType.ERROR: ProfessionalLoopStopReason.ERROR,
        }
        try:
            return mapping[terminal]
        except KeyError as exc:
            raise ProfessionalContinuationRuntimeError(
                f"professional loop stopped on unsupported terminal state: {terminal.value}"
            ) from exc

    @property
    def completed_without_blocker(self) -> bool:
        return self.stop_reason is ProfessionalLoopStopReason.TERMINAL_COMPLETION


def execute_governed_professional_turn(
    *,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
    orchestrator: GovernedToolOrchestrator,
    tool_context: ToolExecutionContext,
    max_tool_hops: int = 8,
    operation_id_factory: OperationIdFactory | None = None,
    model_event_observer: ModelEventObserver | None = None,
    tool_started_observer: ToolStartedObserver | None = None,
    tool_receipt_observer: ToolReceiptObserver | None = None,
) -> ProfessionalGovernedTurnResult:
    """Run provider -> governed tool -> provider continuation until a stop boundary.

    The provider request is first checked against the live runtime registry so
    only actually-backed tools may be projected to the model. A provider-emitted
    proposal must also name one of those explicit request projections before it
    can reach R6C authorization.

    ESCALATED receipts stop the loop and remain outward blockers. EXECUTED,
    DENIED, and ordinary FAILED receipts are returned to the provider as truthful
    tool results/errors so the model may continue without being granted authority.

    ``model.turn.requires_continuation`` is intentionally returned as a distinct
    stop reason. The current adapter contract proves client-tool continuation,
    but does not yet prove one universal provider/server continuation primitive;
    P7 therefore must not fabricate one from tool-result semantics.

    Unsupported provider tool proposals stop before authorization/execution and
    do not manufacture a ToolReceipt. Explicit provider credential/manual errors
    remain distinct stop reasons rather than being reported as generic failure.

    Observer hooks expose already-normalized model events and governed tool
    lifecycle evidence without transferring authorization or execution authority.
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
    for name, observer in (
        ("model_event_observer", model_event_observer),
        ("tool_started_observer", tool_started_observer),
        ("tool_receipt_observer", tool_receipt_observer),
    ):
        if observer is not None and not callable(observer):
            raise TypeError(f"{name} must be callable")

    projected_tools = validate_provider_tool_projection(request=request, orchestrator=orchestrator)

    make_operation_id = operation_id_factory or (lambda: f"runtime-op-{uuid.uuid4().hex}")
    if not callable(make_operation_id):
        raise TypeError("operation_id_factory must be callable")

    turn = execute_professional_turn(
        session_provider=session_provider,
        request=request,
        event_observer=model_event_observer,
    )
    exchanges = [turn]
    receipts: list[ToolReceipt] = []
    hops = 0

    while turn.requires_tool:
        if hops >= max_tool_hops:
            raise ProfessionalContinuationRuntimeError("professional tool continuation exceeded max_tool_hops")

        proposal = _find_terminal_tool_proposal(turn)
        if proposal.tool_name not in projected_tools:
            return ProfessionalGovernedTurnResult(
                exchanges=tuple(exchanges),
                tool_receipts=tuple(receipts),
                final_turn=turn,
                unsupported_capability=proposal.tool_name,
            )
        operation_id = make_operation_id()
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ProfessionalContinuationRuntimeError("operation_id_factory returned an empty operation id")
        operation_id = operation_id.strip()
        if operation_id == proposal.lbe_call_id:
            raise ProfessionalContinuationRuntimeError("runtime operation identity must remain distinct from lbe_call_id")

        if tool_started_observer is not None:
            tool_started_observer(proposal, operation_id)
        receipt = orchestrator.invoke(ToolRequest(
            operation_id=operation_id,
            tool_id=proposal.tool_name or "",
            arguments=dict(proposal.tool_arguments or {}),
            context=tool_context,
        ))
        receipts.append(receipt)
        if tool_receipt_observer is not None:
            tool_receipt_observer(proposal, receipt)

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
            event_observer=model_event_observer,
        )
        exchanges.append(turn)
        hops += 1

    return ProfessionalGovernedTurnResult(
        exchanges=tuple(exchanges),
        tool_receipts=tuple(receipts),
        final_turn=turn,
    )


def validate_provider_tool_projection(
    *,
    request: ProviderTurnRequest,
    orchestrator: GovernedToolOrchestrator,
) -> frozenset[str]:
    """Prove every provider-visible tool has a live registered runtime backend.

    This is a projection/availability check only. It does not decide whether the
    current mode/permission/workspace context authorizes an invocation; R6C keeps
    that authority when a projected proposal is actually requested.
    """
    names: list[str] = []
    for definition in request.tool_definitions:
        name = definition.name.strip()
        if name in names:
            raise ProfessionalContinuationRuntimeError(f"duplicate provider tool projection: {name}")
        if orchestrator.registry.get(name) is None:
            raise ProfessionalUnsupportedCapabilityError(
                name,
                f"provider tool projection has no registered runtime backend: {name}",
            )
        names.append(name)
    return frozenset(names)


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


def _is_manual_blocker_code(value: object) -> bool:
    return isinstance(value, str) and value.strip().upper() in _MANUAL_BLOCKER_CODES
