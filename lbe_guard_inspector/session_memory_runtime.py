from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .memory import (
    CandidateClaim,
    MemoryPromoter,
    MemoryType,
    SessionMemoryAdapter,
    SourceType,
    WorkspaceMemoryStore,
)


class SessionMemoryRuntimeBridge:
    """One bounded runtime bridge for validated session memory.

    Command and tool results must be deterministic structured records. Registry
    receipts remain registry evidence; this bridge only returns correlation
    metadata and never promotes receipts or model prose into workspace truth.
    """

    def __init__(
        self,
        *,
        database_path: str | Path,
        project_workspace_id: str,
        workspace_root: str | Path,
        session_id: str,
    ) -> None:
        clean_session = session_id.strip()
        if not clean_session:
            raise ValueError("session_id must not be empty")
        self.session_id = clean_session
        self.store = WorkspaceMemoryStore(database_path)
        self.adapter = SessionMemoryAdapter(
            store=self.store,
            project_workspace_id=project_workspace_id,
            workspace_root=workspace_root,
        )
        self.promoter = MemoryPromoter(self.store)

    @property
    def project_workspace_id(self) -> str:
        return self.adapter.project_workspace_id

    @property
    def workspace_root(self) -> Path:
        return self.adapter.workspace_root

    def start_or_resume(
        self,
        *,
        task_id: str | None = None,
        recent_messages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self.adapter.rehydrate(
            session_id=self.session_id,
            task_id=task_id,
            recent_messages=recent_messages,
        )

    def ingest_command_result(
        self,
        *,
        command: str,
        cwd: str | Path,
        exit_code: int,
        task_id: str | None = None,
        source_message_id: str | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> str:
        return self.adapter.record_command_result(
            command=command,
            cwd=cwd,
            exit_code=exit_code,
            task_id=task_id,
            source_message_id=source_message_id,
            stdout=stdout,
            stderr=stderr,
        )

    def ingest_tool_result(
        self,
        *,
        tool_name: str,
        result: Mapping[str, Any],
        success: bool,
        task_id: str | None = None,
        source_message_id: str | None = None,
    ) -> str:
        clean_name = tool_name.strip()
        if not clean_name:
            raise ValueError("tool_name must not be empty")
        if not isinstance(result, Mapping):
            raise TypeError("result must be a structured mapping")
        record = self.promoter.promote(
            CandidateClaim(
                project_workspace_id=self.project_workspace_id,
                canonical_workspace_root=str(self.workspace_root),
                task_id=task_id,
                memory_type=MemoryType.VALIDATION_RESULT,
                subject=clean_name,
                predicate="tool_result",
                value={"success": bool(success), "result": dict(result)},
                source_type=SourceType.COMMAND_RESULT,
                source_message_id=source_message_id,
                authority=9,
                validation_method="structured-tool-result",
            )
        )
        return record.memory_id

    def checkpoint(
        self,
        *,
        compaction: str | Path | dict[str, Any],
        active_constraints: list[str] | tuple[str, ...] = (),
    ) -> str:
        return self.adapter.checkpoint_compaction(
            session_id=self.session_id,
            compaction=compaction,
            active_constraints=active_constraints,
        )

    def correlate_registry_receipt(
        self,
        *,
        module_id: str,
        receipt_sequence: int,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        clean_module = module_id.strip()
        if not clean_module:
            raise ValueError("module_id must not be empty")
        if receipt_sequence < 1:
            raise ValueError("receipt_sequence must be positive")
        return {
            "project_workspace_id": self.project_workspace_id,
            "session_id": self.session_id,
            "task_id": task_id,
            "module_id": clean_module,
            "receipt_sequence": receipt_sequence,
            "memory_evidence_stored": False,
        }
