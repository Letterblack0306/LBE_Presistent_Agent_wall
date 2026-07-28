from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .module_registry import ModuleRegistry, ModuleWatcher, RegistryDefectCode


class InspectionEvidenceSource(str, Enum):
    REGISTRY = "registry"
    WATCHER = "watcher"
    SOURCE = "source"


class SourceInspectionReason(str, Enum):
    MODULE_UNREGISTERED = "module_unregistered"
    REGISTRY_CONTRADICTORY = "registry_contradictory"
    REGISTRY_INCOMPLETE = "registry_incomplete"
    OWNERSHIP_SENSITIVE = "ownership_sensitive"
    EXACT_IMPLEMENTATION_REQUIRED = "exact_implementation_required"


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    path: str
    exists: bool
    excerpt: str = ""
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ModuleInspection:
    module_id: str
    registered: bool
    declaration: Mapping[str, Any] | None
    runtime: Mapping[str, Any] | None
    lifecycle: tuple[Mapping[str, Any], ...]
    defects: tuple[Mapping[str, Any], ...]
    missing_evidence: tuple[str, ...]
    source_inspection_reason: SourceInspectionReason | None
    source_evidence: SourceEvidence | None
    evidence_sources: tuple[InspectionEvidenceSource, ...]


SourceInspector = Callable[[str | None, str], SourceEvidence]


class RegistryFirstInspector:
    """Inspect module truth from registry evidence before reading source.

    Source inspection is bounded and invoked only when registry evidence is
    absent, contradictory, incomplete, ownership-sensitive, or exact source
    evidence is explicitly required.
    """

    def __init__(
        self,
        registry: ModuleRegistry,
        watcher: ModuleWatcher,
        *,
        source_inspector: SourceInspector | None = None,
    ) -> None:
        self._registry = registry
        self._watcher = watcher
        self._source_inspector = source_inspector

    def inspect(
        self,
        module_id: str,
        *,
        ownership_sensitive: bool = False,
        exact_implementation_required: bool = False,
    ) -> ModuleInspection:
        clean_id = module_id.strip()
        if not clean_id:
            raise ValueError("module_id must not be empty")

        records = {record.declaration.id: record for record in self._registry.list()}
        record = records.get(clean_id)
        lifecycle = tuple(
            {
                "sequence": event.sequence,
                "event_type": event.event_type.value,
                "module_id": event.module_id,
            }
            for event in self._watcher.history
            if event.module_id == clean_id
        )
        defects = tuple(
            {
                "code": defect.code.value,
                "blocking": defect.blocking,
                "evidence": tuple(defect.evidence),
            }
            for defect in self._registry.defects()
            if defect.module_id == clean_id
        )

        missing: list[str] = []
        declaration: Mapping[str, Any] | None = None
        runtime: Mapping[str, Any] | None = None
        declared_path: str | None = None

        if record is None:
            missing.extend(("module declaration", "runtime record"))
        else:
            declared_path = record.declaration.path
            declaration = {
                "id": record.declaration.id,
                "path": record.declaration.path,
                "type": record.declaration.type.value,
                "purpose": record.declaration.purpose,
                "provides": tuple(record.declaration.provides),
                "depends_on": tuple(record.declaration.depends_on),
                "loaded_by": record.declaration.loaded_by,
                "expected_profiles": tuple(record.declaration.expected_profiles),
            }
            runtime = {
                "state": record.state.value,
                "loaded": record.loaded,
                "running": record.running,
                "healthy": record.healthy,
                "instances": tuple(sorted(record.instances)),
                "current_activity": (
                    {
                        "action": record.current_activity.action,
                        "detail": record.current_activity.detail,
                        "started_at": record.current_activity.started_at,
                    }
                    if record.current_activity is not None
                    else None
                ),
                "updated_at": record.updated_at,
            }
            if not lifecycle:
                missing.append("lifecycle receipts")

        reason = self._source_reason(
            registered=record is not None,
            defects=defects,
            missing=missing,
            ownership_sensitive=ownership_sensitive,
            exact_implementation_required=exact_implementation_required,
        )
        source_evidence = None
        sources = [InspectionEvidenceSource.REGISTRY, InspectionEvidenceSource.WATCHER]
        if reason is not None:
            sources.append(InspectionEvidenceSource.SOURCE)
            if self._source_inspector is not None:
                source_evidence = self._source_inspector(declared_path, clean_id)
            else:
                missing.append("bounded source inspector")

        return ModuleInspection(
            module_id=clean_id,
            registered=record is not None,
            declaration=declaration,
            runtime=runtime,
            lifecycle=lifecycle,
            defects=defects,
            missing_evidence=tuple(dict.fromkeys(missing)),
            source_inspection_reason=reason,
            source_evidence=source_evidence,
            evidence_sources=tuple(sources),
        )

    @staticmethod
    def _source_reason(
        *,
        registered: bool,
        defects: tuple[Mapping[str, Any], ...],
        missing: list[str],
        ownership_sensitive: bool,
        exact_implementation_required: bool,
    ) -> SourceInspectionReason | None:
        if not registered:
            return SourceInspectionReason.MODULE_UNREGISTERED
        if any(
            defect["code"]
            in {
                RegistryDefectCode.CONTRADICTORY_LIFECYCLE_STATE.value,
                RegistryDefectCode.RECEIPT_FOR_UNKNOWN_MODULE.value,
            }
            for defect in defects
        ):
            return SourceInspectionReason.REGISTRY_CONTRADICTORY
        if missing:
            return SourceInspectionReason.REGISTRY_INCOMPLETE
        if ownership_sensitive:
            return SourceInspectionReason.OWNERSHIP_SENSITIVE
        if exact_implementation_required:
            return SourceInspectionReason.EXACT_IMPLEMENTATION_REQUIRED
        return None


def bounded_source_inspector(
    workspace_root: str | Path,
    *,
    max_chars: int = 4000,
) -> SourceInspector:
    """Create a path-bounded source reader for registry fallback evidence."""

    root = Path(workspace_root).resolve()
    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")

    def inspect(declared_path: str | None, module_id: str) -> SourceEvidence:
        if not declared_path:
            return SourceEvidence(
                path="",
                exists=False,
                detail=f"No declared path for {module_id}",
            )
        candidate = (root / declared_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return SourceEvidence(
                path=declared_path,
                exists=False,
                detail="Declared path escapes workspace root",
            )
        if not candidate.is_file():
            return SourceEvidence(
                path=declared_path,
                exists=False,
                detail="Declared source file does not exist",
            )
        text = candidate.read_text(encoding="utf-8", errors="replace")
        return SourceEvidence(
            path=declared_path,
            exists=True,
            excerpt=text[:max_chars],
            detail=f"Read at most {max_chars} characters",
        )

    return inspect
