# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-10
Status: Active canonical roadmap

This document is the implementation sequence for `Letterblack0306/LBE_Presistent_Agent_wall`.

For architecture rationale and provider/CLI boundaries, also read:

- `docs/design/CLI_CONTROL_PLANE_PROVIDER_BOUNDARY.md`
- `docs/design/LLM_REASONING_LAYER_ROADMAP.md`
- `docs/VALIDATED_WORKSPACE_MEMORY.md`
- `docs/CURRENT_STATUS.md`

When this plan and live repository evidence disagree, current source, current Git state, runtime evidence, and current validation win. Update this plan rather than silently creating a competing roadmap.

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
provider adapter
        |
        +-- OpenAI-compatible providers
        +-- Claude/provider APIs
        +-- LM Studio
        +-- Ollama
        +-- future providers
        |
        v
reasoning layer
        |
        v
LBE tools / guards / validation / governance
        |
        v
current workspace
```

The provider reasons. LBE owns the workspace contract.

The product must support two primary user-facing operating paths:

1. **Coding** — governed modification and validation inside authority already granted by the user.
2. **Audit / investigation** — evidence-first inspection without workspace mutation.

Additional surfaces such as a TUI are optional views over the same runtime state. They must not become parallel controllers.

---

## 2. Non-negotiable architecture invariants

### 2.1 LBE remains stable when the model changes

Changing the provider or model must not change:

- workspace identity;
- active rules and profiles;
- permissions;
- deterministic guard semantics;
- evidence authority;
- validation requirements;
- completion requirements;
- persistent session/task state.

Provider changes affect reasoning implementation only.

### 2.2 CLI is a control surface, not the source of authority

The CLI owns user/runtime interaction. LBE Core and the persistent runtime own policy enforcement and execution authority.

Do not implement:

```text
CLI -> model -> raw unrestricted tools
```

Required boundary:

```text
CLI
 -> session controller
 -> LBE policy/capability resolution
 -> provider reasoning
 -> governed tools
 -> current workspace
```

### 2.3 Modes are execution contracts, not model personalities

Do not create separate permanent "coding LLM", "audit LLM", or "rule-learning LLM" authorities.

Use one provider abstraction with mode-specific:

- tool permissions;
- write authority;
- evidence requirements;
- guard requirements;
- validation requirements;
- completion rules.

### 2.4 Rules are injected and enforced, not passively learned

Agents do not become reliable because a model saw a rule previously.

Relevant rules, guards, validated patterns, constraints, and known risks are loaded into the active session contract when applicable.

Permanent policy changes must follow the configured governance path.

### 2.5 Existing authorization must not become repeated confirmation

The runtime must distinguish authorization from per-action confirmation.

If user/session/workspace settings already authorize a class of action, such as applying an existing approved rule, editing allowed source files, or running approved validation, the coding runtime may continue without asking again for every matching action.

Escalation is required only when an operation exceeds active authority, for example:

- path or workspace scope expansion;
- capability class not enabled by policy;
- destructive action outside delegated authority;
- persistent rule/profile creation or widening not already delegated;
- unresolved intent or scope conflict.

### 2.6 Workspace truth remains live

Authority order remains:

```text
current validation
    > current workspace/Git/runtime evidence
    > active workspace policy
    > verified memory/checkpoints
    > verified historical repairs
    > curated reference patterns
    > unverified history
    > model inference
```

Persistent memory must never replace live inspection.

---

## 3. Existing foundation to preserve

The following capabilities are foundation, not targets for redesign:

- reference corpus retrieval and evidence classification;
- target workspace resolution and project-scoped identity;
- typed evidence packages and guard requests/results;
- deterministic guard execution;
- validation and verdict ownership separation;
- reasoning retrieval/query/evidence/guard/investigation/explanation planning;
- governed rule proposal and apply boundary;
- validated project-scoped memory;
- `WorkspaceMemoryStore`;
- `SessionMemoryRuntimeBridge`;
- Module Registry / runtime-map concepts;
- Authority Ownership inspection;
- runtime-neutral invocation concepts.

New work must reuse existing owners rather than create parallel substitutes.

---

# 4. Current gate — finish R2 before expanding runtime

## R2 — Canonical session/task lifecycle persistence

Current PR: `#28`

Current branch:

```text
feat/persistent-runtime-session-task-state
```

Recorded PR head:

```text
124347e6504140682b744c6cafbe98a55fd635f5
```

Current R2 scope:

