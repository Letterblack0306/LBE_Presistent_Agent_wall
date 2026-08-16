# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — evidence reconciled through R6E acceptance

This document defines dependency order and acceptance goals for `Letterblack0306/LBE_Presistent_Agent_wall`.

Authority for current claims:

```text
current validation/runtime evidence
> current workspace/Git evidence
> active machine gate
> active acceptance/checkpoint records
> this roadmap
> historical docs
> model inference
```

## 1. Product goal

Build a persistent, provider-neutral LBE runtime where the provider reasons while LBE owns workspace/session identity, context/evidence authority, mode/policy, authorization, governed execution, receipts, validation/completion truth, and persistent state.

## 2. Non-negotiable invariants

- provider/model changes must not change LBE workspace identity, permissions, guards, evidence authority, validation/completion requirements, or persistent session/task state;
- modes are typed execution contracts, not prompt personalities;
- current workspace/Git/runtime evidence outranks memory/reference history;
- context assembly composes bounded material but does not create authority;
- relevant rules/guards are selected and enforced by LBE;
- pre-authorized operations may proceed without repetitive prompts; authority expansion must `ESCALATE` or `DENY`;
- only explicitly registered governed tools may execute;
- operation identity and receipts prevent accidental duplicate execution;
- provider continuation consumes governed receipts but has no execution authority;
- no unrestricted shell/filesystem bypass around registered governed tools;
- no second session, context, retrieval, mode, authorization, tool, receipt, validation, completion, continuation, or recovery owner.

## 3. Current roadmap state

```text
R3  PROVEN_COMPLETE
R4  PROVEN_COMPLETE
R5  PROVEN_COMPLETE
R6A PROVEN_COMPLETE
R6B PROVEN_COMPLETE
R6C PROVEN_COMPLETE
R6D PROVEN_COMPLETE
R6E PROVEN_COMPLETE
R6F PARTIALLY_PROVEN
CLI PARTIALLY_PROVEN
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current completed phase:

```text
phase: R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE
slice: PROVE_RECEIPT_BACKED_GOVERNED_TOOL_LIFECYCLE_WITH_IDEMPOTENCY_AND_PROVIDER_CONTINUATION
status: PASS
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

No later R6 family is active. Another family requires explicit activation and its own gate.

## 4. R3 — Persistent runtime -> reasoning

**Classification: `PROVEN_COMPLETE`.** Accepted persistent runtime-to-reasoning lifecycle; focused regression `46 passed`.

## 5. R4 — Checkpoint/resume/rehydration

**Classification: `PROVEN_COMPLETE`.** Accepted session/task/config continuity, stale source-backed fact invalidation, checkpoint HEAD protection and current-workspace precedence; focused regression `37 passed`.

## 6. R5 — Bounded classified recovery

**Classification: `PROVEN_COMPLETE`.** Accepted bounded retry, deterministic no-retry classes, persisted attempt/terminal state, idempotency restrictions and duplicate-success blocking; focused regression `30 passed`.

## 7. R6A — Provider abstraction

**Classification: `PROVEN_COMPLETE`.** Same-session provider A -> B preserves LBE identities/policy state; focused regression `64 passed`.

## 8. R6B — Typed mode policy

**Classification: `PROVEN_COMPLETE`.** Typed coding/audit/investigation contracts accepted; focused regression `69 passed`.

## 9. R6C — Permission and authorization

**Classification: `PROVEN_COMPLETE`.** Deterministic authorization/no-execution boundaries and delegated authority accepted; focused regression `81 passed`.

## 10. R6D — Context assembly and rule/guard injection

**Classification: `PROVEN_COMPLETE`.** Accepted bounded context ordering, current-workspace-over-reference authority, separate guard channel, model-prose non-authority and provider-equivalent authoritative context; focused regression `128 passed`.

## 11. R6E — Governed tool orchestration

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
reasoning/provider tool proposal
 -> ToolRequest
 -> ToolRegistry lookup
 -> argument validation
 -> R6C resolve_authorization
 -> GovernedToolOrchestrator
 -> registered handler / existing service owner
 -> ToolReceipt(output/evidence/authorization)
 -> operation-id receipt cache/idempotency
 -> continuation_from_receipt
 -> continue_provider
