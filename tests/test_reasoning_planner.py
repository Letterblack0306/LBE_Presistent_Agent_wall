from pathlib import Path

import pytest

from lbe_guard_inspector.reasoning_contracts import EvidenceRequest, ReasoningPlan
from lbe_guard_inspector.reasoning_planner import ReasoningPolicy, RetrievalMode


def _guard_contract():
    return {
        "path_patterns": ["CSXS/manifest.xml"],
        "extensions": [".xml"],
        "evidence_requirements": ["canonical CEP manifest"],
    }


def test_diagnostic_mode_preserves_literal_problem_query():
    policy = ReasoningPolicy()
    result = policy.build_retrieval_plan(
        problem="Why did the browser agent fail?",
        workspace_id="workspace-1",
    )
    assert result.mode is RetrievalMode.DIAGNOSTIC
    assert result.query == "Why did the browser agent fail?"
    assert result.semantic_search is True
    assert result.rule_id is None


def test_guard_mode_uses_registered_path_not_reason_or_problem():
    policy = ReasoningPolicy()
    result = policy.build_retrieval_plan(
        problem="Search the workspace because this rule requires a manifest",
        workspace_id="workspace-1",
        selected_guard_id="cep.manifest_exists",
        evidence_requests=(
            EvidenceRequest(
                tool_id="workspace.read",
                path="CSXS/manifest.xml",
                reason="planning text that must not become the query",
            ),
        ),
        guard_contract=_guard_contract(),
    )
    assert result.mode is RetrievalMode.GUARD
    assert result.query == "CSXS/manifest.xml"
    assert result.reason == "inspect registered evidence for cep.manifest_exists"
    assert result.path_patterns == ("CSXS/manifest.xml",)
    assert result.extensions == (".xml",)
    assert result.semantic_search is False
    assert "planning text" not in result.query
    assert "because" not in result.query


def test_guard_mode_requires_registered_evidence_contract():
    policy = ReasoningPolicy()
    with pytest.raises(ValueError, match="registered evidence contract"):
        policy.build_retrieval_plan(
            problem="Inspect",
            workspace_id="workspace-1",
            selected_guard_id="cep.manifest_exists",
        )


def test_investigation_mode_keeps_seed_refs_and_scopes_query():
    policy = ReasoningPolicy()
    result = policy.build_retrieval_plan(
        problem="Why did cep.manifest_exists fail?",
        workspace_id="workspace-1",
        seed_evidence_refs=("guard:1", "guard:1", "validation:2"),
    )
    assert result.mode is RetrievalMode.INVESTIGATION
    assert result.query == "Why did cep.manifest_exists fail?"
    assert result.seed_evidence_refs == ("guard:1", "validation:2")
    assert result.semantic_search is True


def test_evidence_plan_reports_declared_missing_requirements():
    policy = ReasoningPolicy()
    result = policy.plan_evidence(
        guard_contract=_guard_contract(),
        evidence_package={
            "indexed_reference_evidence": [],
            "current_workspace_evidence": [],
            "validation_evidence": [],
            "missing_evidence": ["canonical CEP manifest"],
        },
    )
    assert result.required == ("canonical CEP manifest",)
    assert result.missing == ("canonical CEP manifest",)
    assert result.complete is False


def test_evidence_plan_satisfied_by_exact_path_match():
    policy = ReasoningPolicy()
    result = policy.plan_evidence(
        guard_contract=_guard_contract(),
        evidence_package={
            "indexed_reference_evidence": [],
            "current_workspace_evidence": [
                {
                    "path": "CSXS/manifest.xml",
                    "source_type": "workspace",
                    "authority": 9,
                    "verified": True,
                    "classification": "source",
                },
            ],
            "validation_evidence": [],
            "missing_evidence": [],
        },
    )
    assert result.missing == ()
    assert result.complete is True


def test_evidence_plan_satisfied_by_glob_pattern():
    policy = ReasoningPolicy()
    result = policy.plan_evidence(
        guard_contract={**_guard_contract(), "path_patterns": ["**/manifest.xml"]},
        evidence_package={
            "indexed_reference_evidence": [],
            "current_workspace_evidence": [
                {
                    "path": "a/b/CSXS/manifest.xml",
                    "source_type": "workspace",
                    "authority": 9,
                    "verified": True,
                    "classification": "source",
                },
            ],
            "validation_evidence": [],
            "missing_evidence": [],
        },
    )
    assert result.missing == ()
    assert result.complete is True


