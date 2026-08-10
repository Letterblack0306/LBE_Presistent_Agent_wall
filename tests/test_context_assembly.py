from __future__ import annotations

from pathlib import Path

import pytest

from agent import Context, KnowledgeRoot
from lbe_guard_inspector.reasoning_contracts import LBERequest
from lbe_guard_inspector.request_controller import LBERequestController
from lbe_guard_inspector.runtime.context_assembly import assemble_reasoning_context


def test_context_assembly_preserves_caller_context_before_indexed_evidence() -> None:
    caller = {"context_kind": "session_context", "verified": True, "fact": "resume constraint"}
    indexed = {"ref": "index:1", "verified": True, "classification": "reference"}

    result = assemble_reasoning_context(
        request_context=(caller,),
        indexed_reference_evidence=(indexed,),
    )

    assert result == (caller, indexed)
    assert result[0] is not caller
    assert result[1] is not indexed


def test_context_assembly_does_not_mutate_inputs() -> None:
    caller = {"nested": {"value": 1}}
    indexed = {"ref": "index:1"}

    result = assemble_reasoning_context(
        request_context=(caller,),
        indexed_reference_evidence=(indexed,),
    )

    result[0]["added"] = True
    assert "added" not in caller
    assert result[0]["nested"] is caller["nested"]


def test_context_assembly_rejects_non_mapping_entries() -> None:
    with pytest.raises(TypeError, match="request_context entries must be mappings"):
        assemble_reasoning_context(request_context=("bad",))  # type: ignore[arg-type]


class _Backend:
    def __init__(self) -> None:
        self.requests = []

    def plan(self, request):
        self.requests.append(request)
        return {
            "interpreted_problem": "Inspect context handoff.",
            "ambiguities": [],
            "candidate_guard_ids": [],
            "evidence_requests": [],
            "validation_requests": [],
            "explanation_focus": ["state context"],
        }

    def explain(self, request):  # pragma: no cover - no guard is selected in this test
        raise AssertionError("explain should not be called")


class _Profiler:
    def profile(self, workspace_root: Path, *, configured_root_id: str):
        return {
            "outcome": "insufficient_evidence",
            "configured_root_id": configured_root_id,
            "signals": [],
            "guard_packs": [],
        }


class _EvidenceService:
    def build_evidence_package(self, **kwargs):
        return {
            "package_id": "ep-r6d",
            "task_id": kwargs["task_id"],
            "query": kwargs["query"],
            "workspace_id": kwargs["workspace_id"],
            "indexed_reference_evidence": [
                {
                    "ref": "index:r6d",
                    "source_type": "index",
                    "record_id": None,
                    "workspace_id": kwargs["workspace_id"],
                    "path": "docs/context.md",
                    "hash": "a" * 64,
                    "line_start": 1,
                    "line_end": 1,
                    "snippet": "indexed context",
                    "score": 1.0,
                    "matched_terms": [],
                    "exact_phrase": None,
                    "authority": 3,
                    "verified": True,
                    "classification": "reference",
                    "metadata": {},
                }
            ],
            "current_workspace_evidence": [],
            "validation_evidence": [],
            "contradictions": [],
            "missing_evidence": [],
            "generated_at": "2026-08-10T00:00:00+00:00",
        }


def test_controller_preserves_session_context_and_keeps_guard_channel_separate(tmp_path: Path) -> None:
    configured = tmp_path / "configured"
    workspace = configured / "project"
    workspace.mkdir(parents=True)
    context = Context(config={}, governance={}, roots=(KnowledgeRoot("dev", configured),))
    backend = _Backend()
    controller = LBERequestController(
        backend=backend,
        context=context,
        profiler=_Profiler(),
        evidence_service=_EvidenceService(),
    )
    session_context = ({"context_kind": "session_context", "verified": True, "fact": "constraint"},)

    response = controller.run(
        LBERequest(
            problem="Inspect context handoff",
            workspace_root=workspace,
            reference_context=session_context,
            task_id="task-r6d",
        )
    )

    assert response.outcome == "INSUFFICIENT_EVIDENCE"
    reasoning_request = backend.requests[0]
    assert reasoning_request.reference_context[0] == session_context[0]
    assert reasoning_request.reference_context[1]["ref"] == "index:r6d"
    assert reasoning_request.approved_guard_ids
    assert all(item.get("context_kind") != "approved_guard_contract" for item in reasoning_request.reference_context)
