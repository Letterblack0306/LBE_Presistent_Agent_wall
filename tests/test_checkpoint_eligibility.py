from pathlib import Path

from lbe_guard_inspector.contracts import validate_contract
from lbe_guard_inspector.memory.context import (
    protected_checkpoint_eligibility,
)

from lbe_guard_inspector.memory.models import (
CompactionCheckpoint,
canonical_root,
)


def checkpoint_for(root: Path) -> CompactionCheckpoint:
    return CompactionCheckpoint(
        checkpoint_id="cp-test",
        session_id="session-1",
        project_workspace_id="project-1",
        canonical_workspace_root=canonical_root(root),
        source_prefix_hash="sha256:" + "a" * 64,
        source_message_count=10,
        source_last_message_key="id:msg-10",
        branch="main",
        head="abc123",
        verified_memory_ids=("mem-1",),
        active_constraints=("do not commit",),
        created_at="2026-07-31T00:00:00+00:00",
    )


def test_eligible_when_all_evidence_matches(tmp_path: Path) -> None:
    report = protected_checkpoint_eligibility(
        checkpoint=checkpoint_for(tmp_path),
        current_workspace_id="project-1",
        current_workspace_root=tmp_path,
        current_git_state={"branch": "main", "head": "abc123"},
        current_source_prefix_hash="sha256:" + "a" * 64,
    )

    assert report["status"] == "ELIGIBLE"
    assert report["reactivation_allowed"] is True
    assert report["reasons"] == []
    assert set(report["checks"].values()) == {"MATCH"}
    validate_contract("protected_checkpoint_eligibility", report)


def test_ineligible_when_identity_and_git_drift(
    tmp_path: Path,
) -> None:
    other = tmp_path / "other"
    other.mkdir()

    report = protected_checkpoint_eligibility(
        checkpoint=checkpoint_for(tmp_path),
        current_workspace_id="project-2",
        current_workspace_root=other,
        current_git_state={"branch": "feature", "head": "def456"},
        current_source_prefix_hash="sha256:" + "b" * 64,
    )

    assert report["status"] == "INELIGIBLE"
    assert report["reactivation_allowed"] is False
    assert set(report["checks"].values()) == {"MISMATCH"}
    assert report["reasons"] == [
        "BRANCH_MISMATCH",
        "HEAD_MISMATCH",
        "SOURCE_PREFIX_MISMATCH",
        "WORKSPACE_IDENTITY_MISMATCH",
        "WORKSPACE_ROOT_MISMATCH",
    ]


def test_insufficient_when_current_evidence_missing(
    tmp_path: Path,
) -> None:
    report = protected_checkpoint_eligibility(
        checkpoint=checkpoint_for(tmp_path),
        current_workspace_id="project-1",
        current_workspace_root=tmp_path,
        current_git_state={"branch": "", "head": None},
        current_source_prefix_hash=None,
    )

    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["reactivation_allowed"] is False
    assert report["checks"]["workspace_identity"] == "MATCH"
    assert report["checks"]["workspace_root"] == "MATCH"
    assert report["checks"]["source_prefix"] == "UNKNOWN"
    assert report["checks"]["branch"] == "UNKNOWN"
    assert report["checks"]["head"] == "UNKNOWN"


def test_insufficient_without_checkpoint(tmp_path: Path) -> None:
    report = protected_checkpoint_eligibility(
        checkpoint=None,
        current_workspace_id="project-1",
        current_workspace_root=tmp_path,
        current_git_state={"branch": "main", "head": "abc123"},
        current_source_prefix_hash="sha256:" + "a" * 64,
    )

    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["checkpoint_id"] is None
    assert report["reactivation_allowed"] is False
    assert report["reasons"] == ["CHECKPOINT_NOT_FOUND"]
    assert set(report["checks"].values()) == {"UNKNOWN"}
