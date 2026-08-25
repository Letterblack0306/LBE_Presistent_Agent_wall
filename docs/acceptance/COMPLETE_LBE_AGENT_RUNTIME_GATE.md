# Complete LBE Agent Runtime Gate

Status: **OPEN — EXPLICIT USER AUTHORIZATION — PUBLICATION PAUSED**

## Machine-selected state

```text
phase: COMPLETE_LBE_AGENT_RUNTIME_IMPLEMENTATION
slice: FIRST_RUN_LIVE_SESSION_ENTRY
slice_result: OPEN / IMPLEMENTED_VALIDATION_PENDING
status: OPEN
implementation_allowed: true
architecture_changes_allowed: true (explicit user authorization)
next_phase_locked: true
publication_controls: false (nested publication governance records)
```

The machine gate at `.lbe/governance/implementation-gates.json` is the execution authority. This document is the human-readable gate projection.

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

- `SessionMemoryRuntimeBridge`, `WorkspaceMemoryStore`, `SessionOperationalHistory`, and recovery owners for session/task/checkpoint persistence;
- R6C authorization and R6E `GovernedToolOrchestrator` / `ToolRegistry` / `ToolReceipt` for governed capability dispatch;
- provider registry/configuration/health and provider turn runtime for reasoning continuation;
- CLI thin control plane plus terminal projection/Textual client for entry and presentation.

No parallel session, provider, authorization, executor, receipt, evidence, or completion owner may be introduced.

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

Canonical implementation commit: `47885891848ec9a535a4e09694d3129b320da91a`.

LoopTool acceptance:

```text
COMMAND HASH = D0DA7CA90B549E0C51FC2E65C7B68A30ECF7542710CE9CC1AF006D91FCA7F725
focused regression = 80 passed
full regression = 713 passed
```

Checkpoint: `docs/acceptance/MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH_CHECKPOINT.md`.

### GOVERNED_EXTERNAL_CAPABILITY_REGISTRATION — PASS

Canonical implementation HEAD: `02c761ab5ee969edd1c24fed65a6a2d343d20927`.

This slice adds one registration contract for MCP, plugin, subagent, network, and hosted-service capabilities behind the existing LBE execution wall. Raw provider-controlled endpoint, URL, executable, argv, command, shell, and transport selection is rejected. Network/hosted registrations require explicit network metadata. Authorization remains R6C-before-R6E-adapter execution and receipts remain canonical.

LoopTool acceptance:

```text
COMMAND HASH = E474AAD3D03DEC376BF69944FFA3F56251052D534D46369B27547A7E9F563859
MACHINE_BINDING = PASS
focused regression = 58 passed
full regression = 732 passed
HEAD = 02c761ab5ee969edd1c24fed65a6a2d343d20927
local exception = ?? lbe-tui/ (reference-only, untouched)
```

Checkpoint: `docs/acceptance/GOVERNED_EXTERNAL_CAPABILITY_REGISTRATION_CHECKPOINT.md`.

## Active slice — FIRST_RUN_LIVE_SESSION_ENTRY

The product now needs one normal entry path over already-proven owners instead of forcing users to manually compose session creation/restoration and terminal entry.

Required behavior:

```text
lbe start
  -> if --session-id exists: restore persisted identity unchanged
  -> otherwise require explicit workspace + project workspace identity + mode
  -> optionally bind explicit provider/model/profile inputs through existing validation
  -> use existing session creation/persistence owner
  -> validate provider config against persisted provider/model when execution is requested
  -> enter existing Textual/provider-turn runtime
```

Implementation direction:

- `lbe_guard_inspector.product_entry:main` becomes the package entry wrapper;
- every non-`start` command delegates to the historical `lbe_guard_inspector.cli:main` unchanged;
- `lbe start` composes the existing `_tui`, `_session_create`, `WorkspaceMemoryStore`, `SessionMemoryRuntimeBridge`, provider validation/config, provider-turn runtime, and Textual client;
- restoring an existing session may not silently replace persisted workspace/provider/profile/policy identity;
- no provider/model fallback is permitted;
- no second session/provider/TUI/runtime owner is introduced.

Required acceptance evidence:

- new start creates exactly one persisted session;
- existing start restores the same persisted session identity;
- provider/model pair validation is fail-closed;
- provider configuration model mismatch is denied;
- no silent provider fallback;
- existing TUI and provider-turn owners are reused;
- legacy CLI commands still delegate unchanged;
- focused start/CLI tests and full suite pass;
- package entry point resolves to the product entry wrapper;
- `git diff --check` and protected-reference preservation pass.

## Current remaining product sequence

After this slice passes, continue one bounded machine slice at a time:

1. capability registry expansion with concrete installed integration discovery/configuration behind governed dispatch;
2. remaining LBE interface controls and detailed evidence/diff/settings/session surfaces where not already proven;
3. recovery, deterministic completion, TEMP proof/promotion integration, and installed-package acceptance.

## Invariants

- Credentials exist only in the host credential store and outbound transport.
- Cloud provider failure is explicit; another provider/model is never silently substituted.
- MCP, plugins, subagents, network, and hosted-service capabilities are registrations behind LBE dispatch and receive policy, receipts, evidence, and scoped parent identity.
- Ordinary policy-covered work is automatic. High-risk authority expansion uses a separate explicit decision; there is no generic approval queue.
- Provider prose cannot decide completion.
- No integrated agent receives a direct mutation capability that bypasses LBE pre-action authorization and approved adapters.
- Decision identity, operation identity, receipt, and rollback evidence remain correlated from proposal through completion.
- Pre-action authorization, execution evidence, and post-action repository promotion remain separate control layers.

## Exclusions

- publication, tagging, or GitHub release before the publication gate is explicitly reactivated;
- provider API-token fallback without separate authorization;
- parallel session, provider, authorization, executor, receipt, or completion systems;
- treating `lbe-tui/` or `lbe-core/` reference material as canonical runtime authority.
