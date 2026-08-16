# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-16
Status: Active canonical roadmap — evidence reconciled through R6B acceptance

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

Coding and audit/investigation are control contracts over the same LBE authority, not separate model personalities or parallel runtimes.

---

## 2. Non-negotiable invariants

- provider/model changes must not change LBE workspace identity, permissions, guards, evidence authority, validation/completion requirements, or persistent session/task state;
- modes are typed execution contracts, not prompt personalities;
- relevant rules/guards are selected and enforced by LBE;
- pre-authorized operations may proceed without repetitive prompts; authority expansion must `ESCALATE` or `DENY`;
- current workspace/Git/runtime evidence outranks memory/reference history;
- no unrestricted shell/filesystem bypass around registered governed tools;
- no second session, mode, authorization, tool, receipt, validation, completion, or recovery owner;
- Cline/provider mechanics remain behind LBE authority.

---

## 3. Existing foundation to preserve

Current owners already exist for:

- workspace/project identity and live-evidence separation;
- validated memory and stale-data invalidation;
- `WorkspaceMemoryStore` and `SessionMemoryRuntimeBridge`;
- bounded classified recovery;
- provider registry/capabilities/turn/history/control;
- typed mode policy and deterministic authorization;
- `GovernedToolOrchestrator` execution/receipt/idempotency;
- completion policy/runtime/evidence/gate;
- CLI and optional Textual projection;
- bounded Node/stdio Cline continuation.

Missing acceptance evidence must not be treated as permission to reimplement these owners.

---

# 4. Current roadmap state

```text
R3  PROVEN_COMPLETE
R4  PROVEN_COMPLETE
R5  PROVEN_COMPLETE
R6A PROVEN_COMPLETE
R6B PROVEN_COMPLETE
R6C PARTIALLY_PROVEN
R6D IMPLEMENTED_NOT_ACCEPTED
R6E PARTIALLY_PROVEN
R6F PARTIALLY_PROVEN
CLI PARTIALLY_PROVEN
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current completed phase:

```text
phase: R6B_TYPED_MODE_POLICY_ACCEPTANCE
slice: PROVE_TYPED_MODE_CONTRACTS_ACROSS_PERSISTENT_RUNTIME_WITHOUT_PROVIDER_OR_AUTHORITY_DRIFT
status: PASS
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
```

No later R6 slice is active. Another family requires explicit activation and its own gate.

---

# 5. R3 — Persistent runtime -> existing reasoning boundary

**Classification: `PROVEN_COMPLETE`.**

Accepted path:

```text
SessionMemoryRuntimeBridge.run_reasoning
 -> LBERequest
 -> LBERequestController.run
 -> LBEResponse
 -> canonical task lifecycle persistence
```

Accepted mappings:

```text
COMPLETED -> TaskStatus.COMPLETED
INSUFFICIENT_EVIDENCE -> TaskStatus.BLOCKED
ORCHESTRATION_ERROR -> TaskStatus.FAILED
```

Focused regression: `46 passed`. No runtime/test implementation source changed during acceptance.

---

# 6. R4 — Checkpoint, resume, and rehydration

**Classification: `PROVEN_COMPLETE`.**

Accepted path:

```text
SessionMemoryRuntimeBridge.start_or_resume
 -> SessionMemoryAdapter.rehydrate
 -> current Git/source inspection
 -> verified-record loading
 -> stale source-backed record invalidation
 -> protected checkpoint revalidation
 -> current context packet
```

Accepted session/task/config continuity, active-constraint survival, stale source-backed fact invalidation, checkpoint HEAD protection, and current-workspace precedence over summaries/history.

Focused regression: `37 passed`.

---

# 7. R5 — Bounded classified recovery

**Classification: `PROVEN_COMPLETE`.**

Accepted path:

```text
SessionMemoryRuntimeBridge.run_recoverable
 -> recovery.run_with_recovery
 -> classify_failure / RetryPolicy
 -> persist_recovery_state
 -> WorkspaceMemoryStore
```

Accepted bounded retry, persisted attempt/terminal state, deterministic no-retry classes, idempotency restrictions, evidence-between-attempts enforcement, duplicate-success blocking, and source-supported cancellation semantics within the R5 gate’s declared evidence boundary.

Repository discriminator: `7 passed`. Focused regression: `30 passed`.

---

# 8. R6A — Provider abstraction

**Classification: `PROVEN_COMPLETE`.**

Accepted path:

```text
ProviderRegistry
 -> build_provider_controller
 -> provider-neutral backend contract
 -> LBERequestController
 -> SessionMemoryRuntimeBridge.run_reasoning
 -> persisted session/task state
```

Accepted same-session provider A -> B behavior:

```text
provider A -> COMPLETED
provider configuration A/model-a -> B/model-b
provider B -> COMPLETED
```

Session/workspace/task/mode/permission/runtime-policy and LBE policy identities remained stable; only intended provider/model fields changed. Focused regression: `64 passed`. Runtime/test source unchanged.

---

# 9. R6B — Typed mode policy

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
ModeRequest
 -> resolve_mode
 -> ModeDecision
 -> behavior.contracts
 -> SessionMemoryRuntimeBridge
 -> persisted session mode
 -> AuthorizationRequest / resolve_authorization
```

