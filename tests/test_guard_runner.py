from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.guard_inspector import (
    VERDICT_FAIL,
    VERDICT_INSUFFICIENT_EVIDENCE,
    VERDICT_NOT_APPLICABLE,
    VERDICT_PASS,
)
from lbe_guard_inspector.guard_runner import (
    GuardRunner,
    _GUARD_EVIDENCE_REQUIREMENTS,
)
from lbe_guard_inspector.workspace_identity import project_workspace_id


QUERY = "Provided callback is not a function"


class _Root:
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path


class FakeContext:
    def __init__(self, roots=()):
        self.roots = tuple(roots)


class FakeEvidenceService:
    def __init__(self, package):
        self._package = package
        self.last_kwargs = None

    def build_evidence_package(self, **kwargs):
        self.last_kwargs = kwargs
        return self._package


def _ws(ref="workspace:dev:src/app.js", configured_root="dev", relative="src/app.js"):
    return {
        "ref": ref,
        "source_type": "workspace",
        "authority": 2,
        "verified": True,
        "classification": "current_workspace",
        "workspace_id": "dev",
        "path": "C:/ws/src/app.js",
        "hash": "ws-hash",
        "metadata": {
            "configured_root": configured_root,
            "relative_path": relative,
        },
    }


def _package(workspace=None, validation=None, contradictions=None, gaps=None):
    return {
        "package_id": "ep-1",
        "task_id": "task-1",
        "query": QUERY,
        "workspace_id": "dev",
        "indexed_reference_evidence": [],
        "current_workspace_evidence": workspace if workspace is not None else [_ws()],
        "validation_evidence": validation if validation is not None else [],
        "contradictions": contradictions or [],
        "missing_evidence": gaps or [],
        "generated_at": "2026-07-25T00:00:00+00:00",
    }


def _rule(status, rule_id="cep.manifest_exists", message="m"):
    return {"rule_id": rule_id, "status": status, "message": message, "evidence": {}}


def _runner(package, rule_result, inspected_content=QUERY, roots=()):
    es = FakeEvidenceService(package)
    captured = {}

    def fake_rule_runner(pack_id, rule_id, ctx, params):
        captured["pack_id"] = pack_id
        captured["rule_id"] = rule_id
        captured["params"] = params
        return rule_result

    def fake_file_inspector(ctx, virtual):
        captured["virtual"] = virtual
        return {"content": inspected_content, "sha256": "insp-hash"}

    runner = GuardRunner(
        evidence_service=es,
        context_loader=lambda: FakeContext(roots),
        rule_runner=fake_rule_runner,
        file_inspector=fake_file_inspector,
    )
    return runner, captured


def test_run_passes_when_guard_passes_with_workspace_and_validation() -> None:
    runner, captured = _runner(_package(), _rule("passed"))
    result = runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists")
    assert result["guard_result"]["verdict"] == VERDICT_PASS
    assert result["guard_result"]["evidence_refs"] == ["workspace:dev:src/app.js"]
    val = result["evidence_package"]["validation_evidence"]
    assert len(val) == 1
    assert val[0]["source_type"] == "validation"
    assert val[0]["verified"] is True
    assert captured["virtual"] == "dev/src/app.js"


def test_run_insufficient_when_no_workspace_evidence() -> None:
    runner, _ = _runner(_package(workspace=[]), _rule("passed"))
    result = runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists")
    assert result["guard_result"]["verdict"] == VERDICT_INSUFFICIENT_EVIDENCE
    assert result["evidence_package"]["validation_evidence"] == []


def test_run_insufficient_when_validation_does_not_corroborate() -> None:
    runner, _ = _runner(_package(), _rule("passed"), inspected_content="nothing relevant here")
    result = runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists")
    assert result["guard_result"]["verdict"] == VERDICT_INSUFFICIENT_EVIDENCE
    assert result["evidence_package"]["validation_evidence"] == []


def test_run_fail_when_guard_failed_with_workspace_evidence() -> None:
    runner, _ = _runner(_package(), _rule("failed"))
    result = runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists")
    assert result["guard_result"]["verdict"] == VERDICT_FAIL


def test_run_blocked_rule_yields_insufficient() -> None:
    runner, _ = _runner(_package(), _rule("blocked"))
    result = runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists")
    assert result["guard_result"]["verdict"] == VERDICT_INSUFFICIENT_EVIDENCE


def test_run_not_applicable_passes_through() -> None:
    runner, _ = _runner(_package(), _rule("not_applicable"))
    result = runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists")
    assert result["guard_result"]["verdict"] == VERDICT_NOT_APPLICABLE


def test_run_index_only_rule_cannot_pass() -> None:
    runner, _ = _runner(_package(), _rule("passed", rule_id="generic.index_present"))
    result = runner.run(
        problem=QUERY, pack_id="generic", rule_id="generic.index_present"
    )
    assert result["guard_result"]["verdict"] == VERDICT_INSUFFICIENT_EVIDENCE


