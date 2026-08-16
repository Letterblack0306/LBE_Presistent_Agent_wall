# Current Implementation Gate

Status: **OPEN — R6A PROVIDER ABSTRACTION ACCEPTANCE — NEXT PHASE LOCKED**

Current phase: `R6A_PROVIDER_ABSTRACTION_ACCEPTANCE`

Current slice: `PROVE_SAME_SESSION_PROVIDER_SWITCH_WITHOUT_LBE_AUTHORITY_DRIFT`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R6A_PROVIDER_ABSTRACTION_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R6A_PROVIDER_ABSTRACTION_ACCEPTANCE_CHECKPOINT.md
kind: acceptance proof, not implementation
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
status: OPEN
```

## Prior accepted baseline

R3, R4 and R5 remain PASS and `PROVEN_COMPLETE`.

Final synchronized R5 baseline:

```text
HEAD: 535fe532f3faabf4b64a60d9f007ab584e2c8d37
origin/main: 535fe532f3faabf4b64a60d9f007ab584e2c8d37
R5 gate: PASS
next_phase_locked: true
LoopTool command hash: A0AE9161A7A1C9B8533A0E48C15D8D876DC0F02EE181733903903AF68A98551E
```

## Why R6A is selected first

R6A is the dependency-first R6 acceptance boundary because provider neutrality must hold before later R6 mode, context, authorization, governed-tool and completion claims can be considered provider-invariant.

Current source/tests already prove pieces of this contract separately:

- generic provider registration/composition through `ProviderRegistry` and `build_provider_controller()`;
- typed provider backend/request/response contracts;
- persisted session provider configuration changes without changing workspace/task identity.

What remains unaccepted is the combined same-session A -> B proof.

## Existing owners

```text
provider registration/composition:
  ProviderRegistry
  build_provider_controller

provider backend contract:
  reasoning_provider

reasoning boundary:
  LBERequestController
  LBERequest / LBEResponse

persistent session/workspace authority:
  SessionMemoryRuntimeBridge
  WorkspaceMemoryStore
```

## Reuse decision

```text
REUSE
```

R6A is not being reimplemented.

## Acceptance question

Can an equivalent logical request execute through provider A and provider B within one persisted session/workspace contract while provider/model identity changes only where intended and LBE-owned workspace, task, mode, permission, policy, evidence and completion authority remain unchanged?

## Required observable

1. provider A and provider B are composed through the same registered provider owner;
2. provider A handles the first logical request through the existing LBE controller contract;
3. the persisted session switches provider configuration without changing workspace/session/task identity;
4. provider B handles an equivalent logical request through the same LBE controller contract;
5. mode, permission/runtime policy and other LBE authority fields do not drift because of provider change;
6. LBE request/response/evidence semantics remain provider-neutral;
7. no provider-native path gains workspace, authorization, tool, validation or completion authority;
8. no second provider/session/reasoning owner is introduced.

## Falsifier

R6A cannot PASS if switching providers changes workspace/session/task identity, changes delegated LBE authority, bypasses the existing controller contract, requires a provider-specific governance fork, or requires a parallel owner.

## Allowed work

- GitHub inspection of current provider/session/reasoning owners and tests;
- LoopTool execution of repository-owned provider/session tests and bounded diagnostics;
- R6A acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- runtime/test implementation before a real defect is proven;
- R6B-R6F implementation;
- new provider/session/reasoning authority;
- CLI/TUI/MCP/release work;
- architecture changes.

## Current status

```text
source_owner_inspection: PASS
generic provider composition evidence: PRESENT
persisted provider switch evidence: PRESENT
combined same-session A->B integration: NOT RUN
focused regression: NOT RUN
checkpoint: UNVERIFIED
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

Do not advance automatically. If R6A exposes a real implementation defect, stop and activate a separate repair slice before modifying runtime or tests.
