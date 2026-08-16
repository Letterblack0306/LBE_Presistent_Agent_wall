# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-16
Status: Active canonical roadmap — evidence reconciled through R5 acceptance

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

Build a persistent, provider-neutral LBE runtime where the provider reasons while LBE owns workspace/session identity, mode/policy, authorization, governed execution, receipts/evidence, validation/completion truth, and persistent state.

```text
user / external agent
 -> CLI / API / optional TUI
 -> persistent LBE runtime
 -> provider/reasoning engine
 -> governed LBE tools / guards / validation
 -> current workspace
```

Primary user-facing paths:

1. coding — governed modification/validation inside granted authority;
2. audit/investigation — evidence-first inspection without unauthorized mutation.

CLI/API/TUI are control/projection surfaces, not parallel runtime authorities.

---

## 2. Non-negotiable invariants

- provider/model changes must not change LBE workspace identity, permissions, guards, evidence authority, validation/completion requirements, or persistent session/task state;
- modes are typed execution contracts, not separate model personalities;
- relevant rules/guards are selected and enforced by LBE, not passively learned by the model;
- pre-authorized operations may proceed without repetitive prompts; authority expansion must `ESCALATE` or `DENY`;
- current workspace/Git/runtime evidence outranks memory/reference history;
- no unrestricted shell/filesystem bypass around registered governed tools;
- no second session, authorization, tool, receipt, validation, completion, or recovery owner;
- Cline reuse remains `ADAPT`: provider/tool-call/continuation mechanics may be reused behind LBE authority, but `ClineCore` and native mutation paths are not canonical LBE authority.

---

## 3. Existing foundation to preserve

Current owners already exist for:

- project/workspace identity and live evidence separation;
- validated memory and stale-data invalidation;
- deterministic guards and validation-owned verdicts;
- `WorkspaceMemoryStore`;
- `SessionMemoryRuntimeBridge`;
- bounded classified recovery via `recovery.py` and `run_recoverable()`;
- provider registry/capabilities/turn/history/control;
- typed mode policy and deterministic authorization;
- `GovernedToolOrchestrator` execution/receipt/idempotency;
- completion policy/runtime/evidence/gate;
- CLI and optional Textual projection;
- bounded Node/stdio Cline `AgentRuntime` continuation.

Missing acceptance evidence must not be treated as permission to reimplement these owners.

---

# 4. Current roadmap state

The documentation-only roadmap reconciliation is PASS.

R3, R4 and R5 acceptance are PASS.

```text
R3  PROVEN_COMPLETE
R4  PROVEN_COMPLETE
R5  PROVEN_COMPLETE
R6A PARTIALLY_PROVEN
R6B PARTIALLY_PROVEN
R6C PARTIALLY_PROVEN
R6D IMPLEMENTED_NOT_ACCEPTED
R6E PARTIALLY_PROVEN
R6F PARTIALLY_PROVEN
CLI PARTIALLY_PROVEN
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current completed R5 phase:

```text
phase: R5_BOUNDED_RECOVERY_ACCEPTANCE
slice: PROVE_CLASSIFIED_BOUNDED_RECOVERY_AND_DUPLICATE_PREVENTION
status: PASS
next_phase_locked: true
```

No R6 slice is active. The next R6 family must be selected from current evidence and opened under a separate machine/human gate.

---

# 5. R3 — Persistent runtime -> existing reasoning boundary

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
SessionMemoryRuntimeBridge.run_reasoning
 -> existing LBERequest
 -> real existing LBERequestController.run
 -> existing LBEResponse
 -> canonical task lifecycle persistence
```

Accepted lifecycle mappings:

```text
COMPLETED -> TaskStatus.COMPLETED
INSUFFICIENT_EVIDENCE -> TaskStatus.BLOCKED
ORCHESTRATION_ERROR -> TaskStatus.FAILED
```

Focused regression passed with 46 tests across `tests/test_session_memory_runtime.py` and `tests/test_request_controller.py`. No runtime/test implementation source changed during acceptance.

Canonical acceptance record:

```text
docs/acceptance/R3_RUNTIME_REASONING_ACCEPTANCE_CHECKPOINT.md
```

---

