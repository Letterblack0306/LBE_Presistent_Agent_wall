from __future__ import annotations

from pathlib import Path

from agent import Context, KnowledgeRoot
from lbe_guard_inspector.coding_reasoning_provider import PlannedToolRequest, ToolAwareReasoningPlan
from lbe_guard_inspector.request_controller import LBERequestController
from lbe_guard_inspector.reasoning_contracts import LBERequest, ReasoningPlan


class _Backend:
    def __init__(self, plan) -> None:
        self._plan = plan
        self.plan_requests = []

    def plan(self, request):
        self.plan_requests.append(request)
        return self._plan

    def explain(self, request):
        raise AssertionError("tool-only reasoning must not enter guard explanation")


class _EvidenceService:
    def build_evidence_package(self, **kwargs):
        return {
            "package_id": "ep-tool-only",
            "task_id": kwargs["task_id"],
            "query": kwargs["query"],
            "workspace_id": kwargs["workspace_id"],
            "indexed_reference_evidence": [],
            "current_workspace_evidence": [],
            "validation_evidence": [],
            "contradictions": [],
            "missing_evidence": [],
            "generated_at": "2026-08-14T00:00:00+00:00",
        }


def _controller(tmp_path: Path, plan):
    configured = tmp_path / "configured"
    configured.mkdir()
    workspace = configured / "project"
    workspace.mkdir()
    (workspace / "README.md").write_text("before\n", encoding="utf-8")
    context = Context(config={}, governance={}, roots=(KnowledgeRoot("dev", configured),))
    controller = LBERequestController(
        backend=_Backend(plan),
        context=context,
        evidence_service=_EvidenceService(),
        catalog_selector=lambda profile: {"foundation_guard_ids": [], "optional_guard_ids": []},
    )
    controller.configure_approved_tools(("workspace.read", "workspace.replace_text"))
    return controller, workspace


def _tool_only_plan() -> ToolAwareReasoningPlan:
    return ToolAwareReasoningPlan(
        interpreted_problem="replace one bounded text value",
        ambiguities=(),
        candidate_guard_ids=(),
        evidence_requests=(),
        validation_requests=(),
        explanation_focus=(),
        tool_requests=(
            PlannedToolRequest(
                tool_id="workspace.replace_text",
                path="README.md",
                old_text="before",
                new_text="after",
                reason="apply the requested bounded source change",
            ),
        ),
    )


def test_validated_tool_only_plan_completes_reasoning_stage(tmp_path: Path) -> None:
    controller, workspace = _controller(tmp_path, _tool_only_plan())

    response = controller.run(
        LBERequest(problem="Change before to after", workspace_root=workspace, task_id="task-1")
    )

    assert response.outcome == "COMPLETED"
    assert response.error is None
    assert response.deterministic_result is None
    assert response.explanation is None
    assert response.plan is not None
    assert len(response.plan.tool_requests) == 1
    assert (workspace / "README.md").read_text(encoding="utf-8") == "before\n"


def test_no_guard_and_no_tool_request_remains_insufficient_evidence(tmp_path: Path) -> None:
    plan = ReasoningPlan(
        interpreted_problem="no executable reasoning path",
        ambiguities=(),
        candidate_guard_ids=(),
        evidence_requests=(),
        validation_requests=(),
        explanation_focus=(),
    )
    controller, workspace = _controller(tmp_path, plan)

    response = controller.run(
        LBERequest(problem="Inspect without a guard", workspace_root=workspace, task_id="task-2")
    )

    assert response.outcome == "INSUFFICIENT_EVIDENCE"
    assert response.error is not None
    assert response.error.code == "NO_GUARD_SELECTED"
