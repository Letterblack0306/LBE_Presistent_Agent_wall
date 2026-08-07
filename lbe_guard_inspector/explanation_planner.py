"""Bounded deterministic orchestration of the explanation stage.

The explanation layer explains an already-fixed deterministic guard result. It
never invents, alters, or reinterprets the verdict, authority, governance state,
or evidence. It preserves the separation between evidence classes and stops when
there is no deterministic result or governance state to explain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .reasoning_contracts import ExplanationRequest, ExplanationResult

_DEFAULT_EXPLANATION_FOCUS = (
    "why the guard applies",
    "evidence checked",
    "deterministic verdict",
    "missing evidence",
    "validation state",
)


@dataclass(frozen=True)
class ExplanationOutcome:
    """A built bounded explanation request, or an explicit stop reason."""

    request: ExplanationRequest | None
    stop_reason: str | None

    @property
    def executable(self) -> bool:
        return self.request is not None and self.stop_reason is None


class ExplanationPlanner:
    """Build and guard the bounded explanation request for a fixed result."""

    def build_request(
        self,
        *,
        guard_result: Mapping[str, Any],
        current_workspace_evidence: Sequence[Mapping[str, Any]] = (),
        validation_evidence: Sequence[Mapping[str, Any]] = (),
        governance_state: str | None = None,
        explanation_focus: Sequence[str] = (),
    ) -> ExplanationOutcome:
        # Explanations require a deterministic result to explain.
        if not isinstance(guard_result, Mapping) or not guard_result:
            return ExplanationOutcome(None, "MISSING_DETERMINISTIC_RESULT")
        verdict = guard_result.get("verdict")
        if not isinstance(verdict, str) or not verdict.strip():
            return ExplanationOutcome(None, "MISSING_DETERMINISTIC_RESULT")

        governance = _governance(guard_result, governance_state)
        if governance is None:
            return ExplanationOutcome(None, "MISSING_GOVERNANCE_STATE")

        focus = _normalize_focus(explanation_focus, _DEFAULT_EXPLANATION_FOCUS)

        # Only current workspace evidence and validation evidence may enter the
        # explanation. Indexed reference knowledge is structurally excluded.
        request = ExplanationRequest(
            guard_result=_mapping(guard_result),
            current_workspace_evidence=tuple(_mapping(item) for item in current_workspace_evidence),
            validation_evidence=tuple(_mapping(item) for item in validation_evidence),
            governance_state=governance,
            explanation_focus=focus,
        )
        return ExplanationOutcome(request, None)

    def verify_immutable(self, value: Any) -> str | None:
        """Return a stop reason when an explanation would alter the deterministic
        result; return ``None`` when it stays bounded and immutable.

        The exact-key ``ExplanationResult`` contract is the single source of truth
        for immutability, so this reuses it instead of reimplementing a forbidden
        field list.
        """
        if isinstance(value, ExplanationResult):
            return None
        if not isinstance(value, Mapping):
            return "EXPLANATION_NOT_IMMUTABLE"
        try:
            ExplanationResult.from_mapping(value)
        except ValueError:
            return "EXPLANATION_NOT_IMMUTABLE"
        return None


def _governance(guard_result: Mapping[str, Any], provided: str | None) -> str | None:
    if isinstance(provided, str) and provided.strip():
        return provided.strip()
    raw = guard_result.get("governance_state")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _normalize_focus(value: Sequence[str], default: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("explanation_focus must be an array of non-empty strings")
    normalized = tuple(dict.fromkeys(str(topic).strip() for topic in value if str(topic).strip()))
    return normalized or tuple(default)


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("explanation inputs must be objects")
    return value