- canonical `TaskStatus`;
- persisted `session_id`;
- persisted `task_id`;
- project/workspace identity;
- status;
- outcome;
- timestamps;
- existing `WorkspaceMemoryStore` reused;
- existing `SessionMemoryRuntimeBridge` reused.

Explicitly excluded from R2:

- resume execution;
- retry/recovery;
- checkpoint expansion;
- reasoning ownership changes;
- validation ownership changes;
- tool orchestration;
- CLI/provider implementation.

### R2 merge gate

Before R3 begins:

1. update/reconcile PR #28 against current `main` without expanding scope;
2. run the full repository suite on the exact final R2 head;
3. record the full-suite evidence;
4. run focused session-runtime tests;
5. run `git diff --check`;
6. confirm changed files remain inside R2 scope;
7. merge only after the exact head is proven.

Do not use an older reported test count as proof for a newer head.

---

# 5. R3 — Persistent runtime → existing reasoning boundary

## Goal

Make the existing runtime owner invoke the existing reasoning controller and persist the lifecycle outcome.

Required path:

```text
SessionMemoryRuntimeBridge
        |
        v
construct existing LBERequest
        |
        v
LBERequestController.run()
        |
        v
existing LBEResponse
        |
        v
persist task/session outcome
```

## Requirements

- no second reasoning controller;
- no second session lifecycle owner;
- no reasoning knowledge of persistence internals;
- no new verdict authority;
- no tool execution yet;
- no retry/recovery yet;
- preserve project/workspace identity across request and response;
- persist success/failure/interruption outcomes using existing task-state storage.

## Exit proof

- one session can create a task;
- runtime calls the existing reasoning boundary;
- response is returned unchanged except for runtime envelope metadata;
- task lifecycle outcome is persisted;
- reasoning remains independently testable;
- full suite passes.

---

# 6. R4 — Checkpoint, resume, and rehydration

## Goal

Allow a persistent session to stop and continue without treating remembered state as live workspace truth.

## Required session data

A persisted session contract must carry at least:

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

Provider credentials or raw secrets must not be persisted in session state.

## Resume flow

```text
resume requested
      |
      v
resolve canonical workspace
      |
      v
inspect current Git/runtime/workspace state
      |
      v
load persisted session + verified memory
      |
      v
invalidate stale source-backed claims
      |
      v
rebuild bounded context packet
      |
      v
continue through current provider adapter
```

## Revalidation requirements

Before continuing a resumed task:

- re-resolve workspace identity;
- compare relevant Git branch/HEAD state;
- revalidate required source hashes;
- mark stale memory stale rather than silently reuse it;
- preserve active task constraints unless explicitly superseded;
- treat compaction summaries as history only.

## Exit proof

Controlled end-to-end proof:

1. start a session;
2. establish a validated workspace fact;
3. persist active task constraint;
4. checkpoint/compact;
5. change the underlying source;
6. restart/resume;
7. old source fact becomes stale;
8. active constraint survives;
9. current workspace/Git state wins;
10. task continues without trusting summary text as proof.

---

# 7. R5 — Bounded classified retry and recovery

## Goal

Recover from transient or classified failures without turning the agent into an uncontrolled loop.

## Failure classes

At minimum distinguish:

- provider/inference failure;
- timeout;
- temporary tool failure;
- deterministic validation failure;
- permission denial;
- stale workspace state;
- specification/scope conflict;
- missing dependency/resource;
- cancellation/interruption.

## Retry contract

Retry is allowed only when policy explicitly declares:

- retryable failure class;
- maximum attempts;
- delay/backoff if applicable;
- idempotency expectation;
- evidence required between attempts;
- terminal stop condition.

Do not retry deterministic policy denial, scope conflict, or known-invalid input as though it were transient.

## Exit proof

- transient provider/tool failure can recover within policy;
- deterministic failure does not loop;
- retry count persists across session state where required;
- duplicate writes are prevented;
- cancellation stops the loop cleanly;
- final outcome records exact recovery evidence.

---

# 8. R6A — Provider abstraction layer

## Goal

Make the reasoning provider user-selectable without moving authority out of LBE.

## Provider interface

Define one provider contract with capabilities such as:

```text
provider_id
model_id
health_check()
capabilities()
generate()/complete()
stream()              optional capability
tool_call_support     capability metadata
context_limit         capability metadata
```

Exact method names are implementation details; the stable contract is provider neutrality.

## Initial provider targets

Recommended first adapters:

