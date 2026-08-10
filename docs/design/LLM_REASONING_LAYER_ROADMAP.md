# LLM Reasoning Layer Roadmap

**Status:** Design proposal  
**Phase:** After guard catalog integration

## Related documents

- `docs/IMPLEMENTATION_PLAN.md`
- `docs/CURRENT_STATUS.md`
- `docs/reference/COMPLETION_CONTRACT_RESEARCH_EVIDENCE.md`
- Architecture and runtime pipeline design records
- Tool registry and guard selector contracts
- Retrieval, validation, governance, and execution-mode documentation

## Purpose

The LLM reasoning layer is not an autonomous coding agent.

Its responsibility is to convert a user request into a structured inspection plan by combining:

- current workspace facts;
- indexed reference knowledge;
- deterministic guard metadata;
- governance requirements.

It never replaces deterministic inspection, owns runtime execution, or invents workspace truth.

## Design goal

Evolve the current Small LBE Reasoning Agent into a disciplined reasoning engine capable of:

- understanding user intent;
- selecting a retrieval strategy;
- constructing evidence requests;
- selecting relevant registered guards;
- explaining deterministic results;
- proposing workspace protections.

It must not become responsible for:

- execution;
- validation authority;
- `PASS` or `FAIL` decisions;
- repository modification;
- autonomous repair.

## Responsibility boundary

```text
User
        │
        ▼
Reasoning Layer
        │
        ├── classify request
        ├── choose retrieval mode
        ├── build evidence requests
        ├── select guards
        └── explain results
        │
        ▼
Guard Inspector
        │
        ▼
Deterministic Guards
        │
        ▼
Validation
        │
        ▼
LBE Governance
        │
        ▼
Final Verdict
```

The reasoning layer never bypasses deterministic inspection.

## Core responsibilities

The reasoning layer owns reasoning only.

It may:

- interpret requests;
- identify ambiguity;
- recognize project types;
- choose retrieval strategy;
- request missing evidence;
- prioritize investigations;
- explain findings;
- summarize evidence;
- propose workspace rules.

It may not:

- modify files;
- execute repairs;
- approve writes;
- declare validation complete;
- invent evidence;
- infer `PASS`;
- infer `FAIL`.

## Retrieval planning

The reasoning layer must explicitly choose one retrieval mode.

### Diagnostic mode

Purpose: open-ended investigation.

Typical requests:

```text
Why is this failing?
What broke?
Find the problem.
Where is this error coming from?
```

Behavior:

- semantic search;
- code-pattern search;
- handler tracing;
- broad evidence ranking;
- project-scoped exploration.

### Guard mode

Purpose: deterministic rule execution.

Behavior:

- exact project identity;
- registered rule metadata;
- path filters;
- extension filters;
- exact evidence retrieval;
- no semantic expansion for structural checks.

### Investigation mode

Purpose: expand from an existing failure.

Starts from:

- a guard result;
- a validation failure;
- an evidence reference.

Then explores:

- callers;
- ownership;
- handlers;
- dependencies;
- related validation.

## Query construction

The reasoning layer must never merge reasoning text with retrieval input.

It builds typed requests with separate fields:

```text
query
reason
rule_id
workspace_id
path_patterns
extensions
mode
```

Example:

```text
query:
CSXS/manifest.xml

reason:
Validate cep.manifest_exists

rule_id:
cep.manifest_exists

mode:
guard
```

Do not construct queries such as:

```text
Search because the rule requires...
```

Reasoning, planning text, and rule explanation must never contaminate the executed retrieval query.

## Evidence planning

The reasoning layer must decide what evidence is required before requesting tools.

Evidence classes remain separate:

```text
Indexed reference evidence
Current workspace evidence
Validation evidence
Missing evidence
Contradictions
```

Reference evidence may guide inspection. It cannot be promoted into current workspace truth.

## Multi-step reasoning

The reasoning layer progressively refines temporary hypotheses:

```text
Problem
    ↓
Likely project type
    ↓
Likely subsystem
    ↓
Applicable guards
    ↓
Required evidence
    ↓
Evidence gaps
    ↓
Inspection request
    ↓
Deterministic result
    ↓
Explanation
```

