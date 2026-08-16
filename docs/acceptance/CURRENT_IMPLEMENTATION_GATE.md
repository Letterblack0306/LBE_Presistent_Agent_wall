# Current Implementation Gate

Status: **OPEN — R6B TYPED MODE POLICY ACCEPTANCE — NEXT PHASE LOCKED**

Current phase: `R6B_TYPED_MODE_POLICY_ACCEPTANCE`

Current slice: `PROVE_TYPED_MODE_CONTRACTS_ACROSS_PERSISTENT_RUNTIME_WITHOUT_PROVIDER_OR_AUTHORITY_DRIFT`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_CHECKPOINT.md
kind: acceptance proof, not implementation
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
status: OPEN
```

## Prior accepted baseline

```text
R3: PROVEN_COMPLETE
R4: PROVEN_COMPLETE
R5: PROVEN_COMPLETE
R6A: PROVEN_COMPLETE
```

Final synchronized R6A closure baseline:

```text
HEAD: 4deee8e6a45c4ec179dbc6bf3524b76a38e9fd2b
origin/main: 4deee8e6a45c4ec179dbc6bf3524b76a38e9fd2b
R6A gate: PASS
next_phase_locked: true
LoopTool closure command hash: BE73BAAF3292B2DB4FAD6B4C9C548D2BA252D97ADFD12B115FC9C1E4049A35CF
LoopTool response check hash: EFCF5A4D97F74E93A62C79301C8C93E752F360813A7E683955DA8C29F076A37D
```

## Why R6B is selected next

R6C authorization consumes `ModeDecision`, and later governed-tool/completion claims depend on mode exposing the correct bounded capabilities. R6A has already established provider neutrality, so R6B is the next dependency boundary.

Current source/tests already prove pieces independently:

- `ModeRequest` and `ModeDecision` are typed public runtime contracts;
- `resolve_mode()` deterministically maps intent + permission + runtime policy to coding/audit/investigation;
- audit and investigation filter development/write capabilities;
- coding exposes the existing development behavior contract;
- session state persists `mode` independently of provider configuration;
- `AuthorizationRequest` consumes a typed `ModeDecision`.

The missing artifact is the combined persistent-session coding -> audit -> investigation acceptance proof.

## Existing owners

```text
mode authority:
  runtime.mode_controller.ModeRequest
  runtime.mode_controller.ModeDecision
  runtime.mode_controller.resolve_mode

behavior vocabulary:
  behavior.contracts

persistent session/workspace authority:
  SessionMemoryRuntimeBridge
  WorkspaceMemoryStore

downstream typed consumer:
  runtime.authorization_resolver.AuthorizationRequest
```

## Reuse decision

```text
REUSE
```

R6B is not being reimplemented.

## Acceptance question

Can one existing persistent LBE session/runtime apply coding, audit and investigation as typed LBE capability contracts while preserving session/workspace/provider identity, keeping audit/investigation read-only, and preventing provider identity from becoming mode or authorization authority?

## Required observable

1. coding resolves through the existing typed mode owner and exposes only allowed development capabilities;
2. audit resolves through the same owner and excludes write/proposal/promotion capabilities;
3. investigation resolves through the same owner and remains read-only even with elevated/write permission under permissive policy;
4. one persistent session can intentionally transition mode without forking session/workspace/provider identity;
5. provider identity does not choose or override the mode decision;
6. downstream authorization receives the typed `ModeDecision`;
7. no second mode/session/policy owner is introduced.

## Falsifier

R6B cannot PASS if mode is prompt-only, provider identity determines authority, audit/investigation expose write capabilities, mode transition forks session/workspace identity, policy fields drift unintentionally, or a parallel mode/policy owner is required.

## Allowed work

- GitHub inspection of current mode/behavior/session/authorization owners and tests;
- LoopTool execution of repository-owned tests and bounded runtime diagnostics;
- R6B acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- runtime/test implementation before a real defect is proven;
- R6C-R6F implementation;
- new mode/session/policy/authorization authority;
- CLI/TUI/MCP/release work;
- architecture changes.

## Current status

```text
source_owner_inspection: PASS
repository mode tests: PRESENT
persistent session mode evidence: PRESENT SEPARATELY
R6A provider-neutrality baseline: PROVEN_COMPLETE
combined coding -> audit -> investigation integration: NOT RUN
focused regression: NOT RUN
checkpoint: UNVERIFIED
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

Do not advance automatically. If R6B exposes a real implementation defect, stop and activate a separate repair slice before modifying runtime or tests.
