# Implementation Plan

Updated: 2026-07-28

## Goal

Build a deterministic, read-only-first Guard Inspector that diagnoses concrete workspace problems through this authority chain:

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
- Registry evidence is read before broad source reconstruction.
- Source inspection remains available when registry evidence is missing, contradictory, stale, ownership-sensitive, or insufficiently exact.
- Ordinary verdicts come only from deterministic guard execution plus required validation and LBE authorization.
- Invocation boundaries remain configurable and do not hardcode a runtime, workspace, path, port, application, company, vendor, environment, or transport.
- Runtime integrations may map capabilities and configuration, but must not reimplement or reinterpret Guard Inspector decisions.
- Runtime profiles cannot add arbitrary guard selection, mutation, or repair authority.

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

Problem:

```text
Provided callback is not a function
```

Completed sequence:

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

## Phase 14 - Minimal read-only invocation surface

Status: complete and merged through PR `#3`.

Implemented surface:

```text
POST /guard-inspector/callback
```

The endpoint accepts only the narrow callback request, invokes `CallbackVerticalSlice`, remains local-only and read-only, preserves exact workspace resolution, and rejects arbitrary pack or rule selection.

Phases 13 and 14 were merged at `0376f52093d079a5911b8c8b164492373e386046`.

## Phase 15 - Runtime-neutral invocation adapter

Status: complete and merged through PR `#4` at `25ea2560dbd9d440f3caf3be9f9c3b286aed1f5d`.

Implemented:

- one transport-neutral invocation protocol;
- configurable in-process callable transport;
- configurable local HTTP transport;
- unchanged response propagation;
- structured endpoint and transport errors;
- bounded timeout and cancellation;
- no automatic retry;
- no fixed runtime, vendor, workspace, path, endpoint, or port.

Validation:

- focused Phase 15 suite: `13 passed`;
- full repository suite: `189 passed`;
- `git diff --check`: passed.

## Phase 16 - Configurable runtime integration profile contract

Status: complete on `feat/configurable-runtime-integration-profile`.

### Objective

Allow different external runtimes to use the Phase 15 adapter through configuration and capability mapping without modifying adapter core and without hardcoded product, company, workspace, path, port, vendor, environment, or application assumptions.

### Implemented contract

- stable `profile_id` and `version`;
- named `transport_factory` resolved through an externally supplied factory registry;
- externally supplied `transport_config`;
- explicit `request_mapping` into the narrow callback request fields only;
- explicit capability declarations;
- required `callback_inspection` capability;
- deterministic rejection of forbidden capabilities:
  - `arbitrary_guard_selection`;
  - `workspace_mutation`;
  - `repair_execution`;
- bounded timeout configuration;
- explicit cancellation support declaration;
- deterministic validation of unknown, missing, malformed, and contradictory fields;
- unchanged adapter response propagation;
- no direct vendor-specific integration.

### Proven behavior

`tests/test_runtime_integration_profile.py` proves:

1. valid profiles construct adapters through registered factories;
2. runtime input maps only into `workspace_root`, `workspace_id`, `reason`, and `max_results`;
3. unknown profile and runtime fields are rejected;
4. missing factory registrations fail structurally;
5. forbidden and contradictory capabilities fail deterministically;
6. timeout bounds are enforced;
7. cancellation support is enforced;
8. invalid factory results fail deterministically;
9. adapter outputs remain unchanged;
10. generic sample runtimes need no product-specific code.

### Validation record

Validated at `a7e1b0d8812e3f9ec6998311e9df7233dac140ff`:

- focused Phase 16 suite: `16 passed`;
- full repository suite: `205 passed`;
- `git diff --check`: passed;
- working tree: clean;
- branch synchronized with origin.

### Phase 16 exit criteria

- generic typed profile contract exists: complete;
- transport creation is configurable and environment-derived: complete;
- input mapping is restricted to the callback request contract: complete;
- unsupported capabilities are explicit: complete;
- unknown and contradictory fields fail deterministically: complete;
- adapter outputs remain unchanged: complete;
- no hardcoded runtime, workspace, path, port, application, company, vendor, or environment assumptions exist: complete;
- focused and full suites pass: complete;
- `git diff --check` passes: complete;
- working tree remains clean: complete.

## Phase 17 - Profile-driven end-to-end invocation proof

### Objective

Prove the full generic runtime path without adding vendor-specific integration code:

```text
generic runtime input
-> validated RuntimeIntegrationProfile
-> externally supplied transport factory
-> mapped callback request
-> RuntimeNeutralInvocationAdapter
-> fixed CallbackVerticalSlice
-> unchanged structured result or structured error
```

### Required behavior

- use at least one in-process profile and one temporary local HTTP profile;
- use temporary workspaces and temporary ports only;
- prove `PASS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE` remain unchanged through the full profile path;
- preserve request IDs, authorization, evidence refs, validation refs, explanation, fingerprint, and `workspace_unchanged`;
- prove unknown runtime input is rejected before invocation;
- prove missing factory, endpoint rejection, timeout, and cancellation remain structured;
- prove no automatic retry occurs;
- prove no target workspace mutation occurs;
- do not add vendor-specific packages, UI, repair, mutation, or arbitrary guard selection.

### Phase 17 exit criteria

- one complete in-process profile proof exists;
- one complete temporary HTTP profile proof exists;
- all four verdicts are preserved exactly;
- structured failures are preserved;
- timeout and cancellation are deterministic;
- no fixed port, path, workspace, runtime, company, product, or vendor dependency exists;
- full suite and `git diff --check` pass;
- working tree remains clean.

## Deferred work

- broad autonomous repair;
- unrestricted planning;
- passive corpus learning;
- cross-project truth sharing;
- cloud synchronization;
- automatic global-rule creation;
- broad guard-gallery expansion before the profile path is proven end to end;
- complete UI beyond the minimum read-only proof surface;
- direct vendor-specific integrations inside the core package;
- release packaging.

## Immediate next task

1. open and review the Phase 16 pull request;
2. validate branch mergeability and repository checks;
3. merge only after the Phase 16 boundary is accepted;
4. create a separate Phase 17 branch from updated `main`;
5. implement the generic profile-driven end-to-end invocation proof without vendor-specific or hardcoded assumptions.
