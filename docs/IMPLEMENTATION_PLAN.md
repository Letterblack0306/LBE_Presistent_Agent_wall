# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-16
Status: Active canonical roadmap — reconciled against current `main`

This document defines the persistent-runtime dependency order and acceptance goals for `Letterblack0306/LBE_Presistent_Agent_wall`.

For architecture rationale and current status, also read:

- `docs/CURRENT_STATUS.md`
- `docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md`
- `.lbe/governance/implementation-gates.json`
- `docs/design/CLI_CONTROL_PLANE_PROVIDER_BOUNDARY.md`
- `docs/design/LLM_REASONING_LAYER_ROADMAP.md`
- `docs/VALIDATED_WORKSPACE_MEMORY.md`

When this plan and live repository evidence disagree, current validation, runtime/workspace/Git evidence, the active machine gate, and current acceptance records win. Reconcile this plan rather than creating a competing roadmap.

---

## 1. Product goal

Build a persistent, provider-neutral LBE agent runtime where:

```text
user / external agent
        |
        v
LBE CLI / API
        |
        v
persistent session controller
        |
        +-- workspace identity
        +-- execution mode
        +-- active workspace policy
        +-- permissions
        +-- guard/profile selection
        +-- evidence requirements
        +-- validation/completion requirements
        |
        v
provider adapter / reusable provider engine
        |
        v
reasoning layer
        |
        v
LBE governed tools / guards / validation / governance
        |
        v
current workspace
```

The provider reasons. LBE owns the workspace contract, execution authority, evidence, validation, completion truth, and persistent runtime state.

Primary user-facing paths:

1. **Coding** — governed modification and validation inside authority already granted by the user.
2. **Audit / investigation** — evidence-first inspection without workspace mutation.

CLI/API/TUI are views/control surfaces over the same runtime owners; they must not become parallel controllers.

---

## 2. Non-negotiable architecture invariants

### 2.1 LBE remains stable when the model changes

Changing provider/model must not change workspace identity, active rules/profiles, permissions, deterministic guard semantics, evidence authority, validation/completion requirements, or persistent session/task state.

### 2.2 CLI is a control surface, not authority

Do not implement:

```text
CLI -> model -> raw unrestricted tools
```

Required boundary:

```text
CLI/API/TUI
 -> persistent session/runtime controller
 -> LBE policy/capability resolution
 -> provider reasoning
 -> governed tools
 -> current workspace
```

### 2.3 Modes are execution contracts, not model personalities

Coding, audit, and investigation use typed runtime policy over the same provider abstraction. Mode changes capability/permission/evidence/validation contracts, not model authority.

### 2.4 Rules are injected and enforced, not passively learned

Relevant rules/guards/constraints are selected by LBE. Permanent policy changes follow governance; model memory does not create policy authority.

### 2.5 Existing authorization must not become repeated confirmation

Already delegated authority may proceed without repeated prompts. Scope/authority expansion must return `ESCALATE` or `DENY` according to policy.

### 2.6 Workspace truth remains live

```text
current validation
> current workspace/Git/runtime evidence
> active machine/runtime policy
> verified memory/checkpoints
> verified historical repairs
> curated reference patterns
> unverified history
> model inference
```

Persistent memory never replaces live inspection.

---

## 3. Existing foundation to preserve

The following are current owners/foundation, not targets for parallel redesign:

- reference corpus retrieval and evidence classification;
- project/workspace identity and live evidence separation;
- deterministic guards and validation-owned verdicts;
- validated project-scoped memory and `WorkspaceMemoryStore`;
- `SessionMemoryRuntimeBridge` session/task lifecycle owner;
- Module Registry/runtime-map and Authority Ownership inspection;
- provider registry/capability/turn/history/control owners;
- typed mode policy and deterministic authorization;
- `GovernedToolOrchestrator` for registered execution, receipts, and idempotency;
- completion policy/runtime/evidence/gate owners;
- CLI and optional Textual projection;
- accepted bounded Node/stdio Cline `AgentRuntime` continuation path.

Pinned Cline reuse remains `ADAPT`: reuse provider/tool-call/continuation mechanics while LBE keeps workspace/session/policy/tool/evidence/validation/completion authority. Do not adopt `ClineCore` wholesale or expose native Cline mutation/shell paths as canonical LBE execution.

---

# 4. Current gate — roadmap/acceptance reconciliation

Current active phase:

