"""Persist professional model/tool activity into authoritative P4 history.

This module observes the existing professional continuation runtime. It does not
own provider transport, authorization, or tool execution. All records are
written through ``SessionOperationalHistory`` into the same SQLite database that
already owns session/workspace state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .memory.operational_history import (
    ItemStatus,
    OperationalEvent,
    OperationalHistoryError,
    OperationalTurn,
    SessionOperationalHistory,
    TurnStatus,
)
from .professional_continuation_runtime import (
    ProfessionalGovernedTurnResult,
    execute_governed_professional_turn,
)
from .professional_provider_events import ModelEventType, NormalizedModelEvent, ProviderTurnRequest
from .professional_session_provider import ProfessionalSessionProvider
from .runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolReceipt,
    ToolReceiptStatus,
)


_MODEL_TERMINALS = frozenset(
    {
        ModelEventType.TURN_REQUIRES_TOOL,
        ModelEventType.TURN_REQUIRES_CONTINUATION,
        ModelEventType.TURN_COMPLETED,
        ModelEventType.TURN_INCOMPLETE,
        ModelEventType.TURN_REFUSED,
        ModelEventType.CANCELLED,
        ModelEventType.ERROR,
    }
)


@dataclass(frozen=True)
class PersistedProfessionalTurnResult:
    runtime_result: ProfessionalGovernedTurnResult
    operational_turn: OperationalTurn
    replayed_status: TurnStatus


class ProfessionalTurnHistoryRecorder:
    """Translate validated runtime observations into ordered P4 items/events."""

    def __init__(self, *, history: SessionOperationalHistory, session_id: str) -> None:
        if not isinstance(history, SessionOperationalHistory):
            raise TypeError("history must be SessionOperationalHistory")
        self.history = history
        self.turn = history.start_turn(session_id=session_id)
        self._model_item_id: str | None = None
        self._tool_items: dict[str, str] = {}

    @property
    def turn_id(self) -> str:
        return self.turn.turn_id

    def observe_model_event(self, event: NormalizedModelEvent) -> None:
        if not isinstance(event, NormalizedModelEvent):
            raise TypeError("event must be NormalizedModelEvent")
        if event.event_type is ModelEventType.TURN_STARTED:
            if self._model_item_id is not None:
                raise OperationalHistoryError("cannot start a new model exchange before the prior model item finalized")
            item = self.history.start_item(turn_id=self.turn_id, kind="model.exchange")
            self._model_item_id = item.item_id
        if self._model_item_id is None:
            raise OperationalHistoryError("model event observed without an active model exchange item")

        metadata = dict(event.metadata)
        provider_state_ref = _optional_text(metadata.get("provider_state_metadata_ref"))
        raw_diagnostic_ref = _optional_text(metadata.get("raw_diagnostic_ref"))
        self.history.append_event(OperationalEvent(
            session_id=self.turn.session_id,
            turn_id=self.turn_id,
            item_id=self._model_item_id,
            event_type=event.event_type.value,
            payload=_model_payload(event),
            provider_id=event.provider_id,
            model_id=event.model_id,
            provider_request_id=event.provider_request_id,
            provider_item_id=event.provider_item_id,
            provider_tool_call_id=event.provider_tool_call_id,
            lbe_call_id=event.lbe_call_id,
            provider_state_metadata_ref=provider_state_ref,
            raw_diagnostic_ref=raw_diagnostic_ref,
        ))

        if event.event_type in _MODEL_TERMINALS:
            status = ItemStatus.CANCELLED if event.event_type is ModelEventType.CANCELLED else (
                ItemStatus.FAILED if event.event_type is ModelEventType.ERROR else ItemStatus.COMPLETED
            )
            self.history.finalize_item(item_id=self._model_item_id, status=status)
            self._model_item_id = None

    def observe_tool_started(self, proposal: NormalizedModelEvent, operation_id: str) -> None:
        if not proposal.lbe_call_id:
            raise OperationalHistoryError("tool proposal lacks lbe_call_id")
        if proposal.lbe_call_id in self._tool_items:
            raise OperationalHistoryError("duplicate tool start for lbe_call_id")
        item = self.history.start_item(turn_id=self.turn_id, kind="tool.execution")
        self._tool_items[proposal.lbe_call_id] = item.item_id
        self.history.append_event(OperationalEvent(
            session_id=self.turn.session_id,
            turn_id=self.turn_id,
            item_id=item.item_id,
            event_type="tool.started",
            payload={
                "tool_name": proposal.tool_name,
                "arguments": dict(proposal.tool_arguments or {}),
            },
            provider_id=proposal.provider_id,
            model_id=proposal.model_id,
            provider_request_id=proposal.provider_request_id,
            provider_item_id=proposal.provider_item_id,
            provider_tool_call_id=proposal.provider_tool_call_id,
            lbe_call_id=proposal.lbe_call_id,
            runtime_operation_id=operation_id,
        ))

    def observe_tool_receipt(self, proposal: NormalizedModelEvent, receipt: ToolReceipt) -> None:
        if not proposal.lbe_call_id:
            raise OperationalHistoryError("tool proposal lacks lbe_call_id")
        item_id = self._tool_items.pop(proposal.lbe_call_id, None)
        if item_id is None:
            raise OperationalHistoryError("tool receipt observed without matching tool start")
        event_type, item_status = _tool_terminal(receipt.status)
        self.history.append_event(OperationalEvent(
            session_id=self.turn.session_id,
            turn_id=self.turn_id,
            item_id=item_id,
            event_type=event_type,
            payload={
                "tool_name": receipt.tool_id,
                "status": receipt.status.value,
                "output": dict(receipt.output or {}),
                "evidence": [dict(item) for item in receipt.evidence],
                "error_code": receipt.error_code,
                "error_message": receipt.error_message,
            },
            provider_id=proposal.provider_id,
            model_id=proposal.model_id,
            provider_request_id=proposal.provider_request_id,
            provider_item_id=proposal.provider_item_id,
            provider_tool_call_id=proposal.provider_tool_call_id,
            lbe_call_id=proposal.lbe_call_id,
            runtime_operation_id=receipt.operation_id,
            tool_receipt_id=receipt.receipt_id,
        ))
        self.history.finalize_item(item_id=item_id, status=item_status)

    def finalize(self, result: ProfessionalGovernedTurnResult) -> OperationalTurn:
        if self._model_item_id is not None or self._tool_items:
            raise OperationalHistoryError("cannot finalize professional turn with in-flight observed items")
        status = _runtime_turn_status(result)
        self.turn = self.history.finalize_turn(turn_id=self.turn_id, status=status)
        return self.turn


def execute_persisted_governed_professional_turn(
    *,
    history: SessionOperationalHistory,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
    orchestrator: GovernedToolOrchestrator,
    tool_context: ToolExecutionContext,
    max_tool_hops: int = 8,
    operation_id_factory=None,
) -> PersistedProfessionalTurnResult:
    """Execute the existing governed loop while persisting its validated events."""
    recorder = ProfessionalTurnHistoryRecorder(
        history=history,
        session_id=session_provider.session_id,
    )
    result = execute_governed_professional_turn(
        session_provider=session_provider,
        request=request,
        orchestrator=orchestrator,
        tool_context=tool_context,
        max_tool_hops=max_tool_hops,
        operation_id_factory=operation_id_factory,
        model_event_observer=recorder.observe_model_event,
        tool_started_observer=recorder.observe_tool_started,
        tool_receipt_observer=recorder.observe_tool_receipt,
    )
    operational_turn = recorder.finalize(result)
    replayed = replay_turn_status(history=history, turn_id=operational_turn.turn_id)
    if replayed is not operational_turn.status:
        raise OperationalHistoryError(
            f"replayed turn status {replayed.value} does not match finalized status {operational_turn.status.value}"
        )
    return PersistedProfessionalTurnResult(
        runtime_result=result,
        operational_turn=operational_turn,
        replayed_status=replayed,
    )


def replay_turn_status(*, history: SessionOperationalHistory, turn_id: str) -> TurnStatus:
    """Derive the final turn outcome from append-only events, not turn-row status."""
    events = history.events_for_turn(turn_id=turn_id)
    if not events:
        raise OperationalHistoryError("cannot replay turn status without events")
    for event in reversed(events):
        if event.event_type == "tool.escalated":
            return TurnStatus.ESCALATED
        mapping = {
            ModelEventType.TURN_COMPLETED.value: TurnStatus.COMPLETED,
            ModelEventType.TURN_INCOMPLETE.value: TurnStatus.INCOMPLETE,
            ModelEventType.TURN_REFUSED.value: TurnStatus.REFUSED,
            ModelEventType.CANCELLED.value: TurnStatus.CANCELLED,
            ModelEventType.ERROR.value: TurnStatus.FAILED,
        }
        if event.event_type in mapping:
            return mapping[event.event_type]
    raise OperationalHistoryError("operational events do not contain a replayable final turn outcome")


def _model_payload(event: NormalizedModelEvent) -> dict[str, Any]:
    return {
        "protocol_family": event.protocol_family.value,
        "text": event.text,
        "tool_name": event.tool_name,
        "tool_arguments": dict(event.tool_arguments or {}),
        "usage": dict(event.usage or {}),
        "error_code": event.error_code,
        "metadata": dict(event.metadata),
    }


def _tool_terminal(status: ToolReceiptStatus) -> tuple[str, ItemStatus]:
    mapping = {
        ToolReceiptStatus.EXECUTED: ("tool.completed", ItemStatus.COMPLETED),
        ToolReceiptStatus.DENIED: ("tool.denied", ItemStatus.DENIED),
        ToolReceiptStatus.ESCALATED: ("tool.escalated", ItemStatus.ESCALATED),
        ToolReceiptStatus.FAILED: ("tool.failed", ItemStatus.FAILED),
    }
    return mapping[status]


def _runtime_turn_status(result: ProfessionalGovernedTurnResult) -> TurnStatus:
    if result.blocked_receipt is not None:
        if result.blocked_receipt.status is not ToolReceiptStatus.ESCALATED:
            raise OperationalHistoryError("blocked professional turn must carry an escalated receipt")
        return TurnStatus.ESCALATED
    terminal = result.final_turn.terminal_event.event_type
    mapping = {
        ModelEventType.TURN_COMPLETED: TurnStatus.COMPLETED,
        ModelEventType.TURN_INCOMPLETE: TurnStatus.INCOMPLETE,
        ModelEventType.TURN_REFUSED: TurnStatus.REFUSED,
        ModelEventType.CANCELLED: TurnStatus.CANCELLED,
        ModelEventType.ERROR: TurnStatus.FAILED,
    }
    try:
        return mapping[terminal]
    except KeyError as exc:
        raise OperationalHistoryError(
            f"professional runtime ended without a finalizable turn outcome: {terminal.value}"
        ) from exc


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
