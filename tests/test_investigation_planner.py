from __future__ import annotations

import pytest

from lbe_guard_inspector.investigation_planner import InvestigationPlanner


def _seed(**overrides):
    value = {
        "ref": "guard:1",
        "source_type": "guard_result",
        "verified": True,
        "path": "src/service.py",
        "metadata": {
            "callers": ["src/controller.py"],
            "handlers": ["src/handler.py"],
            "dependencies": ["src/dependency.py"],
            "owners": ["src/owner.py"],
            "tests": ["tests/test_service.py"],
        },
    }
    value.update(overrides)
    return value


def test_requires_existing_failure_or_evidence_seed():
    plan = InvestigationPlanner().build(workspace_id="ws-1", seeds=[])
    assert plan.stop_reason == "MISSING_INVESTIGATION_SEED"
    assert not plan.executable
    assert plan.requests == ()


def test_rejects_unverified_seed():
    plan = InvestigationPlanner().build(
        workspace_id="ws-1",
        seeds=[_seed(verified=False)],
    )
    assert plan.stop_reason == "UNVERIFIED_OR_NONCURRENT_SEED"
    assert not plan.executable


def test_rejects_reference_corpus_as_current_seed():
    plan = InvestigationPlanner().build(
        workspace_id="ws-1",
        seeds=[_seed(source_type="indexed_reference_evidence")],
    )
    assert plan.stop_reason == "UNVERIFIED_OR_NONCURRENT_SEED"
    assert plan.requests == ()


def test_expands_only_explicit_relations_from_verified_seed():
    plan = InvestigationPlanner().build(workspace_id="ws-1", seeds=[_seed()])
    assert plan.executable
    assert plan.stop_reason is None
    assert [request.relation for request in plan.requests] == [
        "callers",
        "handlers",
        "dependencies",
        "owners",
        "tests",
    ]
    assert plan.requests[0].query == "src/controller.py"
    assert plan.requests[0].path_patterns == ("src/controller.py",)
    assert plan.requests[0].semantic_search is False
    assert plan.requests[0].workspace_id == "ws-1"
    assert plan.requests[0].seed_refs == ("guard:1",)


def test_reason_text_does_not_become_query():
    seed = _seed()
    seed["metadata"] = {"related_paths": ["src/exact.py"]}
    plan = InvestigationPlanner().build(workspace_id="ws-1", seeds=[seed])
    request = plan.requests[0]
    assert request.query == "src/exact.py"
    assert request.reason == "inspect related_paths linked from verified seed guard:1"
    assert request.reason not in request.query


def test_normalizes_windows_paths_and_derives_extensions():
    seed = _seed()
    seed["metadata"] = {
        "handlers": [r"src\handlers\main.py", r"src\handlers\types.pyi"],
    }
    plan = InvestigationPlanner().build(workspace_id="ws-1", seeds=[seed])
    request = plan.requests[0]
    assert request.path_patterns == ("src/handlers/main.py", "src/handlers/types.pyi")
    assert request.extensions == (".py", ".pyi")


def test_rejects_path_escape_in_relation():
    seed = _seed()
    seed["metadata"] = {"dependencies": ["../outside.py"]}
    with pytest.raises(ValueError, match="escapes workspace"):
        InvestigationPlanner().build(workspace_id="ws-1", seeds=[seed])


def test_stops_when_seed_has_no_bounded_relations():
    seed = _seed()
    seed["metadata"] = {}
    plan = InvestigationPlanner().build(workspace_id="ws-1", seeds=[seed])
    assert plan.stop_reason == "NO_BOUNDED_RELATIONS"
    assert not plan.executable


def test_request_count_is_bounded():
    plan = InvestigationPlanner().build(
        workspace_id="ws-1",
        seeds=[_seed()],
        max_requests=2,
    )
    assert len(plan.requests) == 2
    assert [request.relation for request in plan.requests] == ["callers", "handlers"]


def test_accepts_verified_validation_failure_seed():
    seed = _seed(
        ref="validation:1",
        source_type="validation_failure",
        metadata={"tests": ["tests/test_runtime.py"]},
    )
    plan = InvestigationPlanner().build(workspace_id="ws-1", seeds=[seed])
    assert plan.executable
    assert plan.seed_refs == ("validation:1",)
    assert plan.requests[0].relation == "tests"


def test_accepts_verified_current_workspace_evidence_seed():
    seed = _seed(
        ref="workspace:1",
        source_type="current_workspace_evidence",
        metadata={"owners": ["src/runtime_owner.py"]},
    )
    plan = InvestigationPlanner().build(workspace_id="ws-1", seeds=[seed])
    assert plan.executable
    assert plan.requests[0].path_patterns == ("src/runtime_owner.py",)
