# Current Implementation Gate

Status: **OPEN — COMPLETE LBE AGENT RUNTIME — PUBLICATION PAUSED**

This file is the human-readable projection of `.lbe/governance/implementation-gates.json`.
The machine-declared active plan is
`docs/acceptance/COMPLETE_LBE_AGENT_RUNTIME_GATE.md`; live Git/runtime/validation
evidence and the machine gate outrank this summary.

## CURRENT MACHINE STATE (authoritative)

```text
phase: COMPLETE_LBE_AGENT_RUNTIME_IMPLEMENTATION
slice: WORKSPACE_HYGIENE_GOVERNED_DELETION
status: OPEN
target_version: 2.0.3 (publication paused)
implementation_allowed: true (active workspace-hygiene slice only)
architecture_changes_allowed: true (explicit user authorization)
next_phase_locked: true
publication_controls: false (nested publication governance records)
```

Only the exact paths and scope declared by the machine gate are authorized. The active slice is
governed workspace-hygiene deletion; it does not authorize a second runtime, provider,
execution, authorization, or completion owner.

## Accepted baseline

```text
R3-R6F: PROVEN_COMPLETE
CLI: PROVEN_COMPLETE
R7_INSTALLED_END_TO_END_ACCEPTANCE: PASS
RELEASE_PACKAGE_CONTRACT_REPAIR: PASS
RELEASE_PACKAGE_READINESS_ACCEPTANCE: PASS
PUBLICATION_PRECHECK: PASS
```

## Current proof required before this slice can pass

```text
focused Textual/client handler tests
 -> persisted event/receipt projection tests
 -> manual local TUI launch from current source
 -> git diff --check
```

`publish_allowed` remains false. Version 2.0.3 preparation is paused and must be reactivated by
a future machine-gate change after the active complete-runtime slice passes.

## HISTORICAL FAILURE (preserved, not current state)

The earlier R7 observable-3 installed coding-composition failure is retained in
`docs/acceptance/R7_REPAIR_INVESTIGATION_GATE.md`,
`docs/acceptance/R7_REPAIR_IMPLEMENTATION_GATE.md`, and
`docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md`. It does not mark current R7 as
failed: R7 is `PASS`, with observables 3 and 13 recorded `PASS_AFTER_REPAIR`.

## ARCHITECTURAL LESSON (proposed follow-on review, not an active gate)

> **LBE governs an agent's capabilities and consequences; it does not prescribe the agent's
> reasoning procedure.**

The architectural mistake was that the reasoning controller became the agent:
`LBERequestController` and the fixed `ReasoningPlan` workflow evolved from a bounded inspection
mechanism into the central cognitive path. The intended relationship is:

```text
reasoning agent
    ↓ uses
LBE governed capabilities
```

The provider owns reasoning, strategy, hypothesis formation, capability selection, replanning,
interpretation, and communication. LBE owns identity, mode/policy, authorization, capability
boundaries, governed execution, operation identity, ToolReceipt, evidence provenance,
persistence, and deterministic validation/completion truth.

Existing components must be repositioned rather than discarded: `LBERequestController` becomes a
bounded/specialist investigation capability; `ReasoningPlan` is optional for specific
planning/inspection capabilities; Guard Inspector remains deterministic; R6C/R6E/ToolReceipt
remain the authoritative execution boundary; memory/context are resources for reasoning.

This is a future architecture acceptance requirement / proposed follow-on review. It does not
activate a new machine gate or change this gate state. The complete comparison and acceptance
question are in `docs/design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md` and
`docs/IMPLEMENTATION_PLAN.md` section 15.
