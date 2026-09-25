# Acceptance and Gate Records

This collection holds authorization projections, checkpoints, and validation evidence. It is not
a second roadmap. The authoritative active slice is always
`.lbe/governance/implementation-gates.json`.

## Read first

1. `CURRENT_IMPLEMENTATION_GATE.md` — human-readable projection of the active machine state.
2. The `active_plan` path named in the machine gate — the active acceptance slice.
3. `CURRENT_STATUS.md` and `IMPLEMENTATION_PLAN.md` — current state and ordered work.

## Current state

The machine gate currently names `INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md` as the
active human acceptance plan, with phase `INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE` and
slice `MAIN_HEAD_CONSOLIDATION_AND_TRUTHFUL_ACCEPTANCE`. Publication preparation and older
terminal-workspace records are retained as paused, superseded, or historical evidence; they are not
active authorization.

The current product contract is:

```text
product                 = LBE
entrypoint              = lbe
visible client          = LBE-owned Rust/Ratatui at apps/lbe-terminal/
reasoning               = engine-neutral; Cline supported adapter
runtime/governance      = LBE
final acceptance        = OPEN; release remains blocked pending current proof
```

All other gate/checkpoint files preserve the evidence and authorization that existed when they
were written. They must not be read as current permission merely because their filenames include
"current", "execution", or "publication".

## Historical baseline rule

The R3–R7 records are preserved accepted historical evidence for their declared revisions and
bounded observables. They are not invalidated by later reconciliation, but they are not current
installed-product proof. The active status remains `OPEN` and release remains blocked until the
present packaged `lbe` path re-demonstrates the required provider/model, governed execution,
receipt/evidence, continuation, persistence/resume, completion, and terminal-restoration claims.
