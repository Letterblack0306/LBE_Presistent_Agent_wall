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

Status: complete and merged through PR `#6` at `f41dd154a7450f30b92c05c358220606f5da95fa`.

Proven path:

```text
generic runtime input
-> validated RuntimeIntegrationProfile
-> externally supplied transport factory
-> mapped callback request
-> RuntimeNeutralInvocationAdapter
-> fixed CallbackVerticalSlice
-> unchanged structured result or structured error
```

Validation:

- focused Phase 17 suite: `10 passed`;
- full repository suite: `215 passed`;
- `git diff --check`: passed.

## Phase 18 - Second deterministic guard vertical slice

Status: complete on `feat/second-deterministic-guard-slice`.

### Selected problem

```text
Loaded module receipt has no matching declaration
```

The problem comes directly from `docs/PRIORITY_MODULE_REGISTRY.md`: loaded modules absent from the canonical declaration inventory are blocking defects.

### Fixed identities

- pack: `module_registry`;
- rule: `module_registry.loaded_module_registration`;
- vertical slice: `ModuleRegistryVerticalSlice`;
- current workspace artifact: `.lbe/module-registry.json`.

### Implemented path

```text
fixed module-registry request
-> exact configured workspace resolution
-> current canonical registry artifact inspection
-> bounded declaration and lifecycle-receipt parsing
-> loaded-module/declaration comparison
-> registered deterministic rule execution
-> GuardRunner evidence scoping
-> independent validation re-read
-> LBE authorization
-> structured verdict and evidence-only explanation
```

### Deterministic verdict semantics

- `FAIL`: at least one loaded receipt names a module absent from declarations;
- `PASS`: loaded receipts exist and every loaded module is declared;
- `INSUFFICIENT_EVIDENCE`: the registry exists but contains no loaded receipts or cannot establish runtime load state;
- `NOT_APPLICABLE`: the exact configured workspace has no canonical registry artifact.

### Boundaries preserved

- exact configured workspace only;
- current workspace evidence is authoritative;
- indexed reference evidence cannot prove a current defect;
- registry parsing is bounded by declaration and receipt limits;
- inspection is read-only and workspace fingerprints must remain unchanged;
- one fixed pack and rule are selected internally;
- no caller-controlled arbitrary guard selection;
- no repair, mutation, retry, vendor package, or model-authored verdict;
- callback rule evidence scoping remains compatible.

### Validation record

Validated at `a32ea872d8ffe4f5c68ee7e49c8fdfaef583f0fb`:

- focused Phase 18 suite: `11 passed`;
- full repository suite: `226 passed`;
- `git diff --check`: passed;
- working tree: clean;
- branch synchronized with origin.

### Phase 18 exit criteria

- second problem and fixed deterministic identities documented: complete;
- rule registered and executable through a bounded vertical slice: complete;
- all four verdict semantics explicit: complete;
- current workspace and validation evidence cited exactly: complete;
- indexed reference evidence cannot prove a current defect: complete;
- no workspace mutation: complete;
- callback behavior unchanged: complete;
- focused and full suites pass: complete;
- `git diff --check` passes: complete;
- working tree remains clean: complete.

## Phase 19 - Profile-driven invocation proof for the second guard

### Objective

Expose `ModuleRegistryVerticalSlice` through the same runtime-neutral architecture without turning the profile contract into arbitrary guard execution.

Required path:

```text
generic runtime input
-> validated fixed module-registry profile capability
-> externally supplied transport factory
-> narrow module-registry request mapping
-> RuntimeNeutralInvocationAdapter
-> fixed ModuleRegistryVerticalSlice
-> unchanged structured result or structured error
```

### Required behavior

- preserve the existing callback profile contract and callback tests;
- introduce an explicit fixed `module_registry_inspection` capability rather than caller-selected pack or rule IDs;
- map only `workspace_root`, `workspace_id`, `reason`, and `max_results`;
- prove one in-process and one temporary local HTTP path;
- preserve `PASS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE` exactly;
- preserve authorization, evidence refs, validation refs, explanation, fingerprint, and `workspace_unchanged`;
- preserve structured missing-factory, endpoint, timeout, and cancellation errors;
- prohibit retries, mutation, repair, and arbitrary guard selection;
- use temporary workspaces and ephemeral ports only;
- keep callback and module-registry profiles independently explicit.

### Phase 19 exit criteria

- fixed module-registry profile capability exists without arbitrary selection;
- in-process and temporary HTTP proofs pass;
- all four verdicts remain unchanged;
- callback profile behavior remains unchanged;
- structured failures remain deterministic;
- no workspace mutation or retry occurs;
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
- release packaging until the second guard invocation boundary is proven.

## Immediate next task

1. open and review the Phase 18 pull request;
2. verify mergeability and repository checks;
3. merge only after the fixed module-registry boundary is accepted;
4. create a separate Phase 19 branch from updated `main`;
5. extend the profile contract narrowly for the fixed module-registry capability and prove both transport paths.
