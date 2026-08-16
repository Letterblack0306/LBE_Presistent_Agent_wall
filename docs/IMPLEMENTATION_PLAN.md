# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — R6E acceptance active

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

When this roadmap disagrees with live evidence, reconcile the roadmap rather than creating a competing implementation path.

---

## 1. Product goal

Build a persistent, provider-neutral LBE runtime where the provider reasons while LBE owns workspace/session identity, context/evidence authority, mode/policy, authorization, governed execution, receipts, validation/completion truth, and persistent state.

```text
user / external agent
 -> CLI / API / optional TUI
 -> persistent LBE runtime
 -> provider/reasoning engine
 -> governed LBE tools / guards / validation
 -> current workspace
```

Coding and audit/investigation are control contracts over the same LBE authority, not separate model personalities or parallel runtimes.

---

## 2. Non-negotiable invariants

- provider/model changes must not change LBE workspace identity, permissions, guards, evidence authority, validation/completion requirements, or persistent session/task state;
- modes are typed execution contracts, not prompt personalities;
- current workspace/Git/runtime evidence outranks memory/reference history;
- context assembly composes bounded material but does not create authority;
- relevant rules/guards are selected and enforced by LBE, not inferred into authority by model prose;
- pre-authorized operations may proceed without repetitive prompts; authority expansion must `ESCALATE` or `DENY`;
- only explicitly registered governed tools may execute and provider continuation cannot own execution authority;
- operation identity and receipts must prevent accidental duplicate execution;
- no unrestricted shell/filesystem bypass around registered governed tools;
- no second session, context, retrieval, mode, authorization, tool, receipt, validation, completion, continuation, or recovery owner;
- Cline/provider mechanics remain behind LBE authority.

---

## 3. Existing foundation to preserve

Current owners already exist for workspace/project identity, validated memory, `WorkspaceMemoryStore`, `SessionMemoryRuntimeBridge`, bounded classified recovery, provider registry/capabilities/turn/history/control, typed mode policy, deterministic authorization, context assembly, evidence/guard selection, `GovernedToolOrchestrator`, receipt-backed provider continuation, completion policy/runtime/evidence/gate, CLI/Textual projection, and bounded Node/stdio Cline continuation.

Missing acceptance evidence must not be treated as permission to reimplement these owners.

---

# 4. Current roadmap state

```text
R3  PROVEN_COMPLETE
R4  PROVEN_COMPLETE
R5  PROVEN_COMPLETE
R6A PROVEN_COMPLETE
R6B PROVEN_COMPLETE
R6C PROVEN_COMPLETE
R6D PROVEN_COMPLETE
R6E PARTIALLY_PROVEN — ACTIVE ACCEPTANCE
R6F PARTIALLY_PROVEN
CLI PARTIALLY_PROVEN
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current active phase:

```text
phase: R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE
slice: PROVE_RECEIPT_BACKED_GOVERNED_TOOL_LIFECYCLE_WITH_IDEMPOTENCY_AND_PROVIDER_CONTINUATION
status: OPEN
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
base_sha: a237ac0184116a47fdc5b2efc782940faa065efb
```

No later R6 family is active.

---

# 5. R3 — Persistent runtime -> reasoning boundary

**Classification: `PROVEN_COMPLETE`.**

Accepted path: `SessionMemoryRuntimeBridge.run_reasoning -> LBERequestController.run -> LBEResponse -> canonical task lifecycle persistence`.

Focused regression: `46 passed`. No runtime/test implementation source changed during acceptance.

---

# 6. R4 — Checkpoint, resume, and rehydration

**Classification: `PROVEN_COMPLETE`.**

Accepted session/task/config continuity, active-constraint survival, stale source-backed fact invalidation, checkpoint HEAD protection, and current-workspace precedence over summaries/history.

Focused regression: `37 passed`.

---

# 7. R5 — Bounded classified recovery

**Classification: `PROVEN_COMPLETE`.**

Accepted bounded retry, persisted attempt/terminal state, deterministic no-retry classes, idempotency restrictions, evidence-between-attempts enforcement, duplicate-success blocking, and source-supported cancellation semantics within the declared R5 evidence boundary.

Repository discriminator: `7 passed`. Focused regression: `30 passed`.

---

# 8. R6A — Provider abstraction

**Classification: `PROVEN_COMPLETE`.**

Accepted same-session provider A -> B behavior with session/workspace/task/mode/permission/runtime-policy and LBE policy identities stable while only intended provider/model fields changed. Focused regression: `64 passed`. Runtime/test source unchanged.

---

# 9. R6B — Typed mode policy

**Classification: `PROVEN_COMPLETE`.**

Accepted persistent-session typed mode path:

```text
coding -> propose -> ALLOW
audit -> propose -> ESCALATE
investigation -> propose -> ESCALATE
same session/workspace/task/provider identity preserved
```

Evidence: mode contract tests `28 passed`; focused regression `69 passed`; runtime/test source unchanged; diff/worktree proof PASS.

---

# 10. R6C — Permission and authorization

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
ModeDecision
 -> AuthorizationRequest / resolve_authorization
 -> AuthorizationDecision
 -> ToolExecutionContext
 -> GovernedToolOrchestrator
 -> ToolReceipt
```

