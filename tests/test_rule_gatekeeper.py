from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent import Context, KnowledgeRoot
from lbe_guard_inspector.rule_gatekeeper import (
    RuleGatekeeper,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_PROPOSAL_READY,
)
from lbe_guard_inspector.workspace_identity import resolve_workspace_identity


def _context(root: Path) -> Context:
    return Context(config={}, governance={}, roots=(KnowledgeRoot("dev", root),))


def _gatekeeper(root: Path, resolver=None) -> RuleGatekeeper:
    def registered(pack_id, rule_id):
        if (pack_id, rule_id) == ("generic", "generic.test"):
            return object()
        raise ValueError("unregistered")
    return RuleGatekeeper(
        context=_context(root), rule_resolver=resolver or registered,
        clock=lambda: datetime(2026, 7, 30, tzinfo=timezone.utc),
    )


def _inputs(root: Path):
    (root / "profile.json").write_text('{"rules": {}}', encoding="utf-8")
    source = root / "src.py"
    if not source.exists():
        source.write_text("value = 1\n", encoding="utf-8")
    identity = resolve_workspace_identity(_context(root), root)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    guard = {
        "result_id": "result-1", "guard_id": "generic.test", "guard_version": None,
        "workspace_id": identity.workspace_id, "verdict": "FAIL", "summary": "missing deterministic rule",
        "findings": ["missing"], "evidence_refs": ["workspace"], "validation_refs": [],
        "governance_state": "READ_ONLY", "executed_at": "2026-07-30T00:00:00+00:00",
    }
    package = {
        "package_id": "ep-1", "task_id": "task-1", "query": "src.py", "workspace_id": identity.workspace_id,
        "indexed_reference_evidence": [],
        "current_workspace_evidence": [{
            "ref": "workspace", "source_type": "workspace", "record_id": None,
            "workspace_id": identity.workspace_id, "path": str(source), "hash": digest,
            "line_start": 1, "line_end": 1, "snippet": "value", "score": None,
            "matched_terms": [], "exact_phrase": None, "authority": 9,
            "verified": True, "classification": "source", "metadata": {},
        }],
        "validation_evidence": [], "contradictions": [], "missing_evidence": [],
        "generated_at": "2026-07-30T00:00:00+00:00",
    }
    return identity, guard, package


def _propose(gatekeeper: RuleGatekeeper, root: Path, **overrides):
    _, guard, package = _inputs(root)
    return gatekeeper.propose_rule(**_proposal_arguments(root, guard, package, **overrides))


def _proposal_arguments(root: Path, guard, package, **overrides):
    values = {
        "workspace_root": root, "pack_id": "generic", "guard_result": guard,
        "evidence_package": package, "governance_state": "READ_ONLY",
        "target_profile_path": "profile.json", "trigger": "missing deterministic protection",
        "rationale": "current guard evidence requires a proposal", "scope": ["src.py"],
        "required_action": "Define a deterministic guard.", "severity": "error", "exceptions": [],
        "equivalent_rule_result": "NONE", "contradiction_result": "NONE",
        "validation_plan": ["run focused validation"], "rollback_plan": ["do not apply"],
        "provenance": {"request_id": "request-1"},
    }
    values.update(overrides)
    return values


def test_identical_authoritative_inputs_have_deterministic_id(tmp_path: Path):
    gatekeeper = _gatekeeper(tmp_path)
    assert _propose(gatekeeper, tmp_path)["proposal"]["proposal_id"] == _propose(gatekeeper, tmp_path)["proposal"]["proposal_id"]


def test_workspace_scope_evidence_hash_and_profile_change_id(tmp_path: Path):
    gatekeeper = _gatekeeper(tmp_path)
    base = _propose(gatekeeper, tmp_path)["proposal"]["proposal_id"]
    assert _propose(gatekeeper, tmp_path, scope=["other.py"])["proposal"]["proposal_id"] != base
    (tmp_path / "other.json").write_text("{}", encoding="utf-8")
    assert _propose(gatekeeper, tmp_path, target_profile_path="other.json")["proposal"]["proposal_id"] != base
    (tmp_path / "src.py").write_text("changed = 1\n", encoding="utf-8")
    assert _propose(gatekeeper, tmp_path)["proposal"]["proposal_id"] != base


