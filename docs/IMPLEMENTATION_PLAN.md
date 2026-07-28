# Implementation Plan

Updated: 2026-07-28

## Goal

Build a deterministic, read-only-first Guard Inspector that diagnoses one concrete workspace problem through an explicit authority chain:

```text
reference corpus suggests
current workspace inspection supplies facts
reasoning selects and explains
deterministic guards detect
LBE Core authorizes
validation proves
```

The model may select guards, form hypotheses, and explain results. It must not invent the verdict.

## Non-negotiable invariants

- Live target workspace and current validation outrank stored memory and indexed reference knowledge.
- Session history and compaction are historical context, not workspace truth.
- Reference-corpus evidence and target-workspace evidence remain separate.
- Every production module in the inspected runtime slice is declared.
- Every loaded module emits a runtime receipt.
- Every running module reports current activity.
- Registered-but-not-loaded modules remain visible.
- Loaded-but-unregistered modules are blocking defects.
- Registry evidence is read before broad source reconstruction.
- Source inspection remains available for missing, contradictory, stale, ownership-sensitive, or exact implementation evidence.
- The Authority Ownership Inspector remains read-only and cannot issue ordinary guard `PASS` or `FAIL`.
- Ordinary verdicts come only from deterministic guard execution plus required validation and LBE authorization.
- Invocation boundaries must remain configurable and must not hardcode a runtime, workspace, path, or port.

## Completed foundation: Phases 1-12

### Phase 1 - Module Registry contract and types

Completed:

- canonical declarations;
- lifecycle receipt types;
- module states;
- defect types;
- profile and singleton fields;
- bounded activity history.

### Phase 2 - Registry store and state derivation

Completed:

- declaration and live-record lookup;
- deterministic state derivation;
- bounded activity and last-error retention;
- instance tracking;
- filtering by state, type, profile, capability, loader, and dependency.

### Phase 3 - Registry validation and defects

Completed:

- unregistered module detection;
- registered-not-loaded visibility;
- expected-profile failures;
- unregistered dependency detection;
- singleton conflict detection;
- disabled-but-loaded detection;
- invalid loader and contradictory lifecycle detection.

### Phase 4 - Module Watcher

Completed:

- ordered subscriptions;
- immutable watcher events;
- bounded event history;
- subscriber isolation;
- watcher failure visibility;
- registry and watcher self-registration.

### Phase 5 - Minimal real runtime slice

Completed:

- static declarations for the selected runtime slice;
- load, start, activity, stop, and failure receipts;
- explicit loader and dependency relationships;
- read-only `/module-registry` query surface.

### Phase 6 - Registry-first inspection

Completed:

- registry declarations read first;
- watcher and lifecycle receipts read second;
- declaration/runtime comparison;
- structured missing-evidence and defect output;
- bounded source fallback only when required.

### Phase 7 - Authority ownership declaration contract

Completed:

- one operation per inspection;
- canonical target;
- owner, delegates, observers, subscribers, and projections;
- allowed mutations;
- persistence contract;
- applicability and evidence requirements.

### Phase 8 - Authority ownership schemas

Completed:

- request schema;
- 10-section evidence-package schema;
- result schema;
- evidence-reference requirements;
- seven deterministic findings;
- `pass_fail_authorized: false`.

### Phase 9 - Read-only Authority Ownership Inspector

Completed:

- bounded inspection of one authoritative operation;
- deterministic findings;
- duplicate storage distinguished from duplicate authority;
- unresolved contradictions mapped to `INSUFFICIENT_EVIDENCE`;
- indexed reference knowledge rejected as current proof;
- no workspace writes.

### Phase 10 - Runtime confirmation adapter

Completed:

- safe observation of existing watcher history;
- exact operation and module identity;
- bounded receipt window;
- explicit confirmed, unavailable, and unsafe results;
- no hidden activation.

### Phase 11 - Session memory runtime wiring

Completed:

- `WorkspaceMemoryStore` and `SessionMemoryAdapter` initialization;
- deterministic command and structured tool-result ingestion;
- checkpoint persistence;
- start/resume rehydration;
- stale source-backed memory invalidation;
- active-constraint retention;
- separation and correlation of registry receipts and durable memory evidence.

### Phase 12 - End-to-end foundation proof

Completed proof sequence:

1. verified project/session start;
2. registered runtime startup;
3. current activity receipts;
4. validated source-backed workspace fact;
5. deterministic command failure;
6. active-constraint checkpoint;
7. source change outside the session;
8. restart and rehydration;
9. stale-memory invalidation;
10. constraint retention;
11. runtime confirmation;
12. bounded ownership inspection;
13. deterministic repeatability;
14. no ordinary ownership `PASS` or `FAIL`;
15. no generated evidence committed.

Foundation was merged in PR `#2` at `7f212f406331dfaf7961143eefbf45f8ceaf6a17`.

## Phase 13 - First complete Guard Inspector vertical slice

Status: complete on `feat/guard-inspector-vertical-slice`.

### Problem

```text
Provided callback is not a function
```

### Completed sequence