```

Accepted invariants:

- unregistered tools cannot execute;
- invalid arguments stop before authorization/execution;
- `DENY`/`ESCALATE` prevent handler execution;
- authorized registered execution produces structured output/evidence receipts;
- duplicate operation ID returns the original receipt without re-execution;
- `workspace.read` delegates to `EvidenceService` and rejects path escape before evidence read;
- provider continuation is derived from a governed receipt and preserves operation/receipt/tool/output identity;
- provider continuation has no execution authority;
- escalated receipt stops before provider continuation;
- no second dispatcher/receipt/continuation owner was introduced.

Evidence:

```text
repository baseline: 29 passed
hash: 2C05376D268B47A944EDD267CDD5EF4E37B37342FD19A069DADC2F4435CF90AB

authorized execution/idempotency: PASS
hash: 85A894FA0BB9EFBD297255952B9E61317AEB0250B6D2DF2EBD5DFA453AAB8AD0

receipt-backed continuation: PASS
hash: B24E0F0CECFE6CCA4DD18D54D929D1DF29FB9C35EF02E4CDABD77620888EB600

combined lifecycle + escalation stop: PASS
hash: D5D43751BE65F6F765960CA119CA59D74732181E520D3353AE00F1B0329A7A9A

focused regression: 51 passed
hash: 8D7906D783094242D072C6C2D49D392896810ADF2C162D2B16623A8BFAE9AA43

runtime/test source unchanged: PASS
diff check: PASS
worktree clean: PASS
```

A temporary PowerShell transport truncation (`F37E90BA...`) occurred before Python execution and is retained as a non-product harness failure.

Canonical checkpoint:

```text
docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_CHECKPOINT.md
```

Do not reopen R6E without new contradictory current evidence.

## 12. R6F — Completion and validation

**Classification: `PARTIALLY_PROVEN`.** Model prose cannot establish `DONE`; completion remains evidence/validation-owned. Remaining acceptance must prove the terminal predicate end to end through the normal coding path.

## 13. CLI control surface

**Classification: `PARTIALLY_PROVEN`.** Remaining acceptance must prove accepted runtime services through normal non-interactive/installed paths without CLI-owned authority.

## 14. R7 — End-to-end persistent coding/audit proof

**Classification: `PARTIALLY_PROVEN`.** Required installed/normal-path proof remains for coding, provider switch, resume after external workspace change, read-only audit, and out-of-authority escalation/denial.

## 15. Release/package readiness

**Classification: `PARTIALLY_PROVEN`.** Release follows R7 and requires clean installation, package-content audit, secret/state exclusion, supported runtime matrix, regression and installed end-to-end smoke proof. No external publish without explicit authorization.

## 16. Evidence-reconciled progression

```text
R3 PASS
 -> R4 PASS
 -> R5 PASS
 -> R6A PASS
 -> R6B PASS
 -> R6C PASS
 -> R6D PASS
 -> R6E PASS
 -> remaining R6 acceptance gaps
 -> CLI normal-path coverage
 -> R7 installed end-to-end proof
 -> release/package readiness
```

## 17. Canonical responsibility map

```text
User configuration -> delegated authority/defaults
CLI/API/TUI -> control surfaces
Persistent runtime -> session/task lifecycle/orchestration/recovery
Provider/Cline lower layer -> inference/continuation mechanics only
LLM reasoning -> interpretation/planning/hypotheses/explanation/proposals
Context assembly -> bounded composition only
Current workspace inspector -> current facts
Mode policy -> typed capability contract
Permission/governance -> authorization
Rules/guards -> deterministic detection
Governed tool owner -> registered execution/operation identity/receipts
Provider continuation -> receipt-backed transport only
Validation/completion -> proof and terminal truth
Validated memory/checkpoints -> bounded persistent context, never replacement truth
```

## 18. Final invariant

```text
Provider reasons and proposes.
Persistent runtime orchestrates.
Current workspace supplies facts.
LBE selects and authorizes.
Governed tools execute only through registered owners.
Operation identity prevents unintended duplicate execution.
Receipts carry governed execution evidence/provenance.
Provider continuation consumes receipts but cannot execute tools.
Validation proves.
Completion truth belongs to LBE.
```
