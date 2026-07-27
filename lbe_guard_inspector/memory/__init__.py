"""Validated project-scoped memory for persistent agent sessions.

Session transcripts and compaction summaries are historical inputs. Only records
promoted through deterministic evidence or explicit validation may be queried as
verified workspace memory.
"""

from .compaction import (
    checkpoint_from_compaction,
    load_compaction,
    persist_compaction_checkpoint,
)
from .context import (
    build_context_packet,
    inspect_git_state,
    invalidate_changed_sources,
    rehydrate_context,
)
from .models import (
    CompactionCheckpoint,
    MemoryRecord,
    MemoryType,
    SourceType,
    ValidationStatus,
)
from .promoter import CandidateClaim, MemoryPromoter
from .store import WorkspaceMemoryStore

__all__ = [
    "CandidateClaim",
    "CompactionCheckpoint",
    "MemoryPromoter",
    "MemoryRecord",
    "MemoryType",
    "SourceType",
    "ValidationStatus",
    "WorkspaceMemoryStore",
    "build_context_packet",
    "checkpoint_from_compaction",
    "inspect_git_state",
    "invalidate_changed_sources",
    "load_compaction",
    "persist_compaction_checkpoint",
    "rehydrate_context",
]
