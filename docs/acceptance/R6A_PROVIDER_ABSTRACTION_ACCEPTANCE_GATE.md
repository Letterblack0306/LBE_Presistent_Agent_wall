# R6A Provider Abstraction Acceptance Gate

Status: **OPEN — ACCEPTANCE PROOF ONLY — NEXT PHASE LOCKED**

```text
phase: R6A_PROVIDER_ABSTRACTION_ACCEPTANCE
slice: PROVE_SAME_SESSION_PROVIDER_SWITCH_WITHOUT_LBE_AUTHORITY_DRIFT
base_sha: 32a987971ff0ea6643f7ea9ff89df7f5132ef850
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

## Selection rationale

R6A is the dependency-first R6 acceptance slice because later R6B-R6F claims must remain invariant across provider changes. Provider selection/composition sits below LBE mode, authorization, context, governed tools, evidence, validation and completion authority.

This selection does not declare R6A defective. Current source/tests already prove provider registration/composition and persisted provider configuration independently; the missing artifact is the combined same-session provider-switch acceptance proof.

## Acceptance question

Can the existing runtime execute an equivalent logical request through provider A and provider B within the same persisted session/workspace contract while preserving LBE-owned identity, policy, permissions, evidence semantics and task continuity?

## Existing owners

```text
provider registration/composition:
  lbe_guard_inspector.provider_registry.ProviderRegistry
  lbe_guard_inspector.reasoning_runtime.build_provider_controller

provider backend contract:
  lbe_guard_inspector.reasoning_provider

persistent session authority:
  SessionMemoryRuntimeBridge
  WorkspaceMemoryStore

reasoning authority boundary:
  LBERequestController
  LBERequest / LBEResponse
```

## Reuse decision

```text
REUSE
```

Do not introduce another provider/session/reasoning owner.

## Required observables

1. two provider IDs can be registered and composed through the existing generic provider owner;
2. provider A handles the first logical request through the existing LBE reasoning/controller contract;
3. the same persisted session/workspace identity is retained when provider configuration changes to provider B;
4. provider B handles an equivalent logical request through the same LBE reasoning/controller contract;
5. session ID, project workspace ID, canonical workspace root, mode, permission/runtime policy and task identity do not drift merely because provider changes;
6. provider/model identity changes only in the provider/session configuration fields intended to change;
7. LBE request/response/evidence semantics remain provider-neutral;
8. provider-native mechanics do not acquire workspace, permission, tool, validation or completion authority;
9. no second provider/session/reasoning owner is introduced;
10. focused provider/session regression passes on the exact acceptance head.

## Falsifier

R6A cannot PASS if provider switching changes workspace/session/task identity, bypasses the existing LBE controller contract, changes delegated LBE authority, requires a provider-specific governance fork, or requires a parallel provider/session owner.

## Evidence ladder

```text
source owner inspection
-> repository-owned provider composition/session persistence evidence
-> smallest same-session A->B integration discriminator
-> focused provider/session regression
-> diff/scope/worktree proof
-> checkpoint
```

## Allowed work

- GitHub inspection of provider/session/reasoning owners and tests;
- LoopTool execution of repository-owned tests and bounded runtime diagnostics;
- acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- provider/runtime/test implementation before evidence proves a real defect;
- new provider/session/reasoning authority;
- R6B-R6F implementation;
- CLI/TUI/MCP/release work;
- architecture changes.

## Completion predicate

PASS only when the combined same-session provider A -> provider B invariant is proven at integration level with no falsifier. PASS does not auto-activate R6B or another phase.
