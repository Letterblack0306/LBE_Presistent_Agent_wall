# Implementation Plan

Updated: 2026-07-28

## Goal

Build a deterministic, read-only-first Guard Inspector runtime with two explicit truth layers:

1. validated project-scoped memory for safe continuity across sessions;
2. a complete live Module Registry for runtime inventory, load state, activity, dependencies, instances, and failures.

After those foundations are operational, add a bounded Authority Ownership Inspector that evaluates one authoritative operation at a time without becoming a coding agent, mutation engine, or model-authored verdict system.

## Non-negotiable invariants

- Live target workspace and passing current validation outrank stored memory and indexed reference knowledge.
- Session history and compaction are historical context, not workspace truth.
- Every production module must be declared.
- Every loaded module must emit a runtime receipt.
- Every running module must report current activity.
- Every declared dependency must reference another registered module.
- Registered-but-not-loaded modules remain visible.
- Loaded-but-unregistered modules are blocking defects.
- The registry provides the runtime map; source inspection verifies or investigates that map.
- Source inspection is not removed. It is narrowed to missing, contradictory, ownership-sensitive, or implementation-specific evidence.
- The Authority Ownership Inspector remains read-only and cannot issue ordinary PASS/FAIL until explicitly authorized by a later implementation gate.

## Current baseline

Implemented and validated:

- SQLite-backed project-scoped memory;
- typed records, provenance, authority, and validation state;
- deterministic claim promotion;
- compaction checkpoint provenance;
- source-hash invalidation and supersession;
- rehydrated context packets;
- runtime-neutral `SessionMemoryAdapter`;
- 14 targeted memory/adapter tests passed;
- 67 full-suite tests passed at commit `c79b8968a1da704c17d0052c0e6e51cb90de5829`.

Documented but not implemented:

- live Module Registry;
- Module Watcher;
- production lifecycle receipts;
- registry UI or query endpoint;
- executable Authority Ownership Inspector;
- runtime-specific session integration.

## Phase 1 — Module Registry contract and types

### Deliverables

- canonical module declaration model;
- allowed module types;
- lifecycle receipt models;
- module state enum;
- defect enum;
- explicit active runtime profile input;
- singleton/multi-instance declaration field;
- bounded activity-history model.

### Required declaration fields

- `id`;
- `path`;
- `type`;
- `purpose`;
- `provides`;
- `dependsOn`;
- `loadedBy`;
- `expectedProfiles`.

### Required lifecycle events

- `registered`;
- `loaded`;
- `started`;
- `activity`;
- `stopped`;
- `failed`.

### Exit criteria

- invalid declarations are rejected deterministically;
- duplicate module IDs are rejected;
- unknown states and malformed receipts are rejected;
- schema/type tests pass.

## Phase 2 — Registry store and state derivation

### Deliverables

- in-memory registry store;
- declaration lookup;
- live record lookup;
- list/filter by state, type, profile, capability, loader, and dependency;
- deterministic state derivation;
- bounded recent activity;
- last-error retention;
- instance tracking.

### Required states

- `REGISTERED`;
- `NOT_LOADED`;
- `LOADED`;
- `RUNNING`;
- `IDLE`;
- `BLOCKED`;
- `FAILED`;
- `STOPPED`;
- `DISABLED`.

### Exit criteria

- the same declarations and receipt sequence produce the same live records;
- timestamps and activity ordering are deterministic under injected clocks;
- state-transition tests pass.

## Phase 3 — Registry validation and defects

### Deliverables

Structured defects for:

- `MODULE_UNREGISTERED`;
- `REGISTERED_NOT_LOADED`;
- `EXPECTED_MODULE_NOT_LOADED`;
- `MODULE_DEPENDENCY_UNREGISTERED`;
- `MODULE_INSTANCE_CONFLICT`;
- disabled module loaded;
- receipt for unknown module;
- invalid loader relationship;
- contradictory lifecycle state.

### Exit criteria

- every defect has minimum deterministic evidence;
- registered-but-not-loaded remains visible without always becoming blocking;
- expected-profile and disabled-state behavior is tested;
- dependency and singleton tests pass.

## Phase 4 — Module Watcher

### Deliverables

- watcher subscription API;
- callbacks for registration and every lifecycle event;
- immutable event payloads;
- bounded event history;
- subscriber isolation so one failing watcher cannot corrupt registry state;
- registry and watcher self-registration.

### Exit criteria

- watcher sees events in deterministic order;
- failed subscribers are surfaced without losing registry truth;
- watcher tests pass.

## Phase 5 — Minimal real runtime slice

Choose one small runtime path, not the entire workspace.

Recommended initial slice:

- `app.launcher`;
- `agent.http-server`;
- `agent.service`;
- `browser.chat-bridge`;
- `browser.loop-controller`;
- `module.registry`;
- `module.watcher`.

### Deliverables

- static declarations for selected modules;
- load receipts during startup;
- started/activity/stopped/failed receipts at real lifecycle boundaries;
- explicit loader and dependency relationships;
- one read-only registry query surface.

### Exit criteria

- startup shows declared versus loaded state;
- Start Loop activity chain is visible without source reconstruction;
- missing and unexpected modules produce structured defects;
- no broad runtime-wide instrumentation is attempted yet.

## Phase 6 — Registry-first inspection behavior

### Deliverables

An inspection policy that requires:

1. read registry declarations;
2. read watcher/lifecycle receipts;
3. compare declaration and runtime state;
4. report registry defects and missing evidence;
5. inspect source only when registry evidence is absent, contradictory, incomplete, ownership-sensitive, or exact implementation evidence is required.

### Required proof cases

- answer what modules exist without import search;
- answer what loaded without constructor tracing;
- answer current activity from receipts;
- distinguish two related modules by ID and purpose;
- fall back to bounded source inspection when a module is unregistered;
- detect a false or stale declaration through current source/runtime evidence.

### Exit criteria

- registry-first behavior is covered by tests;
- source inspection remains available as verification/fallback;
- broad random-file reconstruction is not the default path.

## Phase 7 — Authority ownership declaration contract

Do not implement the inspector yet.

### Deliverables

For one explicit authoritative operation, define:

- operation ID and canonical target;
- declared authoritative owner;
- delegates;
- observers;
- subscribers;
- projections;
- canonical state location;
- allowed mutation capabilities;
- persistence contract;
- runtime confirmation requirement;
- applicability and evidence requirements.

### Exit criteria

- one operation per inspection is enforced;
- duplicate storage is not automatically duplicate authority;
- owner/delegate/observer roles are unambiguous;
- unresolved contradictions require insufficient evidence.

## Phase 8 — Authority ownership schemas

### Deliverables

- authority ownership request schema;
- 10-section evidence-package schema;
- ownership result schema;
- role and finding enums;
- evidence-reference requirements;
- `pass_fail_authorized: false` requirement.

### Required findings

- `SINGLE_OWNER_CONFIRMED`;
- `DUPLICATE_AUTHORITY`;
- `UNDECLARED_AUTHORITY`;
- `OWNER_CONTRACT_BROKEN`;
- `STALE_OWNER_RECORD`;
- `INSUFFICIENT_EVIDENCE`;
- `NOT_APPLICABLE`.

### Exit criteria

- each finding has deterministic minimum evidence;
- malformed or incomplete packages fail schema validation;
- no finding can be emitted without required evidence references.

## Phase 9 — Read-only Authority Ownership Inspector

### Inspection sequence

1. resolve the exact target workspace;
2. identify one authoritative operation;
3. read Module Registry declarations and runtime participants;
4. identify canonical state and persistence targets;
5. inspect owner declarations;
6. inspect bounded mutation sites;
7. inspect bounded call paths;
8. inspect persistence paths;
9. classify relationships;
10. obtain runtime confirmation only where required and safe;
11. record contradictions and missing evidence;
12. apply deterministic finding rules;
13. emit a structured result without workspace mutation.

### Exit criteria

- all seven findings have tests;
- duplicate store versus duplicate authority is tested;
- unresolved contradictions produce `INSUFFICIENT_EVIDENCE`;
- indexed reference knowledge cannot prove a current defect;
- no workspace writes occur.

## Phase 10 — Runtime confirmation adapter

### Deliverables

- safe read-only runtime observation interface;
- exact operation and module identity in receipts;
- bounded observation window;
- no mutation or hidden activation;
- evidence timestamps and provenance;
- explicit unavailable/unsafe result.

### Exit criteria

- lifecycle ownership and active persistence can be confirmed when safely observable;
- unavailable runtime observation does not become a guessed finding;
- observation tests pass.

## Phase 11 — Session memory runtime wiring

### Deliverables

At one bounded runtime bridge:

- initialize `WorkspaceMemoryStore`;
- initialize `SessionMemoryAdapter`;
- ingest deterministic command/tool results;
- persist compaction checkpoints;
- rehydrate context at session start/resume;
- mark changed source-backed claims stale;
- preserve active constraints;
- keep registry receipts and memory evidence separate but correlated by workspace/session/task IDs.

### Exit criteria

- no model conclusion is promoted directly;
- current Git and source override stale memory;
- compaction summaries remain historical;
- runtime wiring tests pass.

## Phase 12 — End-to-end proof

### Scenario

1. start a session in a verified project;
2. register and load the minimal runtime slice;
3. emit current activity receipts;
4. validate and store one workspace fact;
5. record one command failure and one active constraint;
6. compact the session;
7. change a source-backed fact outside the session;
8. restart and resume;
9. rehydrate context;
10. verify stale-memory invalidation;
11. verify active constraint retention;
12. verify registry startup and activity visibility;
13. inspect one authoritative operation;
14. confirm source inspection is bounded to relevant participants and mutation/persistence paths;
15. confirm no ordinary PASS/FAIL is produced by the ownership inspector.

### Completion criteria

- deterministic repeatability;
- clean test suite;
- no untracked generated evidence committed;
- exact implementation and rollback documentation;
- PR review confirms boundaries;
- merge only after all proof requirements pass.

## Deferred work

- broad autonomous repair;
- model-generated verdicts;
- automatic global-rule creation;
- unrestricted planning;
- passive corpus learning;
- cross-project truth sharing;
- cloud synchronization;
- authority policy embedded into the basic registry;
- complete UI beyond the minimum read-only registry view;
- expansion to every production module before the minimal slice is proven.

## Immediate next task

Implement **Phase 1 through Phase 3 only** on a dedicated branch or the existing draft branch:

- declaration and receipt types;
- registry store;
- deterministic state derivation;
- structured registry defects;
- focused tests.

Do not wire the full runtime, build the UI, or implement Authority Ownership in the same patch.
