from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import (
    CompactionCheckpoint,
    MemoryRecord,
    MemoryType,
    SessionState,
    SourceType,
    TaskState,
    TaskStatus,
    ValidationStatus,
    utc_now,
)


class WorkspaceMemoryStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        schema_path = Path(__file__).with_name("memory_schema.sql")
        with self._connect() as connection:
            connection.executescript(schema_path.read_text(encoding="utf-8"))
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(session_state)")
            }
            if "permission" not in columns:
                connection.execute("ALTER TABLE session_state ADD COLUMN permission TEXT")
            if "runtime_policy" not in columns:
                connection.execute("ALTER TABLE session_state ADD COLUMN runtime_policy TEXT")

    def upsert(self, record: MemoryRecord) -> MemoryRecord:
        values = record.as_dict()
        values["value_json"] = record.value_json
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT memory_id, created_at
                FROM workspace_memory
                WHERE project_workspace_id = ?
                  AND COALESCE(task_id, '') = COALESCE(?, '')
                  AND COALESCE(rule_id, '') = COALESCE(?, '')
                  AND memory_type = ?
                  AND subject = ?
                  AND predicate = ?
                  AND source_type = ?
                  AND COALESCE(source_path, '') = COALESCE(?, '')
                  AND COALESCE(source_message_id, '') = COALESCE(?, '')
                  AND validation_status <> 'superseded'
                """,
                (
                    record.project_workspace_id,
                    record.task_id,
                    record.rule_id,
                    record.memory_type.value,
                    record.subject,
                    record.predicate,
                    record.source_type.value,
                    record.source_path,
                    record.source_message_id,
                ),
            ).fetchone()
            if existing:
                record.memory_id = str(existing["memory_id"])
                record.created_at = str(existing["created_at"])
                record.updated_at = utc_now()
                values = record.as_dict()
                values["value_json"] = record.value_json
                connection.execute(
                    """
                    UPDATE workspace_memory SET
                        canonical_workspace_root=:canonical_workspace_root,
                        value_json=:value_json,
                        source_hash=:source_hash,
                        source_commit=:source_commit,
                        authority=:authority,
                        validation_status=:validation_status,
                        validation_method=:validation_method,
                        validated_at=:validated_at,
                        confidence=:confidence,
                        updated_at=:updated_at,
                        superseded_by=:superseded_by
                    WHERE memory_id=:memory_id
                    """,
                    values,
                )
            else:
                connection.execute(
                    """
                    INSERT INTO workspace_memory (
                        memory_id, project_workspace_id, canonical_workspace_root,
                        task_id, rule_id, memory_type, subject, predicate, value_json,
                        source_type, source_path, source_hash, source_commit,
                        source_message_id, authority, validation_status,
                        validation_method, validated_at, confidence, created_at,
                        updated_at, superseded_by
                    ) VALUES (
                        :memory_id, :project_workspace_id, :canonical_workspace_root,
                        :task_id, :rule_id, :memory_type, :subject, :predicate,
                        :value_json, :source_type, :source_path, :source_hash,
                        :source_commit, :source_message_id, :authority,
                        :validation_status, :validation_method, :validated_at,
                        :confidence, :created_at, :updated_at, :superseded_by
                    )
                    """,
                    values,
                )
        return record

    def get(self, memory_id: str) -> MemoryRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workspace_memory WHERE memory_id = ?", (memory_id,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def query(
        self,
        *,
        project_workspace_id: str,
        statuses: Iterable[ValidationStatus] = (ValidationStatus.VERIFIED,),
        task_id: str | None = None,
        rule_id: str | None = None,
        memory_types: Iterable[MemoryType] | None = None,
        source_path: str | None = None,
        limit: int = 200,
    ) -> list[MemoryRecord]:
        status_values = [item.value for item in statuses]
        if not status_values:
            return []
        clauses = ["project_workspace_id = ?"]
        params: list[Any] = [project_workspace_id]
        clauses.append("validation_status IN (%s)" % ",".join("?" for _ in status_values))
        params.extend(status_values)
        if task_id is not None:
            clauses.append("task_id = ?")
            params.append(task_id)
        if rule_id is not None:
            clauses.append("rule_id = ?")
            params.append(rule_id)
        if source_path is not None:
            clauses.append("source_path = ?")
            params.append(source_path)
        if memory_types is not None:
            type_values = [item.value for item in memory_types]
            if not type_values:
                return []
            clauses.append("memory_type IN (%s)" % ",".join("?" for _ in type_values))
            params.extend(type_values)
        params.append(max(1, min(int(limit), 1000)))
        sql = (
            "SELECT * FROM workspace_memory WHERE "
            + " AND ".join(clauses)
            + " ORDER BY authority DESC, confidence DESC, updated_at DESC LIMIT ?"
        )
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def mark_stale(self, memory_ids: Iterable[str]) -> int:
        ids = list(dict.fromkeys(memory_ids))
        if not ids:
            return 0
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE workspace_memory SET validation_status='stale', updated_at=? "
                "WHERE memory_id IN (%s) AND validation_status='verified'"
                % ",".join("?" for _ in ids),
                [utc_now(), *ids],
            )
            return cursor.rowcount

    def supersede(self, old_memory_id: str, new_record: MemoryRecord) -> MemoryRecord:
        new_record = self.upsert(new_record)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE workspace_memory
                SET validation_status='superseded', superseded_by=?, updated_at=?
                WHERE memory_id=? AND memory_id<>?
                """,
                (new_record.memory_id, utc_now(), old_memory_id, new_record.memory_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"memory not found or already superseded: {old_memory_id}")
        return new_record

    def save_checkpoint(self, checkpoint: CompactionCheckpoint) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO memory_checkpoints (
                    checkpoint_id, session_id, project_workspace_id,
                    canonical_workspace_root, source_prefix_hash,
                    source_message_count, source_last_message_key, branch, head,
                    verified_memory_ids_json, active_constraints_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint.checkpoint_id,
                    checkpoint.session_id,
                    checkpoint.project_workspace_id,
                    checkpoint.canonical_workspace_root,
                    checkpoint.source_prefix_hash,
                    checkpoint.source_message_count,
                    checkpoint.source_last_message_key,
                    checkpoint.branch,
                    checkpoint.head,
                    json.dumps(checkpoint.verified_memory_ids),
                    json.dumps(checkpoint.active_constraints),
                    checkpoint.created_at,
                ),
            )

    def latest_checkpoint(self, session_id: str) -> CompactionCheckpoint | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM memory_checkpoints
                WHERE session_id=? ORDER BY created_at DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return CompactionCheckpoint(
            checkpoint_id=str(row["checkpoint_id"]),
            session_id=str(row["session_id"]),
            project_workspace_id=str(row["project_workspace_id"]),
            canonical_workspace_root=str(row["canonical_workspace_root"]),
            source_prefix_hash=str(row["source_prefix_hash"]),
            source_message_count=int(row["source_message_count"]),
            source_last_message_key=row["source_last_message_key"],
            branch=row["branch"],
            head=row["head"],
            verified_memory_ids=tuple(json.loads(row["verified_memory_ids_json"])),
            active_constraints=tuple(json.loads(row["active_constraints_json"])),
            created_at=str(row["created_at"]),
        )

    def save_governed_operation(
        self,
        *,
        operation_id: str,
        session_id: str,
        project_workspace_id: str,
        canonical_workspace_root: str,
        tool_id: str,
        capability: str,
        request_fingerprint: str,
        request: dict[str, Any],
        approval_id: str,
    ) -> dict[str, Any]:
        """Persist one exact approval-bound operation without changing its identity."""
        now = utc_now()
        request_json = json.dumps(request, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM governed_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if existing is not None:
                immutable = {
                    "session_id": session_id,
                    "project_workspace_id": project_workspace_id,
                    "canonical_workspace_root": canonical_workspace_root,
                    "tool_id": tool_id,
                    "capability": capability,
                    "request_fingerprint": request_fingerprint,
                    "request_json": request_json,
                    "approval_id": approval_id,
                }
                for name, expected in immutable.items():
                    if str(existing[name]) != str(expected):
                        raise ValueError(
                            "governed operation identity or payload does not match persisted approval"
                        )
                return self._row_to_governed_operation(existing)
            connection.execute(
                """
                INSERT INTO governed_operations (
                    operation_id, session_id, project_workspace_id,
                    canonical_workspace_root, tool_id, capability,
                    request_fingerprint, request_json, approval_id,
                    decision, receipt_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, ?, ?)
                """,
                (
                    operation_id,
                    session_id,
                    project_workspace_id,
                    canonical_workspace_root,
                    tool_id,
                    capability,
                    request_fingerprint,
                    request_json,
                    approval_id,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM governed_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        return self._row_to_governed_operation(row)

    def load_governed_operation(self, *, operation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM governed_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        return None if row is None else self._row_to_governed_operation(row)

    def resolve_governed_operation(
        self, *, operation_id: str, approval_id: str, decision: str
    ) -> dict[str, Any]:
        if decision not in {"approve", "reject"}:
            raise ValueError("governed operation decision must be approve or reject")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM governed_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise ValueError("governed operation is not persisted")
            if str(row["approval_id"]) != approval_id:
                raise ValueError("approval id does not match persisted governed operation")
            current = str(row["decision"])
            target = "approved" if decision == "approve" else "rejected"
            if current in {"executed", "failed"}:
                return self._row_to_governed_operation(row)
            if current == "rejected" and target != "rejected":
                raise ValueError("rejected governed operation cannot be approved")
            if current == "approved" and target == "rejected":
                raise ValueError("approved governed operation cannot be rejected")
            if current != target:
                connection.execute(
                    "UPDATE governed_operations SET decision=?, updated_at=? WHERE operation_id=?",
                    (target, utc_now(), operation_id),
                )
            row = connection.execute(
                "SELECT * FROM governed_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        return self._row_to_governed_operation(row)

    def complete_governed_operation(
        self,
        *,
        operation_id: str,
        receipt: dict[str, Any],
        failed: bool = False,
    ) -> dict[str, Any]:
        receipt_json = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM governed_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise ValueError("governed operation is not persisted")
            if str(row["decision"]) in {"executed", "failed"}:
                persisted = row["receipt_json"]
                if persisted is not None and str(persisted) != receipt_json:
                    raise ValueError("terminal governed operation receipt cannot be replaced")
                return self._row_to_governed_operation(row)
            if str(row["decision"]) != "approved":
                raise ValueError("governed operation must be approved before completion")
            connection.execute(
                """
                UPDATE governed_operations
                SET decision=?, receipt_json=?, updated_at=?
                WHERE operation_id=?
                """,
                ("failed" if failed else "executed", receipt_json, utc_now(), operation_id),
            )
            row = connection.execute(
                "SELECT * FROM governed_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        return self._row_to_governed_operation(row)

    @staticmethod
    def _row_to_governed_operation(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "operation_id": str(row["operation_id"]),
            "session_id": str(row["session_id"]),
            "project_workspace_id": str(row["project_workspace_id"]),
            "canonical_workspace_root": str(row["canonical_workspace_root"]),
            "tool_id": str(row["tool_id"]),
            "capability": str(row["capability"]),
            "request_fingerprint": str(row["request_fingerprint"]),
            "request": json.loads(str(row["request_json"])),
            "approval_id": str(row["approval_id"]),
            "decision": str(row["decision"]),
            "receipt": None
            if row["receipt_json"] is None
            else json.loads(str(row["receipt_json"])),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def save_session_state(self, state: SessionState) -> SessionState:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM session_state WHERE session_id=?",
                (state.session_id,),
            ).fetchone()
            if existing:
                state.created_at = str(existing["created_at"])
                state.updated_at = utc_now()
            connection.execute(
                """
                INSERT INTO session_state (
                    session_id, project_workspace_id, canonical_workspace_root,
                    mode, permission, runtime_policy, provider_id, provider_model, active_profile_id,
                    permission_policy_id, evidence_policy_id, checkpoint_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    project_workspace_id=excluded.project_workspace_id,
                    canonical_workspace_root=excluded.canonical_workspace_root,
                    mode=excluded.mode,
                    permission=excluded.permission,
                    runtime_policy=excluded.runtime_policy,
                    provider_id=excluded.provider_id,
                    provider_model=excluded.provider_model,
                    active_profile_id=excluded.active_profile_id,
                    permission_policy_id=excluded.permission_policy_id,
                    evidence_policy_id=excluded.evidence_policy_id,
                    checkpoint_id=excluded.checkpoint_id,
                    updated_at=excluded.updated_at
                """,
                (
                    state.session_id,
                    state.project_workspace_id,
                    state.canonical_workspace_root,
                    state.mode,
                    state.permission,
                    state.runtime_policy,
                    state.provider_id,
                    state.provider_model,
                    state.active_profile_id,
                    state.permission_policy_id,
                    state.evidence_policy_id,
                    state.checkpoint_id,
                    state.created_at,
                    state.updated_at,
                ),
            )
        return state

    def load_session_state(self, *, session_id: str) -> SessionState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM session_state WHERE session_id=?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return SessionState(
            session_id=str(row["session_id"]),
            project_workspace_id=str(row["project_workspace_id"]),
            canonical_workspace_root=str(row["canonical_workspace_root"]),
            mode=str(row["mode"]),
            permission=row["permission"],
            runtime_policy=row["runtime_policy"],
            provider_id=row["provider_id"],
            provider_model=row["provider_model"],
            active_profile_id=row["active_profile_id"],
            permission_policy_id=row["permission_policy_id"],
            evidence_policy_id=row["evidence_policy_id"],
            checkpoint_id=row["checkpoint_id"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def list_session_states(
        self,
        *,
        project_workspace_id: str | None = None,
        limit: int = 100,
    ) -> tuple[SessionState, ...]:
        """Return bounded persisted sessions without exposing SQLite to clients."""
        bounded_limit = max(1, min(int(limit), 500))
        params: list[Any] = []
        where = ""
        if project_workspace_id is not None:
            clean_workspace = str(project_workspace_id).strip()
            if not clean_workspace:
                raise ValueError("project_workspace_id must not be empty")
            where = " WHERE project_workspace_id=?"
            params.append(clean_workspace)
        params.append(bounded_limit)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT session_id FROM session_state"
                + where
                + " ORDER BY updated_at DESC, session_id ASC LIMIT ?",
                params,
            ).fetchall()
        states = []
        for row in rows:
            state = self.load_session_state(session_id=str(row["session_id"]))
            if state is not None:
                states.append(state)
        return tuple(states)

    def save_session_task(self, state: TaskState) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session_tasks (
                    session_id, task_id, project_workspace_id, canonical_workspace_root,
                    status, last_outcome, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, task_id) DO UPDATE SET
                    project_workspace_id=excluded.project_workspace_id,
                    canonical_workspace_root=excluded.canonical_workspace_root,
                    status=excluded.status,
                    last_outcome=excluded.last_outcome,
                    updated_at=excluded.updated_at
                """,
                (state.session_id, state.task_id, state.project_workspace_id,
                 state.canonical_workspace_root, state.status.value, state.last_outcome,
                 state.created_at, state.updated_at),
            )

    def load_session_task(self, *, session_id: str, task_id: str, project_workspace_id: str) -> TaskState | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM session_tasks
                WHERE session_id=? AND task_id=? AND project_workspace_id=?
                """,
                (session_id, task_id, project_workspace_id),
            ).fetchone()
        if not row:
            return None
        return self._row_to_task_state(row)

    def list_session_tasks(self, *, session_id: str, project_workspace_id: str) -> tuple[TaskState, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM session_tasks
                WHERE session_id=? AND project_workspace_id=?
                ORDER BY updated_at DESC
                """,
                (session_id, project_workspace_id),
            ).fetchall()
        return tuple(self._row_to_task_state(row) for row in rows)

    @staticmethod
    def _row_to_task_state(row: sqlite3.Row) -> TaskState:
        try:
            status = TaskStatus(str(row["status"]))
        except ValueError as exc:
            raise ValueError("Corrupted session task state: invalid status " + repr(row["status"])) from exc
        return TaskState(
            session_id=str(row["session_id"]),
            task_id=str(row["task_id"]),
            project_workspace_id=str(row["project_workspace_id"]),
            canonical_workspace_root=str(row["canonical_workspace_root"]),
            status=status,
            last_outcome=row["last_outcome"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            memory_id=str(row["memory_id"]),
            project_workspace_id=str(row["project_workspace_id"]),
            canonical_workspace_root=str(row["canonical_workspace_root"]),
            task_id=row["task_id"],
            rule_id=row["rule_id"],
            memory_type=MemoryType(str(row["memory_type"])),
            subject=str(row["subject"]),
            predicate=str(row["predicate"]),
            value=json.loads(str(row["value_json"])),
            source_type=SourceType(str(row["source_type"])),
            source_path=row["source_path"],
            source_hash=row["source_hash"],
            source_commit=row["source_commit"],
            source_message_id=row["source_message_id"],
            authority=int(row["authority"]),
            validation_status=ValidationStatus(str(row["validation_status"])),
            validation_method=row["validation_method"],
            validated_at=row["validated_at"],
            confidence=float(row["confidence"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            superseded_by=row["superseded_by"],
        )
