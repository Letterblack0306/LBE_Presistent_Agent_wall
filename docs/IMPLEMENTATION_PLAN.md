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

Validated at commit `91742f5c02f1b0c911ad0f787397e335c48ba0f8`:

- Phase 12 proof: `1 passed`;
- full repository suite: `144 passed`;
- `git diff --check`: passed;
- working tree: clean;
- untracked generated evidence: none.

## Phase 13 - First complete Guard Inspector vertical slice

### Recommended problem

```text
Provided callback is not a function
```

### Objective

Prove the complete read-only product pipeline for one real problem and one registered deterministic guard.

### Required sequence

```text
user problem
-> exact workspace resolution
-> reference retrieval
-> bounded current-workspace inspection
-> evidence package
-> registered guard selection
-> deterministic guard execution
-> LBE governance
-> required validation
-> structured verdict
-> explanation
```

### Deliverables

- one request model for the callback problem;
- deterministic target-workspace resolution;
- reference retrieval scoped independently from workspace inspection;
- duplicate-filename-safe candidate selection;
- evidence records containing:
  - configured root;
  - project root;
  - relative path;
  - file hash;
  - line range;
  - bounded snippet;
  - source class;
  - retrieval provenance;
- one registered callback guard;
- deterministic guard input and output contracts;
- LBE authorization envelope;
- required narrow validation;
- structured verdict contract;
- human-readable explanation generated only from structured evidence and verdict;
- rollback documentation;
- focused and end-to-end tests.

### Verdicts

- `PASS`;
- `FAIL`;
- `INSUFFICIENT_EVIDENCE`;
- `NOT_APPLICABLE`.

### Required proof cases

1. correct target workspace is selected;
2. reference and workspace evidence are never conflated;
3. duplicate filenames do not cause wrong-file inspection;
4. indexed reference evidence cannot prove a current defect;
5. source inspection is bounded to relevant candidates;
6. the selected guard is registered and applicable;
7. identical input and workspace state produce identical guard results;
8. missing evidence produces `INSUFFICIENT_EVIDENCE`;
9. irrelevant workspace produces `NOT_APPLICABLE`;
10. confirmed callback defect produces deterministic `FAIL`;
11. corrected implementation produces deterministic `PASS`;
12. no target-workspace write occurs;
13. explanation cites only evidence referenced by the verdict.

### Exit criteria

- all four verdicts are covered by deterministic tests;
- evidence paths, hashes, snippets, and line ranges are reproducible;
- target and reference scopes are explicit in every record;
- LBE authorization is present for verdict production;
- required validation executes and is recorded;
- no model-generated verdict path exists;
- no workspace mutation occurs;
- complete end-to-end vertical-slice test passes;
- full repository suite passes;
- `git diff --check` passes;
- working tree remains clean.

## Deferred work

- broad autonomous repair;
- unrestricted planning;
- passive corpus learning;
- cross-project truth sharing;
- cloud synchronization;
- automatic global-rule creation;
- expansion to every guard before the first vertical slice is proven;
- complete UI beyond the minimum read-only proof surface;
- production integration with every external agent runtime;
- release packaging.

## Immediate next task

1. update and validate the completed foundation documentation;
2. merge PR `#2` after the validated head and review boundary are confirmed;
3. create a dedicated Phase 13 branch from updated `main`;
4. implement the callback-error vertical slice without broadening scope.
