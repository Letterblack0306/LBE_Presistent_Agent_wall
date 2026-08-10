from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from lbe_guard_inspector.contracts import validate_contract

from .models import (
    CompactionCheckpoint,
    MemoryRecord,
    MemoryType,
    ValidationStatus,
    canonical_root,
)
from .store import WorkspaceMemoryStore


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_git_state(workspace_root: str | Path) -> dict[str, Any]:
    root = Path(workspace_root).resolve()

    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return completed.stdout.strip()

    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "status_short": run("status", "--short").splitlines(),
    }


def invalidate_changed_sources(
    store: WorkspaceMemoryStore,
    records: list[MemoryRecord],
    workspace_root: str | Path,
) -> list[MemoryRecord]:
    root = Path(workspace_root).resolve()
    stale_ids: list[str] = []
    current: list[MemoryRecord] = []
    for record in records:
        if not record.source_path or not record.source_hash:
            current.append(record)
            continue
        source = Path(record.source_path)
        if not source.is_absolute():
            source = root / source
        try:
            source.resolve().relative_to(root)
        except ValueError:
            stale_ids.append(record.memory_id)
            continue
        try:
            matches = source.is_file() and sha256_file(source) == record.source_hash
        except OSError:
            matches = False
        if matches:
            current.append(record)
        else:
            stale_ids.append(record.memory_id)
    store.mark_stale(stale_ids)
    return current


def protected_checkpoint_eligibility(
    *,
    checkpoint: CompactionCheckpoint | None,
    current_workspace_id: str,
    current_workspace_root: str | Path,
    current_git_state: dict[str, Any],
    current_source_prefix_hash: str | None = None,
) -> dict[str, Any]:
    check_names = (
        "workspace_identity",
        "workspace_root",
        "source_prefix",
        "branch",
        "head",
    )

    if checkpoint is None:
        report = {
            "status": "INSUFFICIENT_EVIDENCE",
            "checkpoint_id": None,
            "reasons": ["CHECKPOINT_NOT_FOUND"],
            "checks": {name: "UNKNOWN" for name in check_names},
            "authority_owner": "LBE_MEMORY_RUNTIME",
            "reactivation_allowed": False,
        }
        validate_contract("protected_checkpoint_eligibility", report)
        return report

    current_branch = current_git_state.get("branch")
    current_head = current_git_state.get("head")
    checks = {
        "workspace_identity": (
            "MATCH"
            if checkpoint.project_workspace_id == current_workspace_id
            else "MISMATCH"
        ),
        "workspace_root": (
            "MATCH"
            if checkpoint.canonical_workspace_root == canonical_root(current_workspace_root)
            else "MISMATCH"
        ),
        "source_prefix": (
            "UNKNOWN"
            if current_source_prefix_hash is None
            else (
                "MATCH"
                if checkpoint.source_prefix_hash == current_source_prefix_hash
                else "MISMATCH"
            )
        ),
        "branch": (
            "UNKNOWN"
            if checkpoint.branch is None or not current_branch
            else ("MATCH" if checkpoint.branch == current_branch else "MISMATCH")
        ),
        "head": (
            "UNKNOWN"
            if checkpoint.head is None or not current_head
            else ("MATCH" if checkpoint.head == current_head else "MISMATCH")
        ),
    }

    mismatches = sorted(name for name, result in checks.items() if result == "MISMATCH")
    unknowns = sorted(name for name, result in checks.items() if result == "UNKNOWN")

    if mismatches:
        status = "INELIGIBLE"
        reasons = [f"{name.upper()}_MISMATCH" for name in mismatches]
    elif unknowns:
        status = "INSUFFICIENT_EVIDENCE"
        reasons = [f"{name.upper()}_EVIDENCE_MISSING" for name in unknowns]
    else:
        status = "ELIGIBLE"
        reasons = []

    report = {
        "status": status,
        "checkpoint_id": checkpoint.checkpoint_id,
        "reasons": reasons,
        "checks": checks,
        "authority_owner": "LBE_MEMORY_RUNTIME",
        "reactivation_allowed": status == "ELIGIBLE",
    }
    validate_contract("protected_checkpoint_eligibility", report)
    return report


