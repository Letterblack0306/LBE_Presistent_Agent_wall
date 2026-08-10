from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lbe_guard_inspector.memory import TaskStatus
from lbe_guard_inspector.reasoning_contracts import LBEResponse
from lbe_guard_inspector.runtime.completion_gate import (
    CompletionEvidence,
    CompletionEvidenceStatus,
    CompletionRequirement,
    CompletionVerdict,
    TaskCompletionContract,
    evaluate_completion,
)
from lbe_guard_inspector.runtime.completion_runtime import CodingCompletionRuntime
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


def _contract() -> TaskCompletionContract:
    return TaskCompletionContract(
        requirements=(
            CompletionRequirement("source-change", "source_change"),
            CompletionRequirement("focused-tests", "focused_test"),
            CompletionRequirement("git-state", "git_status"),
        )
    )


def _evidence(kind: str, status: CompletionEvidenceStatus, suffix: str = "1") -> CompletionEvidence:
    return CompletionEvidence(
        evidence_id=f"ev-{kind}-{suffix}",
        kind=kind,
        status=status,
        source="structured-runtime-receipt",
        details={"kind": kind},
    )


def test_model_completion_claim_without_required_evidence_is_blocked() -> None:
    decision = evaluate_completion(contract=_contract(), evidence=(), claimed_complete=True)

    assert decision.verdict is CompletionVerdict.BLOCKED
    assert decision.ready is False
    assert decision.satisfied_requirement_ids == ()
    assert decision.missing_requirement_ids == ("source-change", "focused-tests", "git-state")


def test_stale_evidence_does_not_satisfy_completion() -> None:
    decision = evaluate_completion(
        contract=_contract(),
        evidence=(
            _evidence("source_change", CompletionEvidenceStatus.PASS),
            _evidence("focused_test", CompletionEvidenceStatus.STALE),
            _evidence("git_status", CompletionEvidenceStatus.PASS),
        ),
        claimed_complete=True,
    )

    assert decision.verdict is CompletionVerdict.BLOCKED
    assert decision.missing_requirement_ids == ("focused-tests",)
    assert "ev-focused_test-1" in decision.evidence_ids


def test_failed_required_validation_fails_completion() -> None:
    decision = evaluate_completion(
        contract=_contract(),
        evidence=(
            _evidence("source_change", CompletionEvidenceStatus.PASS),
            _evidence("focused_test", CompletionEvidenceStatus.FAIL),
            _evidence("git_status", CompletionEvidenceStatus.PASS),
        ),
        claimed_complete=True,
    )

    assert decision.verdict is CompletionVerdict.FAILED
    assert decision.failed_requirement_ids == ("focused-tests",)
    assert decision.ready is False


def test_all_required_evidence_must_pass_before_ready() -> None:
    decision = evaluate_completion(
        contract=_contract(),
        evidence=(
            _evidence("source_change", CompletionEvidenceStatus.PASS),
            _evidence("focused_test", CompletionEvidenceStatus.PASS),
            _evidence("git_status", CompletionEvidenceStatus.PASS),
        ),
        claimed_complete=True,
    )

    assert decision.verdict is CompletionVerdict.READY
    assert decision.ready is True
    assert decision.missing_requirement_ids == ()
    assert decision.failed_requirement_ids == ()
    assert decision.satisfied_requirement_ids == ("source-change", "focused-tests", "git-state")


def test_passing_evidence_without_completion_request_remains_blocked() -> None:
    decision = evaluate_completion(
        contract=_contract(),
        evidence=(
            _evidence("source_change", CompletionEvidenceStatus.PASS),
            _evidence("focused_test", CompletionEvidenceStatus.PASS),
            _evidence("git_status", CompletionEvidenceStatus.PASS),
        ),
        claimed_complete=False,
    )

    assert decision.verdict is CompletionVerdict.BLOCKED
    assert decision.satisfied_requirement_ids == ("source-change", "focused-tests", "git-state")


def test_duplicate_requirement_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        TaskCompletionContract(
            requirements=(
                CompletionRequirement("same", "a"),
                CompletionRequirement("same", "b"),
            )
        )


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _runtime(tmp_path: Path, root: Path) -> SessionMemoryRuntimeBridge:
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite",
        project_workspace_id="project-1",
        workspace_root=root,
        session_id="session-1",
        mode="coding",
    )


class _CompletedReasoningController:
    def run(self, request):
        return LBEResponse(
            task_id=request.task_id,
            workspace_identity={"workspace_id": "project-1"},
            workspace_profile={},
            plan=None,
            deterministic_result=None,
            explanation=None,
            outcome="COMPLETED",
        )


def test_coding_reasoning_completed_is_provisional_until_validation(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
    coordinator = CodingCompletionRuntime(runtime=runtime)

    result = coordinator.run_reasoning(
        controller=_CompletedReasoningController(),
        problem="Fix the defect",
        task_id="task-1",
    )

    assert result.response.outcome == "COMPLETED"
    assert result.task_state.status is TaskStatus.RUNNING
    assert result.task_state.last_outcome == "AWAITING_VALIDATION"
    persisted = runtime.load_task_status(task_id="task-1")
    assert persisted is not None
    assert persisted.status is TaskStatus.RUNNING


def test_missing_validation_persists_incomplete_task(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
    coordinator = CodingCompletionRuntime(runtime=runtime)
    runtime.record_task_status(task_id="task-2", status=TaskStatus.RUNNING)

    decision, state = coordinator.finalize(
        task_id="task-2",
        contract=_contract(),
        evidence=(_evidence("source_change", CompletionEvidenceStatus.PASS),),
    )

    assert decision.verdict is CompletionVerdict.BLOCKED
    assert state.status is TaskStatus.BLOCKED
    assert state.last_outcome == "VALIDATION_INCOMPLETE"


def test_failed_validation_persists_failed_task(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
    coordinator = CodingCompletionRuntime(runtime=runtime)
    runtime.record_task_status(task_id="task-3", status=TaskStatus.RUNNING)

    decision, state = coordinator.finalize(
        task_id="task-3",
        contract=_contract(),
        evidence=(
            _evidence("source_change", CompletionEvidenceStatus.PASS),
            _evidence("focused_test", CompletionEvidenceStatus.FAIL),
            _evidence("git_status", CompletionEvidenceStatus.PASS),
        ),
    )

    assert decision.verdict is CompletionVerdict.FAILED
    assert state.status is TaskStatus.FAILED
    assert state.last_outcome == "VALIDATION_FAILED"


def test_passing_completion_proof_promotes_canonical_task_state(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runtime = _runtime(tmp_path, root)
    coordinator = CodingCompletionRuntime(runtime=runtime)
    runtime.record_task_status(task_id="task-4", status=TaskStatus.RUNNING)

    decision, state = coordinator.finalize(
        task_id="task-4",
        contract=_contract(),
        evidence=(
            _evidence("source_change", CompletionEvidenceStatus.PASS),
            _evidence("focused_test", CompletionEvidenceStatus.PASS),
            _evidence("git_status", CompletionEvidenceStatus.PASS),
        ),
    )

    assert decision.verdict is CompletionVerdict.READY
    assert state.status is TaskStatus.COMPLETED
    assert state.last_outcome == "VALIDATED_COMPLETION"
    persisted = runtime.load_task_status(task_id="task-4")
    assert persisted is not None
    assert persisted.status is TaskStatus.COMPLETED
