"""Evidence-bound Guard Inspector evaluation layer.

This module implements the evaluation layer that turns an *existing registered
deterministic rule* outcome plus the *current evidence package* into a
``guard_result`` contract:

```text
existing registered deterministic rule (RuleOutcome)
        |
        v
current evidence package
        |
        v
evidence-policy enforcement
        |
        v
guard_result contract
        |
        v
PASS / FAIL / INSUFFICIENT_EVIDENCE / NOT_APPLICABLE
```

The mapping is **not** a blind rename of the deterministic rule status.  An
evidence policy gates every promotion to a workspace compliance verdict:

* ``passed`` -> ``PASS`` only when current workspace evidence refs support it,
  there are no contradictions, and validation refs are present.
* ``failed`` -> ``FAIL`` only when current workspace evidence refs support it.
* ``blocked`` -> normally ``INSUFFICIENT_EVIDENCE``.
* ``not_applicable`` -> ``NOT_APPLICABLE``.

Indexed-only rule results can never become ``PASS`` or ``FAIL``:

* rules that inspect only the SQLite index (e.g. ``generic.index_present``) are
  classified by :class:`EvidencePolicy` and cannot claim a workspace compliance
  verdict;
* any rule result that lacks current workspace evidence refs is downgraded to
  ``INSUFFICIENT_EVIDENCE`` regardless of its own status.

Contradictions between indexed and workspace evidence prevent an unsupported
``PASS``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .contracts import validate_contract

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
VERDICT_NOT_APPLICABLE = "NOT_APPLICABLE"

#: Base (pre-policy) mapping from a deterministic rule status to a guard verdict.
#: Every entry is gated by :meth:`GuardInspector.evaluate` before promotion.
_RULE_STATUS_TO_VERDICT_BASE: dict[str, str] = {
    "passed": VERDICT_PASS,
    "failed": VERDICT_FAIL,
    "blocked": VERDICT_INSUFFICIENT_EVIDENCE,
    "not_applicable": VERDICT_NOT_APPLICABLE,
}

VALID_RULE_STATUSES = frozenset(_RULE_STATUS_TO_VERDICT_BASE)

#: Default rule ids that inspect only the SQLite index and therefore cannot
#: claim a workspace compliance verdict.
DEFAULT_INDEX_ONLY_RULE_IDS = frozenset({"generic.index_present"})


@dataclass(frozen=True)
class RuleOutcome:
    """Normalized outcome of an existing registered deterministic rule."""

    rule_id: str
    status: str
    message: str
    evidence: dict[str, Any]


def coerce_rule_result(rule_result: Any) -> RuleOutcome:
    """Normalize a deterministic rule result into a :class:`RuleOutcome`.

    Accepts an ``audit_controller.RuleResult`` dataclass instance, a mapping
    (dict), or any object exposing ``rule_id`` / ``status`` / ``message`` /
    ``evidence`` attributes.  This keeps the evaluation layer decoupled from the
    rule-execution infrastructure while still consuming its real output.
    """
    if isinstance(rule_result, Mapping):
        rule_id = rule_result.get("rule_id")
        status = rule_result.get("status")
        message = rule_result.get("message") or ""
        evidence = rule_result.get("evidence")
    else:
        rule_id = getattr(rule_result, "rule_id", None)
        status = getattr(rule_result, "status", None)
        message = getattr(rule_result, "message", "") or ""
        evidence = getattr(rule_result, "evidence", None)

    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ValueError("rule_result must provide a non-empty 'rule_id'")
    if not isinstance(status, str) or not status.strip():
        raise ValueError("rule_result must provide a non-empty 'status'")
    if status not in VALID_RULE_STATUSES:
        raise ValueError(
            f"rule_result.status '{status}' is not a valid deterministic rule "
            f"status (expected one of {sorted(VALID_RULE_STATUSES)})"
        )
    if not isinstance(evidence, dict):
        evidence = {}

    return RuleOutcome(
        rule_id=rule_id.strip(),
        status=status,
        message=str(message),
        evidence=dict(evidence),
    )


@dataclass(frozen=True)
class EvidencePolicy:
    """Policy that classifies which deterministic rules are index-only.

    Index-only rules inspect the SQLite index (or static configuration) and
    therefore cannot claim a workspace compliance verdict (``PASS`` / ``FAIL``).
    """

    index_only_rule_ids: frozenset[str] = DEFAULT_INDEX_ONLY_RULE_IDS

    def is_index_only(self, rule_id: str) -> bool:
        """Return True when ``rule_id`` is known to inspect only the index."""
        return rule_id in self.index_only_rule_ids


def _unique_refs(refs: Any) -> list[str]:
    """De-duplicate a sequence of evidence ref strings, preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    if refs is None:
        return out
    try:
        iterator = iter(refs)
    except TypeError:
        return out
    for ref in iterator:
        if isinstance(ref, str) and ref and ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


