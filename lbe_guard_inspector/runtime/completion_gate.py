"""Deterministic completion validation for R6F.

This module evaluates already-produced structured evidence against an explicit
completion contract. It does not run tools, tests, guards, provider calls, or
own persistent task state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Sequence


class CompletionEvidenceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    STALE = "STALE"


class CompletionVerdict(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CompletionRequirement:
    requirement_id: str
    evidence_kind: str
    description: str = ""

    def __post_init__(self) -> None:
        for name in ("requirement_id", "evidence_kind"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class CompletionEvidence:
    evidence_id: str
    kind: str
    status: CompletionEvidenceStatus
    source: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("evidence_id", "kind", "source"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.status, CompletionEvidenceStatus):
            raise TypeError("status must be CompletionEvidenceStatus")
        if not isinstance(self.details, Mapping):
            raise TypeError("details must be a mapping")
        object.__setattr__(self, "details", dict(self.details))


@dataclass(frozen=True)
class TaskCompletionContract:
    requirements: tuple[CompletionRequirement, ...]

    def __post_init__(self) -> None:
        if not self.requirements:
            raise ValueError("completion contract requires at least one requirement")
        ids = [item.requirement_id for item in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("completion requirement IDs must be unique")


@dataclass(frozen=True)
class CompletionDecision:
    verdict: CompletionVerdict
    claimed_complete: bool
    satisfied_requirement_ids: tuple[str, ...]
    missing_requirement_ids: tuple[str, ...]
    failed_requirement_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    rationale: str

    @property
    def ready(self) -> bool:
        return self.verdict is CompletionVerdict.READY


def evaluate_completion(
    *,
    contract: TaskCompletionContract,
    evidence: Sequence[CompletionEvidence],
    claimed_complete: bool,
) -> CompletionDecision:
    """Evaluate completion from structured evidence, never model prose alone."""
    if not isinstance(contract, TaskCompletionContract):
        raise TypeError("contract must be TaskCompletionContract")
    if not isinstance(claimed_complete, bool):
        raise TypeError("claimed_complete must be bool")
    items = tuple(evidence)
    if not all(isinstance(item, CompletionEvidence) for item in items):
        raise TypeError("evidence entries must be CompletionEvidence")

    satisfied: list[str] = []
    missing: list[str] = []
    failed: list[str] = []
    used_evidence: list[str] = []

    for requirement in contract.requirements:
        matches = [item for item in items if item.kind == requirement.evidence_kind]
        passing = [item for item in matches if item.status is CompletionEvidenceStatus.PASS]
        if passing:
            satisfied.append(requirement.requirement_id)
            used_evidence.extend(item.evidence_id for item in passing)
            continue
        if any(item.status is CompletionEvidenceStatus.FAIL for item in matches):
            failed.append(requirement.requirement_id)
            used_evidence.extend(item.evidence_id for item in matches)
            continue
        missing.append(requirement.requirement_id)
        used_evidence.extend(item.evidence_id for item in matches)

    if failed:
        verdict = CompletionVerdict.FAILED
        rationale = "Required completion evidence contains a deterministic failure."
    elif missing:
        verdict = CompletionVerdict.BLOCKED
        rationale = "Required completion evidence is missing or stale."
    elif not claimed_complete:
        verdict = CompletionVerdict.BLOCKED
        rationale = "Required evidence passes, but completion has not been requested."
    else:
        verdict = CompletionVerdict.READY
        rationale = "All required completion evidence passes."

    return CompletionDecision(
        verdict=verdict,
        claimed_complete=claimed_complete,
        satisfied_requirement_ids=tuple(satisfied),
        missing_requirement_ids=tuple(missing),
        failed_requirement_ids=tuple(failed),
        evidence_ids=tuple(dict.fromkeys(used_evidence)),
        rationale=rationale,
    )
