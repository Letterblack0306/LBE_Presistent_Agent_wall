from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .models import CompactionCheckpoint, canonical_root, utc_now
from .store import WorkspaceMemoryStore


def load_compaction(value: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        payload = value
    else:
        payload = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("compaction payload must be a JSON object")
    required = {
        "source_message_count",
        "source_prefix_hash",
        "source_last_message_key",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"compaction payload missing fields: {missing}")
    if not isinstance(payload["source_message_count"], int):
        raise ValueError("source_message_count must be an integer")
    if payload["source_message_count"] < 0:
        raise ValueError("source_message_count must be non-negative")
    prefix_hash = str(payload["source_prefix_hash"])
    if not prefix_hash.startswith("sha256:"):
        raise ValueError("source_prefix_hash must use sha256: prefix")
    return payload


def checkpoint_from_compaction(
    *,
    session_id: str,
    project_workspace_id: str,
    workspace_root: str | Path,
    compaction: str | Path | dict[str, Any],
    verified_memory_ids: list[str] | tuple[str, ...],
    active_constraints: list[str] | tuple[str, ...],
    branch: str | None = None,
    head: str | None = None,
) -> CompactionCheckpoint:
    payload = load_compaction(compaction)
    return CompactionCheckpoint(
        checkpoint_id=f"cp-{uuid.uuid4().hex}",
        session_id=session_id,
        project_workspace_id=project_workspace_id,
        canonical_workspace_root=canonical_root(workspace_root),
        source_prefix_hash=str(payload["source_prefix_hash"]),
        source_message_count=int(payload["source_message_count"]),
        source_last_message_key=(
            str(payload["source_last_message_key"])
            if payload["source_last_message_key"] is not None
            else None
        ),
        branch=branch,
        head=head,
        verified_memory_ids=tuple(dict.fromkeys(verified_memory_ids)),
        active_constraints=tuple(dict.fromkeys(active_constraints)),
        created_at=utc_now(),
    )


def persist_compaction_checkpoint(
    store: WorkspaceMemoryStore,
    **kwargs: Any,
) -> CompactionCheckpoint:
    checkpoint = checkpoint_from_compaction(**kwargs)
    store.save_checkpoint(checkpoint)
    return checkpoint
