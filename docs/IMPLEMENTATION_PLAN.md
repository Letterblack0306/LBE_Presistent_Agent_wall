# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — evidence reconciled through R6D acceptance

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
- no unrestricted shell/filesystem bypass around registered governed tools;
- no second session, context, retrieval, mode, authorization, tool, receipt, validation, completion, or recovery owner;
- Cline/provider mechanics remain behind LBE authority.

---

## 3. Existing foundation to preserve

Current owners already exist for workspace/project identity, validated memory, `WorkspaceMemoryStore`, `SessionMemoryRuntimeBridge`, bounded classified recovery, provider registry/capabilities/turn/history/control, typed mode policy, deterministic authorization, context assembly, evidence/guard selection, `GovernedToolOrchestrator`, completion policy/runtime/evidence/gate, CLI/Textual projection, and bounded Node/stdio Cline continuation.

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
R6E PARTIALLY_PROVEN
R6F PARTIALLY_PROVEN
CLI PARTIALLY_PROVEN
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current completed phase:

```text
phase: R6D_CONTEXT_ASSEMBLY_ACCEPTANCE
slice: PROVE_BOUNDED_AUTHORITY_PRESERVING_CONTEXT_ACROSS_PROVIDER_AND_LIVE_WORKSPACE_BOUNDARIES
status: PASS
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

No later R6 family is active. Another family requires explicit activation and its own gate.

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

Authorization provenance remained visible in receipts. Repository-owned tests also cover persistent-policy authority expansion/delegation. Baseline `26 passed`; focused regression `81 passed`; runtime/test source unchanged.

---

# 11. R6D — Context assembly and rule/guard injection

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
LBERequest.reference_context / persisted session context
 -> runtime.context_assembly.assemble_reasoning_context
 -> validated indexed reference evidence
 -> ReasoningRequest.reference_context

LBE-selected guard applicability
 -> ReasoningRequest.approved_guard_ids

current workspace inspection
 -> EvidenceService / GuardRunner / validated evidence contracts
 -> deterministic LBE result
```

Accepted invariants:

- caller/session context remains ahead of indexed reference evidence and assembly does not mutate source mappings;
- stale indexed evidence is detected against an independent current-workspace reread rather than promoted to current truth;
- provider planning receives bounded indexed/reference context while current-workspace and validation truth remain LBE-owned;
- approved guards stay on the separate typed guard channel;
- authority-bearing model plan fields are rejected and explanation cannot overwrite deterministic verdict;
- provider A/B receive equivalent LBE reference context, workspace identity/profile, approved guards and approved tools for equivalent authoritative inputs;
- no second context/retrieval/guard/policy authority was introduced.

Evidence:

```text
context/provider baseline: 14 passed
hash: 8E61C736848B5CDAEB144F7D80A1304BB119D1CFD6E6C14C4E84CC9B2AD54698

authority discriminators: 9 passed
hash: 73222C712C91124E873E1A30E3F9241C62ED6C61A4CB568AED17178F9B360820

provider equivalence discriminator: PASS
hash: 61CDCECAAC3951B7A79051F10819BDB3CC3BA65CD6F8635900CD8ACA2CBE17C7

focused regression: 128 passed
hash: 0157C71BFDAF6ACC55A00573C97FAF4181D23D660E3290852B35166EBB841DA9

runtime/test source unchanged: PASS
diff check: PASS
worktree clean: PASS
```

Two temporary harness failures were investigated and retained as non-product evidence: one invalid synthetic evidence fixture that reached zero provider requests, and one PowerShell transport truncation before Python execution.

Canonical checkpoint:

```text
docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_CHECKPOINT.md
```

Do not reopen R6D without new contradictory current evidence.

---

# 12. R6E — Governed tool orchestration

**Classification: `PARTIALLY_PROVEN`.**

Current owner: `GovernedToolOrchestrator`.

Required lifecycle remains:

```text
reasoning proposes tool
 -> registered lookup
 -> authorization
 -> workspace/precondition checks
 -> governed execution
 -> structured receipt/evidence
 -> runtime/history update
 -> required validation
 -> provider continuation where applicable
```

R6C proves the authorization/no-execution boundary consumed inside this owner. R6D proves context/provider authority remains stable before tool proposal. Broader governed-tool acceptance remains separate.

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

R6A-R6D provide accepted lower-layer invariants but do not substitute for installed/normal-path R7 evidence.

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
 -> remaining R6 acceptance gaps in dependency order
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

Do not drift into foundation-model training, passive model learning, separate coding/audit model authorities, unrestricted autonomous shell/filesystem mutation, model-authored guard/verdict authority, cross-project memory as live truth, provider-specific governance/context forks, premature TUI/cloud work, broad multi-agent orchestration, or wholesale ClineCore authority adoption.

---

# 22. Canonical responsibility map

```text
User configuration -> delegated authority/defaults
CLI/API/TUI -> control surfaces
Persistent runtime -> session/task lifecycle/orchestration/recovery
Provider/Cline lower layer -> provider-native inference/continuation mechanics
LLM reasoning -> interpretation/planning/hypotheses/explanation/proposals
Context assembly -> bounded composition only
Reference retrieval -> historical candidate guidance
Current workspace inspector -> current project facts
Mode policy -> typed capability contract
Permission/governance -> authorization
Rules/guards -> deterministic detection
Governed tool owner -> execution/operation identity/receipts
Validation/completion -> proof and terminal truth
Validated memory/checkpoints -> bounded persistent context, never replacement truth
```

---

# 23. Final invariant

```text
Provider reasons.
Persistent runtime orchestrates.
Context assembly composes but does not create authority.
Current workspace supplies facts.
Reference/history remains subordinate context.
LBE selects/injects applicable rules and guards.
Typed mode policy bounds capabilities.
Permission policy authorizes actions.
Authority expansion is escalated or denied.
Governed tools execute only through registered LBE owners after authorization.
Deterministic guards detect.
Validation proves.
Completion truth belongs to LBE.
Persistent memory carries only bounded supported context.
```

If a proposed feature creates a competing owner for one of these responsibilities, stop and reconcile the ownership boundary before implementation.