# 6. R4 — Checkpoint, resume, and rehydration

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
SessionMemoryRuntimeBridge.start_or_resume
 -> SessionMemoryAdapter.rehydrate
 -> memory.context.rehydrate_context
 -> inspect current Git state
 -> load VERIFIED records
 -> invalidate changed source-backed records
 -> protected checkpoint revalidation
 -> current context packet
```

Acceptance established session/task/config continuity, active-constraint survival, current Git/source reinspection, stale source-backed fact invalidation, checkpoint HEAD mismatch/ineligibility after external change, and the rule that assistant/compaction summaries are not current workspace truth.

Focused R4 regression: `37 passed`.

Canonical acceptance record:

```text
docs/acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_CHECKPOINT.md
```

---

# 7. R5 — Bounded classified recovery

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
SessionMemoryRuntimeBridge.run_recoverable
 -> recovery.run_with_recovery
 -> classify_failure / RetryPolicy
 -> persist_recovery_state
 -> WorkspaceMemoryStore
```

Accepted behavior:

- transient retryable failure recovers only within declared policy;
- attempt count and terminal state persist;
- retry count survives runtime reconstruction;
- permission denial does not retry;
- deterministic classes including scope conflict cannot be configured as retryable;
- non-idempotent retryable operations are rejected before retry execution;
- required evidence-between-attempts blocks another attempt when absent;
- terminal success blocks duplicate execution under the same task/operation identity;
- cancellation is terminal by canonical source: checked before another attempt, persisted as `CANCELLATION`, `terminal=true`, `succeeded=false`, and forbidden from retryable policy.

Repository-owned discriminator:

```text
tests/test_runtime_recovery.py
7 passed
```

Focused R5 regression:

```text
tests/test_runtime_recovery.py
tests/test_session_memory_runtime.py
30 passed
```

No runtime/test implementation source changed during R5 acceptance.

Cancellation limitation is explicit: direct ad hoc runtime synthesis was not obtained because LoopTool command transport corrupted the embedded Python payload before runtime entry. The active gate permitted source-supported cancellation classification when no repository-owned direct cancellation harness existed.

Canonical acceptance record:

```text
docs/acceptance/R5_BOUNDED_RECOVERY_ACCEPTANCE_CHECKPOINT.md
```

Do not reopen R5 implementation unless current evidence later disproves the accepted owner.

---

# 8. R6A — Provider abstraction

**Classification: `PARTIALLY_PROVEN`.**

Provider registry/capability/health/turn/event owners and accepted P-series/Cline continuation checkpoints prove substantial mechanics.

Remaining acceptance requirement:

```text
provider A -> reasoning request -> response
provider B -> equivalent logical request -> response
```

within the same persisted session/workspace contract while preserving LBE policy, permissions, guards, evidence semantics, and task identity.

---

# 9. R6B — Mode policy

**Classification: `PARTIALLY_PROVEN`.**

Coding, audit and investigation must be proven as typed LBE capability/evidence/validation contracts over the same provider/runtime path, not prompt-only personalities.

---

# 10. R6C — Permission and authorization

**Classification: `PARTIALLY_PROVEN`.**

Current deterministic output remains:

```text
ALLOW
DENY
ESCALATE
```

Accepted Cline negative-path evidence proves denied/escalated tool proposals do not execute handlers and cannot bypass LBE.

Remaining acceptance includes repeated pre-authorized operations, visible policy provenance, and explicit authority-change behavior.

---

# 11. R6D — Context assembly and rule/guard injection

**Classification: `IMPLEMENTED_NOT_ACCEPTED`.**

Current owner: `runtime/context_assembly.py` plus existing evidence/reasoning/guard/memory owners.

Acceptance must prove bounded reproducible context, absence of irrelevant rules, live workspace facts outranking reference evidence, equivalent authoritative context across provider switches, and no contamination of retrieval authority by model prose.

---

# 12. R6E — Governed tool orchestration

**Classification: `PARTIALLY_PROVEN`.**

Current owner: `GovernedToolOrchestrator`.

Required lifecycle:

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

Broader installed coding workflows must still prove required read/write/validation tool classes and receipt-bound validation.

---

# 13. R6F — Completion and validation

**Classification: `PARTIALLY_PROVEN`.**

Model prose cannot establish `DONE`. Task-specific evidence requirements may include source/diff state, tests, build/package proof, Git/workspace state, guards and unresolved validation state.