Unsupported leaps are prohibited.

## Conflict resolution

Evidence authority is ranked as follows:

```text
Passing current validation
    ↓
Current workspace source and configuration
    ↓
Active workspace profile and policy
    ↓
Verified checkpoints
    ↓
Verified repairs
    ↓
Curated reference corpus
    ↓
Unverified patterns
    ↓
Model inference
```

Higher-authority evidence overrides lower-authority evidence.

The reasoning layer may explain contradictions, but it may not resolve them by preference or speculation.

## Guard selection

The reasoning layer selects guards. It does not execute or decide them.

```text
Problem
    ↓
Candidate registered guards
    ↓
Applicability assessment
    ↓
Required evidence
    ↓
Guard request
```

Selection rules:

- use only registered guard IDs;
- prefer exact trigger matches;
- prefer workspace-profile guards over generic guards;
- do not run every guard;
- do not select a guard from keyword similarity alone;
- stop when applicability cannot be established.

When evidence is insufficient, the reasoning layer must stop rather than continue selecting guards.

## Explanation layer

After deterministic execution, the reasoning layer may explain:

- why a guard applied;
- why it did not apply;
- which evidence supported it;
- which evidence was missing;
- why validation failed;
- which uncertainty remains.

It must not alter the deterministic result or governance state.

## Workspace-rule proposal

When verified evidence justifies a persistent workspace constraint, the reasoning layer may propose:

```text
Workspace rule
    ↓
Equivalent-rule and contradiction check
    ↓
Exact profile diff
    ↓
User approval
    ↓
LBE governance authorization
    ↓
Application
    ↓
Activation validation
```

Rule creation is never automatic.

A single workspace finding must not be promoted directly into a global guard.

## Operational capabilities still missing

### Retrieval planner

Chooses among:

- diagnostic;
- guard;
- investigation.

### Typed query builder

Keeps the following independent:

- literal query;
- reason;
- rule ID;
- workspace identity;
- path and extension filters;
- retrieval mode.

### Evidence planner

Determines:

- required evidence;
- optional evidence;
- missing evidence;
- validation requirements.

The reasoning layer may identify that validation is needed, but it must not define authoritative task-completion evidence kinds or select validation IDs. Current runtime source rejects model-selected `validation_requests`; deterministic validation and completion requirements belong to LBE-owned task/policy state.

### Conflict resolver

Ranks contradictory evidence according to authority and records unresolved contradictions without guessing.

### Guard planner

Chooses only necessary registered guards and produces typed guard requests.

### Investigation planner

Expands from failures, operations, or evidence references without scanning the entire workspace unnecessarily.

### Explanation generator

Produces:

- user-facing explanation;
- evidence summary;
- guard rationale;
- explicit uncertainty.

It cannot change deterministic findings.

## Future runtime relationship

The reasoning layer remains independent of the host runtime.

Future runtime responsibilities include:

- session persistence;
- checkpointing;
- objective management;
- tool orchestration;
- retries and recovery;
- scheduling;
- runtime lifecycle events;
- resolution and persistence of task completion requirements;
- trusted semantic validation production;
- deterministic completion evaluation.

The runtime may call the reasoning layer, but runtime state and tool execution remain outside model authority.

## Completion criteria

The reasoning layer is complete when it can reliably:

- classify user requests;
- select the correct retrieval mode;
- build typed retrieval requests;
- keep query text separate from reasoning;
- plan and request evidence;
- select only registered guards;
- produce structured guard requests;
- rank evidence by authority;
- identify contradictions and missing evidence;
- stop on insufficient evidence;
- explain deterministic results;
- propose workspace-specific rules through governance;
- avoid inventing workspace truth;
- remain independent from runtime execution.

## Implementation order

```text
Current reasoning foundation
        │
        ▼
Retrieval planner
        │
        ▼
Typed query builder
        │
        ▼
Evidence planner
        │
        ▼
Conflict resolver
        │
        ▼
Guard planner
        │
        ▼
Investigation planner
        │
        ▼
Explanation layer
        │
        ▼
Workspace-rule proposal integration
        │
        ▼
Persistent runtime integration
```