```text
LBE_RUNTIME_ROADMAP_RECONCILIATION
```

Current active slice:

```text
CLASSIFY_IMPLEMENTED_VS_ACCEPTED_RUNTIME_CAPABILITIES
```

Current rules:

```text
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
```

The former R2-current wording in this plan is historical and no longer describes `main`.

Evidence reconciliation found that R3, R4, R5, and substantial R6/CLI runtime owners already exist. Later P0-P16 checkpoints also accepted substantial provider/event/tool/control/TUI runtime layers, and the subsequent Cline provider-continuation slice is PASS.

The classification rule is therefore:

```text
file/test exists != roadmap accepted
old roadmap says future != implementation missing
```

Use one of:

- `PROVEN_COMPLETE`
- `IMPLEMENTED_NOT_ACCEPTED`
- `PARTIALLY_PROVEN`
- `NOT_IMPLEMENTED`
- `BLOCKED_CONFIGURATION`
- `STALE_DOCUMENT_ONLY`
- `UNKNOWN`

Current reconciliation record:

```text
docs/acceptance/LBE_RUNTIME_ROADMAP_RECONCILIATION_CHECKPOINT.md
```

Preliminary earliest insufficiently proven family:

```text
R3_RUNTIME_REASONING_ACCEPTANCE
classification: IMPLEMENTED_NOT_ACCEPTED
```

This means the next candidate is an **R3 acceptance-proof slice**, not R3 source implementation. It is not active until this reconciliation slice reaches PASS and a separate machine/human gate is explicitly activated.

### Historical R2

R2 canonical session/task persistence is already present in the existing `WorkspaceMemoryStore` / `SessionMemoryRuntimeBridge` path and is not the current implementation gate. Historical branch/PR details must not be used to restart R2 work.

---

# 5. R3 — Persistent runtime -> existing reasoning boundary

**Current reconciliation classification: `IMPLEMENTED_NOT_ACCEPTED`.**

## Goal

The existing runtime owner invokes the existing reasoning controller and persists the lifecycle outcome.

Required path:

```text
SessionMemoryRuntimeBridge
        |
        v
construct existing LBERequest
        |
        v
existing reasoning controller.run()
        |
        v
existing LBEResponse
        |
        v
persist task/session outcome
```

Current source already contains this path in `SessionMemoryRuntimeBridge.run_reasoning()` and focused tests cover completed, blocked, and failed outcomes.

## Requirements

- no second reasoning controller;
- no second session lifecycle owner;
- no reasoning knowledge of persistence internals;
- no new verdict authority;
- preserve project/workspace/task identity;
- persist success/failure/interruption using existing task state.

## Exit proof still required for roadmap acceptance

- one canonical session creates/uses one task;
- runtime invokes the existing reasoning boundary;
- existing response contract is preserved;
- task lifecycle outcome is persisted;
- reasoning remains independently testable;
- required regression passes on the exact acceptance head;
- acceptance is recorded in a dedicated checkpoint.

The next post-reconciliation candidate should prove this path; do not reimplement it.

---

# 6. R4 — Checkpoint, resume, and rehydration

**Current reconciliation classification: `IMPLEMENTED_NOT_ACCEPTED`.**

## Goal

Allow a persistent session to stop and continue without treating remembered state as live workspace truth.

Current source/tests already cover persisted session contract, checkpoint constraints, restart, Git branch/HEAD revalidation, stale source-backed claim invalidation, and provider/session preservation.

## Required session data

```text
session_id
task_id
project_workspace_id
canonical_workspace_root
mode
provider_id/provider_model
active_profile_id
permission_policy_id
evidence_policy_id
TaskStatus
last_outcome
checkpoint identity
created_at
updated_at
```

Raw provider secrets must not be persisted.

## Resume flow

```text
resume requested
 -> resolve canonical workspace
 -> inspect current Git/runtime/workspace state
 -> load persisted session + verified memory
 -> invalidate stale source-backed claims
 -> rebuild bounded context
 -> continue through current provider/runtime path
```

## Exit proof still required for roadmap acceptance

1. start session;
2. establish validated workspace fact;
3. persist active task constraint;
4. checkpoint/compact;
5. change underlying source;
6. restart/resume;
7. old source fact becomes stale;
8. active constraint survives;
9. current workspace/Git state wins;
10. continuation does not trust summary text as proof;
11. record acceptance on exact head.

---

# 7. R5 — Bounded classified retry and recovery