1. OpenAI-compatible HTTP provider;
2. LM Studio through OpenAI-compatible local endpoint;
3. Ollama;
4. Anthropic/Claude adapter when its API-specific mapping is needed.

Do not hardcode workspace policy into provider adapters.

## Adapter responsibilities

Provider adapters may translate:

- authentication/configuration;
- request/response formats;
- streaming format;
- tool-call serialization;
- context-window/capability metadata;
- health/model discovery.

They may not reinterpret:

- workspace permissions;
- guard verdicts;
- evidence authority;
- completion truth;
- persistent rules.

## Provider switching proof

Within the same workspace/session contract:

```text
provider A -> reasoning request -> response
provider B -> same logical reasoning request -> response
```

The switch must preserve:

- workspace identity;
- policy;
- permissions;
- guards;
- evidence package semantics;
- task lifecycle.

---

# 9. R6B — Mode policy engine

## Goal

Represent coding, audit, and investigation as typed runtime policy rather than prompt-only behavior.

## Coding mode

Purpose: build, fix, modify, and validate within granted authority.

Potential capabilities when enabled by active policy:

- inspect workspace;
- search/retrieve evidence;
- edit approved paths;
- create bounded patches;
- run approved commands/tests/builds;
- apply existing approved workspace rules;
- invoke relevant guards;
- validate before completion.

Coding mode does not automatically mean unrestricted write authority.

## Audit mode

Purpose: determine current reality.

Default characteristics:

- read-only;
- current workspace evidence required for project-specific claims;
- deterministic guard results;
- strict validation requirements;
- no repair/edit path;
- explanations cannot alter verdicts.

## Investigation mode

Purpose: diagnose an unknown failure or expand from a known failure.

Characteristics:

- starts from error/evidence/guard result/runtime event;
- may search semantically and trace callers/handlers/dependencies;
- remains project-scoped by default;
- produces diagnosis/evidence;
- no mutation unless explicitly operating under coding authority.

## Exit proof

The same provider can run under each mode and receives different allowed capabilities from LBE policy, not from separate model identities.

---

# 10. R6C — Permission and authorization resolver

## Goal

Turn user-configured authority into deterministic runtime decisions and remove unnecessary repeated prompts.

## Inputs

```text
workspace identity
session mode
user settings
workspace profile
requested capability/action
path/scope
risk class
persistent-policy impact
```

## Output

```text
ALLOW
DENY
ESCALATE
```

with reason and policy provenance.

## Rules

### ALLOW

Use when the active policy already grants the exact operation class and scope.

Examples:

- edit inside configured source scope;
- run approved test command class;
- apply an existing approved workspace rule;
- execute allowed validation.

### ESCALATE

Use when additional user authority is genuinely required.

Examples:

- write outside configured scope;
- destructive action not delegated;
- new external/network capability not permitted;
- creation/widening of persistent policy when not delegated;
- unresolved conflict with active intent.

### DENY

Use when policy explicitly prohibits the action or it violates a hard safety/workspace boundary.

## Important distinction

```text
existing approved rule + already delegated apply authority
    -> may apply without another prompt

new rule / wider policy / new authority class
    -> follow policy-change authorization rules
```

## Exit proof

- repeated allowed edits do not repeatedly ask permission;
- out-of-scope action cannot bypass resolver;
- policy provenance is recorded;
- provider cannot self-upgrade its authority.

---

# 11. R6D — Context assembly and guard/rule injection

## Goal

Build the exact bounded context needed for the current turn instead of dumping memory or workspace content into the model.

## Context sources

Potential packet sections:

```text
current session/task identity
current mode
provider capability summary
active workspace identity
active permissions
current task/goal
verified active constraints
relevant workspace rules
applicable guard metadata
bounded indexed reference evidence
current workspace evidence requested for reasoning
recent validated failures/patterns
checkpoint context
missing/contradictory evidence
```

Evidence classes must remain distinguishable.

## Rule selection behavior

Do not inject every rule.

Use:

- workspace profile;
- current project type;
- task/failure domain;
- guard applicability;
- previous validated pattern triggers.

A model may request additional evidence but cannot invent a guard or declare a rule applied when runtime did not apply it.

## Exit proof

- context is bounded and reproducible;
- irrelevant rules are absent;
- current workspace facts are not replaced by reference matches;
- provider switch receives equivalent authoritative context;
- reason/planning text cannot contaminate retrieval queries.

---

# 12. R6E — Governed tool orchestration