Accepted integration behavior:

```text
op-allow-1 -> ALLOW -> EXECUTED
op-allow-2 -> ALLOW -> EXECUTED
op-deny -> DENY -> handler not executed
op-escalate -> ESCALATE -> handler not executed
explicit destructive delegation -> ALLOW -> EXECUTED
```

Authorization provenance remained visible in receipts. Baseline `26 passed`; focused regression `81 passed`; runtime/test source unchanged.

---

# 11. R6D — Context assembly and rule/guard injection

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
LBERequest.reference_context / persisted session context
 -> assemble_reasoning_context
 -> validated indexed reference evidence
 -> ReasoningRequest.reference_context

LBE-selected guard applicability
 -> ReasoningRequest.approved_guard_ids

current workspace inspection
 -> EvidenceService / GuardRunner / validated evidence contracts
 -> deterministic LBE result
```

Accepted invariants include caller-before-reference ordering, stale-reference/current-workspace contradiction handling, separate guard authority, rejection of model-authored authority fields, and provider-equivalent LBE context for equivalent inputs. Baseline `14 passed`; authority discriminators `9 passed`; provider-equivalence discriminator PASS; focused regression `128 passed`; runtime/test source unchanged.

---

# 12. R6E — Governed tool orchestration

**Classification: `PARTIALLY_PROVEN` — active acceptance.**

Existing owner path:

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

Current source/tests already establish separately:

- unregistered tools cannot execute;
- invalid arguments fail before authorization or handler execution;
- `DENY`/`ESCALATE` prevent handler execution;
- authorized registered execution produces structured output/evidence receipts;
- duplicate operation ID returns the original receipt without re-execution;
- `workspace.read` delegates to `EvidenceService` and rejects path escape before evidence read;
- provider continuation is constructed from an existing `ToolReceipt`, preserves operation/receipt/tool identity and has no execution authority;
- escalated receipt stops before provider continuation.

Active R6E acceptance must prove the combined lifecycle through the existing owners:

```text
registered + authorized operation
 -> exactly one governed execution
 -> structured receipt/evidence
 -> same operation repeated -> original receipt / no re-execution
 -> receipt-backed provider continuation
```

It must also prove the combined stop path:

```text
ESCALATE
 -> no handler execution
 -> no provider continuation
