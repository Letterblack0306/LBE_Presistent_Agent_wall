from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .compaction import persist_compaction_checkpoint
from .context import inspect_git_state, rehydrate_context
from .models import MemoryType, SourceType, ValidationStatus, canonical_root
from .promoter import CandidateClaim, MemoryPromoter
from .store import WorkspaceMemoryStore


class SessionMemoryAdapter:
    """Narrow runtime adapter between session/tool events and validated memory.

    The adapter accepts structured, deterministic evidence only. It never parses
    assistant prose, compaction summaries, or natural-language conclusions into
    verified workspace facts.
    """

    def __init__(
        self,
        *,
        store: WorkspaceMemoryStore,
        project_workspace_id: str,
        workspace_root: str | Path,
    ) -> None:
        self.store = store
        self.project_workspace_id = project_workspace_id.strip()
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        if not self.project_workspace_id:
            raise ValueError("project_workspace_id must not be empty")
        if not self.workspace_root.exists() or not self.workspace_root.is_dir():
            raise FileNotFoundError(
                f"Workspace root does not exist or is not a directory: {self.workspace_root}"
            )
        self.promoter = MemoryPromoter(store)

    def record_git_state(
        self,
        *,
        source_message_id: str | None = None,
        task_id: str | None = None,
    ) -> list[str]:
        state = inspect_git_state(self.workspace_root)
        records = []
        for predicate, value in (
            ("git_branch", state.get("branch")),
            ("git_head", state.get("head")),
            ("changed_files", list(state.get("status_short") or [])),
        ):
            records.append(
                self.promoter.promote(
                    CandidateClaim(
                        project_workspace_id=self.project_workspace_id,
                        canonical_workspace_root=str(self.workspace_root),
                        task_id=task_id,
                        memory_type=MemoryType.WORKSPACE_FACT,
                        subject="repository",
                        predicate=predicate,
                        value=value,
                        source_type=SourceType.GIT,
                        source_commit=state.get("head"),
                        source_message_id=source_message_id,
                        authority=10,
                    )
                )
            )
        return [record.memory_id for record in records]

    def record_command_result(
        self,
        *,
        command: str,
        cwd: str | Path,
        exit_code: int,
        source_message_id: str | None = None,
        task_id: str | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> str:
        value = {
            "command": command,
            "cwd": canonical_root(cwd),
            "exit_code": int(exit_code),
            "stdout": stdout,
            "stderr": stderr,
        }
        record = self.promoter.promote(
            CandidateClaim(
                project_workspace_id=self.project_workspace_id,
                canonical_workspace_root=str(self.workspace_root),
                task_id=task_id,
                memory_type=MemoryType.VALIDATION_RESULT,
                subject=command,
                predicate="command_exit_code",
                value=value,
                source_type=SourceType.COMMAND_RESULT,
                source_message_id=source_message_id,
                authority=9,
                validation_method="process-exit-code",
            )
        )
        return record.memory_id

    def record_file_hash(
        self,
        *,
        relative_path: str,
        source_message_id: str | None = None,
        task_id: str | None = None,
    ) -> str:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("relative_path must remain inside the workspace")
        candidate = (self.workspace_root / relative).resolve()
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ValueError("relative_path escapes the workspace") from exc
        if not candidate.is_file():
            raise FileNotFoundError(f"Workspace file does not exist: {candidate}")
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        normalized = candidate.relative_to(self.workspace_root).as_posix()
        record = self.promoter.promote(
            CandidateClaim(
                project_workspace_id=self.project_workspace_id,
                canonical_workspace_root=str(self.workspace_root),
                task_id=task_id,
                memory_type=MemoryType.WORKSPACE_FACT,
                subject=normalized,
                predicate="file_sha256",
                value=digest,
                source_type=SourceType.LIVE_WORKSPACE,
                source_path=normalized,
                source_hash=digest,
                source_message_id=source_message_id,
                authority=10,
                validation_method="sha256",
            )
        )
        return record.memory_id

    def record_assistant_observation(
        self,
        *,
        subject: str,
        predicate: str,
        value: Any,
        source_message_id: str | None = None,
        task_id: str | None = None,
    ) -> str:
        record = self.promoter.promote(
            CandidateClaim(
                project_workspace_id=self.project_workspace_id,
                canonical_workspace_root=str(self.workspace_root),
                task_id=task_id,
                memory_type=MemoryType.HISTORICAL_OBSERVATION,
                subject=subject,
                predicate=predicate,
                value=value,
                source_type=SourceType.ASSISTANT_REASONING,
                source_message_id=source_message_id,
                authority=1,
            )
        )
        if record.validation_status is not ValidationStatus.UNVERIFIED:
            raise RuntimeError("assistant observation was promoted unexpectedly")
        return record.memory_id

    def checkpoint_compaction(
        self,
        *,
        session_id: str,
        compaction: str | Path | dict[str, Any],
        active_constraints: list[str] | tuple[str, ...] = (),
    ) -> str:
        verified = self.store.query(
            project_workspace_id=self.project_workspace_id,
            statuses=(ValidationStatus.VERIFIED,),
            limit=500,
        )
        git_state = inspect_git_state(self.workspace_root)
        checkpoint = persist_compaction_checkpoint(
            self.store,
            session_id=session_id,
            project_workspace_id=self.project_workspace_id,
            workspace_root=self.workspace_root,
            compaction=compaction,
            verified_memory_ids=[record.memory_id for record in verified],
            active_constraints=active_constraints,
            branch=git_state.get("branch"),
            head=git_state.get("head"),
        )
        return checkpoint.checkpoint_id

    def rehydrate(
        self,
        *,
        session_id: str | None = None,
        task_id: str | None = None,
        recent_messages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return rehydrate_context(
            store=self.store,
            project_workspace_id=self.project_workspace_id,
            workspace_root=self.workspace_root,
            task_id=task_id,
            recent_messages=recent_messages,
            session_id=session_id,
        )
