"""Bounded deterministic expansion from verified investigation seeds.

The reasoning backend may identify a problem and candidate guards. This module
turns already-verified guard/validation/workspace evidence into narrowly scoped
follow-up evidence requests. It never executes tools, creates verdicts, or
promotes reference knowledge into current-workspace truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence


_ALLOWED_SEED_TYPES = frozenset({
    "guard_result",
    "validation_failure",
    "current_workspace_evidence",
})
_ALLOWED_RELATIONS = (
    "callers",
    "handlers",
    "dependencies",
    "owners",
    "tests",
    "related_paths",
)


@dataclass(frozen=True)
class InvestigationSeed:
    ref: str
    seed_type: str
    path: str | None
    verified: bool
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class InvestigationEvidenceRequest:
    query: str
    reason: str
    workspace_id: str
    relation: str
    path_patterns: tuple[str, ...]
    extensions: tuple[str, ...]
    semantic_search: bool
    seed_refs: tuple[str, ...]


@dataclass(frozen=True)
class InvestigationPlan:
    seed_refs: tuple[str, ...]
    requests: tuple[InvestigationEvidenceRequest, ...]
    stop_reason: str | None

    @property
    def executable(self) -> bool:
        return self.stop_reason is None and bool(self.requests)


class InvestigationPlanner:
    """Build bounded follow-up requests from verified current evidence."""

    def build(
        self,
        *,
        workspace_id: str,
        seeds: Sequence[Mapping[str, Any]],
        max_requests: int = 8,
    ) -> InvestigationPlan:
        workspace_id = _text(workspace_id, "workspace_id")
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1")

        normalized = tuple(_seed(item) for item in seeds)
        if not normalized:
            return InvestigationPlan((), (), "MISSING_INVESTIGATION_SEED")

        invalid = tuple(seed.ref for seed in normalized if not _seed_is_authoritative(seed))
        if invalid:
            return InvestigationPlan(
                tuple(seed.ref for seed in normalized),
                (),
                "UNVERIFIED_OR_NONCURRENT_SEED",
            )

        requests: list[InvestigationEvidenceRequest] = []
        seen: set[tuple[str, tuple[str, ...]]] = set()

        for seed in normalized:
            for relation in _ALLOWED_RELATIONS:
                paths = _relation_paths(seed.metadata.get(relation))
                if not paths:
                    continue
                key = (relation, paths)
                if key in seen:
                    continue
                seen.add(key)
                requests.append(
                    _request(
                        workspace_id=workspace_id,
                        seed=seed,
                        relation=relation,
                        paths=paths,
                    )
                )
                if len(requests) >= max_requests:
                    break
            if len(requests) >= max_requests:
                break

        if not requests:
            return InvestigationPlan(
                tuple(seed.ref for seed in normalized),
                (),
                "NO_BOUNDED_RELATIONS",
            )

        return InvestigationPlan(
            tuple(dict.fromkeys(seed.ref for seed in normalized)),
            tuple(requests),
            None,
        )


def _seed(value: Mapping[str, Any]) -> InvestigationSeed:
    if not isinstance(value, Mapping):
        raise ValueError("investigation seed must be an object")
    ref = _text(value.get("ref"), "seed.ref")
    seed_type = _text(value.get("source_type") or value.get("seed_type"), "seed.source_type")
    raw_path = value.get("path")
    path = _normalize_path(raw_path) if isinstance(raw_path, str) and raw_path.strip() else None
    metadata = value.get("metadata") or {}
    if not isinstance(metadata, Mapping):
        raise ValueError("seed.metadata must be an object")
    return InvestigationSeed(
        ref=ref,
        seed_type=seed_type,
        path=path,
        verified=value.get("verified") is True,
        metadata=metadata,
    )


def _seed_is_authoritative(seed: InvestigationSeed) -> bool:
    return seed.verified and seed.seed_type in _ALLOWED_SEED_TYPES


def _relation_paths(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = tuple(value)
    else:
        raise ValueError("investigation relation paths must be a string or array")

    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("investigation relation paths must contain non-empty strings")
        path = _normalize_path(item)
        if path not in normalized:
            normalized.append(path)
    return tuple(normalized)


def _request(
    *,
    workspace_id: str,
    seed: InvestigationSeed,
    relation: str,
    paths: tuple[str, ...],
) -> InvestigationEvidenceRequest:
    extensions = tuple(dict.fromkeys(_extension(path) for path in paths if _extension(path)))
    return InvestigationEvidenceRequest(
        query=paths[0],
        reason=f"inspect {relation} linked from verified seed {seed.ref}",
        workspace_id=workspace_id,
        relation=relation,
        path_patterns=paths,
        extensions=extensions,
        semantic_search=False,
        seed_refs=(seed.ref,),
    )


def _normalize_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"investigation path escapes workspace: {value}")
    return str(path)


def _extension(path: str) -> str:
    suffix = PurePosixPath(path).suffix
    return suffix.lower() if suffix else ""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()
