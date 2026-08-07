"""Bounded reasoning-layer proposal generation for governed workspace rules.

The model may draft a rule candidate. This module bounds that draft, requires
verified current-workspace evidence and explicit deterministic probes, and
delegates the deterministic, read-only proposal construction to the
RuleGatekeeper. It never applies, approves, or writes anything: LBE governance
owns application and mutation authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .rule_gatekeeper import (
    RuleGatekeeper,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_PROPOSAL_READY,
)

_PROPOSAL_FIELDS = (
    "target_profile_path",
    "trigger",
    "rationale",
    "scope",
    "required_action",
    "severity",
    "exceptions",
    "validation_plan",
    "rollback_plan",
)

_FORBIDDEN_PROPOSAL_FIELDS = frozenset({
    "verdict", "pass", "fail", "status", "write", "apply", "approve",
    "decision", "authorize", "authorization", "command", "commit", "execute",
    "repair", "mutation", "policy", "memory_promotion", "promote_memory",
})

_SEVERITY_VALUES = frozenset({"info", "warning", "error", "blocking"})


@dataclass(frozen=True)
class ProposalCandidate:
    """A model-drafted, structurally bounded rule candidate."""

    target_profile_path: str
    trigger: str
    rationale: str
    scope: tuple[str, ...]
    required_action: str
    severity: str
    exceptions: tuple[str, ...]
    validation_plan: tuple[str, ...]
    rollback_plan: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "ProposalCandidate":
        if not isinstance(value, Mapping):
            raise ValueError("proposal candidate must be an object")
        if set(value) & _FORBIDDEN_PROPOSAL_FIELDS:
            raise ValueError("proposal candidate contains forbidden authority fields")
        if set(value) != set(_PROPOSAL_FIELDS):
            raise ValueError("proposal candidate fields are invalid")
        severity = _text(value.get("severity"), "severity")
        if severity not in _SEVERITY_VALUES:
            raise ValueError(f"invalid severity: {severity}")
        return cls(
            target_profile_path=_workspace_relative(value.get("target_profile_path"), "target_profile_path"),
            trigger=_text(value.get("trigger"), "trigger"),
            rationale=_text(value.get("rationale"), "rationale"),
            scope=tuple(_workspace_relative(item, "scope") for item in _list(value.get("scope"), "scope")),
            required_action=_text(value.get("required_action"), "required_action"),
            severity=severity,
            exceptions=tuple(_text(item, "exceptions") for item in _list(value.get("exceptions"), "exceptions", allow_empty=True)),
            validation_plan=tuple(_text(item, "validation_plan") for item in _list(value.get("validation_plan"), "validation_plan")),
            rollback_plan=tuple(_text(item, "rollback_plan") for item in _list(value.get("rollback_plan"), "rollback_plan")),
        )


@dataclass(frozen=True)
class ProposalOutcome:
    """A generated governed proposal, or an explicit stop reason."""

    proposal: Mapping[str, Any] | None
    stop_reason: str | None
    missing: tuple[str, ...] = ()
    read_only: bool = True

    @property
    def executable(self) -> bool:
        return self.proposal is not None and self.stop_reason is None


class ProposalPlanner:
    """Adjudicate a model-drafted rule candidate and delegate deterministic,
    read-only proposal construction to the RuleGatekeeper."""

    def __init__(self, gatekeeper: RuleGatekeeper) -> None:
        self._gatekeeper = gatekeeper

    def build(
        self,
        *,
        workspace_root: str | Path,
        pack_id: str,
        guard_result: Mapping[str, Any],
        evidence_package: Mapping[str, Any],
        governance_state: str,
        candidate: Mapping[str, Any],
        provenance: Mapping[str, Any],
        equivalent_rule_result: Mapping[str, Any] | str,
        contradiction_result: Mapping[str, Any] | str,
    ) -> ProposalOutcome:
        try:
            proposal_candidate = ProposalCandidate.from_mapping(candidate)
        except ValueError as exc:
            return ProposalOutcome(None, "INVALID_PROPOSAL_CANDIDATE", (str(exc),))

        result = self._gatekeeper.propose_rule(
            workspace_root=workspace_root,
            pack_id=pack_id,
            guard_result=guard_result,
            evidence_package=evidence_package,
            governance_state=governance_state,
            target_profile_path=proposal_candidate.target_profile_path,
            trigger=proposal_candidate.trigger,
            rationale=proposal_candidate.rationale,
            scope=proposal_candidate.scope,
            required_action=proposal_candidate.required_action,
            severity=proposal_candidate.severity,
            exceptions=proposal_candidate.exceptions,
            equivalent_rule_result=equivalent_rule_result,
            contradiction_result=contradiction_result,
            validation_plan=proposal_candidate.validation_plan,
            rollback_plan=proposal_candidate.rollback_plan,
            provenance=provenance,
        )

        read_only = result.get("runtime_mutations_performed") is False
        if result.get("status") == STATUS_INSUFFICIENT_EVIDENCE:
            return ProposalOutcome(
                None,
                "INSUFFICIENT_EVIDENCE",
                tuple(result.get("missing_evidence") or ()),
                read_only=read_only,
            )
        if result.get("status") != STATUS_PROPOSAL_READY or not isinstance(result.get("proposal"), Mapping):
            return ProposalOutcome(None, "PROPOSAL_UNAVAILABLE", read_only=read_only)
        return ProposalOutcome(result["proposal"], None, read_only=read_only)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _list(values: Any, name: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be an array")
    result = [_text(item, name) for item in values]
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _workspace_relative(value: Any, name: str) -> str:
    text = _text(value, name)
    parts = tuple(part for part in text.replace(chr(92), "/").split("/") if part)
    if Path(text).is_absolute() or ".." in parts:
        raise ValueError(f"{name} must be a workspace-relative path without traversal: {text}")
    return text
