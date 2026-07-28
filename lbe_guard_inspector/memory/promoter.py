from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import (
    MemoryRecord,
    MemoryType,
    SourceType,
    ValidationStatus,
)
from .store import WorkspaceMemoryStore


@dataclass(slots=True, frozen=True)
class CandidateClaim:
    subject: str
    predicate: str
    value: Any
    memory_type: MemoryType
    source_type: SourceType
    project_workspace_id: str
    canonical_workspace_root: str
    task_id: str | None = None
    rule_id: str | None = None
    source_path: str | None = None
    source_hash: str | None = None
    source_commit: str | None = None
    source_message_id: str | None = None
    authority: int = 0
    validation_method: str | None = None
    validated: bool = False


_DETERMINISTIC_PREDICATES = {
    "canonical_workspace_root",
    "git_branch",
    "git_head",
    "file_sha256",
    "test_exit_code",
    "command_exit_code",
    "changed_files",
    "validated_configuration_value",
}

_INTERPRETIVE_PREDICATES = {
    "is_broken",
    "feature_implemented",
    "task_complete",
    "requirement_proven",
    "repository_clean",
    "rule_passes",
    "defect_fixed",
}


class MemoryPromoter:
    """Promote only claims supported by deterministic or explicit validation evidence."""

    def __init__(self, store: WorkspaceMemoryStore) -> None:
        self.store = store

    def promote(self, claim: CandidateClaim) -> MemoryRecord:
        status, confidence, method = self._classify(claim)
        record = MemoryRecord(
            project_workspace_id=claim.project_workspace_id,
            canonical_workspace_root=claim.canonical_workspace_root,
            task_id=claim.task_id,
            rule_id=claim.rule_id,
            memory_type=claim.memory_type,
            subject=claim.subject,
            predicate=claim.predicate,
            value=claim.value,
            source_type=claim.source_type,
            source_path=claim.source_path,
            source_hash=claim.source_hash,
            source_commit=claim.source_commit,
            source_message_id=claim.source_message_id,
            authority=claim.authority,
            validation_status=status,
            validation_method=method,
            confidence=confidence,
        )
        return self.store.upsert(record)

    @staticmethod
    def _classify(
        claim: CandidateClaim,
    ) -> tuple[ValidationStatus, float, str | None]:
        if claim.source_type in {
            SourceType.ASSISTANT_REASONING,
            SourceType.COMPACTION,
        }:
            return ValidationStatus.UNVERIFIED, 0.2, None

        if claim.validated:
            if not claim.validation_method:
                raise ValueError("validated claim requires validation_method")
            return ValidationStatus.VERIFIED, 1.0, claim.validation_method

        if claim.predicate in _DETERMINISTIC_PREDICATES and claim.source_type in {
            SourceType.LIVE_WORKSPACE,
            SourceType.GIT,
            SourceType.TEST_RUN,
            SourceType.COMMAND_RESULT,
        }:
            method = claim.validation_method or f"trusted:{claim.source_type.value}"
            return ValidationStatus.VERIFIED, 1.0, method

        if claim.predicate in _INTERPRETIVE_PREDICATES:
            return ValidationStatus.UNVERIFIED, 0.2, None

        if claim.source_type is SourceType.USER_INSTRUCTION:
            return ValidationStatus.UNVERIFIED, 0.8, None

        return ValidationStatus.UNVERIFIED, 0.5, None
