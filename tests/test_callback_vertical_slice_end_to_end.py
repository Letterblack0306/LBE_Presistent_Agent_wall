from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agent import Context, KnowledgeRoot
from lbe_guard_inspector.callback_vertical_slice import CallbackVerticalSlice
from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.guard_runner import GuardRunner

# Importing the pack performs its deterministic programmatic registration.
import rules.cep_callback  # noqa: F401


def _context(root: Path) -> Context:
    return Context(
        config={
            "max_file_bytes": 1_000_000,
            "exclude_patterns": [],
        },
        governance={},
        roots=(KnowledgeRoot("workspace", root),),
    )


def _service(root: Path, monkeypatch: pytest.MonkeyPatch) -> CallbackVerticalSlice:
    ctx = _context(root)

    class _BoundContext:
        @classmethod
        def load(cls) -> Context:
            return ctx

    monkeypatch.setattr(
        "lbe_guard_inspector.evidence_service.Context",
        _BoundContext,
    )
    runner = GuardRunner(
        evidence_service=EvidenceService(),
        context_loader=lambda: ctx,
    )
    return CallbackVerticalSlice(runner=runner, context_loader=lambda: ctx)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _write_panel(path: Path, callback: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// Provided callback is not a function\n"
        "const payload = 'work';\n"
        f"cs.evalScript(payload, {callback});\n",
        encoding="utf-8",
    )


def test_real_pipeline_reports_fail_and_selects_exact_duplicate_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "project"
    _write_panel(target / "client" / "panel.js", "null")
    _write_panel(target / "reference" / "panel.js", "function () { return true; }")
    before = _tree_hash(target)

    result = _service(tmp_path, monkeypatch).run(workspace_root=str(target))

    assert result["decision"]["guard_result"]["verdict"] == "FAIL"
    assert result["decision"]["rule_result"]["status"] == "failed"
    invalid = result["decision"]["rule_result"]["evidence"]["invalid_callbacks"]
    assert [item["path"] for item in invalid] == ["workspace/project/client/panel.js"]
    assert result["authorization"]["write_allowed"] is False
    assert _tree_hash(target) == before

    citations = result["explanation"]["citations"]
    assert citations
    assert all(item["source_type"] in {"workspace", "validation"} for item in citations)
    assert all(item["hash"] for item in citations)
    assert all(item["path"] == "workspace/project/client/panel.js" for item in citations)


def test_real_pipeline_reports_pass_for_inline_function(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "project"
    _write_panel(target / "panel.js", "function (result) { return result; }")

    result = _service(tmp_path, monkeypatch).run(workspace_root=str(target))

    assert result["decision"]["guard_result"]["verdict"] == "PASS"
    assert result["decision"]["rule_result"]["status"] == "passed"
    assert result["decision"]["guard_result"]["validation_refs"]
    assert result["authorization"]["governance_state"] == "READ_ONLY"


def test_real_pipeline_reports_insufficient_for_unresolved_identifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "project"
    _write_panel(target / "panel.js", "onResult")

    result = _service(tmp_path, monkeypatch).run(workspace_root=str(target))

    assert result["decision"]["guard_result"]["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert result["decision"]["rule_result"]["status"] == "blocked"
    assert result["authorization"]["governance_state"] == "INCOMPLETE"


def test_real_pipeline_reports_not_applicable_for_irrelevant_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "project"
    target.mkdir()
    (target / "panel.js").write_text(
        "// Provided callback is not a function\nconst value = 1;\n",
        encoding="utf-8",
    )

    result = _service(tmp_path, monkeypatch).run(workspace_root=str(target))

    assert result["decision"]["guard_result"]["verdict"] == "NOT_APPLICABLE"
    assert result["decision"]["rule_result"]["status"] == "not_applicable"


def test_identical_real_workspace_state_has_identical_semantic_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "project"
    _write_panel(target / "panel.js", "null")
    service = _service(tmp_path, monkeypatch)

    first = service.run(workspace_root=str(target))
    second = service.run(workspace_root=str(target))

    assert first["decision_fingerprint"] == second["decision_fingerprint"]
