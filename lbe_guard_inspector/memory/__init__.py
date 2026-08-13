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
from .integration import SessionMemoryAdapter
from .models import (
    CompactionCheckpoint,
    MemoryRecord,
    MemoryType,
    SessionState,
    SourceType,
    TaskState,
    TaskStatus,
    ValidationStatus,
)
from .operational_history import (
    ItemStatus,
    OperationalEvent,
    OperationalHistoryError,
    OperationalItem,
    OperationalTurn,
    SessionOperationalHistory,
    TurnStatus,
)
from .promoter import CandidateClaim, MemoryPromoter
from .store import WorkspaceMemoryStore

__all__ = [
    "CandidateClaim",
    "CompactionCheckpoint",
    "ItemStatus",
    "MemoryPromoter",
    "MemoryRecord",
    "MemoryType",
    "OperationalEvent",
    "OperationalHistoryError",
    "OperationalItem",
    "OperationalTurn",
    "SessionMemoryAdapter",
    "SessionOperationalHistory",
    "SessionState",
    "SourceType",
    "TaskState",
    "TaskStatus",
    "TurnStatus",
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
