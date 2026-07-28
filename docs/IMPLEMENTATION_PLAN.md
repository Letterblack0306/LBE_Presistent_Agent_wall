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

### Validation record

Validated at implementation head `c1b2877869b44db0030d0258c3ec97c53b2cc4e9`:

- focused Phase 13 and runner suite: `29 passed`;
- full repository suite: `160 passed`;
- `git diff --check`: passed;
- working tree: clean;
- branch synchronized with origin.

## Phase 14 - Minimal read-only invocation surface

### Objective

Expose the completed callback vertical slice through the smallest practical invocation boundary without changing its authority model or broadening it into a generic agent endpoint.

### Required behavior

- accept one explicit `workspace_root` and optional `workspace_id`, `reason`, and bounded `max_results`;
- invoke `CallbackVerticalSlice`, not a caller-selected arbitrary guard;
- remain local-only and read-only;
- preserve exact workspace resolution;
- return the existing request, authorization, decision, explanation, fingerprint, and workspace-unchanged fields;
- map invalid input and governance failures to structured errors;
- add deterministic endpoint or CLI tests;
- do not add mutation, repair, or unrestricted planning.

### Recommended first surface

Add one dedicated local endpoint, for example:

```text
POST /guard-inspector/callback
```

The existing `/search` and `/inspect` endpoints remain retrieval utilities. The callback endpoint should be a narrow product invocation surface rather than a generic arbitrary-rule executor.

### Phase 14 exit criteria

- dedicated read-only invocation path exists;
- all four verdicts remain reachable through deterministic tests;
- invalid and outside-root workspaces are rejected;
- no caller-controlled pack or rule selection is exposed;
- no target workspace mutation occurs;
- full suite and `git diff --check` pass;
- working tree remains clean.

## Deferred work

- broad autonomous repair;
- unrestricted planning;
- passive corpus learning;
- cross-project truth sharing;
- cloud synchronization;
- automatic global-rule creation;
- broad guard-gallery expansion before the invocation surface is proven;
- complete UI beyond the minimum read-only proof surface;
- production integration with every external agent runtime;
- release packaging.

## Immediate next task

Implement and test the minimal dedicated read-only invocation surface for `CallbackVerticalSlice`, then open the Phase 13 pull request for review. Do not merge without explicit authorization.