Remaining acceptance must prove this predicate end to end through the normal coding path.

---

# 14. CLI control surface

**Classification: `PARTIALLY_PROVEN`.**

Current CLI families already include session create/continue/status/inspect/evidence/validate, code/audit/investigate, provider list/check/select, policy/permissions and TUI.

Remaining acceptance must prove required R6 services through normal non-interactive/installed paths without CLI-owned authority.

---

# 15. Configuration system

Configuration precedence:

```text
explicit command/session override
> workspace profile
> user configuration
> safe product defaults
```

Raw credentials must not be persisted in memory, task records, receipts, checkpoints or logs.

---

# 16. Optional API surface

API operations must converge on the same runtime/session services as CLI and must not introduce another policy engine.

---

# 17. Optional TUI/operator console

Textual remains a projection/control client over canonical runtime history/control owners, not another agent/runtime authority.

---

# 18. R7 — End-to-end persistent coding/audit proof

**Classification: `PARTIALLY_PROVEN`.**

Required installed/normal-path proof families remain:

- A: coding session with governed edit/test/validation/completion;
- B: provider switch in the same session without policy drift;
- C: resume after external workspace change with stale-memory invalidation;
- D: read-only audit with live evidence and no mutation;
- E: out-of-authority escalation/denial with no provider bypass.

R7 is complete only when all required families pass from the installed/normal path.

---

# 19. Release/package readiness

**Classification: `PARTIALLY_PROVEN`.**

Release follows R7 acceptance and requires supported runtime matrix, clean installation, CLI entrypoints, package-content audit, secret/state exclusion, configuration/migration documentation, focused/full regression, and installed end-to-end smoke proof.

No external publish action occurs without explicit authorization.

---

# 20. Evidence-reconciled progression

```text
R3 acceptance: PASS
        |
        v
R4 acceptance: PASS
        |
        v
R5 acceptance: PASS
        |
        v
R6 acceptance gaps in dependency order
        |
        v
CLI normal-path coverage
        |
        v
R7 installed end-to-end proof
        |
        v
release/package readiness
```

At every step classify the gap first:

```text
acceptance only
repair of existing owner
missing integration
truly missing implementation
blocked configuration
```

Only a proven defective/missing owner permits implementation changes in that family.

---

# 21. Slice discipline

Every slice must define exact objective, existing owner, reuse classification, allowed scope, exclusions, falsifier/failure behavior, required evidence level, targeted diagnostics/tests, regression requirement, Git/worktree proof, acceptance condition and next-phase lock.

Do not combine multiple roadmap families into one patch/proof slice.

---

# 22. Explicit non-goals

Do not drift into dedicated LBE foundation-model training, passive model learning, separate coding/audit model authorities, unrestricted autonomous repair/shell access, model-authored guard verdicts, cross-project memory as live truth, TUI-first development, provider-specific governance forks, premature cloud sync, broad multi-agent orchestration, or wholesale ClineCore authority adoption.

---

# 23. Canonical responsibility map

```text
User configuration -> delegated authority/defaults
CLI/API/TUI -> control surfaces
Persistent runtime -> session/task lifecycle/orchestration/recovery
Provider/Cline lower layer -> provider-native inference/continuation mechanics
LLM reasoning -> interpretation/planning/hypotheses/explanation/proposals
Reference retrieval -> historical candidate guidance
Current workspace inspector -> current project facts
Rules/guards -> deterministic detection
Permission/governance -> authorization
Governed tool owner -> execution/operation identity/receipts
Validation/completion -> proof and terminal truth
Validated memory/checkpoints -> bounded persistent context, never replacement truth
```

---

# 24. Final invariant

```text
Provider reasons.
Persistent runtime orchestrates.
CLI/API/TUI expose the runtime.
Current workspace supplies facts.
LBE selects/injects applicable rules and guards.
Permission policy authorizes actions.
Pre-authorized actions proceed without repetitive approval.
Authority expansion is escalated.
Governed tools execute through registered LBE owners.
Deterministic guards detect.
Validation proves.
Completion truth belongs to LBE.
Persistent memory carries only bounded supported context.
```

If a proposed feature creates a competing owner for one of these responsibilities, stop and reconcile the ownership boundary before implementation.
