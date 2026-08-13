"""Completion-gated composition for the persistent professional provider loop.

Provider completion is a claim, not task authority. This module composes the
already-persisted governed provider turn with CodingCompletionRuntime, which
remains the canonical deterministic completion owner. It introduces no new
validation policy, evidence store, task status model, or tool authority.
"""
from __future__ import annotations

from dataclasses import dataclass

from .memory import TaskState
from .memory.operational_history import SessionOperationalHistory
from .professional_history_runtime import (
    PersistedProfessionalTurnResult,
    execute_persisted_governed_professional_turn,
)
from .professional_provider_events import ModelEventType, ProviderTurnRequest
from .professional_session_provider import ProfessionalSessionProvider
from .runtime.completion_gate import CompletionDecision, TaskCompletionContract
from .runtime.completion_runtime import CodingCompletionRuntime
from .runtime.tool_orchestration import GovernedToolOrchestrator, ToolExecutionContext


class ProfessionalCompletionRuntimeError(RuntimeError):
    """Raised when deterministic completion prerequisites are unavailable."""


@dataclass(frozen=True)
class CompletionGatedProfessionalTurnResult:
    persisted_turn: PersistedProfessionalTurnResult
    completion_contract: TaskCompletionContract
    completion_decision: CompletionDecision | None
    task_state: TaskState | None

    @property
    def validated_complete(self) -> bool:
        return self.completion_decision is not None and self.completion_decision.ready


def execute_completion_gated_persisted_professional_turn(
    *,
    history: SessionOperationalHistory,
    session_provider: ProfessionalSessionProvider,
    request: ProviderTurnRequest,
    orchestrator: GovernedToolOrchestrator,
    tool_context: ToolExecutionContext,
    completion_runtime: CodingCompletionRuntime,
    task_id: str,
    max_tool_hops: int = 8,
    operation_id_factory=None,
) -> CompletionGatedProfessionalTurnResult:
    """Execute one persistent professional turn and gate model completion.

    A persisted LBE completion contract is required before execution so a later
    provider completion claim can never bypass deterministic task completion.
    Only ``model.turn.completed`` is treated as ``claimed_complete=True``.
    Escalated, incomplete, refused, cancelled, and error terminals retain their
    existing professional runtime meaning and do not invoke completion promotion.
    """
    if not isinstance(completion_runtime, CodingCompletionRuntime):
        raise TypeError("completion_runtime must be CodingCompletionRuntime")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("task_id must be a non-empty string")
    task_id = task_id.strip()

    contract = completion_runtime.load_contract(task_id=task_id)
    if contract is None:
        raise ProfessionalCompletionRuntimeError(
            "professional completion requires a persisted LBE task completion contract"
        )

    persisted = execute_persisted_governed_professional_turn(
        history=history,
        session_provider=session_provider,
        request=request,
        orchestrator=orchestrator,
        tool_context=tool_context,
        max_tool_hops=max_tool_hops,
        operation_id_factory=operation_id_factory,
    )

    runtime_result = persisted.runtime_result
    if runtime_result.blocked_receipt is not None:
        return CompletionGatedProfessionalTurnResult(
            persisted_turn=persisted,
            completion_contract=contract,
            completion_decision=None,
            task_state=None,
        )

    terminal_type = runtime_result.final_turn.terminal_event.event_type
    if terminal_type is not ModelEventType.TURN_COMPLETED:
        return CompletionGatedProfessionalTurnResult(
            persisted_turn=persisted,
            completion_contract=contract,
            completion_decision=None,
            task_state=None,
        )

    evidence = completion_runtime.load_evidence(task_id=task_id)
    decision, state = completion_runtime.finalize(
        task_id=task_id,
        contract=contract,
        evidence=evidence,
        claimed_complete=True,
    )
    return CompletionGatedProfessionalTurnResult(
        persisted_turn=persisted,
        completion_contract=contract,
        completion_decision=decision,
        task_state=state,
    )