## Goal

Allow coding mode to use real tools while LBE remains the authority boundary.

## Tool lifecycle

```text
reasoning requests tool
        |
        v
registered tool lookup
        |
        v
permission resolver
        |
        v
preconditions / workspace boundary
        |
        v
execute
        |
        v
capture structured evidence
        |
        v
update task/runtime state
        |
        v
validation when required
```

## Tool registry requirements

Each executable capability must declare:

- tool ID;
- schema;
- read/write class;
- network behavior;
- risk class;
- timeout;
- retry policy;
- preconditions;
- expected evidence;
- failure modes.

## Initial coding tool classes

Implement only what is required by real workflows, for example:

- workspace tree/read/search/hash;
- controlled file patch/write;
- approved command execution;
- test/build/validation execution;
- Git status/diff inspection;
- optional governed commit/push only if later explicitly included by policy.

Do not give models a generic unrestricted shell bypass around registered tool policy.

## Exit proof

- model requests cannot bypass the registry;
- write scope is checked before mutation;
- tool outputs become structured evidence;
- duplicate operation identity is available for recovery/idempotency;
- validation can bind to actual execution receipts.

---

# 13. R6F — Completion and validation gate

## Goal

Prevent the coding runtime from converting a plausible model response into `DONE`.

## Completion predicate

Task completion must evaluate the claim actually being made.

Possible evidence:

- required source changes exist;
- expected diff scope is satisfied;
- targeted tests pass;
- required full suite passes;
- build/package validation passes;
- current Git/workspace state is known;
- relevant deterministic guards pass where required;
- no unresolved required validation remains.

Not every task requires every evidence type. The task contract defines the required proof.

## Exit proof

- model saying "done" is insufficient;
- missing required validation keeps task incomplete;
- failures are preserved as evidence;
- successful completion stores a validated lifecycle outcome rather than model opinion.

---

# 14. CLI implementation

## Goal

Expose the persistent runtime through one stable, automation-friendly interface.

The CLI must remain thin: it parses user intent/configuration and invokes runtime services. It must not duplicate provider, permission, memory, guard, or validation logic.

## Core command families

Exact names may evolve, but the required capabilities are:

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
```

Convenience commands such as `lbe code` may create/continue the appropriate session internally, but session state remains canonical.

## Session creation inputs

At minimum:

```text
workspace
mode
provider/model
workspace/profile policy
permission policy
```

Defaults may come from user configuration, but the resolved values must be visible through `session status`.

## CLI exit proof

- non-interactive use works;
- structured output is available for external agents/scripts;
- human-readable output is available for terminal users;
- no CLI command bypasses runtime authority;
- session can be continued with a different provider without changing workspace policy.

---

# 15. Configuration system

## Goal

Make provider and permission choices user-configurable without embedding environment-specific assumptions into source.

## Configuration levels

Recommended precedence:

```text
explicit command/session override
        > workspace profile
        > user configuration
        > safe product defaults
