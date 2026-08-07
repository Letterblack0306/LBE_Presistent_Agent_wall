from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from agent import Context, KnowledgeRoot
from lbe_guard_inspector.proposal_planner import ProposalPlanner
from lbe_guard_inspector.rule_gatekeeper import RuleGatekeeper
from lbe_guard_inspector.workspace_identity import resolve_workspace_identity


def _context(root: Path) -> Context:
    return Context(config={}, governance={}, roots=(KnowledgeRoot("dev", root),))


def _gatekeeper(root: Path) -> RuleGatekeeper:
    def registered(pack_id, rule_id):
        if (pack_id, rule_id) == ("generic", "generic.test"):
            return object()
        raise ValueError("unregistered")
    return RuleGatekeeper(
        context=_context(root), rule_resolver=registered,
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


def _candidate(**overrides):
    values = {
        "target_profile_path": "profile.json",
        "trigger": "missing deterministic protection",
        "rationale": "current guard evidence requires a proposal",
        "scope": ["src.py"],
        "required_action": "Define a deterministic guard.",
        "severity": "error",
        "exceptions": [],
        "validation_plan": ["run focused validation"],
        "rollback_plan": ["do not apply"],
    }
    values.update(overrides)
    return values


def _build(root: Path, **overrides):
    planner = ProposalPlanner(_gatekeeper(root))
    _, guard, package = _inputs(root)
    kwargs = dict(
        workspace_root=root, pack_id="generic", guard_result=guard,
        evidence_package=package, governance_state="READ_ONLY",
        candidate=_candidate(), provenance={"source": "deterministic"},
        equivalent_rule_result="NONE", contradiction_result="NONE",
    )
    kwargs.update(overrides)
    return planner.build(**kwargs)


def test_build_generates_read_only_deterministic_proposal(tmp_path: Path):
    outcome = _build(tmp_path)
    assert outcome.executable is True
    assert outcome.stop_reason is None
    assert outcome.read_only is True
    assert outcome.proposal["approval_required"] is True
    assert outcome.proposal["workspace_id"]
    assert outcome.proposal["equivalent_rule_checked"] is True


def test_build_is_deterministic_for_identical_inputs(tmp_path: Path):
    assert _build(tmp_path).proposal["proposal_id"] == _build(tmp_path).proposal["proposal_id"]


def test_build_never_writes_workspace(tmp_path: Path):
    _, guard, package = _inputs(tmp_path)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    _build(tmp_path, guard_result=guard, evidence_package=package)
    after = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert before == after


def test_build_rejects_forbidden_authority_fields(tmp_path: Path):
    outcome = _build(tmp_path, candidate=_candidate(apply="now"))
    assert outcome.executable is False
    assert outcome.stop_reason == "INVALID_PROPOSAL_CANDIDATE"
    assert outcome.read_only is True


def test_build_rejects_invalid_severity(tmp_path: Path):
    outcome = _build(tmp_path, candidate=_candidate(severity="critical"))
    assert outcome.stop_reason == "INVALID_PROPOSAL_CANDIDATE"


def test_build_rejects_escaping_scope_path(tmp_path: Path):
    outcome = _build(tmp_path, candidate=_candidate(scope=["../escape.py"]))
    assert outcome.stop_reason == "INVALID_PROPOSAL_CANDIDATE"


def test_build_stops_on_reference_only_evidence(tmp_path: Path):
    _, guard, package = _inputs(tmp_path)
    package["indexed_reference_evidence"] = [{
        "ref": "index:1", "source_type": "index", "record_id": 1, "workspace_id": guard["workspace_id"],
        "path": None, "hash": None, "line_start": None, "line_end": None, "snippet": None,
        "score": 1, "matched_terms": [], "exact_phrase": None, "authority": 1, "verified": False,
        "classification": "reference", "metadata": {},
    }]
    package["current_workspace_evidence"] = []
    outcome = _build(tmp_path, guard_result=guard, evidence_package=package)
    assert outcome.executable is False
    assert outcome.stop_reason == "INSUFFICIENT_EVIDENCE"
    assert outcome.read_only is True
