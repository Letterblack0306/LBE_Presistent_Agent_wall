from lbe_guard_inspector.reasoning_guard_planner import GuardCandidate, GuardPlanner
from lbe_guard_inspector.reasoning_planner import EvidencePlan


def _candidate(guard_id: str, *, missing=()):
    return GuardCandidate(
        guard_id=guard_id,
        reason="candidate",
        evidence_plan=EvidencePlan(
            required=("required",),
            optional=(),
            missing=tuple(missing),
        ),
    )


def test_selects_one_registered_guard_with_complete_evidence():
    result = GuardPlanner().select(
        candidates=(_candidate("cep.manifest_exists"),),
        approved_guard_ids=("cep.manifest_exists",),
    )
    assert result.executable is True
    assert result.selected_guard_id == "cep.manifest_exists"


def test_rejects_unknown_guard_before_execution():
    result = GuardPlanner().select(
        candidates=(_candidate("invented.guard"),),
        approved_guard_ids=("cep.manifest_exists",),
    )
    assert result.executable is False
    assert result.rejected_guard_ids == ("invented.guard",)
    assert result.stop_reason == "UNKNOWN_GUARD"


def test_stops_when_required_evidence_is_missing():
    result = GuardPlanner().select(
        candidates=(_candidate("cep.manifest_exists", missing=("required",)),),
        approved_guard_ids=("cep.manifest_exists",),
    )
    assert result.executable is False
    assert result.stop_reason == "INSUFFICIENT_EVIDENCE"


def test_stops_when_multiple_registered_guards_remain_ambiguous():
    result = GuardPlanner().select(
        candidates=(
            _candidate("cep.manifest_exists"),
            _candidate("cep.host_version"),
        ),
        approved_guard_ids=("cep.manifest_exists", "cep.host_version"),
    )
    assert result.executable is False
    assert result.stop_reason == "AMBIGUOUS_GUARD_SELECTION"


def test_workspace_profile_guard_has_priority_over_generic_candidate():
    result = GuardPlanner().select(
        candidates=(
            _candidate("generic.index_present"),
            _candidate("cep.manifest_exists"),
        ),
        approved_guard_ids=("generic.index_present", "cep.manifest_exists"),
        workspace_profile={"enabled_guard_ids": ["cep.manifest_exists"]},
    )
    assert result.executable is True
    assert result.selected_guard_id == "cep.manifest_exists"
