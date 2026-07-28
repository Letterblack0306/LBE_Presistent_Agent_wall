from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from lbe_guard_inspector.callback_vertical_slice import (
    CALLBACK_PACK_ID,
    CALLBACK_PROBLEM,
    CALLBACK_RULE_ID,
    CallbackVerticalSlice,
)


class _Runner:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.calls: list[dict] = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _context(root: Path):
    return SimpleNamespace(roots=(SimpleNamespace(name="workspace", path=root),))


def _decision(verdict: str = "FAIL") -> dict:
    workspace_ref = "workspace:workspace:src/panel.js:abc"
    validation_ref = "validation:workspace_corroboration:workspace/src/panel.js"
    return {
        "task": {
            "task_id": "task-1",
            "problem": CALLBACK_PROBLEM,
            "workspace_id": "workspace",
            "workspace_root": "unused",
            "mode": "inspect",
            "write_allowed": False,
            "constraints": [],
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        "evidence_package": {
            "workspace_id": "workspace",
            "current_workspace_evidence": [
                {
                    "ref": workspace_ref,
                    "source_type": "workspace",
                    "path": "workspace/src/panel.js",
                    "hash": "abc",
                    "line_start": 4,
                    "line_end": 4,
                    "snippet": "cs.evalScript(payload, null);",
                }
            ],
            "validation_evidence": [
                {
                    "ref": validation_ref,
                    "source_type": "validation",
                    "path": "workspace/src/panel.js",
                    "hash": "abc",
                    "line_start": 4,
                    "line_end": 4,
                    "snippet": "cs.evalScript(payload, null);",
                }
            ],
            "indexed_evidence": [
                {
                    "ref": "indexed:reference-only",
                    "source_type": "indexed",
                    "path": "reference/panel.js",
                }
            ],
        },
        "rule_result": {
            "rule_id": CALLBACK_RULE_ID,
            "status": "failed" if verdict == "FAIL" else "passed",
            "message": "deterministic result",
            "evidence": {},
            "severity": "error",
            "required": True,
            "fast_fail": False,
        },
        "guard_result": {
            "result_id": "random-result-id",
            "guard_id": CALLBACK_RULE_ID,
            "guard_version": None,
            "workspace_id": "workspace",
            "verdict": verdict,
            "summary": f"{verdict}: callback contract result",
            "findings": ["deterministic result"],
            "evidence_refs": [workspace_ref],
            "validation_refs": [validation_ref],
            "governance_state": "READ_ONLY",
            "executed_at": "2026-01-01T00:00:00+00:00",
        },
    }


def test_fixed_registered_guard_and_exact_workspace_selection(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runner = _Runner(_decision())
    service = CallbackVerticalSlice(runner=runner, context_loader=lambda: _context(tmp_path))

    result = service.run(workspace_root=str(project))

    call = runner.calls[0]
    assert call["problem"] == CALLBACK_PROBLEM
    assert call["pack_id"] == CALLBACK_PACK_ID
    assert call["rule_id"] == CALLBACK_RULE_ID
    assert call["roots"] == ["workspace"]
    assert call["workspace_root"] == str(project.resolve())
    assert result["authorization"]["write_allowed"] is False
    assert result["authorization"]["authorized"] is True


def test_reference_evidence_cannot_enter_explanation_citations(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    service = CallbackVerticalSlice(
        runner=_Runner(_decision()), context_loader=lambda: _context(tmp_path)
    )

    result = service.run(workspace_root=str(project))

    refs = [item["ref"] for item in result["explanation"]["citations"]]
    assert "indexed:reference-only" not in refs
    assert refs == sorted(
        result["decision"]["guard_result"]["evidence_refs"]
        + result["decision"]["guard_result"]["validation_refs"]
    )


def test_identical_semantic_decision_has_identical_fingerprint(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    first = _decision()
    second = _decision()
    second["guard_result"]["result_id"] = "different-random-id"
    second["guard_result"]["executed_at"] = "2026-02-01T00:00:00+00:00"

    one = CallbackVerticalSlice(
        runner=_Runner(first), context_loader=lambda: _context(tmp_path)
    ).run(workspace_root=str(project))
    two = CallbackVerticalSlice(
        runner=_Runner(second), context_loader=lambda: _context(tmp_path)
    ).run(workspace_root=str(project))

    assert one["decision_fingerprint"] == two["decision_fingerprint"]


def test_workspace_mutation_is_rejected(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    target = project / "panel.js"
    target.write_text("before", encoding="utf-8")

    class MutatingRunner(_Runner):
        def run(self, **kwargs):
            target.write_text("after", encoding="utf-8")
            return super().run(**kwargs)

    service = CallbackVerticalSlice(
        runner=MutatingRunner(_decision()), context_loader=lambda: _context(tmp_path)
    )
    with pytest.raises(RuntimeError, match="changed the target workspace"):
        service.run(workspace_root=str(project))


def test_outside_configured_roots_is_rejected(tmp_path: Path) -> None:
    configured = tmp_path / "configured"
    configured.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    service = CallbackVerticalSlice(
        runner=_Runner(_decision()), context_loader=lambda: _context(configured)
    )

    with pytest.raises(Exception, match="outside configured knowledge roots"):
        service.run(workspace_root=str(outside))