def test_evidence_plan_normalizes_windows_path_separators():
    policy = ReasoningPolicy()
    result = policy.plan_evidence(
        guard_contract=_guard_contract(),
        evidence_package={
            "indexed_reference_evidence": [],
            "current_workspace_evidence": [
                {
                    "path": r"CSXS\manifest.xml",
                    "source_type": "workspace",
                    "authority": 9,
                    "verified": True,
                    "classification": "source",
                },
            ],
            "validation_evidence": [],
            "missing_evidence": [],
        },
    )
    assert result.missing == ()
    assert result.complete is True


def test_evidence_plan_unrelated_path_does_not_match():
    policy = ReasoningPolicy()
    result = policy.plan_evidence(
        guard_contract=_guard_contract(),
        evidence_package={
            "indexed_reference_evidence": [],
            "current_workspace_evidence": [
                {
                    "path": "src/app.py",
                    "source_type": "workspace",
                    "authority": 9,
                    "verified": True,
                    "classification": "source",
                },
            ],
            "validation_evidence": [],
            "missing_evidence": [],
        },
    )
    assert result.missing == ("canonical CEP manifest",)
    assert result.complete is False


def test_evidence_plan_multiple_requirements_satisfied_by_single_path_match():
    policy = ReasoningPolicy()
    result = policy.plan_evidence(
        guard_contract={
            "path_patterns": ["CSXS/manifest.xml"],
            "extensions": [".xml"],
            "evidence_requirements": [
                "canonical CEP manifest",
                "bounded project metadata",
            ],
        },
        evidence_package={
            "indexed_reference_evidence": [],
            "current_workspace_evidence": [
                {
                    "path": "CSXS/manifest.xml",
                    "source_type": "workspace",
                    "authority": 9,
                    "verified": True,
                    "classification": "source",
                },
            ],
            "validation_evidence": [],
            "missing_evidence": [],
        },
    )
    assert result.missing == ()
    assert result.complete is True


def test_conflict_resolver_prefers_verified_higher_authority():
    policy = ReasoningPolicy()
    result = policy.resolve_conflicts([
        {
            "ref": "reference:old",
            "source_type": "reference",
            "path": "CSXS/manifest.xml",
            "hash": "a" * 64,
            "verified": False,
            "authority": 2,
        },
        {
            "ref": "workspace:current",
            "source_type": "reference",
            "path": "CSXS/manifest.xml",
            "hash": "b" * 64,
            "verified": True,
            "authority": 9,
        },
    ])
    assert result.selected_refs == ("workspace:current",)
    assert result.unresolved_refs == ()
    assert result.stop_required is False


def test_conflict_resolver_stops_on_equal_authority_different_hashes():
    policy = ReasoningPolicy()
    result = policy.resolve_conflicts([
        {
            "ref": "workspace:first",
            "source_type": "workspace",
            "path": "src/app.py",
            "hash": "a" * 64,
            "verified": True,
            "authority": 9,
        },
        {
            "ref": "workspace:second",
            "source_type": "workspace",
            "path": "src/app.py",
            "hash": "b" * 64,
            "verified": True,
            "authority": 9,
        },
    ])
    assert set(result.unresolved_refs) == {"workspace:first", "workspace:second"}
    assert result.stop_required is True


def test_evidence_request_validation_rejects_unknown_tool_and_escape(tmp_path):
    policy = ReasoningPolicy()
    with pytest.raises(ValueError, match="unapproved evidence tool"):
        policy.validate_evidence_requests(
            requests=(EvidenceRequest("shell.execute", "src/app.py", "bad"),),
            workspace_root=tmp_path,
            approved_tools=("workspace.read",),
        )
    with pytest.raises(ValueError, match="escapes workspace"):
        policy.validate_evidence_requests(
            requests=(EvidenceRequest("workspace.read", "../outside.py", "bad"),),
            workspace_root=tmp_path,
            approved_tools=("workspace.read",),
        )


def test_explanation_focus_defaults_to_evidence_bounded_topics():
    policy = ReasoningPolicy()
    plan = ReasoningPlan(
        interpreted_problem="Inspect",
        ambiguities=(),
        candidate_guard_ids=(),
        evidence_requests=(),
        validation_requests=(),
        explanation_focus=(),
    )
    assert policy.normalize_explanation_focus(plan) == (
        "why the guard applies",
        "evidence checked",
        "deterministic verdict",
        "missing evidence",
        "validation state",
    )