**Current reconciliation classification: `IMPLEMENTED_NOT_ACCEPTED`.**

Current `recovery.py` and `SessionMemoryRuntimeBridge.run_recoverable()` already implement persisted, bounded retry/recovery behavior with focused tests.

## Failure classes

At minimum distinguish provider/inference failure, timeout, temporary tool failure, deterministic validation failure, permission denial, stale workspace state, scope/specification conflict, missing dependency/resource, and cancellation/interruption.

## Retry contract

Retry is permitted only when policy declares retryable class, maximum attempts, delay/backoff where applicable, idempotency expectation, evidence between attempts where required, and terminal stop condition.

Never retry deterministic policy denial, scope conflict, or known-invalid input as if transient.

## Exit proof still required for roadmap acceptance

- transient failure recovers within policy;
- deterministic failure does not loop;
- retry count persists where required;
- duplicate writes are prevented;
- cancellation stops cleanly;
- final outcome records exact recovery evidence;
- exact acceptance head is checkpointed.

---

# 8. R6A — Provider abstraction layer

**Current reconciliation classification: `PARTIALLY_PROVEN`.**

Current provider registry/capability/health/turn/event owners and accepted P-series checkpoints prove substantial provider mechanics. The accepted Cline continuation path adds a mature reusable provider/agent engine behind LBE authority.

## Stable provider responsibility

Provider layers may translate authentication/configuration, request/response/streaming, provider tool-call syntax, model capability/context metadata, health/model discovery, and continuation mechanics.

They may not reinterpret workspace permissions, guard verdicts, evidence authority, completion truth, or persistent policy.

## Remaining roadmap acceptance proof

Within the same persisted workspace/session contract:

```text
provider A -> reasoning request -> response
provider B -> equivalent logical request -> response
```

The switch must preserve workspace identity, policy, permissions, guards, evidence semantics, and task lifecycle. Configuration/listing alone is insufficient provider proof.

---

# 9. R6B — Mode policy engine

**Current reconciliation classification: `PARTIALLY_PROVEN`.**

Current `runtime/mode_controller.py`, persisted session policy, and focused mode tests establish typed policy ownership.

## Required semantics

- Coding: governed modification/validation inside granted authority.
- Audit: read-only current-reality determination with deterministic evidence/guards.
- Investigation: evidence-driven diagnosis; no mutation unless coding authority is active.

## Remaining roadmap acceptance proof

The same provider/runtime path must operate under each mode and receive different allowed capabilities from LBE policy—not from separate model identities or prompt-only personality changes.

---

# 10. R6C — Permission and authorization resolver

**Current reconciliation classification: `PARTIALLY_PROVEN`.**

Current deterministic owner: `runtime/authorization_resolver.py`, composed with `GovernedToolOrchestrator`.

Output remains:

```text
ALLOW
DENY
ESCALATE
```

The accepted Cline continuation proof additionally demonstrated that `DENIED` and `ESCALATED` governed results do not execute the tool handler and cannot be bypassed by the provider continuation.

## Remaining roadmap acceptance proof

- repeated already-authorized operations do not repeatedly ask permission;
- out-of-scope operations cannot bypass resolver;
- policy provenance is visible;
- provider cannot self-upgrade authority;
- authority change, where permitted, is explicit and then becomes the new active policy.

---

# 11. R6D — Context assembly and guard/rule injection

**Current reconciliation classification: `IMPLEMENTED_NOT_ACCEPTED`.**

Current owner: `runtime/context_assembly.py` plus existing evidence/reasoning/guard/memory owners.

## Goal

Build a bounded, reproducible context packet containing only current task/session identity, current mode/provider capability summary, active workspace/policy/permissions, verified constraints, relevant rules/guards, bounded reference evidence, requested current workspace evidence, recent validated failures, checkpoint context, and missing/contradictory evidence.

## Remaining roadmap acceptance proof

- packet is bounded and reproducible;
- irrelevant rules are absent;
- current workspace facts are not replaced by reference evidence;
- equivalent authoritative context survives provider switching;
- reasoning prose cannot contaminate retrieval authority.

---

# 12. R6E — Governed tool orchestration

**Current reconciliation classification: `PARTIALLY_PROVEN`.**

Current owner: `runtime/tool_orchestration.py::GovernedToolOrchestrator`.

Accepted P5/P7 and the Cline continuation slice prove receipt-backed governed execution/continuation and negative authorization boundaries.

Required lifecycle remains:

```text
reasoning proposes tool
 -> registered tool lookup
 -> permission resolver
 -> preconditions/workspace boundary
 -> execute through existing owner
 -> structured receipt/evidence
 -> runtime/history update
 -> required validation
 -> provider continuation where applicable
```

No generic unrestricted shell bypass is permitted.

## Remaining roadmap acceptance proof

Broader normal coding workflows must prove required read/write/validation tool classes, write scope before mutation, structured evidence, idempotent operation identity, and validation binding to actual receipts through the normal installed path.

---

# 13. R6F — Completion and validation gate

**Current reconciliation classification: `PARTIALLY_PROVEN`.**

Current completion policy/runtime/gate/evidence owners and tests already exist. CLI `session validate` delegates to these existing owners.

## Goal

A plausible model response never becomes `DONE` by itself.

Task-specific completion may require source/diff evidence, targeted/full tests, build/package proof, current Git/workspace state, applicable guard results, and no unresolved required validation.

## Remaining roadmap acceptance proof

- model saying “done” is insufficient;
- missing validation keeps task incomplete;
- failures are preserved;
- successful completion stores validated lifecycle outcome;
- installed/normal coding flow demonstrates the predicate end to end.

---

# 14. CLI control surface

**Current reconciliation classification: `PARTIALLY_PROVEN`.**

Current `lbe_guard_inspector/cli.py` already exposes:

```text
lbe session create
lbe session continue
lbe session status
lbe session inspect
lbe session evidence
lbe session validate

lbe code
lbe audit
lbe investigate

lbe provider list
lbe provider check
lbe provider select

lbe policy show
lbe permissions show
lbe tui
```

P12/P13 provide installed CLI/TUI proof for portions of this control surface.

## Remaining CLI acceptance proof

- non-interactive structured output;
- human-readable output where required;
- no command bypasses runtime authority;
- provider/session continuation preserves workspace policy;
- required R3-R6 runtime proofs are reachable through the normal control surface rather than source-only fixtures.

---

# 15. Configuration system

Configuration precedence remains:

```text
explicit command/session override
> workspace profile
> user configuration
> safe product defaults
```

Only explicitly overridable values participate. Raw credentials must not be persisted in workspace memory, task records, receipts, checkpoints, or logs.

---

# 16. Optional API surface

API operations should converge on the same runtime/session services as CLI. It must not implement a second policy engine.

Potential operations include create/continue session, submit task/input, status/evidence/validation, cancel, and provider health.

---

# 17. Optional TUI/operator console

A Textual projection already exists and has partial installed/runtime acceptance. It remains a client projection—not a second agent/runtime authority.

It may expose sessions, workspace, provider/model, mode, task state, profile/guards, permissions, evidence, validation, escalations, and recovery state by consuming the same authoritative runtime history/control APIs.

---

# 18. R7 — End-to-end persistent coding/audit runtime proof

**Current reconciliation classification: `PARTIALLY_PROVEN`.**

Lower-level components have substantial accepted evidence, but there is no current project-owned R7 acceptance record on `main` proving all required families through the installed/normal path. Therefore:

```text
project_user_ready: NO
release_ready: NO
```

## Proof A — coding session

1. create session for controlled repository;
2. choose provider A;
3. coding mode loads workspace identity/rules/permissions/evidence policy;
4. bounded edit/test authority is active;
5. reasoning requests permitted tools;
6. pre-authorized actions proceed without repetitive prompts;
7. mutation stays inside allowed scope;
8. required validation executes;
9. completion gate records validated outcome;
10. session persists.

## Proof B — provider switch

Continue same session with provider B, rehydrate current authoritative context, and prove workspace policy/permissions/task identity remain unchanged.

## Proof C — resume after workspace change

Checkpoint, change relevant source externally, restart/resume, invalidate stale source-backed memory, preserve supported task constraints, and prove current workspace evidence wins.

## Proof D — audit mode

Open audit session, enforce read-only policy, retrieve reference patterns where useful, inspect live workspace, run deterministic guards/validation, produce evidence-backed result, and prove no mutation occurred.

## Proof E — escalation

Out-of-authority request must return `ESCALATE` or `DENY`; provider cannot bypass it. After an explicit authorized policy change, execution may proceed only according to the new active policy.

## R7 completion condition

All required proof families must pass from installed/normal execution paths. Lower-level source/unit/integration proof cannot be promoted into overall R7 readiness.

---

