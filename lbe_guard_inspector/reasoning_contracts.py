"""Typed, provider-neutral contracts for bounded LBE reasoning."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


_FORBIDDEN_REASONING_FIELDS = frozenset({
    "verdict", "pass", "fail", "status", "write", "apply", "command",
    "memory_promotion", "promote_memory", "authorization", "authorize",
    "policy", "repair", "mutation",
})


@dataclass(frozen=True)
class LBERequest:
    problem: str
    workspace_root: str | Path
    reference_context: tuple[Mapping[str, Any], ...] = ()
    task_id: str | None = None
    max_results: int = 10


@dataclass(frozen=True)
class EvidenceRequest:
    tool_id: str
    path: str
    reason: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvidenceRequest":
        _require_exact_keys(value, {"tool_id", "path", "reason"}, "evidence request")
        return cls(
            tool_id=_text(value.get("tool_id"), "evidence_request.tool_id"),
            path=_text(value.get("path"), "evidence_request.path"),
            reason=_text(value.get("reason"), "evidence_request.reason"),
        )


@dataclass(frozen=True)
class ReasoningRequest:
    problem: str
    workspace_identity: Mapping[str, str]
    workspace_profile: Mapping[str, Any]
    approved_guard_ids: tuple[str, ...]
    approved_tools: tuple[str, ...]
    reference_context: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class ReasoningPlan:
    interpreted_problem: str
    ambiguities: tuple[str, ...]
    candidate_guard_ids: tuple[str, ...]
    evidence_requests: tuple[EvidenceRequest, ...]
    validation_requests: tuple[str, ...]
    explanation_focus: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReasoningPlan":
        _reject_forbidden(value, "reasoning plan")
        _require_exact_keys(
            value,
            {"interpreted_problem", "ambiguities", "candidate_guard_ids", "evidence_requests", "validation_requests", "explanation_focus"},
            "reasoning plan",
        )
        evidence = value.get("evidence_requests")
        if not isinstance(evidence, list):
            raise ValueError("reasoning_plan.evidence_requests must be an array")
        if not all(isinstance(item, Mapping) for item in evidence):
            raise ValueError("reasoning_plan.evidence_requests must contain objects")
        return cls(
            interpreted_problem=_text(value.get("interpreted_problem"), "reasoning_plan.interpreted_problem"),
            ambiguities=_strings(value.get("ambiguities"), "reasoning_plan.ambiguities", allow_empty=True),
            candidate_guard_ids=_strings(value.get("candidate_guard_ids"), "reasoning_plan.candidate_guard_ids", allow_empty=True),
            evidence_requests=tuple(EvidenceRequest.from_mapping(item) for item in evidence),
            validation_requests=_strings(value.get("validation_requests"), "reasoning_plan.validation_requests", allow_empty=True),
            explanation_focus=_strings(value.get("explanation_focus"), "reasoning_plan.explanation_focus", allow_empty=True),
        )


@dataclass(frozen=True)
class ExplanationRequest:
    guard_result: Mapping[str, Any]
    current_workspace_evidence: tuple[Mapping[str, Any], ...]
    validation_evidence: tuple[Mapping[str, Any], ...]
    governance_state: str
    explanation_focus: tuple[str, ...]


@dataclass(frozen=True)
class ExplanationResult:
    explanation: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExplanationResult":
        _reject_forbidden(value, "explanation result")
        _require_exact_keys(value, {"explanation"}, "explanation result")
        return cls(explanation=_text(value.get("explanation"), "explanation_result.explanation"))


class ReasoningBackend(Protocol):
    """A provider-neutral dependency; implementations never own LBE authority."""

    def plan(self, request: ReasoningRequest) -> ReasoningPlan | Mapping[str, Any]: ...

    def explain(self, request: ExplanationRequest) -> ExplanationResult | Mapping[str, Any]: ...


@dataclass(frozen=True)
class OrchestrationError:
    code: str
    message: str
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class LBEResponse:
    task_id: str
    workspace_identity: Mapping[str, str]
    workspace_profile: Mapping[str, Any]
    plan: ReasoningPlan | None
    deterministic_result: Mapping[str, Any] | None
    explanation: ExplanationResult | None
    outcome: str
    error: OrchestrationError | None = None
    read_only: bool = True


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _strings(value: Any, field: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    result = tuple(_text(item, field) for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{field} must not be empty")
    return result


def _reject_forbidden(value: Mapping[str, Any], name: str) -> None:
    present = sorted(set(value) & _FORBIDDEN_REASONING_FIELDS)
    if present:
        raise ValueError(f"{name} contains forbidden fields: {', '.join(present)}")


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        parts = []
        if missing:
            parts.append("missing " + ", ".join(missing))
        if extra:
            parts.append("unsupported " + ", ".join(extra))
        raise ValueError(f"{name} fields are invalid: {'; '.join(parts)}")
