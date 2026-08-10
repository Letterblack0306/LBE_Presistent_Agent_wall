from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any


class MemoryType(StrEnum):
    WORKSPACE_FACT = "workspace_fact"
    TASK_CONSTRAINT = "task_constraint"
    DECISION = "decision"
    FAILURE_PATTERN = "failure_pattern"
    VALIDATION_RESULT = "validation_result"
    CHECKPOINT = "checkpoint"
    USER_PREFERENCE = "user_preference"
    HISTORICAL_OBSERVATION = "historical_observation"


class ValidationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    STALE = "stale"
    CONTRADICTED = "contradicted"
    SUPERSEDED = "superseded"


class SourceType(StrEnum):
    LIVE_WORKSPACE = "live_workspace"
    GIT = "git"
    TEST_RUN = "test_run"
    COMMAND_RESULT = "command_result"
    SESSION_MESSAGE = "session_message"
    COMPACTION = "compaction"
    ASSISTANT_REASONING = "assistant_reasoning"
    USER_INSTRUCTION = "user_instruction"


class TaskStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_root(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve()).replace("\\", "/").rstrip("/")


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


@dataclass(slots=True)
class MemoryRecord:
    project_workspace_id: str
    canonical_workspace_root: str
    memory_type: MemoryType
    subject: str
    predicate: str
    value: Any
    source_type: SourceType
    validation_status: ValidationStatus
    confidence: float
    memory_id: str = field(default_factory=lambda: f"mem-{uuid.uuid4().hex}")
    task_id: str | None = None
    rule_id: str | None = None
    source_path: str | None = None
    source_hash: str | None = None
    source_commit: str | None = None
    source_message_id: str | None = None
    authority: int = 0
    validation_method: str | None = None
    validated_at: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        self.project_workspace_id = self.project_workspace_id.strip()
        self.canonical_workspace_root = canonical_root(self.canonical_workspace_root)
        self.subject = self.subject.strip()
        self.predicate = self.predicate.strip()
        if not self.project_workspace_id:
            raise ValueError("project_workspace_id must not be empty")
        if not self.subject or not self.predicate:
            raise ValueError("subject and predicate must not be empty")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.validation_status is ValidationStatus.VERIFIED:
            if not self.validation_method:
                raise ValueError("verified memory requires validation_method")
            if not self.validated_at:
                self.validated_at = utc_now()
        if self.source_type in {
            SourceType.ASSISTANT_REASONING,
            SourceType.COMPACTION,
        } and self.validation_status is ValidationStatus.VERIFIED:
            raise ValueError(
                f"{self.source_type.value} cannot be promoted directly as verified memory"
            )

    @property
    def value_json(self) -> str:
        return json.dumps(self.value, ensure_ascii=False, sort_keys=True)

    def as_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "project_workspace_id": self.project_workspace_id,
            "canonical_workspace_root": self.canonical_workspace_root,
            "task_id": self.task_id,
            "rule_id": self.rule_id,
            "memory_type": self.memory_type.value,
            "subject": self.subject,
            "predicate": self.predicate,
            "value": self.value,
            "source_type": self.source_type.value,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "source_commit": self.source_commit,
            "source_message_id": self.source_message_id,
            "authority": self.authority,
            "validation_status": self.validation_status.value,
            "validation_method": self.validation_method,
            "validated_at": self.validated_at,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "superseded_by": self.superseded_by,
        }


@dataclass(slots=True, frozen=True)
class CompactionCheckpoint:
    checkpoint_id: str
    session_id: str
    project_workspace_id: str
    canonical_workspace_root: str
    source_prefix_hash: str
    source_message_count: int
    source_last_message_key: str | None
    branch: str | None
    head: str | None
    verified_memory_ids: tuple[str, ...]
    active_constraints: tuple[str, ...]
    created_at: str


@dataclass(slots=True)
class SessionState:
    session_id: str
    project_workspace_id: str
    canonical_workspace_root: str
    mode: str
    provider_id: str | None = None
    provider_model: str | None = None
    active_profile_id: str | None = None
    permission_policy_id: str | None = None
    evidence_policy_id: str | None = None
    checkpoint_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.session_id = self.session_id.strip()
        self.project_workspace_id = self.project_workspace_id.strip()
        self.canonical_workspace_root = canonical_root(self.canonical_workspace_root)
        self.mode = self.mode.strip()
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if not self.project_workspace_id:
            raise ValueError("project_workspace_id must not be empty")
        if not self.mode:
            raise ValueError("mode must not be empty")
        self.provider_id = _optional_text(self.provider_id)
        self.provider_model = _optional_text(self.provider_model)
        self.active_profile_id = _optional_text(self.active_profile_id)
        self.permission_policy_id = _optional_text(self.permission_policy_id)
        self.evidence_policy_id = _optional_text(self.evidence_policy_id)
        self.checkpoint_id = _optional_text(self.checkpoint_id)

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "project_workspace_id": self.project_workspace_id,
            "canonical_workspace_root": self.canonical_workspace_root,
            "mode": self.mode,
            "provider_id": self.provider_id,
            "provider_model": self.provider_model,
            "active_profile_id": self.active_profile_id,
            "permission_policy_id": self.permission_policy_id,
            "evidence_policy_id": self.evidence_policy_id,
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class TaskState:
    session_id: str
    task_id: str
    project_workspace_id: str
    canonical_workspace_root: str
    status: TaskStatus
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    last_outcome: str | None = None

    def __post_init__(self) -> None:
        self.session_id = self.session_id.strip()
        self.task_id = self.task_id.strip()
        self.project_workspace_id = self.project_workspace_id.strip()
        self.canonical_workspace_root = canonical_root(self.canonical_workspace_root)
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if not self.task_id:
            raise ValueError("task_id must not be empty")
        if not self.project_workspace_id:
            raise ValueError("project_workspace_id must not be empty")
        if not isinstance(self.status, TaskStatus):
            raise ValueError(f"status must be a TaskStatus, got {self.status!r}")
        if self.last_outcome is not None:
            self.last_outcome = self.last_outcome.strip() or None