# 19. Release and packaging

**Current reconciliation classification: `PARTIALLY_PROVEN`.**

Packaging/install tests and prior installed checkpoints exist, but release readiness is not accepted.

After R7 acceptance:

- define supported Python/Node/runtime matrix from evidence;
- keep provider dependencies modular where practical;
- validate clean installation and CLI entry points;
- audit package contents and Cline runtime/package resources;
- exclude state/config/secrets/workspace artifacts;
- document configuration/migration and required third-party notices;
- run focused/full suites and installed end-to-end smoke proof;
- do not publish externally without explicit release action.

---

# 20. Evidence-reconciled progression sequence

Do **not** re-run already implemented roadmap families as source implementation merely because their old section appears earlier in this document.

Current progression:

```text
CURRENT
LBE_RUNTIME_ROADMAP_RECONCILIATION
        |
        | PASS required
        v
R3 acceptance proof
(PROVE existing runtime -> existing reasoning boundary)
        |
        v
R4 acceptance proof
(existing checkpoint/resume/stale-state behavior)
        |
        v
R5 acceptance proof
(existing bounded recovery behavior)
        |
        v
R6 acceptance gaps in dependency order
(provider switch / mode / authorization / context / tools / completion)
        |
        v
CLI normal-path coverage for required runtime proofs
        |
        v
R7 installed end-to-end proof families A-E
        |
        v
release/package readiness
```

At each step, first determine whether the gap is:

```text
acceptance only
repair of existing owner
missing integration
truly missing implementation
blocked configuration
```

Only a proven `NOT_IMPLEMENTED`/defective owner permits source implementation in that family. Never create a second owner because an acceptance record is missing.

The optional API/TUI work remains subordinate to runtime acceptance and must not reorder authority dependencies.

---

# 21. Slice discipline

Every slice must define:

- exact objective/question;
- existing authoritative owner;
- classification (`REUSE`, `ADAPT`, repair, or genuinely new architecture where authorized);
- allowed files/components;
- explicit exclusions;
- typed input/output contract where implementation is involved;
- failure behavior;
- required evidence level;
- targeted tests/diagnostics;
- regression requirement where appropriate;
- Git/worktree/diff evidence;
- acceptance condition;
- next-phase lock.

Do not combine provider adapters, CLI UX, tool orchestration, recovery, resume, policy, and acceptance proof into one large slice.

---

# 22. Explicit non-goals

Do not drift into:

- training a dedicated LBE foundation model;
- passive model learning from conversations;
- separate coding/audit model authorities;
- unrestricted autonomous repair;
- unrestricted shell access;
- model-authored guard verdicts;
- cross-project memory as current truth;
- replacing Git/current workspace inspection with memory;
- automatic global-rule creation from one finding;
- TUI-first product development;
- provider-specific governance forks;
- cloud synchronization before local runtime proof;
- broad multi-agent orchestration before one persistent governed-agent path is accepted;
- wholesale ClineCore/session/tool authority adoption.

---

# 23. Canonical responsibility map

```text
User configuration
    -> delegated authority and defaults

CLI / API / optional TUI
    -> control surfaces

Persistent runtime
    -> session/task lifecycle, orchestration, recovery

Provider adapter / Cline lower layer where selected
    -> provider-native inference/stream/tool-call/continuation mechanics

LLM reasoning layer
    -> interpretation, planning, hypotheses, explanation, proposals

Reference retrieval
    -> historical patterns and candidate guidance

Current workspace inspector
    -> current project facts

Rules / deterministic guards
    -> deterministic condition detection

Permission/governance layer
    -> authorization

Governed tool owner
    -> execution, operation identity, receipts

Validation/completion
    -> proof and terminal truth

Validated memory/checkpoints
    -> bounded persistent context, never replacement truth
```

---

# 24. Final invariant

Every future decision must preserve:

```text
Provider reasons.
Persistent runtime orchestrates.
CLI/API/TUI expose the runtime.
Current workspace supplies facts.
Relevant rules and guards are selected/injected by LBE.
Permission policy authorizes actions.
Pre-authorized actions proceed without repetitive approval.
Authority expansion is escalated according to policy.
Governed tools execute through registered LBE owners.
Deterministic guards detect.
Validation proves.
Completion truth belongs to LBE.
Persistent memory carries only bounded supported context.
```

If a proposed feature creates a competing owner for any of these responsibilities, stop and reconcile the ownership boundary before implementation.