Accepted persistent-session discriminator on acceptance head `9086ad67bebb48f6505c7b3660f1ac49e0cc57c3`:

```text
coding -> propose -> ALLOW
audit -> propose -> ESCALATE
investigation -> propose -> ESCALATE
mode sequence: coding -> audit -> investigation
same session/workspace/task/provider identity preserved
permission: write_allowed
runtime policy: permissive
```

This proves coding, audit and investigation as typed LBE runtime capability/authorization contracts at the accepted boundary rather than prompt-only personalities. Provider identity did not determine mode authority. Audit and investigation excluded the tested proposal capability. Downstream authorization consumed typed `ModeDecision`.

Evidence:

```text
mode contract tests: 28 passed
integration command hash: 9C54DBC9E1792039991E4EEFDD4F0FE0C2ED59782318E94BC8DA904135159859
focused regression: 69 passed
runtime/test source unchanged: PASS
diff check: PASS
worktree clean: PASS
```

The initial oversized temporary probe was truncated before Python execution and remains classified `TEST_HARNESS_TRANSPORT_TRUNCATION`, not a product defect.

Canonical checkpoint:

```text
docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_CHECKPOINT.md
```

Do not reopen R6B without new contradictory current evidence.

---

# 10. R6C — Permission and authorization

**Classification: `PARTIALLY_PROVEN`.**

Current deterministic verdict vocabulary:

```text
ALLOW
DENY
ESCALATE
```

Current owner: `runtime.authorization_resolver`. R6B now supplies the accepted typed `ModeDecision` input boundary. Remaining R6C acceptance includes repeated pre-authorized operations, visible policy provenance, scope/authority expansion behavior, destructive/persistent-policy boundaries, and no provider bypass.

R6C is not active until explicitly gated.

---

# 11. R6D — Context assembly and rule/guard injection

**Classification: `IMPLEMENTED_NOT_ACCEPTED`.**

Current owner: `runtime/context_assembly.py` plus existing evidence/reasoning/guard/memory owners.

Acceptance must prove bounded reproducible context, absence of irrelevant rules, live workspace facts outranking reference evidence, equivalent authoritative context across provider switches, and no model-prose contamination of retrieval authority.

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

Broader installed coding workflows still require claim-matched proof.

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

# 16. Optional API surface

API operations must converge on the same runtime/session services as CLI and must not introduce another policy engine.

---

# 17. Optional TUI/operator console

Textual remains a projection/control client over canonical runtime history/control owners, not another runtime authority.

---

# 18. R7 — End-to-end persistent coding/audit proof

**Classification: `PARTIALLY_PROVEN`.**

Required installed/normal-path proof families remain:

- A: coding session with governed edit/test/validation/completion;
- B: provider switch in the same session without policy drift;
- C: resume after external workspace change with stale-memory invalidation;
- D: read-only audit with live evidence and no mutation;
- E: out-of-authority escalation/denial with no provider bypass.

R6A and R6B provide lower-layer accepted invariants but do not substitute for installed/normal-path R7 evidence.

---

# 19. Release/package readiness

**Classification: `PARTIALLY_PROVEN`.**

Release follows R7 acceptance and requires supported runtime matrix, clean installation, CLI entrypoints, package-content audit, secret/state exclusion, configuration/migration documentation, focused/full regression, and installed end-to-end smoke proof.

No external publish occurs without explicit authorization.

---

# 20. Evidence-reconciled progression

```text
R3 PASS
 -> R4 PASS
 -> R5 PASS
 -> R6A PASS
 -> R6B PASS
 -> remaining R6 acceptance gaps in dependency order
 -> CLI normal-path coverage
 -> R7 installed end-to-end proof
 -> release/package readiness
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

Every slice must define objective, existing owner, reuse classification, scope, exclusions, falsifier, required evidence level, targeted diagnostics/tests, regression requirement, Git/worktree proof, acceptance condition, and next-phase lock.

Do not combine roadmap families into one proof or repair slice.

---

# 22. Explicit non-goals

Do not drift into dedicated foundation-model training, passive model learning, separate coding/audit model authorities, unrestricted autonomous shell/filesystem mutation, model-authored guard verdicts, cross-project memory as live truth, TUI-first development, provider-specific governance forks, premature cloud sync, broad multi-agent orchestration, or wholesale ClineCore authority adoption.

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
Mode policy -> typed capability contract
Permission/governance -> authorization
Rules/guards -> deterministic detection
Governed tool owner -> execution/operation identity/receipts
Validation/completion -> proof and terminal truth
Validated memory/checkpoints -> bounded persistent context, never replacement truth
```

---

# 24. Final invariant

```text
Provider reasons.
Persistent runtime orchestrates.
Typed LBE mode policy bounds capabilities.
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
