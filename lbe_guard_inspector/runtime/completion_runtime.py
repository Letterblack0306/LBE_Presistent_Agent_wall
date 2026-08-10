"""Coding completion coordinator for R6F.

SessionMemoryRuntimeBridge remains the canonical persistence owner. This layer
only ensures that coding reasoning success is provisional until the R6F gate
validates the task completion contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..memory import TaskState, TaskStatus
from ..reasoning_contracts import LBEResponse
from ..session_memory_runtime import ReasoningController, SessionMemoryRuntimeBridge
from .completion_gate import (
    CompletionDecision,
    CompletionEvidence,
    CompletionVerdict,
    TaskCompletionContract,
    evaluate_completion,
)


@dataclass(frozen=True)
class CodingReasoningResult:
    response: LBEResponse
    task_state: TaskState


class CodingCompletionRuntime:
    """Compose the existing runtime bridge with deterministic completion proof."""

    def __init__(self, *, runtime: SessionMemoryRuntimeBridge) -> None:
        if not isinstance(runtime, SessionMemoryRuntimeBridge):
            raise TypeError("runtime must be SessionMemoryRuntimeBridge")
        self._runtime = runtime

    def run_reasoning(
        self,
        *,
        controller: ReasoningController,
        problem: str,
        task_id: str,
        reference_context: tuple[Mapping[str, object], ...] = (),
        max_results: int = 10,
    ) -> CodingReasoningResult:
        response = self._runtime.run_reasoning(
            controller=controller,
            problem=problem,
            task_id=task_id,
            reference_context=reference_context,
            max_results=max_results,
        )
        if response.outcome == "COMPLETED":
            state = self._runtime.record_task_status(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                last_outcome="AWAITING_VALIDATION",
            )
        else:
            state = self._runtime.load_task_status(task_id=task_id)
            if state is None:
                raise RuntimeError("reasoning outcome did not persist task state")
        return CodingReasoningResult(response=response, task_state=state)

    def finalize(
        self,
        *,
        task_id: str,
        contract: TaskCompletionContract,
        evidence: Sequence[CompletionEvidence],
        claimed_complete: bool = True,
    ) -> tuple[CompletionDecision, TaskState]:
        decision = evaluate_completion(
            contract=contract,
            evidence=evidence,
            claimed_complete=claimed_complete,
        )
        if decision.verdict is CompletionVerdict.READY:
            status = TaskStatus.COMPLETED
            outcome = "VALIDATED_COMPLETION"
        elif decision.verdict is CompletionVerdict.FAILED:
            status = TaskStatus.FAILED
            outcome = "VALIDATION_FAILED"
        else:
            status = TaskStatus.BLOCKED
            outcome = "VALIDATION_INCOMPLETE"
        state = self._runtime.record_task_status(
            task_id=task_id,
            status=status,
            last_outcome=outcome,
        )
        return decision, state