Each step must preserve the existing evidence, validation, and governance boundaries.

## Suggested implementation slices

### Slice 1 — Retrieval plan contract

Define and test a typed retrieval-plan object containing:

- mode;
- workspace identity;
- literal query;
- reason;
- rule ID;
- path patterns;
- extensions;
- semantic-search permission;
- seed evidence references.

### Slice 2 — Deterministic query discipline

Prove that:

- reason text cannot alter search terms;
- structural guard requests can use exact path selection without semantic search;
- executed queries and filters are recorded in the evidence package.

### Slice 3 — Evidence requirement planning

Map registered guard metadata to:

- required indexed evidence;
- required current workspace evidence;
- required validation;
- not-applicable conditions.

These reasoning-time validation needs remain advisory/request-oriented. They must not be converted directly into the task's authoritative `TaskCompletionContract`.

### Slice 4 — Guard request generation

Generate schema-valid guard requests from the evidence package and catalog without allowing model-invented guard IDs.

### Slice 5 — Conflict and stop behavior

Prove that contradictory or incomplete evidence yields an explicit stop or `INSUFFICIENT_EVIDENCE` path rather than speculative continuation.

### Slice 6 — Investigation expansion

Allow a failed guard or validation result to seed bounded diagnostic expansion into related files, handlers, ownership paths, and tests.

### Slice 7 — Explanation and proposal integration

Explain deterministic results and optionally produce a governed workspace-profile proposal without applying it automatically.

## Acceptance requirements

Tests must prove that the reasoning layer:

1. selects diagnostic mode for open-ended failures;
2. selects guard mode for explicit deterministic checks;
3. selects investigation mode when seeded by an existing failure or evidence reference;
4. never places reason or planning text in the executed query;
5. never selects an unregistered guard;
6. does not run every matching guard;
7. preserves reference, workspace, and validation evidence separation;
8. stops when required evidence is missing or contradictory;
9. cannot emit authoritative `PASS` or `FAIL` without deterministic guard output;
10. cannot authorize writes or modify the workspace;
11. can explain an existing result without changing its verdict;
12. can propose, but not silently apply, a workspace-specific rule;
13. cannot define or mutate the authoritative task completion contract;
14. cannot classify arbitrary command/tool success as semantic completion evidence.

## Non-goals

This roadmap does not introduce:

- foundation-model training;
- unrestricted autonomous coding;
- broad autonomous repair;
- model-generated verdict authority;
- passive learning from all indexed content;
- runtime ownership by the model;
- automatic global-rule creation;
- replacement of live workspace validation with memory or search results.

## Success definition

The reasoning layer is complete when it can transform an ambiguous user problem into a bounded, evidence-driven, deterministic inspection workflow while preserving strict separation between:

- reasoning;
- retrieval;
- workspace inspection;
- deterministic guards;
- validation;
- governance;
- runtime execution.

At that point it becomes the decision-support component of the LBE architecture. Deterministic guards, validation, and LBE Core remain authoritative for inspection results, proof, and execution.

---

## 2026-08-10 completion-contract research checkpoint

Research recorded in `docs/reference/COMPLETION_CONTRACT_RESEARCH_EVIDENCE.md` changes the dependency order for the next agent/CLI milestone.

Verified current behavior:

- provider `COMPLETED` is provisional for coding tasks;
- model-selected `validation_requests` are forbidden;
- durable completion-contract storage exists;
- durable producer-bound completion-evidence storage exists;
- production task establishment does not yet prove where the authoritative completion contract is resolved.

Therefore the next implementation sequence is:

```text
identify existing LBE-owned task/policy completion-requirement source
        ↓
resolve + persist immutable task completion contract
        ↓
execute trusted registered semantic validation producers
        ↓
persist producer-bound completion evidence
        ↓
existing deterministic completion gate
        ↓
thin CLI/API validation surface
```

Do not implement `lbe session validate` as a place that invents requirements, accepts caller-selected PASS evidence, or classifies raw command success.

Before introducing a new completion-contract resolver, prove from current source that no existing task, session-policy, mode, behavior, or evidence-policy owner already contains the required semantics.