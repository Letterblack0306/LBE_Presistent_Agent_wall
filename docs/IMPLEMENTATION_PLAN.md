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
- explicit `request_mapping` into the narrow inspection request fields;
- explicit capability declarations;
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

## Phase 17 - Profile-driven callback invocation proof

Status: complete and merged through PR `#6` at `f41dd154a7450f30b92c05c358220606f5da95fa`.

Proven path:

```text
generic runtime input
-> validated callback RuntimeIntegrationProfile
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

Status: complete and merged through PR `#7` at `7345149b99d09ac34debaf16bd006107510b8095`.

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

### Validation record

- focused Phase 18 suite: `11 passed`;
- full repository suite: `226 passed`;
- `git diff --check`: passed.

## Phase 19 - Profile-driven invocation proof for the second guard

Status: complete on `feat/module-registry-profile-proof`.

### Proven path

```text
generic runtime input
-> validated module_registry_inspection capability
-> externally supplied transport factory
-> narrow module-registry request mapping
-> RuntimeNeutralInvocationAdapter
-> fixed ModuleRegistryVerticalSlice
-> unchanged structured result or structured error
```

### Implemented contract

`RuntimeIntegrationProfile` now accepts exactly one enabled fixed inspection capability:

- `callback_inspection`; or
- `module_registry_inspection`.

Profiles enabling neither or both are rejected deterministically. The profile continues to map only:

- `workspace_root`;
- `workspace_id`;
- `reason`;
- `max_results`.

The following remain prohibited:

- `arbitrary_guard_selection`;
- `workspace_mutation`;
- `repair_execution`.

### Fixed HTTP surface

```text
POST /guard-inspector/module-registry
```

The endpoint accepts the same narrow request field set and invokes only `ModuleRegistryVerticalSlice`. Caller-supplied pack IDs, rule IDs, guard IDs, repair requests, and mutation controls remain invalid.

### Proven behavior

`tests/test_module_registry_profile_end_to_end.py` proves:

1. callback and module-registry profiles remain independently explicit;
2. contradictory capability combinations are rejected;
3. the in-process profile path preserves `PASS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE`;
4. the temporary local HTTP path preserves the complete endpoint result;
5. authorization, evidence refs, validation refs, explanation, decision fingerprint, and workspace immutability remain intact;
6. arbitrary guard-selection fields are rejected;
7. missing factory and endpoint rejection remain structured;
8. timeout and cancellation remain deterministic;
9. transport failures are not retried;
10. temporary workspaces and ephemeral ports avoid fixed environment assumptions;
11. callback profile and callback endpoint behavior remain unchanged.

### Validation record

Validated at `b74f2c14b8f9409cf76b401961b5174e0fd3edf9`:

- focused Phase 19 suite: `54 passed`;
- full repository suite: `238 passed`;
- `git diff --check`: passed;
- working tree: clean;
- branch synchronized with origin.

### Phase 19 exit criteria

- fixed module-registry profile capability exists without arbitrary selection: complete;
- in-process and temporary HTTP proofs pass: complete;
- all four verdicts remain unchanged: complete;
- callback profile behavior remains unchanged: complete;
- structured failures remain deterministic: complete;
- no workspace mutation or retry occurs: complete;
- focused and full suites pass: complete;
- `git diff --check` passes: complete;
- working tree remains clean: complete.

## Phase 20 - Minimum release-readiness boundary

### Objective

Make the proven read-only Guard Inspector distributable and verifiable without expanding product authority.

### Required scope

- define the supported Python and operating-system compatibility matrix from actual CI/runtime evidence;
- define stable public entry points for callback and module-registry inspection;
- document the two fixed profile capabilities and their request/result contracts;
- add packaging metadata and build validation only where missing;
- validate installation into a clean temporary environment;
- validate both in-process and local HTTP smoke paths from the installed package;
- ensure package contents exclude development-only, private, generated, cache, and workspace-specific artifacts;
- preserve local-only HTTP defaults and read-only behavior;
- preserve all deterministic verdict, evidence, authorization, timeout, cancellation, and no-retry semantics;
- avoid release automation that publishes externally without explicit user action.

### Phase 20 exit criteria

- one reproducible package build succeeds from a clean tree;
- one clean-environment installation succeeds;
- both fixed guard slices execute from the installed artifact;
- callback and module-registry profile examples validate;
- public documentation matches actual invocation contracts;
- package-content audit passes;
- focused and full suites pass;
- `git diff --check` passes;
- working tree remains clean;
- no publish action occurs automatically.

## Deferred work

- broad autonomous repair;
- unrestricted planning;
- passive corpus learning;
- cross-project truth sharing;
- cloud synchronization;
- automatic global-rule creation;
- complete UI beyond the minimum read-only proof surface;
- direct vendor-specific integrations inside the core package;
- additional guard gallery expansion until release readiness is established.

## Immediate next task

1. open and review the Phase 19 pull request;
2. verify mergeability and repository checks;
3. merge only after the mutually exclusive fixed-capability boundary is accepted;
4. create a separate Phase 20 branch from updated `main`;
5. inspect current packaging and CI truth before modifying release files.