class GuardInspector:
    """Evidence-bound evaluation layer producing ``guard_result`` contracts.

    The inspector consumes the outcome of an existing registered deterministic
    rule and the current evidence package, applies evidence-policy enforcement,
    and emits a ``guard_result`` validated against the JSON Schema contract.
    """

    def __init__(self, policy: EvidencePolicy | None = None) -> None:
        self.policy = policy or EvidencePolicy()

    def evaluate(
        self,
        *,
        rule_result: Any,
        evidence_package: Mapping[str, Any],
        guard_id: str | None = None,
        guard_version: str | None = None,
        workspace_id: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Map a deterministic rule result + evidence package to a guard_result.

        ``rule_result`` may be a real ``RuleResult`` or a dict; ``evidence_package``
        is the current evidence package produced by :class:`EvidenceService`.
        """
        outcome = coerce_rule_result(rule_result)
        package = _coerce_evidence_package(evidence_package)

        workspace_refs = _unique_refs(
            item.get("ref") for item in package["current_workspace_evidence"]
        )
        validation_refs = _unique_refs(
            item.get("ref") for item in package["validation_evidence"]
        )
        contradictions = [str(c) for c in (package.get("contradictions") or []) if c]
        gaps = [str(g) for g in (package.get("missing_evidence") or []) if g]
        index_only = self.policy.is_index_only(outcome.rule_id)

        findings: list[str] = []
        if outcome.message:
            findings.append(outcome.message)
        if reason:
            findings.append(reason)

        verdict, evidence_refs, validation_refs_out, governance_state = (
            self._enforce_policy(
                outcome=outcome,
                workspace_refs=workspace_refs,
                validation_refs=validation_refs,
                contradictions=contradictions,
                index_only=index_only,
                findings=findings,
            )
        )

        if index_only:
            findings.append(
                f"Rule '{outcome.rule_id}' inspects only the SQLite index; "
                "it cannot claim a workspace compliance verdict."
            )
        for contradiction in contradictions:
            findings.append(f"contradiction: {contradiction}")
        for gap in gaps:
            findings.append(f"evidence_gap: {gap}")

        guard_result = {
            "result_id": f"gr-{uuid.uuid4()}",
            "guard_id": guard_id or outcome.rule_id,
            "guard_version": guard_version,
            "workspace_id": workspace_id or package.get("workspace_id"),
            "verdict": verdict,
            "summary": self._summary(outcome, verdict, index_only),
            "findings": findings,
            "evidence_refs": evidence_refs,
            "validation_refs": validation_refs_out,
            "governance_state": governance_state,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
        return validate_contract("guard_result", guard_result)

    def _enforce_policy(
        self,
        *,
        outcome: RuleOutcome,
        workspace_refs: list[str],
        validation_refs: list[str],
        contradictions: list[str],
        index_only: bool,
        findings: list[str],
    ) -> tuple[str, list[str], list[str], str]:
        """Apply evidence-policy enforcement and return the verdict triple.

        Returns ``(verdict, evidence_refs, validation_refs, governance_state)``.
        ``evidence_refs`` are the current workspace evidence refs that support
        the verdict; ``validation_refs`` are the validation evidence refs.
        """
        # not_applicable passes through unchanged.
        if outcome.status == "not_applicable":
            return (
                VERDICT_NOT_APPLICABLE,
                list(workspace_refs),
                list(validation_refs),
                "READ_ONLY",
            )

        # blocked -> normally INSUFFICIENT_EVIDENCE.
        if outcome.status == "blocked":
            findings.append(
                "Rule was blocked; required evidence or validation is missing, "
                "ambiguous, or contradictory."
            )
            return (
                VERDICT_INSUFFICIENT_EVIDENCE,
                list(workspace_refs),
                list(validation_refs),
                "INCOMPLETE",
            )

        # From here the rule status is 'passed' or 'failed'.  An index-only rule
        # (e.g. generic.index_present) cannot claim a workspace compliance
        # verdict, and a result with no current workspace evidence refs cannot
        # become PASS or FAIL.
        if index_only:
            findings.append(
                "Index-only rule result is not promoted to a workspace PASS or FAIL."
            )
            return (
                VERDICT_INSUFFICIENT_EVIDENCE,
                list(workspace_refs),
                list(validation_refs),
                "INCOMPLETE",
            )

        if not workspace_refs:
            findings.append(
                "No current workspace evidence refs support a workspace PASS or FAIL."
            )
            return (
                VERDICT_INSUFFICIENT_EVIDENCE,
                list(workspace_refs),
                list(validation_refs),
                "INCOMPLETE",
            )

        if outcome.status == "passed":
            # Contradictions must prevent an unsupported PASS.
            if contradictions:
                findings.append(
                    "Contradictions between indexed and workspace evidence "
                    "prevent an unsupported PASS."
                )
                return (
                    VERDICT_INSUFFICIENT_EVIDENCE,
                    list(workspace_refs),
                    list(validation_refs),
                    "INCOMPLETE",
                )
            # Never convert missing validation into PASS.
            if not validation_refs:
                findings.append(
                    "Missing validation evidence; cannot promote a passed rule to PASS."
                )
                return (
                    VERDICT_INSUFFICIENT_EVIDENCE,
                    list(workspace_refs),
                    list(validation_refs),
                    "INCOMPLETE",
                )
            return (
                VERDICT_PASS,
                list(workspace_refs),
                list(validation_refs),
                "READ_ONLY",
            )

        # failed -> FAIL only when current workspace evidence refs support it.
        return (
            VERDICT_FAIL,
            list(workspace_refs),
            list(validation_refs),
            "READ_ONLY",
        )

    @staticmethod
    def _summary(outcome: RuleOutcome, verdict: str, index_only: bool) -> str:
        if verdict == VERDICT_NOT_APPLICABLE:
            return f"NOT_APPLICABLE: {outcome.rule_id} does not apply to this scope."
        if verdict == VERDICT_INSUFFICIENT_EVIDENCE:
            if index_only:
                return (
                    f"INSUFFICIENT_EVIDENCE: {outcome.rule_id} is index-only; "
                    "a workspace compliance verdict is not claimed."
                )
            return (
                f"INSUFFICIENT_EVIDENCE: {outcome.rule_id} cannot reach a reliable "
                "verdict; required workspace evidence or validation is missing, "
                "ambiguous, or contradictory."
            )
        if verdict == VERDICT_PASS:
            return (
                f"PASS: {outcome.rule_id} passed and is supported by current "
                "workspace evidence."
            )
        if verdict == VERDICT_FAIL:
            return (
                f"FAIL: {outcome.rule_id} found a violation supported by current "
                "workspace evidence."
            )
        return f"{verdict}: {outcome.rule_id}"


def _coerce_evidence_package(package: Any) -> dict[str, Any]:
    """Lightly coerce an evidence package mapping, filling missing lists."""
    if not isinstance(package, Mapping):
        raise ValueError("evidence_package must be a mapping")
    coerced = dict(package)
    for key, default in (
        ("indexed_reference_evidence", []),
        ("current_workspace_evidence", []),
        ("validation_evidence", []),
        ("contradictions", []),
        ("missing_evidence", []),
    ):
        value = coerced.get(key)
        if not isinstance(value, list):
            coerced[key] = list(default)
    coerced.setdefault("workspace_id", None)
    return coerced
