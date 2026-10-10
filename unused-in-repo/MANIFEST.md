# `unused-in-repo/` Preservation Manifest

Status: **CANONICAL PRESERVATION REGISTER**

This manifest records material moved out of the live repository surface only after
evidence proves that it does not participate in the current canonical project.
It is a recovery and review index, not a declaration that the content may be deleted.

## Lookup order

```text
canonical project
    -> this manifest
    -> historical/reference repositories
    -> deeper filesystem discovery only when still unresolved
```

## Move requirements

Every entry must include all fields below before the move is staged:

```text
ORIGINAL_PATH
CURRENT_PATH
CLASSIFICATION: UNUSED_BUT_PRESERVED
WHY_UNUSED
REFERENCE_SCAN
IMPORT/CONSUMER_SCAN
GIT_STATUS
OWNER_BEFORE_MOVE
MOVE_COMMIT
DATE
RESTORE_NOTES
```

The required negative proof is explicit: no current source import, runtime call,
test dependency, build/release dependency, governance dependency, active acceptance
dependency, documentation-authority dependency, tool-path dependency, protected-user
ownership, runtime/database/state role, embedded-repository role, or deliberate local
reference role.

`UNREFERENCED` is not `UNUSED`; `UNUSED` is not `DISPOSABLE`; and `DISPOSABLE` is
not automatic permission to delete.

## Entries

```text
ORIGINAL_PATH: lbe_guard_inspector/textual_tui.py
CURRENT_PATH: unused-in-repo/textual_tui.py
CLASSIFICATION: UNUSED_BUT_PRESERVED
WHY_UNUSED: Superseded by canonical Rust Ratatui TUI implementation in apps/lbe-terminal
REFERENCE_SCAN: Verified no active import or runtime dependency in product UI execution
IMPORT/CONSUMER_SCAN: Clear
GIT_STATUS: Moved out of live python package surface
OWNER_BEFORE_MOVE: lbe_guard_inspector
MOVE_COMMIT: WORKSPACE_MAINTENANCE_20261011
DATE: 2026-10-11
RESTORE_NOTES: Reference Python Textual prototype; active TUI owner is apps/lbe-terminal
```
