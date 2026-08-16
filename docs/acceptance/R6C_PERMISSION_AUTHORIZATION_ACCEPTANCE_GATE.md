# R6C Permission and Authorization Acceptance Gate

Status: **OPEN — ACCEPTANCE PROOF ONLY — NEXT PHASE LOCKED**

```text
phase: R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE
slice: PROVE_DELEGATED_AUTHORITY_REUSE_AND_EXPANSION_BOUNDARIES_THROUGH_GOVERNED_EXECUTION
base_sha: d584752b105fc8db8f941dc09b66ed32f803ec4c
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

## Selection rationale

R6C is the next dependency slice after R6B because governed tool execution consumes deterministic authorization before handler invocation. R6B proved typed mode decisions and capability boundaries. R6C must now prove that existing delegated authority is reusable without repetitive confirmation, while authority expansion is deterministically escalated or denied and cannot execute through the governed tool boundary.

This selection does not declare R6C defective. Current source/tests already prove the resolver and governed execution pieces independently. The missing artifact is a combined integration-level authorization proof with explicit provenance and repeated operations.

## Acceptance question

Can the existing LBE authorization/runtime path reuse already delegated authority for repeated operations without repetitive approval, deterministically DENY explicitly forbidden operations, ESCALATE authority expansion, and prevent denied/escalated operations from reaching governed handlers while preserving visible authorization provenance?

## Existing owners

```text
typed mode/capability authority:
  lbe_guard_inspector.runtime.mode_controller.ModeDecision

authorization authority:
  lbe_guard_inspector.runtime.authorization_resolver.AuthorizationRequest
  lbe_guard_inspector.runtime.authorization_resolver.AuthorizationDecision
  lbe_guard_inspector.runtime.authorization_resolver.resolve_authorization

governed execution consumer:
  lbe_guard_inspector.runtime.tool_orchestration.GovernedToolOrchestrator
  ToolExecutionContext
  ToolReceipt
```

## Reuse decision

```text
REUSE
```

Do not introduce another permission/authorization/prompt-approval owner.

## Required observables

1. two distinct operations using the same already-delegated capability resolve `ALLOW` and execute without an intervening confirmation state;
2. explicitly forbidden operation resolves `DENY` and its handler is not invoked;
3. capability outside active mode resolves `ESCALATE` and its handler is not invoked;
4. workspace-scope expansion resolves `ESCALATE` and does not execute;
5. destructive operation without prior destructive delegation resolves `ESCALATE`; the same operation class with explicit destructive delegation may `ALLOW`;
6. persistent-policy change without prior delegation resolves `ESCALATE`; the same class with explicit persistent-policy delegation may `ALLOW`;
7. each governed receipt exposes the authorization verdict and rationale/provenance needed to explain the decision;
8. no provider-native or prompt-only approval path bypasses the resolver at the tested boundary;
9. no second authorization/execution authority is introduced;
10. focused authorization/mode/tool regression passes on the exact acceptance head.

## Falsifier

R6C cannot PASS if already delegated operations require an unrelated new approval state, if denied/escalated operations invoke handlers, if explicit forbidden operations can become `ALLOW`, if authority expansion is silently executed, if authorization provenance disappears at the governed receipt boundary, or if a parallel authorization owner is required.

## Evidence ladder

```text
source owner inspection
-> repository-owned authorization tests
-> repository-owned governed-tool authorization tests
-> smallest repeated-ALLOW / DENY / ESCALATE integration discriminator
-> authority-expansion discriminator
-> focused authorization/mode/tool regression
-> diff/scope/worktree proof
-> checkpoint
```

## Allowed work

- GitHub inspection of current mode/authorization/tool owners and tests;
- LoopTool execution of repository-owned tests and bounded runtime diagnostics;
- acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- runtime/test implementation before evidence proves a real defect;
- new permission/authorization/prompt approval owner;
- R6D-R6F implementation;
- CLI/TUI/MCP/release work;
- architecture changes.

## Completion predicate

PASS only when delegated authority reuse, DENY, ESCALATE, no-execution boundaries, explicit authority-change behavior, and authorization provenance are proven at integration level through the existing governed execution path with no falsifier. PASS does not auto-activate R6D or another phase.