```text
fixed callback request
-> exact workspace resolution
-> independently scoped reference retrieval
-> bounded live target-workspace inspection
-> evidence package
-> registered cep.callback_contract selection
-> deterministic guard execution
-> LBE authorization
-> independent narrow validation
-> structured verdict
-> evidence-only explanation
```

### Completed deliverables

- fixed request model for the callback problem;
- deterministic target-workspace resolution;
- reference retrieval scoped independently from workspace inspection;
- duplicate-filename-safe candidate selection;
- evidence records containing configured root, project root, relative path, hash, line range, bounded snippet, source class, and retrieval provenance;
- registered callback guard `cep.callback_contract` in pack `cep_callback`;
- deterministic guard input and output contracts;
- explicit read-only LBE authorization envelope;
- required narrow validation;
- `PASS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE` verdicts;
- explanation generated only from structured evidence referenced by the verdict;
- workspace before/after fingerprint verification;
- rollback documentation in `docs/PHASE_13_CALLBACK_VERTICAL_SLICE.md`;
- focused and end-to-end tests.

### Proven cases

1. correct target workspace is selected;
2. reference and workspace evidence are never conflated;
3. duplicate filenames do not cause wrong-file inspection;
4. indexed reference evidence cannot prove a current defect;
5. source inspection is bounded to relevant candidates;
6. the selected guard is registered and applicable;
7. identical input and workspace state produce identical semantic fingerprints;
8. missing or unresolved evidence produces `INSUFFICIENT_EVIDENCE`;
9. irrelevant workspace produces `NOT_APPLICABLE`;
10. confirmed callback defect produces deterministic `FAIL`;
11. corrected implementation produces deterministic `PASS`;
12. no target-workspace write occurs;
13. explanation cites only evidence referenced by the verdict.

## Phase 14 - Minimal read-only invocation surface

Status: complete on `feat/guard-inspector-vertical-slice`.

### Implemented surface

```text
POST /guard-inspector/callback
```

### Completed behavior

- accepts required `workspace_root`;
- accepts optional `workspace_id`, `reason`, and bounded `max_results`;
- invokes `CallbackVerticalSlice`, not a caller-selected arbitrary guard;
- remains local-only and read-only;
- preserves exact workspace resolution;
- returns request, authorization, decision, explanation, fingerprint, and workspace-unchanged fields;
- maps invalid input and governance failures to structured errors;
- rejects unknown fields, including caller-controlled `pack_id` and `rule_id`;
- preserves `/search` and `/inspect` as separate retrieval utilities;
- does not add mutation, repair, or unrestricted planning.

### Phase 14 proof

`tests/test_callback_http_endpoint.py` proves:

1. `PASS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE` remain reachable;
2. missing and malformed input is rejected;
3. `max_results` is bounded and validated;
4. outside-root workspaces are rejected;
5. arbitrary guard selection fields are rejected;
6. read-only authorization remains explicit;
7. target workspace mutation remains prohibited;
8. the endpoint returns the complete existing vertical-slice contract.

### Validation record

Validated at `163e5319ea5797387d5470fa3dfcec8897b72238`:

- focused Phase 13/14 and runner suite: `45 passed`;
- full repository suite: `176 passed`;
- `git diff --check`: passed;
- working tree: clean;
- branch synchronized with origin.

## Phase 15 - Runtime-neutral invocation adapter contract

### Objective

Define one small adapter boundary that allows an external runtime to invoke the proven callback endpoint without embedding Guard Inspector logic into that runtime and without binding the product to a fixed application, path, workspace, port, or transport configuration.

### Required behavior

- adapter accepts a configurable endpoint or in-process callable;
- adapter accepts the same narrow callback request contract;
- adapter returns the endpoint response without reinterpreting the verdict;
- adapter preserves request IDs, authorization, evidence refs, validation refs, fingerprint, and structured errors;
- adapter does not select arbitrary guards;
- adapter does not mutate the workspace;
- adapter does not retry unsafe or governance-rejected requests automatically;
- adapter exposes bounded timeout and cancellation controls;
- tests use temporary/local transports rather than fixed ports;
- no runtime-specific UI or vendor integration is added in this phase.

### Phase 15 exit criteria

- one transport-neutral adapter interface exists;
- in-process and local HTTP invocation can be tested through the same contract;
- response fields are preserved exactly;
- structured endpoint failures remain structured;
- cancellation and timeout behavior are deterministic;
- no hardcoded port, workspace path, runtime, or vendor dependency exists;
- full suite and `git diff --check` pass;
- working tree remains clean.

## Deferred work

- broad autonomous repair;
- unrestricted planning;
- passive corpus learning;
- cross-project truth sharing;
- cloud synchronization;
- automatic global-rule creation;
- broad guard-gallery expansion before the adapter boundary is proven;
- complete UI beyond the minimum read-only proof surface;
- runtime-specific integration with Cline, Brew, Browser Dev, or another external runtime;
- release packaging.

## Immediate next task

1. review PR `#3` branch and CI state;
2. do not merge without explicit authorization;
3. implement Phase 15 as a runtime-neutral, configurable adapter contract on a separate branch after Phase 13/14 integration is accepted.