def build_context_packet(
    *,
    project_workspace_id: str,
    workspace_root: str | Path,
    git_state: dict[str, Any],
    records: list[MemoryRecord],
    task_id: str | None = None,
    recent_messages: list[dict[str, Any]] | None = None,
    checkpoint: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    task_state: dict[str, Any] | None = None,
    checkpoint_revalidation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verified_facts: list[dict[str, Any]] = []
    active_constraints: list[dict[str, Any]] = []
    recent_failures: list[dict[str, Any]] = []
    for record in records:
        payload = record.as_dict()
        if record.memory_type is MemoryType.TASK_CONSTRAINT:
            active_constraints.append(payload)
        elif record.memory_type is MemoryType.FAILURE_PATTERN:
            recent_failures.append(payload)
        else:
            verified_facts.append(payload)

    task_payload = task_state or {"task_id": task_id, "current_status": "in_progress"}
    return {
        "session": session_state,
        "workspace": {
            "project_workspace_id": project_workspace_id,
            "canonical_root": canonical_root(workspace_root),
            "branch": git_state.get("branch"),
            "head": git_state.get("head"),
            "status_short": list(git_state.get("status_short") or []),
        },
        "task": task_payload,
        "checkpoint": checkpoint,
        "checkpoint_revalidation": checkpoint_revalidation,
        "verified_facts": verified_facts,
        "active_constraints": active_constraints,
        "checkpoint_constraints": list((checkpoint or {}).get("active_constraints") or []),
        "recent_failures": recent_failures,
        "live_evidence_required": [
            "Revalidate Git state before write operations.",
            "Revalidate source hashes before treating stored facts as current.",
            "Do not use assistant reasoning or compaction summaries as authority.",
        ],
        "recent_messages": list(recent_messages or []),
    }


def rehydrate_context(
    *,
    store: WorkspaceMemoryStore,
    project_workspace_id: str,
    workspace_root: str | Path,
    task_id: str | None = None,
    recent_messages: list[dict[str, Any]] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    root = canonical_root(workspace_root)
    session = store.load_session_state(session_id=session_id) if session_id else None
    if session is not None:
        if session.project_workspace_id != project_workspace_id:
            raise ValueError("persisted session workspace identity does not match runtime workspace")
        if session.canonical_workspace_root != root:
            raise ValueError("persisted session workspace root does not match runtime workspace")

    git_state = inspect_git_state(workspace_root)
    records = store.query(
        project_workspace_id=project_workspace_id,
        statuses=(ValidationStatus.VERIFIED,),
        limit=500,
    )
    current_records = invalidate_changed_sources(store, records, workspace_root)
    checkpoint = store.latest_checkpoint(session_id) if session_id else None
    checkpoint_payload = None
    checkpoint_revalidation = None
    if checkpoint:
        checkpoint_payload = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "source_prefix_hash": checkpoint.source_prefix_hash,
            "source_message_count": checkpoint.source_message_count,
            "branch": checkpoint.branch,
            "head": checkpoint.head,
            "active_constraints": list(checkpoint.active_constraints),
            "created_at": checkpoint.created_at,
        }
        checkpoint_revalidation = protected_checkpoint_eligibility(
            checkpoint=checkpoint,
            current_workspace_id=project_workspace_id,
            current_workspace_root=workspace_root,
            current_git_state=git_state,
        )

    task = None
    if session_id and task_id:
        task = store.load_session_task(
            session_id=session_id,
            task_id=task_id,
            project_workspace_id=project_workspace_id,
        )

    return build_context_packet(
        project_workspace_id=project_workspace_id,
        workspace_root=workspace_root,
        git_state=git_state,
        records=current_records,
        task_id=task_id,
        recent_messages=recent_messages,
        checkpoint=checkpoint_payload,
        session_state=session.as_dict() if session else None,
        task_state=(
            {
                "task_id": task.task_id,
                "current_status": task.status.value,
                "last_outcome": task.last_outcome,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
            if task
            else None
        ),
        checkpoint_revalidation=checkpoint_revalidation,
    )
