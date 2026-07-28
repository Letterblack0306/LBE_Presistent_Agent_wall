from __future__ import annotations

from pathlib import Path

from lbe_guard_inspector.registry_inspection import (
    InspectionEvidenceSource,
    RegistryFirstInspector,
    SourceEvidence,
    SourceInspectionReason,
    bounded_source_inspector,
)
from lbe_guard_inspector.runtime_slice import RuntimeSlice


def test_answers_declared_loaded_and_activity_from_registry_receipts() -> None:
    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()
    source_calls: list[tuple[str | None, str]] = []

    def source(path: str | None, module_id: str) -> SourceEvidence:
        source_calls.append((path, module_id))
        return SourceEvidence(path=path or "", exists=True)

    inspector = RegistryFirstInspector(
        runtime.registry,
        runtime.watcher,
        source_inspector=source,
    )
    result = inspector.inspect("agent.http-server")

    assert result.registered is True
    assert result.declaration is not None
    assert result.declaration["purpose"].startswith("Exposes read-only")
    assert result.runtime is not None
    assert result.runtime["loaded"] is True
    assert result.runtime["current_activity"]["action"] == "listen"
    assert result.lifecycle
    assert result.source_inspection_reason is None
    assert result.source_evidence is None
    assert source_calls == []
    assert result.evidence_sources == (
        InspectionEvidenceSource.REGISTRY,
        InspectionEvidenceSource.WATCHER,
    )


def test_distinguishes_related_modules_by_id_and_purpose() -> None:
    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()
    inspector = RegistryFirstInspector(runtime.registry, runtime.watcher)

    registry = inspector.inspect("module.registry")
    watcher = inspector.inspect("module.watcher")

    assert registry.declaration is not None
    assert watcher.declaration is not None
    assert registry.declaration["id"] != watcher.declaration["id"]
    assert registry.declaration["purpose"] != watcher.declaration["purpose"]
    assert "module.lifecycle" in registry.declaration["provides"]
    assert "module.event-history" in watcher.declaration["provides"]


def test_unregistered_module_uses_bounded_source_fallback() -> None:
    runtime = RuntimeSlice(active_profile="test")
    calls: list[tuple[str | None, str]] = []

    def source(path: str | None, module_id: str) -> SourceEvidence:
        calls.append((path, module_id))
        return SourceEvidence(
            path="src/missing.py",
            exists=False,
            detail="No registered path; bounded lookup only",
        )

    result = RegistryFirstInspector(
        runtime.registry,
        runtime.watcher,
        source_inspector=source,
    ).inspect("unregistered.module")

    assert result.registered is False
    assert result.source_inspection_reason is SourceInspectionReason.MODULE_UNREGISTERED
    assert result.source_evidence is not None
    assert result.source_evidence.exists is False
    assert calls == [(None, "unregistered.module")]
    assert "module declaration" in result.missing_evidence
    assert result.evidence_sources[-1] is InspectionEvidenceSource.SOURCE


def test_exact_implementation_request_triggers_source_verification(tmp_path: Path) -> None:
    source_path = tmp_path / "lbe_guard_inspector" / "server.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("def main():\n    return 'live'\n", encoding="utf-8")

    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()
    inspector = RegistryFirstInspector(
        runtime.registry,
        runtime.watcher,
        source_inspector=bounded_source_inspector(tmp_path, max_chars=12),
    )
    result = inspector.inspect(
        "agent.http-server",
        exact_implementation_required=True,
    )

    assert result.source_inspection_reason is (
        SourceInspectionReason.EXACT_IMPLEMENTATION_REQUIRED
    )
    assert result.source_evidence is not None
    assert result.source_evidence.exists is True
    assert len(result.source_evidence.excerpt) == 12


def test_stale_declared_path_is_detected_by_current_source_evidence(tmp_path: Path) -> None:
    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()
    inspector = RegistryFirstInspector(
        runtime.registry,
        runtime.watcher,
        source_inspector=bounded_source_inspector(tmp_path),
    )

    result = inspector.inspect(
        "guard.runner",
        exact_implementation_required=True,
    )

    assert result.declaration is not None
    assert result.declaration["path"] == "lbe_guard_inspector/guard_runner.py"
    assert result.source_evidence is not None
    assert result.source_evidence.exists is False
    assert result.source_evidence.detail == "Declared source file does not exist"


def test_registered_without_receipts_is_incomplete_and_uses_fallback() -> None:
    runtime = RuntimeSlice(active_profile="test")
    calls: list[str] = []

    def source(path: str | None, module_id: str) -> SourceEvidence:
        calls.append(module_id)
        return SourceEvidence(path=path or "", exists=True)

    result = RegistryFirstInspector(
        runtime.registry,
        runtime.watcher,
        source_inspector=source,
    ).inspect("agent.http-server")

    assert result.source_inspection_reason is SourceInspectionReason.REGISTRY_INCOMPLETE
    assert "lifecycle receipts" in result.missing_evidence
    assert calls == ["agent.http-server"]
