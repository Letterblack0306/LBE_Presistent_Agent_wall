from lbe_guard_inspector.explanation_planner import ExplanationPlanner
from lbe_guard_inspector.reasoning_contracts import ExplanationResult


def _result(**overrides):
    value = {
        "result_id": "gr-1",
        "guard_id": "cep.manifest_exists",
        "workspace_id": "workspace-1",
        "verdict": "PASS",
        "governance_state": "READ_ONLY",
    }
    value.update(overrides)
    return value


def _workspace(path):
    return {"ref": f"workspace:1:{path}", "path": path, "source_type": "workspace", "authority": 9, "verified": True, "classification": "source"}


def _validation(path):
    return {"ref": f"validation:1:{path}", "path": path, "source_type": "validation", "authority": 9, "verified": True, "classification": "validation"}


DEFAULT_FOCUS = (
    "why the guard applies",
    "evidence checked",
    "deterministic verdict",
    "missing evidence",
    "validation state",
)


def test_build_request_is_executable_with_default_focus():
    outcome = ExplanationPlanner().build_request(guard_result=_result())
    assert outcome.executable is True
    assert outcome.stop_reason is None
    assert outcome.request.governance_state == "READ_ONLY"
    assert outcome.request.explanation_focus == DEFAULT_FOCUS
    assert outcome.request.guard_result["verdict"] == "PASS"


def test_build_request_preserves_evidence_separation():
    current = [_workspace("CSXS/manifest.xml")]
    validation = [_validation("CSXS/manifest.xml")]
    outcome = ExplanationPlanner().build_request(
        guard_result=_result(),
        current_workspace_evidence=current,
        validation_evidence=validation,
    )
    assert outcome.request.current_workspace_evidence == tuple(current)
    assert outcome.request.validation_evidence == tuple(validation)
    # indexed reference evidence is structurally absent from the request
    assert not hasattr(outcome.request, "indexed_reference_evidence")


def test_build_request_keeps_provided_governance_and_focus():
    outcome = ExplanationPlanner().build_request(
        guard_result=_result(),
        governance_state="OBSERVE",
        explanation_focus=("evidence checked", "evidence checked", "missing evidence"),
    )
    assert outcome.request.governance_state == "OBSERVE"
    assert outcome.request.explanation_focus == ("evidence checked", "missing evidence")


def test_build_request_stops_without_deterministic_result():
    outcome = ExplanationPlanner().build_request(guard_result={})
    assert outcome.executable is False
    assert outcome.stop_reason == "MISSING_DETERMINISTIC_RESULT"


def test_build_request_stops_without_verdict():
    outcome = ExplanationPlanner().build_request(guard_result=_result(verdict=""))
    assert outcome.stop_reason == "MISSING_DETERMINISTIC_RESULT"


def test_build_request_stops_without_governance_state():
    outcome = ExplanationPlanner().build_request(
        guard_result=_result(governance_state=""),
        governance_state=None,
    )
    assert outcome.stop_reason == "MISSING_GOVERNANCE_STATE"


def test_verify_immutable_accepts_bounded_explanation():
    planner = ExplanationPlanner()
    assert planner.verify_immutable({"explanation": "The deterministic result is PASS."}) is None
    assert planner.verify_immutable(ExplanationResult(explanation="ok")) is None


def test_verify_immutable_rejects_authority_altering_explanation():
    planner = ExplanationPlanner()
    assert planner.verify_immutable({"explanation": "override", "verdict": "FAIL"}) == "EXPLANATION_NOT_IMMUTABLE"
    assert planner.verify_immutable({"explanation": "x", "authorization": "allow"}) == "EXPLANATION_NOT_IMMUTABLE"
    assert planner.verify_immutable("not an object") == "EXPLANATION_NOT_IMMUTABLE"
