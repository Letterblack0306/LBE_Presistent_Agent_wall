# 08 — LBE Gallery and Indexed Knowledge

## Purpose

Store and retrieve distilled engineering knowledge without treating all records as equally authoritative.

## Record types

- rule;
- deterministic guard metadata;
- workspace profile;
- architecture pattern;
- handler pattern;
- data-flow pattern;
- state-owner pattern;
- validation pattern;
- failure pattern;
- repair pattern;
- anti-pattern;
- verified proof;
- protected checkpoint;
- confirmed decision;
- negative example;
- historical chat or Q&A context.

## Required metadata

- ID;
- title;
- record type;
- project types;
- workspace scope;
- trigger;
- problem;
- rationale;
- evidence references;
- source classification;
- authority level;
- confidence;
- verification status;
- verified timestamp;
- superseded status;
- hash or version.

## State-owner knowledge

A state-owner pattern records which component is authorized to create or mutate a canonical state or side effect.

The core roles are:

- **authoritative owner** — the single component permitted to create or mutate canonical state;
- **observer or subscriber** — receives authoritative events and may derive secondary state without rewriting canonical state;
- **delegate** — performs a bounded operation on behalf of the owner under an explicit contract;
- **projection** — displays owner-supplied state and cannot independently mutate it.

Authority Ownership is stored as a `state-owner pattern`, not as a separate agent tool. The concrete reference record is:

```text
examples/reference/state_owner_authority_ownership.yaml
```

The reasoning layer may retrieve this pattern when investigating duplicate execution, competing writers, repeated triggers, persistence ownership, lifecycle hooks, or UI/runtime disagreement. The record alone cannot prove that a target workspace contains a duplicate authority.

Current workspace inspection must identify all writers, callers, persistence locations, projections, and runtime effects before an authority finding is produced.

A knowledge-only state-owner record must not produce `PASS` or `FAIL`. Deterministic verdicts require a registered executable guard and the validation evidence declared by that guard.

## Tool boundary

State-owner knowledge uses the existing LBE tool chain:

- `memory.search` retrieves the reference pattern;
- `workspace.resolve`, `workspace.read`, and `workspace.hash` collect current facts;
- `guard.catalog` exposes registered deterministic implementations;
- `guard.inspect` executes a selected implementation;
- `validation.run` corroborates the result;
- `lbe.decide` evaluates governance and authority.

Do not create a dedicated authority-owner tool when the existing guard and inspection interfaces can represent the operation. A separate tool would create a second execution surface and weaken ownership clarity.

## Promotion boundary

A state-owner pattern follows the standard rule promotion path:

```text
Reference pattern
→ verified target-workspace occurrence
→ workspace-profile proposal
→ repeated verified pattern
→ deterministic guard candidate
→ tests + review + explicit approval
→ reusable global guard
```

Reference knowledge must retain its origin and cannot be relabeled as current workspace truth.

## Retrieval boundary

The gallery supplies context. It does not:

- decide which workspace is active;
- prove the current project has the same defect;
- authorize edits;
- produce final verdicts.

## Authority requirement

Search results must preserve their source class, authority, verification state, and workspace scope in the evidence package.