```

Only values allowed to be overridden should participate in this precedence.

## User configuration may define

- default provider/model;
- provider endpoint references;
- default operating mode;
- automatic application of existing approved rules;
- allowed write/tool classes;
- network policy;
- validation behavior;
- interactive escalation preference;
- output format preferences.

## Secret handling

Configuration should reference credentials through secure environment/provider mechanisms. Do not persist raw credentials in workspace memory, task records, or logs.

---

# 16. Optional API surface

The API should expose the same runtime/session operations needed by external integrations.

It must not implement a second policy engine.

Potential operations:

```text
create session
continue session
submit task/input
inspect status
retrieve evidence
validate
cancel
provider health
```

CLI and API should converge on the same runtime service layer.

---

# 17. Optional TUI/operator console — after CLI/runtime proof

Do not make TUI a prerequisite for runtime completion.

The TUI may display/control existing runtime state:

- active sessions;
- workspace;
- provider/model;
- mode;
- task status;
- active guards/profile;
- permissions;
- evidence;
- validation;
- escalations;
- failures/recovery state.

It must consume the same API/runtime contract as CLI and must not become another agent implementation.

---

# 18. R7 — End-to-end persistent coding/audit runtime proof

## Goal

Prove the full architecture with real provider switching, governed coding, read-only audit, persistence, resume, and validation.

## Proof A — coding session

1. create session for a real controlled repository;
2. choose provider A;
3. coding mode loads workspace identity, rules, permissions, and evidence policy;
4. user grants/uses a profile allowing bounded edits and tests;
5. reasoning requests permitted inspection/edit tools;
6. permission resolver allows pre-authorized actions without repeated prompts;
7. change is applied only inside allowed scope;
8. required validation executes;
9. completion gate records validated outcome;
10. session state persists.

## Proof B — provider switch

1. continue same session;
2. switch to provider B;
3. rehydrate current authoritative context;
4. verify workspace policy and permissions are unchanged;
5. continue reasoning without provider becoming authority.

## Proof C — resume after workspace change

1. checkpoint session;
2. modify relevant source externally;
3. restart runtime;
4. resume;
5. stale source-backed memory is invalidated;
6. current workspace evidence wins;
7. session/task constraints survive appropriately.

## Proof D — audit mode

1. open audit session on same or another project;
2. enforce read-only policy;
3. retrieve patterns where useful;
4. inspect live current workspace;
5. run deterministic guards/validation;
6. produce evidence-backed verdict/explanation;
7. prove no workspace mutation occurred.

## Proof E — escalation

1. coding model requests operation outside configured authority;
2. resolver returns `ESCALATE` or `DENY`;
3. provider cannot bypass the decision;
4. after explicit authority change, runtime can proceed according to the newly active policy.

## R7 completion condition

The runtime is considered architecture-complete for this milestone only when all required proofs pass from the installed/normal execution path, not just unit-test fakes.

---

# 19. Release and packaging

After R7 proof:

- define supported Python/runtime matrix from evidence;
- ensure provider dependencies remain optional/modular where possible;
- validate clean installation;
- validate CLI entry points from installed package;
- audit package contents;
- ensure state/config/secrets/workspace artifacts are excluded;
- document configuration and migration;
- run focused and full suites;
- run installed end-to-end smoke proof;
- do not publish externally without explicit release action.

---

# 20. Implementation sequence

Use this order unless current evidence proves a dependency must change:

```text
CURRENT
R2 merge readiness (#28)
        |
        v
R3 runtime -> existing reasoning controller
        |
        v
R4 checkpoint / resume / rehydration
        |
        v
R5 bounded classified recovery
        |
        v
R6A provider abstraction
        |
        v
R6B typed mode policies
        |
        v
R6C permission / authorization resolver
        |
        v
R6D context assembly + relevant rule/guard injection
        |
        v
R6E governed tool orchestration
        |
        v
R6F completion / validation gate
        |
        v
CLI command surface over the proven runtime services
        |
        v
optional API integration surface
        |
        v
R7 real end-to-end proof
        |
        v
release/package readiness
        |
        v
optional TUI operator console
```

### Important implementation note

The CLI shell can be scaffolded earlier if useful, but it must remain a thin wrapper. Do not implement CLI-owned behavior before the corresponding runtime service exists and is tested.

---

# 21. Slice discipline

Every implementation slice must define:

- exact objective;
- existing authoritative owner being extended;
- allowed files/components;
- explicit exclusions;
- typed input/output contract;
- failure behavior;
- targeted tests;
- full regression requirement when appropriate;
- Git diff/scope evidence;
- acceptance condition.

Do not combine provider adapters, CLI UX, tool orchestration, retry, resume, and policy changes into one large patch.

Recommended branch/PR granularity follows the numbered runtime slices above.

---

# 22. Explicit non-goals for the current roadmap

Do not drift into:

- training a dedicated LBE foundation model;
- passive model learning from all conversations;
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
- broad multi-agent orchestration before one persistent agent path is proven.

---

# 23. Canonical responsibility map

```text
User configuration
    -> delegated authority and defaults

CLI / API / optional TUI
    -> control surfaces

Persistent runtime
    -> session/task lifecycle, orchestration, recovery

Provider adapter
    -> translates provider-specific inference capabilities

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

Validation
    -> proof

Validated memory/checkpoints
    -> bounded persistent context, never replacement truth
```

---

# 24. Final invariant

Every future implementation decision should preserve this chain:

```text
Provider reasons.
Persistent runtime orchestrates.
CLI/API/TUI expose the runtime.
Current workspace supplies facts.
Relevant rules and guards are selected/injected by LBE.
Permission policy authorizes actions.
Pre-authorized actions proceed without repetitive approval.
Authority expansion is escalated according to policy.
Deterministic guards detect.
Validation proves.
Persistent memory carries only bounded supported context.
```

If a proposed feature creates another owner for any of these responsibilities, stop and reconcile the ownership boundary before implementation.