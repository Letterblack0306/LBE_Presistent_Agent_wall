# Acceptance and Gate Records

This collection holds authorization projections, checkpoints, and validation evidence. It is not
a second roadmap. The authoritative active slice is always
`.lbe/governance/implementation-gates.json`.

## Read first

1. `CURRENT_IMPLEMENTATION_GATE.md` — human-readable projection of the active machine state.
2. The `active_plan` path named in the machine gate — the active acceptance slice.
3. `CURRENT_STATUS.md` and `IMPLEMENTATION_PLAN.md` — current state and ordered work.

## Current state

The machine gate currently names `COMPLETE_LBE_AGENT_RUNTIME_GATE.md` as the active human
acceptance plan, with phase `COMPLETE_LBE_AGENT_RUNTIME_IMPLEMENTATION` and slice
`DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE`. Publication preparation and terminal-workspace foundation
records are retained as paused or superseded evidence; they are not active authorization.

All other gate/checkpoint files preserve the evidence and authorization that existed when they
were written. They must not be read as current permission merely because their filenames include
"current", "execution", or "publication".
