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

The model may select guards, form hypotheses, and explain results. It must not invent or reinterpret the verdict.

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
- Invocation boundaries remain configurable and do not hardcode a runtime, workspace, path, port, application, vendor, or transport.
- Runtime integrations may map capabilities and configuration, but must not reimplement or reinterpret Guard Inspector decisions.

## Completed foundation: Phases 1-12

Completed foundation includes:

- Module Registry contracts, lifecycle receipts, state derivation, validation, and Module Watcher;
- minimal registered runtime slice and read-only `/module-registry` surface;
- registry-first inspection with bounded source fallback;
- Authority Ownership declaration, schemas, deterministic inspector, and read-only enforcement;
- runtime confirmation without hidden activation;
- validated workspace memory and session-memory runtime wiring;
- complete Phase 12 end-to-end proof.

Foundation was merged in PR `#2` at `7f212f406331dfaf7961143eefbf45f8ceaf6a17`.

## Phase 13 - First complete Guard Inspector vertical slice

Status: complete and merged through PR `#3`.

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

## Phase 14 - Minimal read-only invocation surface

Status: complete and merged through PR `#3`.

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

Phases 13 and 14 were merged at `0376f52093d079a5911b8c8b164492373e386046`.

## Phase 15 - Runtime-neutral invocation adapter contract

Status: complete on `feat/runtime-neutral-invocation-adapter`.

### Objective

Allow an external runtime to invoke the proven callback inspection without embedding Guard Inspector logic and without binding the product to a fixed application, path, workspace, port, vendor, or transport configuration.

### Implemented contract

- `InvocationTransport` protocol with one narrow `invoke` method;
- `CallbackInvocationAdapter` using the callback request contract;
- configurable `InProcessTransport` accepting a supplied callable;
- configurable `LocalHttpTransport` accepting a supplied local endpoint;
- explicit `CancellationSignal` protocol and `CancellationToken` implementation;
- bounded positive timeout validation;
- stable `InvocationAdapterError` with structured code, message, details, and retryability;
- exact response preservation without verdict reinterpretation;
- no caller-controlled guard selection;
- no workspace mutation;
- no automatic retries;
- no fixed port, endpoint, path, workspace, runtime, or vendor dependency.

### Proven behavior

`tests/test_invocation_adapter.py` proves:

1. in-process and local HTTP transports use the same adapter contract;
2. complete successful responses are preserved exactly;
3. request IDs, authorization, evidence refs, validation refs, fingerprints, and nested structures are not rewritten;
4. endpoint failures remain structured;
5. malformed and non-object responses are rejected deterministically;
6. arbitrary request fields and guard-selection identifiers are rejected;
7. timeout behavior is deterministic;
8. cancellation before or during waiting is deterministic;
9. temporary local HTTP servers avoid fixed ports;
10. transport failures are not retried automatically.

### Validation record

Validated at `8120fed0b0827384c3e248b96334c4ab7cb4fd4a`:

- focused Phase 15 suite: `13 passed`;
- full repository suite: `189 passed`;
- `git diff --check`: passed;
- working tree: clean;
- branch synchronized with origin.

### Phase 15 exit criteria

- one transport-neutral adapter interface exists: complete;
- in-process and local HTTP invocation use the same contract: complete;
- response fields are preserved exactly: complete;
- structured endpoint failures remain structured: complete;
- cancellation and timeout behavior are deterministic: complete;
- no hardcoded port, workspace path, runtime, application, or vendor dependency exists: complete;
- full suite and `git diff --check` pass: complete;
- working tree remains clean: complete.

## Phase 16 - Configurable runtime integration profile contract

### Objective

Define a small configuration and capability-mapping contract that allows different external runtimes to use the Phase 15 adapter without modifying the adapter core and without creating hardcoded integrations for a particular product, company, workspace, path, port, or environment.

### Required behavior

- profile has a stable identifier and version;
- profile selects a configured transport factory rather than a fixed transport instance;
- profile supplies endpoint or in-process callable configuration externally;
- profile maps runtime input into the existing narrow callback request fields only;
- profile declares supported capabilities and unavailable capabilities explicitly;
- profile preserves the adapter response without verdict reinterpretation;
- profile does not select arbitrary guards;
- profile does not add mutation or repair authority;
- profile exposes timeout and cancellation configuration within adapter bounds;
- profile validates missing, unknown, and contradictory configuration deterministically;
- tests use generic sample runtimes and temporary endpoints rather than vendor-specific implementations.

### Recommended contract shape

```text
runtime input
-> validated integration profile
-> callback request mapping
-> CallbackInvocationAdapter
-> unchanged structured result or structured adapter error
```

The core profile contract should remain generic. Optional vendor- or application-specific packages may be added later as separate adapters only after the generic profile boundary is proven.

### Phase 16 exit criteria

- generic profile schema or typed contract exists;
- transport creation is configurable and environment-derived;
- input mapping is restricted to the callback request contract;
- unsupported capabilities are explicit;
- unknown and contradictory profile fields fail deterministically;
- adapter outputs remain unchanged;
- no hardcoded runtime, workspace, path, port, application, company, or vendor assumptions exist;
- focused and full suites pass;
- `git diff --check` passes;
- working tree remains clean.

## Deferred work

- broad autonomous repair;
- unrestricted planning;
- passive corpus learning;
- cross-project truth sharing;
- cloud synchronization;
- automatic global-rule creation;
- broad guard-gallery expansion before the integration profile boundary is proven;
- complete UI beyond the minimum read-only proof surface;
- direct vendor-specific integrations inside the core package;
- release packaging.

## Immediate next task

1. open and review the Phase 15 pull request;
2. validate branch mergeability and any repository checks;
3. merge only after the Phase 15 boundary is accepted;
4. create a separate Phase 16 branch from the updated `main`;
5. implement the generic configurable runtime integration profile contract without vendor-specific or hardcoded assumptions.
