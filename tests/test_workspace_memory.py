from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from lbe_guard_inspector.memory import (
    CandidateClaim,
    MemoryPromoter,
    MemoryRecord,
    MemoryType,
    SourceType,
    ValidationStatus,
    WorkspaceMemoryStore,
    build_context_packet,
    invalidate_changed_sources,
    persist_compaction_checkpoint,
)


def make_store(tmp_path: Path) -> WorkspaceMemoryStore:
    return WorkspaceMemoryStore(tmp_path / "state" / "memory.db")


def test_assistant_reasoning_cannot_be_verified_directly(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be promoted directly"):
        MemoryRecord(
            project_workspace_id="project-1",
            canonical_workspace_root=tmp_path,
            memory_type=MemoryType.WORKSPACE_FACT,
            subject="agent.py",
            predicate="is_broken",
            value=True,
            source_type=SourceType.ASSISTANT_REASONING,
            validation_status=ValidationStatus.VERIFIED,
            validation_method="assistant conclusion",
            confidence=1.0,
        )


def test_promoter_keeps_assistant_conclusion_unverified(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    record = MemoryPromoter(store).promote(
        CandidateClaim(
            project_workspace_id="project-1",
            canonical_workspace_root=str(tmp_path),
            memory_type=MemoryType.HISTORICAL_OBSERVATION,
            subject="agent.py",
            predicate="is_broken",
            value=True,
            source_type=SourceType.ASSISTANT_REASONING,
            source_message_id="msg-1",
        )
    )
    assert record.validation_status is ValidationStatus.UNVERIFIED
    assert record.confidence == 0.2
    assert store.query(project_workspace_id="project-1") == []


def test_deterministic_git_fact_is_promoted(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    record = MemoryPromoter(store).promote(
        CandidateClaim(
            project_workspace_id="project-1",
            canonical_workspace_root=str(tmp_path),
            memory_type=MemoryType.WORKSPACE_FACT,
            subject="repository",
            predicate="git_head",
            value="abc123",
            source_type=SourceType.GIT,
            source_commit="abc123",
            authority=10,
        )
    )
    assert record.validation_status is ValidationStatus.VERIFIED
    assert record.validation_method == "trusted:git"
    assert store.query(project_workspace_id="project-1")[0].value == "abc123"


def test_upsert_updates_same_memory_identity(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    promoter = MemoryPromoter(store)
    claim = CandidateClaim(
        project_workspace_id="project-1",
        canonical_workspace_root=str(tmp_path),
        memory_type=MemoryType.WORKSPACE_FACT,
        subject="repository",
        predicate="git_branch",
        value="main",
        source_type=SourceType.GIT,
    )
    first = promoter.promote(claim)
    second = promoter.promote(claim)
    assert first.memory_id == second.memory_id
    assert len(store.query(project_workspace_id="project-1")) == 1


def test_changed_source_hash_marks_verified_memory_stale(tmp_path: Path) -> None:
    source = tmp_path / "config.json"
    source.write_text('{"value": 1}', encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    store = make_store(tmp_path)
    record = store.upsert(
        MemoryRecord(
            project_workspace_id="project-1",
            canonical_workspace_root=tmp_path,
            memory_type=MemoryType.WORKSPACE_FACT,
            subject="config.json",
            predicate="validated_configuration_value",
            value=1,
            source_type=SourceType.LIVE_WORKSPACE,
            source_path="config.json",
            source_hash=digest,
            validation_status=ValidationStatus.VERIFIED,
            validation_method="sha256+json-parse",
            confidence=1.0,
        )
    )
    source.write_text('{"value": 2}', encoding="utf-8")
    current = invalidate_changed_sources(store, [record], tmp_path)
    assert current == []
    stale = store.query(
        project_workspace_id="project-1",
        statuses=(ValidationStatus.STALE,),
    )
    assert [item.memory_id for item in stale] == [record.memory_id]


def test_compaction_checkpoint_preserves_prefix_provenance(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    checkpoint = persist_compaction_checkpoint(
        store,
        session_id="session-1",
        project_workspace_id="project-1",
        workspace_root=tmp_path,
        compaction={
            "source_message_count": 275,
            "source_prefix_hash": "sha256:" + "a" * 64,
            "source_last_message_key": "id:msg-275",
            "messages": [],
        },
        verified_memory_ids=["mem-1", "mem-1", "mem-2"],
        active_constraints=["do not commit", "do not commit"],
        branch="main",
        head="abc123",
    )
    loaded = store.latest_checkpoint("session-1")
    assert loaded == checkpoint
    assert loaded is not None
    assert loaded.verified_memory_ids == ("mem-1", "mem-2")
    assert loaded.active_constraints == ("do not commit",)


def test_context_packet_separates_constraints_and_failures(tmp_path: Path) -> None:
    constraint = MemoryRecord(
        project_workspace_id="project-1",
        canonical_workspace_root=tmp_path,
        memory_type=MemoryType.TASK_CONSTRAINT,
        subject="task",
        predicate="forbidden_file",
        value="agent.py",
        source_type=SourceType.USER_INSTRUCTION,
        validation_status=ValidationStatus.UNVERIFIED,
        confidence=0.8,
    )
    failure = MemoryRecord(
        project_workspace_id="project-1",
        canonical_workspace_root=tmp_path,
        memory_type=MemoryType.FAILURE_PATTERN,
        subject="powershell",
        predicate="command_failure",
        value="Set-Content does not support -Append",
        source_type=SourceType.COMMAND_RESULT,
        validation_status=ValidationStatus.VERIFIED,
        validation_method="exit-code+stderr",
        confidence=1.0,
    )
    packet = build_context_packet(
        project_workspace_id="project-1",
        workspace_root=tmp_path,
        git_state={"branch": "main", "head": "abc", "status_short": []},
        records=[constraint, failure],
        recent_messages=[{"role": "user", "content": "continue"}],
    )
    assert len(packet["active_constraints"]) == 1
    assert len(packet["recent_failures"]) == 1
    assert packet["verified_facts"] == []
    assert packet["workspace"]["head"] == "abc"


def test_invalid_compaction_hash_is_rejected(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="sha256"):
        persist_compaction_checkpoint(
            store,
            session_id="session-1",
            project_workspace_id="project-1",
            workspace_root=tmp_path,
            compaction={
                "source_message_count": 1,
                "source_prefix_hash": "not-a-hash",
                "source_last_message_key": "id:msg-1",
            },
            verified_memory_ids=[],
            active_constraints=[],
        )
