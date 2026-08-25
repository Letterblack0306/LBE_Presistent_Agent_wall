"""Provisional-to-verified task completion proof over existing memory owners.

This module does not evaluate task completion. Provider/model completion may create
only an UNVERIFIED candidate. The existing deterministic completion gate must
return READY and persist TaskStatus.COMPLETED before the same claim can be
promoted to VERIFIED memory.
"""
from __future__ import annotations

from ..memory import (
    CandidateClaim,
    MemoryRecord,
    MemoryType,
    SourceType,
    TaskStatus,
    ValidationStatus,
)
from ..session_memory_runtime import SessionMemoryRuntimeBridge
from .completion_gate import CompletionDecision, CompletionVerdict


class CompletionProofPromotion:
    """Project completion truth through the existing MemoryPromoter owner."""

    def __init__(self, *, runtime: SessionMemoryRuntimeBridge) -> None:
        if not isinstance(runtime, SessionMemoryRuntimeBridge):
            raise TypeError("runtime must be SessionMemoryRuntimeBridge")
        self._runtime = runtime

    @staticmethod
    def _subject(task_id: str) -> str:
        clean = str(task_id).strip()
        if not clean:
            raise ValueError("task_id must not be empty")
        return f"task-completion:{clean}"

    def record_provisional(
        self,
        *,
        task_id: str,
        operation_id: str,
        provider_outcome: str,
    ) -> MemoryRecord:
        clean_operation = str(operation_id).strip()
        if not clean_operation:
            raise ValueError("operation_id must not be empty")
        if provider_outcome != "COMPLETED":
            raise ValueError("only provider COMPLETED may create provisional completion proof")
        return self._runtime.promoter.promote(
            CandidateClaim(
                project_workspace_id=self._runtime.project_workspace_id,
                canonical_workspace_root=str(self._runtime.workspace_root),
                task_id=task_id,
                memory_type=MemoryType.VALIDATION_RESULT,
                subject=self._subject(task_id),
                predicate="task_complete",
                value={
                    "proof_state": "TEMP",
                    "operation_id": clean_operation,
                    "provider_outcome": provider_outcome,
                    "lbe_completion_verdict": None,
                    "evidence_ids": [],
                },
                source_type=SourceType.COMMAND_RESULT,
                authority=5,
                validated=False,
            )
        )

    def promote_ready(
        self,
        *,
        task_id: str,
        operation_id: str,
        decision: CompletionDecision,
    ) -> MemoryRecord:
        if not isinstance(decision, CompletionDecision):
            raise TypeError("decision must be CompletionDecision")
        if decision.verdict is not CompletionVerdict.READY:
            raise ValueError("only READY completion may be promoted to verified memory")
        state = self._runtime.load_task_status(task_id=task_id)
        if state is None or state.status is not TaskStatus.COMPLETED:
            raise ValueError("task must be persisted COMPLETED before completion proof promotion")
        clean_operation = str(operation_id).strip()
        if not clean_operation:
            raise ValueError("operation_id must not be empty")
        return self._runtime.promoter.promote(
            CandidateClaim(
                project_workspace_id=self._runtime.project_workspace_id,
                canonical_workspace_root=str(self._runtime.workspace_root),
                task_id=task_id,
                memory_type=MemoryType.VALIDATION_RESULT,
                subject=self._subject(task_id),
                predicate="task_complete",
                value={
                    "proof_state": "VERIFIED",
                    "operation_id": clean_operation,
                    "provider_outcome": "COMPLETED",
                    "lbe_completion_verdict": decision.verdict.value,
                    "evidence_ids": list(decision.evidence_ids),
                    "satisfied_requirement_ids": list(decision.satisfied_requirement_ids),
                },
                source_type=SourceType.COMMAND_RESULT,
                authority=10,
                validation_method="lbe-deterministic-completion-gate",
                validated=True,
            )
        )

    def load(self, *, task_id: str) -> MemoryRecord | None:
        subject = self._subject(task_id)
        records = self._runtime.store.query(
            project_workspace_id=self._runtime.project_workspace_id,
            statuses=(ValidationStatus.VERIFIED, ValidationStatus.UNVERIFIED),
            task_id=str(task_id).strip(),
            memory_types=(MemoryType.VALIDATION_RESULT,),
            limit=200,
        )
        for record in records:
            if (
                record.subject == subject
                and record.predicate == "task_complete"
                and record.source_type is SourceType.COMMAND_RESULT
            ):
                return record
        return None
