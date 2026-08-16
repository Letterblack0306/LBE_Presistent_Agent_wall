# R6B Typed Mode Policy Acceptance Gate

Status: **OPEN — ACCEPTANCE PROOF ONLY — NEXT PHASE LOCKED**

```text
phase: R6B_TYPED_MODE_POLICY_ACCEPTANCE
slice: PROVE_TYPED_MODE_CONTRACTS_ACROSS_PERSISTENT_RUNTIME_WITHOUT_PROVIDER_OR_AUTHORITY_DRIFT
base_sha: 4deee8e6a45c4ec179dbc6bf3524b76a38e9fd2b
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

## Selection rationale

R6B is the next dependency slice after R6A because authorization (R6C) consumes `ModeDecision`, and later governed-tool/completion claims depend on the active mode exposing the correct capability boundary. R6A already proved provider neutrality. R6B must now prove that coding, audit and investigation are typed LBE runtime contracts rather than prompt-only personalities.

This selection does not declare R6B defective. Current source/tests already prove deterministic mode resolution, behavior filtering and capability filtering. The missing artifact is the combined persistent-runtime acceptance proof.

## Acceptance question

Can one existing persistent LBE session/runtime apply the typed `ModeController` decisions for coding, audit and investigation while preserving session/workspace/provider identity and enforcing the intended capability/evidence boundary for each mode?

## Existing owners

```text
mode authority:
  lbe_guard_inspector.runtime.mode_controller.ModeRequest
  lbe_guard_inspector.runtime.mode_controller.ModeDecision
  lbe_guard_inspector.runtime.mode_controller.resolve_mode

behavior vocabulary:
  lbe_guard_inspector.behavior.contracts

persistent session authority:
  SessionMemoryRuntimeBridge
  WorkspaceMemoryStore

downstream typed consumer:
  lbe_guard_inspector.runtime.authorization_resolver.AuthorizationRequest
```

## Reuse decision

```text
REUSE
```

Do not introduce another mode/policy/session owner.

## Required observables

1. coding resolves from existing intent/permission/runtime-policy inputs to a typed `ModeDecision`;
2. audit resolves to a typed read-only capability contract;
3. investigation resolves to a typed read-only investigation contract even when write/elevated permission exists under permissive policy;
4. coding exposes development capabilities such as proposal/testing only where the existing behavior contract allows them;
5. audit and investigation do not expose write/proposal/promotion capabilities;
6. the same persisted session/workspace/provider identity survives mode transitions unless an explicitly intended session field changes;
7. provider identity does not determine or override the resolved mode contract;
8. mode decisions remain LBE-owned inputs to downstream authorization rather than provider-native authority;
9. no second mode/session/policy owner is introduced;
10. focused mode/session/authorization regression passes on the exact acceptance head.

## Falsifier

R6B cannot PASS if mode is only prompt text, if provider identity determines authority, if audit/investigation expose write capabilities, if changing mode forks session/workspace identity, if persisted policy fields drift unintentionally, or if a parallel mode/policy owner is required.

## Evidence ladder

```text
source owner inspection
-> repository-owned mode/behavior tests
-> smallest persistent-session coding -> audit -> investigation discriminator
-> downstream authorization type-consumption proof
-> focused mode/session/authorization regression
-> diff/scope/worktree proof
-> checkpoint
```

## Allowed work

- GitHub inspection of current mode, behavior, session and authorization owners/tests;
- LoopTool execution of repository-owned tests and bounded runtime diagnostics;
- acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- runtime/test implementation before evidence proves a real defect;
- new mode/session/policy/authorization authority;
- R6C-R6F implementation;
- CLI/TUI/MCP/release work;
- architecture changes.

## Completion predicate

PASS only when coding, audit and investigation are proven as typed LBE capability contracts at integration level across the existing persistent runtime/session boundary with no falsifier. PASS does not auto-activate R6C or another phase.
