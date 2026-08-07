"""Deterministic planning policies around the provider-backed reasoning layer.

The model may interpret and select. This module owns the non-model contracts that
keep retrieval, evidence requirements, conflict handling, and explanation focus
bounded and reproducible.
"""
from __future__ import annotations
import fnmatch


from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from .reasoning_contracts import EvidenceRequest, ReasoningPlan


class RetrievalMode(str, Enum):
    DIAGNOSTIC = "diagnostic"
    GUARD = "guard"
    INVESTIGATION = "investigation"


@dataclass(frozen=True)
class RetrievalPlan:
    mode: RetrievalMode
    query: str
    reason: str
    workspace_id: str
    rule_id: str | None = None
    path_patterns: tuple[str, ...] = ()
    extensions: tuple[str, ...] = ()
    semantic_search: bool = False
    seed_evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidencePlan:
    required: tuple[str, ...]
    optional: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing


@dataclass(frozen=True)
class ConflictResolution:
    selected_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...]
    stop_required: bool


class ReasoningPolicy:
    """Provider-independent policy for safe reasoning orchestration."""

    def classify_mode(
        self,
        *,
        selected_guard_id: str | None,
        seed_evidence_refs: Sequence[str] = (),
    ) -> RetrievalMode:
        if selected_guard_id:
            return RetrievalMode.GUARD
        if seed_evidence_refs:
            return RetrievalMode.INVESTIGATION
        return RetrievalMode.DIAGNOSTIC

    def build_retrieval_plan(
        self,
        *,
        problem: str,
        workspace_id: str,
        selected_guard_id: str | None = None,
        evidence_requests: Sequence[EvidenceRequest] = (),
        guard_contract: Mapping[str, Any] | None = None,
        seed_evidence_refs: Sequence[str] = (),
    ) -> RetrievalPlan:
        problem = _text(problem, "problem")
        workspace_id = _text(workspace_id, "workspace_id")
        mode = self.classify_mode(
            selected_guard_id=selected_guard_id,
            seed_evidence_refs=seed_evidence_refs,
        )

        if mode is RetrievalMode.GUARD:
            if guard_contract is None:
                raise ValueError("guard retrieval requires a registered evidence contract")
            patterns = _strings(guard_contract.get("path_patterns", ()), "path_patterns")
            if not patterns:
                raise ValueError("guard retrieval requires explicit path_patterns")
            extensions = _strings(guard_contract.get("extensions", ()), "extensions", allow_empty=True)
            # Structural guard retrieval is path-driven. Natural-language reasoning
            # and the model's evidence reasons never become search terms.
            return RetrievalPlan(
                mode=mode,
                query=patterns[0],
                reason=f"inspect registered evidence for {selected_guard_id}",
                workspace_id=workspace_id,
                rule_id=selected_guard_id,
                path_patterns=patterns,
                extensions=extensions,
                semantic_search=False,
            )

        if mode is RetrievalMode.INVESTIGATION:
            return RetrievalPlan(
                mode=mode,
                query=problem,
                reason="expand from supplied deterministic evidence",
                workspace_id=workspace_id,
                semantic_search=True,
                seed_evidence_refs=tuple(dict.fromkeys(_text(ref, "seed_evidence_ref") for ref in seed_evidence_refs)),
            )

        return RetrievalPlan(
            mode=mode,
            query=problem,
            reason="open-ended diagnostic retrieval",
            workspace_id=workspace_id,
            semantic_search=True,
        )

    def plan_evidence(
        self,
        *,
        guard_contract: Mapping[str, Any],
        evidence_package: Mapping[str, Any],
    ) -> EvidencePlan:
        required = _strings(
            guard_contract.get("evidence_requirements", ()),
            "evidence_requirements",
            allow_empty=True,
        )
        optional = _strings(
            guard_contract.get("optional_evidence_requirements", ()),
            "optional_evidence_requirements",
            allow_empty=True,
        )
        path_patterns = tuple(guard_contract.get("path_patterns", ()))
        satisfied = set()
        if path_patterns:
            for collection in (
                evidence_package.get("indexed_reference_evidence", ()),
                evidence_package.get("current_workspace_evidence", ()),
                evidence_package.get("validation_evidence", ()),
            ):
                if not isinstance(collection, Sequence) or isinstance(collection, (str, bytes)):
                    continue
                for item in collection:
                    if not isinstance(item, Mapping):
                        continue
                    if any(
                        _evidence_matches_path(item, pattern) for pattern in path_patterns
                    ):
                        for requirement in required:
                            satisfied.add(requirement)
                        break
                if satisfied:
                    break
        declared_missing = {
            str(item)
            for item in evidence_package.get("missing_evidence", ())
            if isinstance(item, str) and item.strip()
        }
        missing = tuple(
            requirement
            for requirement in required
            if requirement in declared_missing or (required and requirement not in satisfied)
        )
        return EvidencePlan(required=required, optional=optional, missing=missing)

    def resolve_conflicts(self, evidence: Sequence[Mapping[str, Any]]) -> ConflictResolution:
        """Prefer verified higher-authority evidence and stop on unresolved peers."""
        grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for item in evidence:
            path = str(item.get("path") or "")
            source_type = str(item.get("source_type") or "")
            grouped.setdefault((source_type, path), []).append(item)

        selected: list[str] = []
        unresolved: list[str] = []
        for items in grouped.values():
            ranked = sorted(items, key=_authority_rank, reverse=True)
            top_rank = _authority_rank(ranked[0])
            peers = [item for item in ranked if _authority_rank(item) == top_rank]
            peer_hashes = {str(item.get("hash") or "") for item in peers}
            refs = [str(item.get("ref") or "") for item in peers if item.get("ref")]
            if len(peer_hashes) > 1:
                unresolved.extend(refs)
            elif refs:
                selected.append(refs[0])

        return ConflictResolution(
            selected_refs=tuple(dict.fromkeys(selected)),
            unresolved_refs=tuple(dict.fromkeys(unresolved)),
            stop_required=bool(unresolved),
        )

    def normalize_explanation_focus(self, plan: ReasoningPlan) -> tuple[str, ...]:
        allowed = (
            "why the guard applies",
            "evidence checked",
            "deterministic verdict",
            "missing evidence",
            "validation state",
        )
        requested = tuple(dict.fromkeys(item.strip() for item in plan.explanation_focus if item.strip()))
        return requested or allowed

    def validate_evidence_requests(
        self,
        *,
        requests: Sequence[EvidenceRequest],
        workspace_root: Path,
        approved_tools: Sequence[str],
    ) -> None:
        approved = set(approved_tools)
        root = workspace_root.resolve()
        for request in requests:
            if request.tool_id not in approved:
                raise ValueError(f"unapproved evidence tool: {request.tool_id}")
            path = Path(request.path)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"evidence path escapes workspace: {request.path}")
            try:
                (root / path).resolve().relative_to(root)
            except ValueError as exc:
                raise ValueError(f"evidence path escapes workspace: {request.path}") from exc


def _authority_rank(item: Mapping[str, Any]) -> tuple[int, int]:
    verified = 1 if item.get("verified") is True else 0
    authority = item.get("authority", 0)
    return verified, int(authority) if isinstance(authority, int) else 0


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _strings(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field} must be an array")
    result = tuple(_text(item, field) for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{field} must not be empty")
    return result


def _evidence_path(item: Mapping[str, Any]) -> str:
    path = str(item.get("path") or "")
    if path:
        return path.replace("\\", "/")
    metadata = item.get("metadata") or {}
    return str(metadata.get("relative_path") or "").replace(chr(92), "/")


def _evidence_matches_path(item: Mapping[str, Any], pattern: str) -> bool:
    path = _evidence_path(item)
    if not path or not pattern:
        return False
    normalized_pattern = pattern.replace("\\", "/").strip("/")
    if fnmatch.fnmatch(path, normalized_pattern):
        return True
    if path.endswith("/" + normalized_pattern) or path.endswith(normalized_pattern):
        return True
    return False