```

Canonical active records:

```text
docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_GATE.md
docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_CHECKPOINT.md
```

Implementation remains disabled unless acceptance proves a real defect and a separate repair slice is explicitly activated.

---

# 13. R6F — Completion and validation

**Classification: `PARTIALLY_PROVEN`.**

Model prose cannot establish `DONE`. Completion remains evidence/validation-owned. Remaining acceptance must prove the terminal predicate end to end through the normal coding path.

---

# 14. CLI control surface

**Classification: `PARTIALLY_PROVEN`.**

CLI families already expose session, provider, mode, policy, permissions, evidence and validation operations. Remaining acceptance must prove accepted runtime services through normal non-interactive/installed paths without CLI-owned authority.

---

# 15. Configuration system

Configuration precedence remains:

```text
explicit command/session override
> workspace profile
> user configuration
> safe product defaults
```

Raw credentials must not be persisted in memory, task records, receipts, checkpoints, or logs.

---

# 16. Optional API/TUI surfaces

API and Textual projection must converge on the same runtime/session authorities and must not introduce another policy, context, or execution engine.

---

# 17. R7 — End-to-end persistent coding/audit proof

**Classification: `PARTIALLY_PROVEN`.**

Required installed/normal-path proof families remain:

- A: coding session with governed edit/test/validation/completion;
- B: provider switch in the same session without policy drift;
- C: resume after external workspace change with stale-memory invalidation;
- D: read-only audit with live evidence and no mutation;
- E: out-of-authority escalation/denial with no provider bypass.

R6A-R6E provide lower-layer invariants only after their respective acceptance gates pass; they do not substitute for installed/normal-path R7 evidence.

---

# 18. Release/package readiness

**Classification: `PARTIALLY_PROVEN`.**

Release follows R7 acceptance and requires supported runtime matrix, clean installation, CLI entrypoints, package-content audit, secret/state exclusion, configuration/migration documentation, focused/full regression, and installed end-to-end smoke proof. No external publish occurs without explicit authorization.

---

# 19. Evidence-reconciled progression

```text
R3 PASS
 -> R4 PASS
 -> R5 PASS
 -> R6A PASS
 -> R6B PASS
 -> R6C PASS
 -> R6D PASS
 -> R6E acceptance ACTIVE
 -> remaining R6 acceptance gaps
 -> CLI normal-path coverage
 -> R7 installed end-to-end proof
 -> release/package readiness
```

At every step classify the gap first: acceptance only, repair of existing owner, missing integration, truly missing implementation, or blocked configuration. Only a proven defective/missing owner permits implementation changes in that family.

---

# 20. Slice discipline

Every slice must define objective, existing owner, reuse classification, scope, exclusions, falsifier, required evidence level, targeted diagnostics/tests, regression requirement, Git/worktree proof, acceptance condition, and next-phase lock. Do not combine roadmap families into one proof or repair slice.

---

# 21. Explicit non-goals

Do not drift into foundation-model training, passive model learning, separate coding/audit model authorities, unrestricted autonomous shell/filesystem mutation, provider-native tool execution bypass, model-authored guard/verdict authority, cross-project memory as live truth, provider-specific governance/context forks, premature TUI/cloud work, broad multi-agent orchestration, or wholesale ClineCore authority adoption.

---

# 22. Canonical responsibility map

```text
User configuration -> delegated authority/defaults
CLI/API/TUI -> control surfaces
Persistent runtime -> session/task lifecycle/orchestration/recovery
Provider/Cline lower layer -> inference/continuation mechanics only
LLM reasoning -> interpretation/planning/hypotheses/explanation/proposals
Context assembly -> bounded composition only
Reference retrieval -> historical candidate guidance
Current workspace inspector -> current project facts
Mode policy -> typed capability contract
Permission/governance -> authorization
Rules/guards -> deterministic detection
Governed tool owner -> registered execution/operation identity/receipts
Provider continuation -> receipt-backed transport only
Validation/completion -> proof and terminal truth
Validated memory/checkpoints -> bounded persistent context, never replacement truth
```

---

# 23. Final invariant

```text
Provider reasons and proposes.
Persistent runtime orchestrates.
Context assembly composes but does not create authority.
Current workspace supplies facts.
LBE selects/injects applicable rules and guards.
Typed mode policy bounds capabilities.
Permission policy authorizes actions.
Governed tools execute only through registered LBE owners after authorization.
Operation identity prevents unintended duplicate execution.
Receipts carry governed execution evidence/provenance.
Provider continuation consumes receipts but cannot execute tools.
Deterministic guards detect.
Validation proves.
Completion truth belongs to LBE.
Persistent memory carries only bounded supported context.
```

If a proposed feature creates a competing owner for one of these responsibilities, stop and reconcile the ownership boundary before implementation.
