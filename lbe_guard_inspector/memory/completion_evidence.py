"""Persistence adapter for producer-bound completion evidence.

This module stores semantic completion evidence only after an LBE-owned
validation producer has already classified it. It does not derive evidence
kinds from model/CLI input and does not evaluate task completion.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .models import canonical_root, utc_now
from .store import WorkspaceMemoryStore


_VALID_STATUSES = frozenset({"PASS", "FAIL", "STALE"})


@dataclass(frozen=True)
class StoredCompletionEvidence:
    session_id: str
    task_id: str
    project_workspace_id: str
    canonical_workspace_root: str
    evidence_id: str
    kind: str
    status: str
    source: str
    producer_id: str
    operation_id: str
    details: Mapping[str, Any]
    created_at: str


class TaskCompletionEvidencePersistence:
    """Store immutable evidence emitted by trusted validation producers."""

    def __init__(self, store: WorkspaceMemoryStore) -> None:
        if not isinstance(store, WorkspaceMemoryStore):
            raise TypeError("store must be WorkspaceMemoryStore")
        self._store = store

    def save(
        self,
        *,
        session_id: str,
        task_id: str,
        project_workspace_id: str,
        canonical_workspace_root: str,
        evidence_id: str,
        kind: str,
        status: str,
        source: str,
        producer_id: str,
        operation_id: str,
        details: Mapping[str, Any] | None = None,
    ) -> StoredCompletionEvidence:
        clean_session = _required(session_id, "session_id")
        clean_task = _required(task_id, "task_id")
        clean_project = _required(project_workspace_id, "project_workspace_id")
        clean_root = canonical_root(canonical_workspace_root)
        clean_evidence = _required(evidence_id, "evidence_id")
        clean_kind = _required(kind, "kind")
        clean_status = _required(status, "status").upper()
        clean_source = _required(source, "source")
        clean_producer = _required(producer_id, "producer_id")
        clean_operation = _required(operation_id, "operation_id")
        if clean_status not in _VALID_STATUSES:
            raise ValueError(f"unsupported completion evidence status: {clean_status}")
        if details is None:
            clean_details: dict[str, Any] = {}
        elif isinstance(details, Mapping):
            clean_details = dict(details)
        else:
            raise TypeError("details must be a mapping")

        session = self._store.load_session_state(session_id=clean_session)
        if session is None:
            raise FileNotFoundError(f"persistent session not found: {clean_session}")
        if session.project_workspace_id != clean_project:
            raise ValueError("completion evidence workspace identity does not match session")
        if session.canonical_workspace_root != clean_root:
            raise ValueError("completion evidence workspace root does not match session")

        candidate = StoredCompletionEvidence(
            session_id=clean_session,
            task_id=clean_task,
            project_workspace_id=clean_project,
            canonical_workspace_root=clean_root,
            evidence_id=clean_evidence,
            kind=clean_kind,
            status=clean_status,
            source=clean_source,
            producer_id=clean_producer,
            operation_id=clean_operation,
            details=clean_details,
            created_at=utc_now(),
        )
        existing = self._load_one(
            session_id=clean_session,
            task_id=clean_task,
            evidence_id=clean_evidence,
        )
        if existing is not None:
            if _identity_payload(existing) != _identity_payload(candidate):
                raise ValueError("completion evidence already exists and cannot be replaced implicitly")
            return existing

        with self._store._connect() as connection:
            connection.execute(
                """
                INSERT INTO task_completion_evidence (
                    session_id, task_id, project_workspace_id,
                    canonical_workspace_root, evidence_id, kind, status,
                    source, producer_id, operation_id, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.session_id,
                    candidate.task_id,
                    candidate.project_workspace_id,
                    candidate.canonical_workspace_root,
                    candidate.evidence_id,
                    candidate.kind,
                    candidate.status,
                    candidate.source,
                    candidate.producer_id,
                    candidate.operation_id,
                    _details_json(candidate.details),
                    candidate.created_at,
                ),
            )
        return candidate

    def load(
        self,
        *,
        session_id: str,
        task_id: str,
        project_workspace_id: str,
    ) -> tuple[StoredCompletionEvidence, ...]:
        clean_session = _required(session_id, "session_id")
        clean_task = _required(task_id, "task_id")
        clean_project = _required(project_workspace_id, "project_workspace_id")
        with self._store._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM task_completion_evidence
                WHERE session_id=? AND task_id=? AND project_workspace_id=?
                ORDER BY created_at ASC, evidence_id ASC
                """,
                (clean_session, clean_task, clean_project),
            ).fetchall()
        return tuple(_row(item) for item in rows)

    def _load_one(
        self,
        *,
        session_id: str,
        task_id: str,
        evidence_id: str,
    ) -> StoredCompletionEvidence | None:
        with self._store._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM task_completion_evidence
                WHERE session_id=? AND task_id=? AND evidence_id=?
                """,
                (session_id, task_id, evidence_id),
            ).fetchone()
        return None if row is None else _row(row)


def _required(value: object, name: str) -> str:
    clean = str(value).strip()
    if not clean:
        raise ValueError(f"{name} must not be empty")
    return clean


def _details_json(details: Mapping[str, Any]) -> str:
    return json.dumps(dict(details), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identity_payload(item: StoredCompletionEvidence) -> tuple[object, ...]:
    return (
        item.project_workspace_id,
        item.canonical_workspace_root,
        item.kind,
        item.status,
        item.source,
        item.producer_id,
        item.operation_id,
        _details_json(item.details),
    )


def _row(row: Mapping[str, Any]) -> StoredCompletionEvidence:
    details = json.loads(str(row["details_json"]))
    if not isinstance(details, dict):
        raise ValueError("corrupted completion evidence details")
    status = str(row["status"])
    if status not in _VALID_STATUSES:
        raise ValueError("corrupted completion evidence status")
    return StoredCompletionEvidence(
        session_id=str(row["session_id"]),
        task_id=str(row["task_id"]),
        project_workspace_id=str(row["project_workspace_id"]),
        canonical_workspace_root=canonical_root(str(row["canonical_workspace_root"])),
        evidence_id=str(row["evidence_id"]),
        kind=str(row["kind"]),
        status=status,
        source=str(row["source"]),
        producer_id=str(row["producer_id"]),
        operation_id=str(row["operation_id"]),
        details=details,
        created_at=str(row["created_at"]),
    )