def test_run_contradictions_prevent_pass() -> None:
    runner, _ = _runner(_package(contradictions=["stale-indexed-hash at src/app.js"]), _rule("passed"))
    result = runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists")
    assert result["guard_result"]["verdict"] == VERDICT_INSUFFICIENT_EVIDENCE


def test_run_returns_full_decision_context() -> None:
    runner, _ = _runner(_package(), _rule("passed"))
    result = runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists")
    assert set(result) == {"task", "evidence_package", "rule_result", "guard_result"}
    assert result["task"]["mode"] == "inspect"
    assert result["task"]["write_allowed"] is False
    assert result["rule_result"]["status"] == "passed"
    assert "guard_result" in result


def test_run_rejects_empty_problem() -> None:
    runner, _ = _runner(_package(), _rule("passed"))
    with pytest.raises(ValueError):
        runner.run(problem="", pack_id="cep", rule_id="cep.manifest_exists")


def test_run_requires_pack_and_rule_ids() -> None:
    runner, _ = _runner(_package(), _rule("passed"))
    with pytest.raises(ValueError):
        runner.run(problem=QUERY, pack_id="", rule_id="cep.manifest_exists")
    with pytest.raises(ValueError):
        runner.run(problem=QUERY, pack_id="cep", rule_id="")


def test_rule_runner_receives_resolved_roots_param(tmp_path) -> None:
    root = _Root("dev", tmp_path)
    runner, captured = _runner(_package(), _rule("passed"), roots=(root,))
    runner.run(problem=QUERY, pack_id="cep", rule_id="cep.manifest_exists", roots=["dev"])
    assert captured["params"]["roots"] == ["dev"]
    assert captured["pack_id"] == "cep"
    assert captured["rule_id"] == "cep.manifest_exists"


def test_resolve_root_name_via_workspace_root(tmp_path) -> None:
    ws = tmp_path / "project"
    ws.mkdir()
    root = _Root("dev", tmp_path)
    runner, _ = _runner(_package(), _rule("passed"), roots=(root,))
    result = runner.run(
        problem=QUERY,
        pack_id="cep",
        rule_id="cep.manifest_exists",
        workspace_root=str(ws),
    )
    assert result["guard_result"]["verdict"] == VERDICT_PASS

def test_rule_runner_receives_canonical_workspace_identity(tmp_path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()

    expected_id = project_workspace_id(
        workspace,
        "Readable Project",
    )

    package = _package()
    package["workspace_id"] = expected_id
    package["current_workspace_evidence"][0]["workspace_id"] = expected_id

    configured_root = _Root("dev", tmp_path)
    runner, captured = _runner(
        package,
        _rule("passed"),
        roots=(configured_root,),
    )

    result = runner.run(
        problem=QUERY,
        pack_id="cep",
        rule_id="cep.manifest_exists",
        workspace_root=str(workspace),
        workspace_id="Readable Project",
        retrieval_mode="guard",
    )

    canonical = workspace.resolve()

    assert result["task"]["workspace_root"] == str(canonical)
    assert result["task"]["workspace_id"] == expected_id

    evidence_kwargs = runner.evidence_service.last_kwargs
    assert evidence_kwargs["workspace_root"] == str(canonical)
    assert evidence_kwargs["workspace_id"] == expected_id

    assert captured["params"]["workspace_root"] == str(canonical)
    assert captured["params"]["workspace_id"] == expected_id

def test_guard_mode_uses_exact_rule_evidence_requirements(tmp_path) -> None:
    expected = {
        "cep.manifest_exists": {
            "path_patterns": ["CSXS/manifest.xml"],
            "extensions": [".xml"],
            "content_search": False,
        },
        "cep.host_version": {
            "path_patterns": ["CSXS/manifest.xml"],
            "extensions": [".xml"],
            "content_search": False,
        },
        "cep.menubar_extension": {
            "path_patterns": ["CSXS/manifest.xml"],
            "extensions": [".xml"],
            "content_search": False,
        },
        "cep.symlink_free": {
            "path_patterns": [],
            "extensions": [],
            "content_search": False,
        },
    }

    assert _GUARD_EVIDENCE_REQUIREMENTS == expected

    workspace = tmp_path / "project"
    workspace.mkdir()

    configured_root = _Root("dev", tmp_path)
    runner, _ = _runner(
        _package(),
        _rule("passed"),
        roots=(configured_root,),
    )

    runner.run(
        problem=QUERY,
        pack_id="cep",
        rule_id="cep.manifest_exists",
        workspace_root=str(workspace),
        retrieval_mode="guard",
        extensions=[".py"],
        path_patterns=["wrong/path.py"],
        content_search=True,
    )

    evidence_kwargs = runner.evidence_service.last_kwargs

    assert evidence_kwargs["extensions"] == [".xml"]
    assert evidence_kwargs["path_patterns"] == ["CSXS/manifest.xml"]
    assert evidence_kwargs["content_search"] is False
