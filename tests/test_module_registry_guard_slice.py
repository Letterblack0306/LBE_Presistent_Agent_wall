from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agent import Context, KnowledgeRoot
from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.guard_runner import GuardRunner
from lbe_guard_inspector.module_registry_vertical_slice import (
    MODULE_REGISTRY_RULE_ID,
    ModuleRegistryGuardRunner,
    ModuleRegistryVerticalSlice,
)
from rules.module_registry import rule_loaded_module_registration


def _context(root: Path) -> Context:
    return Context(
        config={"max_file_bytes": 1_000_000, "exclude_patterns": []},
        governance={},
        roots=(KnowledgeRoot("workspace", root),),
    )


def _write_registry(
    root: Path,
    *,
    declarations: list[dict] | None = None,
    receipts: list[dict] | None = None,
) -> Path:
    target = root / ".lbe" / "module-registry.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "declarations": declarations if declarations is not None else [],
                "receipts": receipts if receipts is not None else [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return target


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _service(root: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleRegistryVerticalSlice:
    ctx = _context(root)

    class _BoundContext:
        @classmethod
        def load(cls) -> Context:
            return ctx

    monkeypatch.setattr("lbe_guard_inspector.evidence_service.Context", _BoundContext)
    runner = ModuleRegistryGuardRunner(
        evidence_service=EvidenceService(),
        context_loader=lambda: ctx,
    )
    return ModuleRegistryVerticalSlice(runner=runner, context_loader=lambda: ctx)


def test_rule_fails_for_loaded_module_without_declaration(tmp_path: Path) -> None:
    registry = _write_registry(
        tmp_path,
        declarations=[{"id": "app.launcher"}],
        receipts=[
            {"type": "loaded", "module_id": "app.launcher", "instance_id": "app-1"},
            {"type": "loaded", "module_id": "hidden.runtime", "instance_id": "hidden-1"},
        ],
    )

    result = rule_loaded_module_registration(
        _context(tmp_path),
        {"workspace_root": str(tmp_path), "roots": ["workspace"]},
    )

    assert result.status == "failed"
    finding = result.evidence["unregistered_loaded_modules"][0]
    assert finding["module_id"] == "hidden.runtime"
    assert finding["path"] == "workspace/.lbe/module-registry.json"
    assert finding["hash"] == hashlib.sha256(registry.read_bytes()).hexdigest()
    assert result.evidence["read_only"] is True
    assert result.evidence["bounded"] is True


def test_rule_passes_when_every_loaded_module_is_declared(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        declarations=[{"id": "app.launcher"}, {"id": "browser.loop-controller"}],
        receipts=[
            {"type": "loaded", "module_id": "app.launcher", "instance_id": "app-1"},
            {
                "type": "loaded",
                "module_id": "browser.loop-controller",
                "instance_id": "loop-1",
            },
        ],
    )

    result = rule_loaded_module_registration(
        _context(tmp_path),
        {"workspace_root": str(tmp_path), "roots": ["workspace"]},
    )

    assert result.status == "passed"
    assert result.evidence["unregistered_loaded_modules"] == []
    assert len(result.evidence["registered_loaded_modules"]) == 2


def test_rule_blocks_when_loaded_receipts_are_missing_or_malformed(tmp_path: Path) -> None:
    _write_registry(tmp_path, declarations=[{"id": "app.launcher"}], receipts=[])
    missing = rule_loaded_module_registration(
        _context(tmp_path),
        {"workspace_root": str(tmp_path), "roots": ["workspace"]},
    )
    assert missing.status == "blocked"
    assert missing.evidence["supporting_findings"][0]["classification"] == "missing_loaded_receipts"

    _write_registry(
        tmp_path,
        declarations=[{"id": "app.launcher"}],
        receipts=[{"type": "loaded", "instance_id": "app-1"}],
    )
    malformed = rule_loaded_module_registration(
        _context(tmp_path),
        {"workspace_root": str(tmp_path), "roots": ["workspace"]},
    )
    assert malformed.status == "blocked"
    assert malformed.evidence["malformed_receipt_indexes"] == [0]


def test_rule_is_not_applicable_without_registry_artifact(tmp_path: Path) -> None:
    result = rule_loaded_module_registration(
        _context(tmp_path),
        {"workspace_root": str(tmp_path), "roots": ["workspace"]},
    )
    assert result.status == "not_applicable"


def test_rule_rejects_nested_workspace_scope(tmp_path: Path) -> None:
    child = tmp_path / "child"
    child.mkdir()
    with pytest.raises(Exception, match="exact configured"):
        rule_loaded_module_registration(
            _context(tmp_path),
            {"workspace_root": str(child), "roots": ["workspace"]},
        )


@pytest.mark.parametrize(
    ("declarations", "receipts", "expected"),
    [
        (
            [{"id": "app.launcher"}],
            [{"type": "loaded", "module_id": "hidden.runtime", "instance_id": "hidden-1"}],
            "FAIL",
        ),
        (
            [{"id": "app.launcher"}],
            [{"type": "loaded", "module_id": "app.launcher", "instance_id": "app-1"}],
            "PASS",
        ),
        ([{"id": "app.launcher"}], [], "INSUFFICIENT_EVIDENCE"),
    ],
)
def test_vertical_slice_preserves_verdicts_and_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declarations: list[dict],
    receipts: list[dict],
    expected: str,
) -> None:
    _write_registry(tmp_path, declarations=declarations, receipts=receipts)
    before = _tree_hash(tmp_path)

    result = _service(tmp_path, monkeypatch).run(workspace_root=str(tmp_path))

    assert result["decision"]["guard_result"]["verdict"] == expected
    assert result["authorization"]["write_allowed"] is False
    assert result["authorization"]["guard_id"] == MODULE_REGISTRY_RULE_ID
    assert result["workspace_unchanged"] is True
    assert _tree_hash(tmp_path) == before
    assert result["decision_fingerprint"]


def test_vertical_slice_is_not_applicable_without_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _service(tmp_path, monkeypatch).run(workspace_root=str(tmp_path))
    assert result["decision"]["guard_result"]["verdict"] == "NOT_APPLICABLE"
    assert result["workspace_unchanged"] is True


def test_vertical_slice_requires_exact_configured_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = tmp_path / "child"
    child.mkdir()
    with pytest.raises(Exception, match="exact configured"):
        _service(tmp_path, monkeypatch).run(workspace_root=str(child))


def test_callback_runner_behavior_remains_available() -> None:
    assert GuardRunner._rule_support_paths(
        {
            "status": "failed",
            "evidence": {"invalid_callbacks": [{"path": "workspace/panel.js"}]},
        }
    ) == {"workspace/panel.js"}
