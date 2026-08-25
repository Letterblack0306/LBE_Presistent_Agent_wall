# Complete LBE Agent Runtime Gate

Status: **OPEN — EXPLICIT USER AUTHORIZATION — PUBLICATION PAUSED**

## Machine-selected state

```text
phase: COMPLETE_LBE_AGENT_RUNTIME_IMPLEMENTATION
slice: MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH
slice_result: PASS
status: OPEN
implementation_allowed: true
architecture_changes_allowed: true (explicit user authorization)
next_phase_locked: true
publication_controls: false (nested publication governance records)
next_product_slice: NOT YET ACTIVATED
```

The machine gate at `.lbe/governance/implementation-gates.json` is the execution authority. This document is the human-readable gate projection and must not independently select a new slice.

## Scope

Deliver one local LBE agent runtime. Providers supply reasoning only; LBE owns workspace identity, doctrine/mode, policy, authorization, governed dispatch, receipts, evidence, persistence, recovery, and deterministic completion. The terminal is the user-facing LBE projection/control client and must not become a second runtime.

```text
open LBE
  -> resolve workspace/session/provider/profile/doctrine
  -> load bounded project context
  -> provider/agent reasons and requests a capability
  -> LBE authorizes before execution
  -> approved adapter executes
  -> ToolReceipt/evidence returns
  -> provider continues
  -> LBE validates completion
  -> LBE interface projects result/evidence/diff/uncertainty/next action
```

## Existing owners to reuse

- `SessionMemoryRuntimeBridge`, `SessionOperationalHistory`, and recovery owners for session/task/checkpoint persistence;
- R6C authorization and R6E `GovernedToolOrchestrator` / `ToolRegistry` / `ToolReceipt` for governed capability dispatch;
- provider registry and provider turn runtime for reasoning continuation;
- terminal projection and Textual client for terminal rendering and controls.

No parallel session, authorization, executor, receipt, evidence, or completion owner may be introduced.

## Completed slice checkpoints

### VERSIONED_USER_STATE_AND_PROVIDER_PROFILE_LIFECYCLE — PASS

Completed with focused provider/profile contracts, Windows Credential Manager round-trip proof, persisted user-state non-leakage, and explicit migration behavior.

### DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE — PASS

Canonical implementation commit: `0098e9c86614643e8364dd941e4f23e0295994d7`.

Checkpoint: `docs/acceptance/DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE_CHECKPOINT.md`.

### WORKSPACE_HYGIENE_GOVERNED_DELETION — PASS

Focused governed orchestration/mode regression: `52 passed`.

Nine approved disposable targets were deleted through governed `workspace.delete`; zero approved disposable targets remain. Fourteen historical snapshot/backup artifacts remain preserved and non-blocking.

Checkpoint: `docs/acceptance/WORKSPACE_HYGIENE_GOVERNED_DELETION_CHECKPOINT.md`.

### MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH — PASS

Canonical implementation commit:

`47885891848ec9a535a4e09694d3129b320da91a`

This bounded slice proves the provider-facing coding path for filesystem/text mutation, registered process execution, and Git mutation is governed through existing LBE owners:

- provider receives only LBE-generated registered tool definitions;
- bounded workspace write uses workspace containment and stale-write identity;
- arbitrary native shell exposure is unavailable;
- process execution is restricted to an LBE-owned registered command catalog;
- Git mutation is restricted to the primary `main` workspace;
- Git staging/commit is limited to paths mutated through governed LBE tools in the current reasoning turn;
- authorization occurs before handler execution;
- success and failure produce correlated receipts/evidence;
- audit/investigation read-only behavior is preserved;
- no second authority owner is introduced.

LoopTool validation:

```text
COMMAND HASH = D0DA7CA90B549E0C51FC2E65C7B68A30ECF7542710CE9CC1AF006D91FCA7F725
MACHINE_BINDING = PASS
focused regression = 80 passed
full regression = 713 passed
HEAD = 47885891848ec9a535a4e09694d3129b320da91a
local exception = ?? lbe-tui/ (reference-only, untouched)
```

Checkpoint: `docs/acceptance/MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH_CHECKPOINT.md`.

This PASS does **not** imply completion of the remaining integrated capability classes such as MCP/plugin, subagent, network, or hosted-service operations.

## Current remaining product sequence

The complete-runtime gate remains OPEN. The remaining product work must be selected one bounded machine slice at a time from the following canonical sequence:

1. trace/reuse existing capability owners rather than create parallel owners;
2. finish mandatory governed dispatch for the remaining integrated mutation classes: MCP/plugin, subagent, network, and hosted-service operations;
3. first-run setup and live session entry over persisted owners;
4. capability registry expansion behind governed dispatch;
5. terminal controls and detailed evidence/diff/settings/session surfaces where not already proven;
6. recovery, deterministic completion, TEMP proof/promotion integration, and installed-package acceptance.

The next slice is intentionally not activated by this checkpoint alone. It must be bound in `.lbe/governance/implementation-gates.json` to an active intent after its existing owners and exact mutation scope are identified.

## Invariants

- Credentials exist only in the host credential store and outbound transport.
- Cloud provider failure is explicit; another provider/model is never silently substituted.
- MCP, plugins, subagents, network, and hosted-service capabilities are registrations behind LBE dispatch and receive policy, receipts, evidence, and scoped parent identity.
- Ordinary policy-covered work is automatic. High-risk authority expansion uses a separate explicit decision; there is no generic approval queue.
- Provider prose cannot decide completion.
- No integrated agent receives a direct mutation capability that bypasses LBE pre-action authorization and approved adapters.
- Decision identity, operation identity, receipt, and rollback evidence remain correlated from proposal through completion.
- Pre-action authorization, execution evidence, and post-action repository promotion remain separate control layers.

## Complete-runtime PASS evidence still required

- focused tests for each remaining capability/integration slice;
- persisted receipts/events/evidence/recovery proof;
- installed local runtime acceptance;
- at least one valid local-provider and one cloud-provider proof where required by the final gate;
- direct-bypass adversarial proof for integrated capabilities;
- transaction/rollback and tamper/adversarial evidence appropriate to the selected assurance profile;
- package-output and state secret scan;
- `git diff --check`.

## Exclusions

- publication, tagging, or GitHub release before the publication gate is explicitly reactivated;
- provider API-token fallback without separate authorization;
- parallel session, authorization, executor, receipt, or completion systems;
- treating `lbe-tui/` or `lbe-core/` reference material as canonical runtime authority.
