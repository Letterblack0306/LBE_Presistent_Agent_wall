# Validated Workspace Memory

## Invariant

> Session history records what happened. Durable memory records only validated claims. Live workspace inspection remains authoritative.

This implementation keeps Cline-style session files unchanged:

- `<session-id>.json` — runtime/session metadata;
- `<session-id>.messages.json` — complete chronological history;
- `<session-id>.compaction.json` — lossy continuation context.

None of those files is treated as authoritative workspace truth.

## Layers

```text
Live workspace and Git
    -> deterministic evidence
    -> promotion policy
    -> project-scoped SQLite memory
    -> rehydrated context packet
    -> LLM
```

The SQLite store is scoped by both `project_workspace_id` and
`canonical_workspace_root`. Reference-repository patterns must be stored under a
different project identity and lower authority than current-project evidence.

## Modules

| Module | Responsibility |
|---|---|
| `memory_schema.sql` | Durable records and compaction checkpoints |
| `models.py` | Typed memory, provenance, validation states |
| `store.py` | Insert/upsert/query/stale/supersede/checkpoint operations |
| `promoter.py` | Evidence-based promotion policy |
| `compaction.py` | Validate compaction metadata and persist checkpoint provenance |
| `context.py` | Hash invalidation, Git inspection, and context-packet construction |
| `integration.py` | Runtime-neutral `SessionMemoryAdapter` for session, command, compaction, and resume integration |

## Trust rules

Automatically verifiable predicates include canonical workspace roots, Git
branch/HEAD, file hashes, exact command/test exit codes, changed-file lists, and
validated configuration values when they come from trusted tools.

Interpretive claims such as “feature implemented”, “task complete”, “file
broken”, or “defect fixed” remain unverified until a separate validator supplies
an explicit validation method.

Assistant reasoning and compaction summaries can only be stored as unverified
historical observations. The typed model rejects attempts to create them as
verified records.

## Compaction handling

When a compaction file is produced:

1. keep the raw messages file;
2. validate `source_message_count`, `source_prefix_hash`, and
   `source_last_message_key`;
3. persist a checkpoint containing branch, HEAD, verified memory IDs, and active
   constraints;
4. on the next turn, retrieve verified project memory;
5. recompute hashes for file-backed records and mark mismatches `stale`;
6. inspect current Git branch, HEAD, and worktree status;
7. build a bounded context packet with recent messages instead of replaying the
   complete transcript.

## Example

```python
from lbe_guard_inspector.memory import (
    CandidateClaim,
    MemoryPromoter,
    MemoryType,
    SessionMemoryAdapter,
    SourceType,
    WorkspaceMemoryStore,
    persist_compaction_checkpoint,
    rehydrate_context,
)

store = WorkspaceMemoryStore("state/workspace-memory.db")
promoter = MemoryPromoter(store)

head = promoter.promote(
    CandidateClaim(
        project_workspace_id="project-123",
        canonical_workspace_root="C:/workspace/project",
        memory_type=MemoryType.WORKSPACE_FACT,
        subject="repository",
        predicate="git_head",
        value="abc123",
        source_type=SourceType.GIT,
        authority=10,
    )
)

persist_compaction_checkpoint(
    store,
    session_id="session-1",
    project_workspace_id="project-123",
    workspace_root="C:/workspace/project",
    compaction="session-1.compaction.json",
    verified_memory_ids=[head.memory_id],
    active_constraints=["do not commit"],
    branch="main",
    head="abc123",
)

packet = rehydrate_context(
    store=store,
    session_id="session-1",
    project_workspace_id="project-123",
    workspace_root="C:/workspace/project",
    recent_messages=[],
)
```

## Validated implementation status

The repository-side memory foundation and runtime-neutral adapter are implemented on
`feat/validated-workspace-memory-integration`.

Validated at commit `c79b8968a1da704c17d0052c0e6e51cb90de5829`:

- targeted memory and adapter tests: 14 passed;
- full repository suite: 67 passed;
- `git diff --check`: passed;
- validation worktree: clean.

This proves the storage, promotion, checkpoint, invalidation, context-building,
and adapter contracts. It does not prove integration with a real external agent
runtime.

## Module Registry priority

The next implementation priority is the live Module Registry defined in
`docs/PRIORITY_MODULE_REGISTRY.md`.

The registry complements memory rather than replacing it:

- validated memory answers what remains safe to carry across sessions;
- the Module Registry answers what modules exist, what loaded, what is running,
  what each module is doing, which dependencies it uses, and what failed.

Agents must consult registry declarations and runtime receipts before attempting
to reconstruct runtime behavior from imports or broad source inspection.

## Current scope

This branch currently provides:

- validated project-scoped memory;
- compaction checkpoint provenance;
- stale-source invalidation;
- rehydrated context packets;
- a runtime-neutral `SessionMemoryAdapter`;
- the priority Module Registry architecture contract;
- a current-status document at `docs/CURRENT_STATUS.md`.

It does not yet provide:

- live Module Registry code;
- module watcher code;
- registry UI;
- runtime-specific Cline, Brew, Browser Dev, or other lifecycle wiring;
- automatic prompt injection, compaction capture, or module receipts from a real runtime.

The next implementation slice must build and validate the registry foundation,
then connect both registry receipts and `SessionMemoryAdapter` to the actual
runtime authority.
