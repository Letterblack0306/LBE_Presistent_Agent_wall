# Current Implementation Gate

Status: **OPEN — R6C PERMISSION / AUTHORIZATION ACCEPTANCE — NEXT PHASE LOCKED**

Current phase: `R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE`

Current slice: `PROVE_DELEGATED_AUTHORITY_REUSE_AND_EXPANSION_BOUNDARIES_THROUGH_GOVERNED_EXECUTION`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_CHECKPOINT.md
kind: acceptance proof, not implementation
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
status: OPEN
```

## Accepted baseline

```text
R3: PROVEN_COMPLETE
R4: PROVEN_COMPLETE
R5: PROVEN_COMPLETE
R6A: PROVEN_COMPLETE
R6B: PROVEN_COMPLETE
```

Final synchronized R6B closure baseline:

```text
HEAD: d584752b105fc8db8f941dc09b66ed32f803ec4c
origin/main: d584752b105fc8db8f941dc09b66ed32f803ec4c
R6B gate: PASS
next_phase_locked: true
LoopTool closure command hash: 57DD2253CC26768B4F311D94DBC45B289568F515CE65B987BEFA106D3869ACBC
```

## Why R6C is selected next

R6B proved typed mode/capability authority. `GovernedToolOrchestrator` consumes `resolve_authorization()` before handler execution, so R6C is the next dependency boundary before broader governed-tool acceptance.

Current source/tests already prove pieces independently:

- `AuthorizationRequest` consumes typed `ModeDecision`;
- `resolve_authorization()` returns deterministic `ALLOW`, `DENY`, or `ESCALATE`;
- already-enabled capability may `ALLOW` without repeat confirmation;
- explicit forbidden policy `DENY`s;
- missing capability, workspace expansion, unresolved scope conflict, undelegated destructive action and undelegated persistent-policy change `ESCALATE`;
- explicitly delegated destructive and persistent-policy changes may `ALLOW`;
- `GovernedToolOrchestrator` maps `DENY`/`ESCALATE` into receipts and does not invoke handlers;
- only `ALLOW` reaches the registered handler.

The missing artifact is the combined repeated-authority / authority-expansion / provenance integration proof.

## Existing owners

```text
ModeDecision
AuthorizationRequest
AuthorizationDecision
resolve_authorization
ToolExecutionContext
GovernedToolOrchestrator
ToolReceipt
```

## Reuse decision

```text
REUSE
```

R6C is not being reimplemented.

## Acceptance question

Can the existing LBE authorization path reuse already delegated authority for repeated governed operations without repetitive approval, deterministically block or escalate authority expansion, prevent denied/escalated handler execution, and preserve visible authorization provenance in receipts?

## Required observable

1. two distinct already-delegated governed operations execute with `ALLOW` and no separate approval state;
2. explicitly forbidden operation returns `DENY` and handler call count does not increase;
3. capability/scope expansion returns `ESCALATE` and handler call count does not increase;
4. undelegated destructive/persistent-policy changes `ESCALATE`, while explicitly delegated equivalents may `ALLOW`;
5. receipts retain authorization verdict and rationale;
6. no provider-native/prompt-only approval bypass or parallel authorization owner is introduced.

## Falsifier

R6C cannot PASS if already delegated operations need an unrelated new confirmation mechanism, if denied/escalated operations execute handlers, if explicit forbidden policy can silently execute, if authority expansion bypasses escalation, if authorization provenance is lost, or if a second authorization owner is required.

## Allowed work

- GitHub inspection of current mode/authorization/tool owners and tests;
- LoopTool execution of repository-owned tests and bounded runtime diagnostics;
- R6C acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- runtime/test implementation before a real defect is proven;
- R6D-R6F implementation;
- new permission/authorization/prompt-approval authority;
- CLI/TUI/MCP/release work;
- architecture changes.

## Current status

```text
source_owner_inspection: PASS
repository authorization tests: PRESENT
repository governed-tool authorization tests: PRESENT
combined repeated-authority integration: NOT RUN
focused regression: NOT RUN
checkpoint: UNVERIFIED
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

Do not advance automatically. If R6C exposes a real implementation defect, stop and activate a separate repair slice before modifying runtime or tests.