def test_different_workspace_changes_proposal_id(tmp_path: Path):
    first_root, second_root = tmp_path / "one", tmp_path / "two"
    first_root.mkdir(); second_root.mkdir()
    first = _propose(_gatekeeper(first_root), first_root)["proposal"]
    second = _propose(_gatekeeper(second_root), second_root)["proposal"]
    assert first["workspace_id"] != second["workspace_id"]
    assert first["proposal_id"] != second["proposal_id"]


def test_identity_and_reference_only_evidence_are_rejected(tmp_path: Path):
    gatekeeper = _gatekeeper(tmp_path)
    identity, guard, package = _inputs(tmp_path)
    guard["workspace_id"] = "workspace_wrong"
    assert _propose(gatekeeper, tmp_path, guard_result=guard, evidence_package=package)["status"] == STATUS_INSUFFICIENT_EVIDENCE
    _, guard, package = _inputs(tmp_path)
    package["current_workspace_evidence"] = []
    package["indexed_reference_evidence"] = [{
        "ref": "index:1", "source_type": "index", "record_id": 1, "workspace_id": identity.workspace_id,
        "path": None, "hash": None, "line_start": None, "line_end": None, "snippet": None,
        "score": 1, "matched_terms": [], "exact_phrase": None, "authority": 1, "verified": False,
        "classification": "reference", "metadata": {},
    }]
    assert _propose(gatekeeper, tmp_path, guard_result=guard, evidence_package=package)["status"] == STATUS_INSUFFICIENT_EVIDENCE


def test_proposal_preserves_contract_fields_and_does_not_write(tmp_path: Path):
    gatekeeper = _gatekeeper(tmp_path)
    _, guard, package = _inputs(tmp_path)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = gatekeeper.propose_rule(**_proposal_arguments(tmp_path, guard, package))
    proposal = result["proposal"]
    assert result["status"] == STATUS_PROPOSAL_READY
    assert proposal["pack_id"] == "generic" and proposal["target_profile_path"] == "profile.json"
    assert proposal["equivalent_rule_result"] == "NONE" and proposal["contradiction_result"] == "NONE"
    assert proposal["source_hashes"] and proposal["provenance"]["source_guard_id"] == "generic.test"
    assert result["runtime_mutations_performed"] is False
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir()}


def test_revalidation_rejects_changed_identity_missing_and_superseded_evidence(tmp_path: Path):
    gatekeeper = _gatekeeper(tmp_path)
    proposal = _propose(gatekeeper, tmp_path)["proposal"]
    assert gatekeeper.revalidate_proposal(workspace_root=tmp_path, proposal=proposal)["status"] == STATUS_PROPOSAL_READY
    (tmp_path / "src.py").write_text("changed\n", encoding="utf-8")
    assert gatekeeper.revalidate_proposal(workspace_root=tmp_path, proposal=proposal)["status"] == STATUS_INSUFFICIENT_EVIDENCE
    (tmp_path / "src.py").unlink()
    assert gatekeeper.revalidate_proposal(workspace_root=tmp_path, proposal=proposal)["status"] == STATUS_INSUFFICIENT_EVIDENCE
    rejected = _gatekeeper(tmp_path, resolver=lambda *_: (_ for _ in ()).throw(ValueError("removed")))
    assert rejected.revalidate_proposal(workspace_root=tmp_path, proposal=proposal)["status"] == STATUS_INSUFFICIENT_EVIDENCE
    assert gatekeeper.revalidate_proposal(workspace_root=tmp_path, proposal={**proposal, "workspace_id": "workspace_other"})["status"] == STATUS_INSUFFICIENT_EVIDENCE


def test_apply_is_explicitly_blocked(tmp_path: Path):
    gatekeeper = _gatekeeper(tmp_path)
    proposal = _propose(gatekeeper, tmp_path)["proposal"]
    with pytest.raises(PermissionError, match="read-only"):
        gatekeeper.apply_proposal(proposal)


def test_inspect_and_revalidate_are_read_only(tmp_path: Path):
    gatekeeper = _gatekeeper(tmp_path)
    identity, guard, package = _inputs(tmp_path)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    inspection = gatekeeper.inspect(
        workspace_root=tmp_path, pack_id="generic", guard_result=guard,
        evidence_package=package, governance_state="READ_ONLY",
    )
    proposal = gatekeeper.propose_rule(**_proposal_arguments(tmp_path, guard, package))["proposal"]
    assert inspection["workspace_id"] == identity.workspace_id
    assert gatekeeper.revalidate_proposal(workspace_root=tmp_path, proposal=proposal)["runtime_mutations_performed"] is False
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir()}
