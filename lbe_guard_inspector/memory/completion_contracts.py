"""Persistence adapter for immutable task completion contracts.

The contract is durable LBE state, separate from task lifecycle status and from
verified workspace memory. This module persists already-resolved completion
requirements; it does not decide policy or validate task completion.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from .models import canonical_root, utc_now
from .store import WorkspaceMemoryStore


@dataclass(frozen=True)
class StoredCompletionRequirement:
    requirement_id: str
    evidence_kind: str
    description: str = ""

    def __post_init__(self) -> None:
        for name in ("requirement_id", "evidence_kind"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        object.__setattr__(self, "requirement_id", self.requirement_id.strip())
        object.__setattr__(self, "evidence_kind", self.evidence_kind.strip())
        object.__setattr__(self, "description", str(self.description or "").strip())

    def as_dict(self) -> dict[str, str]:
        return {
            "requirement_id": self.requirement_id,
            "evidence_kind": self.evidence_kind,
            "description": self.description,
        }


@dataclass(frozen=True)
class StoredTaskCompletionContract:
    session_id: str
    task_id: str
    project_workspace_id: str
    canonical_workspace_root: str
    requirements: tuple[StoredCompletionRequirement, ...]
    created_at: str


class TaskCompletionContractPersistence:
    """Persist task completion contracts through the existing workspace store."""

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
        requirements: Sequence[Mapping[str, str] | StoredCompletionRequirement],
    ) -> StoredTaskCompletionContract:
        clean_session = str(session_id).strip()
        clean_task = str(task_id).strip()
        clean_project = str(project_workspace_id).strip()
        clean_root = canonical_root(canonical_workspace_root)
        if not clean_session:
            raise ValueError("session_id must not be empty")
        if not clean_task:
            raise ValueError("task_id must not be empty")
        if not clean_project:
            raise ValueError("project_workspace_id must not be empty")

        session = self._store.load_session_state(session_id=clean_session)
        if session is None:
            raise FileNotFoundError(f"persistent session not found: {clean_session}")
        if session.project_workspace_id != clean_project:
            raise ValueError("completion contract workspace identity does not match session")
        if session.canonical_workspace_root != clean_root:
            raise ValueError("completion contract workspace root does not match session")

        normalized = tuple(_requirement(item) for item in requirements)
        if not normalized:
            raise ValueError("completion contract requires at least one requirement")
        ids = [item.requirement_id for item in normalized]
        if len(ids) != len(set(ids)):
            raise ValueError("completion requirement IDs must be unique")

        payload = json.dumps(
            [item.as_dict() for item in normalized],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        existing = self.load(
            session_id=clean_session,
            task_id=clean_task,
            project_workspace_id=clean_project,
        )
        if existing is not None:
            existing_payload = json.dumps(
                [item.as_dict() for item in existing.requirements],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if existing.canonical_workspace_root != clean_root or existing_payload != payload:
                raise ValueError(
                    "completion contract already exists and cannot be replaced implicitly"
                )
            return existing

        created_at = utc_now()
        with self._store._connect() as connection:
            connection.execute(
                """
                INSERT INTO task_completion_contracts (
                    session_id, task_id, project_workspace_id,
                    canonical_workspace_root, requirements_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_session,
                    clean_task,
                    clean_project,
                    clean_root,
                    payload,
                    created_at,
                ),
            )
        return StoredTaskCompletionContract(
            session_id=clean_session,
            task_id=clean_task,
            project_workspace_id=clean_project,
            canonical_workspace_root=clean_root,
            requirements=normalized,
            created_at=created_at,
        )

    def load(
        self,
        *,
        session_id: str,
        task_id: str,
        project_workspace_id: str,
    ) -> StoredTaskCompletionContract | None:
        clean_session = str(session_id).strip()
        clean_task = str(task_id).strip()
        clean_project = str(project_workspace_id).strip()
        if not clean_session or not clean_task or not clean_project:
            raise ValueError("session_id, task_id, and project_workspace_id must not be empty")
        with self._store._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM task_completion_contracts
                WHERE session_id=? AND task_id=? AND project_workspace_id=?
                """,
                (clean_session, clean_task, clean_project),
            ).fetchone()
        if row is None:
            return None
        raw = json.loads(str(row["requirements_json"]))
        if not isinstance(raw, list):
            raise ValueError("corrupted completion contract requirements")
        requirements = tuple(_requirement(item) for item in raw)
        if not requirements:
            raise ValueError("corrupted completion contract has no requirements")
        return StoredTaskCompletionContract(
            session_id=str(row["session_id"]),
            task_id=str(row["task_id"]),
            project_workspace_id=str(row["project_workspace_id"]),
            canonical_workspace_root=canonical_root(str(row["canonical_workspace_root"])),
            requirements=requirements,
            created_at=str(row["created_at"]),
        )


def _requirement(
    value: Mapping[str, str] | StoredCompletionRequirement,
) -> StoredCompletionRequirement:
    if isinstance(value, StoredCompletionRequirement):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("completion requirements must be mappings or stored requirements")
    return StoredCompletionRequirement(
        requirement_id=str(value.get("requirement_id", "")),
        evidence_kind=str(value.get("evidence_kind", "")),
        description=str(value.get("description", "")),
    )
