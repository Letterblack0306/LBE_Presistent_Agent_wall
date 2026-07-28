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

Status: complete and merged through PR `#5` at `575283ab986abc723de226c0340ec88c81ea2a10`.

Implemented:

- stable `profile_id` and `version`;
- named `transport_factory` resolved through an externally supplied factory registry;
- externally supplied `transport_config`;
- explicit `request_mapping` into the narrow callback request fields only;
- explicit capability declarations;
- required `callback_inspection` capability;
- deterministic rejection of arbitrary guard selection, workspace mutation, and repair execution;
- bounded timeout configuration;
- explicit cancellation support declaration;
- deterministic validation of unknown, missing, malformed, and contradictory fields;
- unchanged adapter response propagation;
- no direct vendor-specific integration.

Validation:

- focused Phase 16 suite: `16 passed`;
- full repository suite: `205 passed`;
- `git diff --check`: passed.

## Phase 17 - Profile-driven end-to-end invocation proof

Status: complete on `feat/profile-driven-end-to-end-proof`.

### Proven path

```text
generic runtime input
-> validated RuntimeIntegrationProfile
-> externally supplied transport factory
-> mapped callback request
-> RuntimeNeutralInvocationAdapter
-> fixed CallbackVerticalSlice
-> unchanged structured result or structured error
```

### Proven behavior

`tests/test_profile_driven_end_to_end.py` proves:

1. one complete in-process profile path reaches the real callback vertical slice;
2. one complete temporary local HTTP profile path reaches the same fixed callback endpoint;
3. `PASS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE` remain unchanged;
4. request data, authorization, evidence refs, validation refs, explanation, fingerprint, and `workspace_unchanged` remain intact;
5. unknown runtime input is rejected before invocation;
6. missing factory registration remains a structured profile failure;
7. endpoint rejection remains a structured adapter failure;
8. timeout and cancellation are deterministic;
9. no automatic retry occurs;
10. temporary workspaces and temporary ports avoid hardcoded assumptions;
11. target workspace state remains unchanged;
12. no vendor-specific package, UI, repair, mutation, or arbitrary guard-selection path is added.

### Validation record

Validated at `a0c77934dfc61240f6e59f2a63dbcc64cf4a1c12`:

- focused Phase 17 suite: `10 passed`;
- full repository suite: `215 passed`;
- `git diff --check`: passed;
- working tree: clean;
- branch synchronized with origin.

### Phase 17 exit criteria

- complete in-process profile proof: complete;
- complete temporary HTTP profile proof: complete;
- all four verdicts preserved exactly: complete;
- structured failures preserved: complete;
- timeout and cancellation deterministic: complete;
- no fixed port, path, workspace, runtime, company, product, or vendor dependency: complete;
- full suite and `git diff --check` pass: complete;
- working tree remains clean: complete.

## Phase 18 - Second deterministic guard vertical slice

### Objective

Expand the guard gallery by exactly one additional project-scoped problem while preserving every boundary proven by the callback slice and profile-driven invocation path.

### Selection requirements

- select one problem from `docs/PRIORITY_MODULE_REGISTRY.md` or another already registered priority source;
- prefer a problem with deterministic source evidence and narrow validation;
- define one fixed pack and one fixed rule identity;
- avoid broad autonomous repair, unrestricted planning, or model-authored verdicts;
- keep reference evidence separate from current workspace evidence;
- require exact configured workspace resolution;
- keep inspection bounded and read-only;
- reuse the existing evidence package, GuardRunner, LBE authorization, validation, explanation, adapter, and profile boundaries where compatible;
- add a dedicated endpoint or invocation request only if the second problem requires a distinct narrow contract;
- do not generalize into arbitrary caller-selected guard execution.

### Phase 18 exit criteria

- one second problem and fixed deterministic rule are selected and documented;
- the rule is registered and executable through a bounded vertical slice;
- `PASS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE` semantics are explicit where applicable;
- current workspace evidence and validation evidence are cited exactly;
- indexed reference evidence cannot prove a current defect;
- no workspace mutation occurs;
- existing callback behavior remains unchanged;
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
- complete UI beyond the minimum read-only proof surface;
- direct vendor-specific integrations inside the core package;
- release packaging before at least one additional deterministic guard path is proven.

## Immediate next task

1. open and review the Phase 17 pull request;
2. validate branch mergeability and repository checks;
3. merge only after the Phase 17 proof boundary is accepted;
4. create a separate Phase 18 branch from updated `main`;
5. inspect the priority module registry and select exactly one second deterministic guard problem before implementation.
