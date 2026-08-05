"""Deterministic adjudication of model-proposed guard candidates.

This module does not decide guard truth. It decides whether a proposed guard is
registered, uniquely selected, and sufficiently evidenced to be executable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .reasoning_planner import EvidencePlan


@dataclass(frozen=True)
class GuardCandidate:
    guard_id: str
    reason: str
    evidence_plan: EvidencePlan


@dataclass(frozen=True)
class GuardSelection:
    selected_guard_id: str | None
    rejected_guard_ids: tuple[str, ...]
    stop_reason: str | None

    @property
    def executable(self) -> bool:
        return self.selected_guard_id is not None and self.stop_reason is None


class GuardPlanner:
    """Adjudicate bounded guard candidates without producing a verdict."""

    def select(
        self,
        *,
        candidates: Sequence[GuardCandidate],
        approved_guard_ids: Sequence[str],
        workspace_profile: Mapping[str, object] | None = None,
    ) -> GuardSelection:
        approved = set(approved_guard_ids)
        rejected = tuple(dict.fromkeys(
            candidate.guard_id for candidate in candidates if candidate.guard_id not in approved
        ))
        eligible = [
            candidate
            for candidate in candidates
            if candidate.guard_id in approved and candidate.evidence_plan.complete
        ]

        if rejected:
            return GuardSelection(
                selected_guard_id=None,
                rejected_guard_ids=rejected,
                stop_reason="UNKNOWN_GUARD",
            )
        if not candidates:
            return GuardSelection(None, (), "NO_GUARD_SELECTED")
        if not eligible:
            return GuardSelection(None, (), "INSUFFICIENT_EVIDENCE")

        profile_guards = _profile_guard_ids(workspace_profile or {})
        profile_eligible = [candidate for candidate in eligible if candidate.guard_id in profile_guards]
        pool = profile_eligible or eligible
        unique_ids = tuple(dict.fromkeys(candidate.guard_id for candidate in pool))
        if len(unique_ids) != 1:
            return GuardSelection(None, (), "AMBIGUOUS_GUARD_SELECTION")
        return GuardSelection(unique_ids[0], (), None)


def _profile_guard_ids(profile: Mapping[str, object]) -> set[str]:
    values = profile.get("enabled_guard_ids", ())
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return set()
    return {value for value in values if isinstance(value, str) and value.strip()}
