> **Governance Notice:** This workspace operates under a strict **no destructive action** policy. No file modification, code generation, rule creation, memory promotion, or workspace mutation is permitted without explicit user authorization. All operations are read-only unless explicitly approved. Governance violations must be reported as findings, not silently corrected. See `governance.json` for the current allowed-read and forbidden-glob configuration.
# Current Status

Updated: 2026-07-30

## Objective

Build a focused, project-scoped Guard Inspector and persistent evidence system that diagnoses concrete workspace problems through this authority chain:

```text
reference corpus suggests
current workspace inspection supplies facts
reasoning selects and explains
deterministic guards detect
LBE Core authorizes
validation proves
```

Live target workspace state and current validation remain authoritative.

## Repository state

- Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
- Base branch: `main`
- Foundation PR `#2`: merged at `7f212f406331dfaf7961143eefbf45f8ceaf6a17`
- Callback vertical-slice PR `#3`: merged at `0376f52093d079a5911b8c8b164492373e386046`
- Runtime-neutral adapter PR `#4`: merged at `25ea2560dbd9d440f3caf3be9f9c3b286aed1f5d`
- Runtime integration profile PR `#5`: merged at `575283ab986abc723de226c0340ec88c81ea2a10`
- Profile-driven proof PR `#6`: merged at `f41dd154a7450f30b92c05c358220606f5da95fa`
- Second deterministic guard PR `#7`: merged at `7345149b99d09ac34debaf16bd006107510b8095`
- Authority-evidence PR `#9`: closed as already integrated/stale; its older
  branch must not be merged into `main`.
- Only valid implementation baseline: `main`.
- Current baseline head: `536ac8143fc380c6d9f821881eaa8d7f6691dd03`.

## Completed foundation

Phases 1-12 provide:

- validated, project-scoped workspace memory with provenance and stale-data invalidation;
- Module Registry and Module Watcher lifecycle visibility;
- registry-first inspection with bounded source fallback;
- read-only Authority Ownership inspection;
- bounded runtime confirmation without hidden activation;
- end-to-end foundation proof.

## Phase 13 complete: callback Guard Inspector vertical slice

The first complete deterministic product path diagnoses:

```text
Provided callback is not a function
```

It resolves one exact configured workspace, separates reference evidence from current workspace evidence, runs the registered `cep.callback_contract` guard, applies read-only LBE authorization, validates independently, and returns `PASS`, `FAIL`, `INSUFFICIENT_EVIDENCE`, or `NOT_APPLICABLE` with evidence-only explanation.

## Phase 14 complete: minimal local invocation surface

The proven callback slice is exposed through:

```text
POST /guard-inspector/callback
```

The endpoint remains local-only, read-only, fixed to `CallbackVerticalSlice`, bounded to the narrow callback request contract, and rejects caller-controlled pack or rule selection.

## Phase 15 complete: runtime-neutral invocation adapter

Merged through PR `#4`.

Implemented:

- transport-neutral `InvocationTransport` protocol;
- configurable in-process callable transport;
- configurable local HTTP endpoint transport;
- exact response pass-through without verdict reinterpretation;
- bounded timeout and explicit cancellation;
- structured adapter errors;
- no automatic retry;
- no fixed runtime, vendor, workspace, path, endpoint, or port.

## Phase 16 complete: configurable runtime integration profile

Merged through PR `#5`.

Implemented:

- stable profile identifier and version;
- externally supplied transport-factory registry;
- externally supplied transport configuration;
- runtime-input mapping restricted to `workspace_root`, `workspace_id`, `reason`, and `max_results`;
- explicit capability declarations;
- deterministic rejection of arbitrary guard selection, workspace mutation, and repair execution;
- bounded timeout and cancellation configuration;
- deterministic validation of unknown, missing, malformed, and contradictory profile configuration;
- unchanged adapter response propagation;
- no vendor-, product-, company-, workspace-, path-, port-, or environment-specific assumptions.

## Phase 17 complete: profile-driven callback invocation proof

Merged through PR `#6` at `f41dd154a7450f30b92c05c358220606f5da95fa`.

The proof covers the full generic callback profile path through both in-process and temporary local HTTP transports. It preserves all four verdicts, structured failures, timeout, cancellation, evidence references, validation references, explanation, decision fingerprint, and workspace immutability without vendor-specific integration.

Validation:

- focused Phase 17 suite: `10 passed`;
- full repository suite: `215 passed`;
- `git diff --check`: passed.

## Phase 18 complete: second deterministic guard vertical slice

Merged through PR `#7` at `7345149b99d09ac34debaf16bd006107510b8095`.

Selected problem:

```text
Loaded module receipt has no matching declaration
```

Fixed identities:

- pack: `module_registry`;
- rule: `module_registry.loaded_module_registration`;
- vertical slice: `ModuleRegistryVerticalSlice`.

Implemented:

- deterministic inspection of `.lbe/module-registry.json` in one exact configured workspace;
- bounded declaration and lifecycle-receipt parsing;
- detection of loaded module receipts whose module IDs are absent from declarations;
- exact registry path, hash, and supporting evidence;
- explicit `FAIL`, `PASS`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE` semantics;
- independent validation through `GuardRunner`;
- read-only workspace fingerprint enforcement;
- fixed guard selection with no caller-controlled pack or rule;
- callback behavior unchanged.

Validation:

- focused Phase 18 suite: `11 passed`;
- full repository suite: `226 passed`;
- `git diff --check`: passed.

## Phase 19 complete: profile-driven module-registry invocation proof

Implemented on `feat/module-registry-profile-proof`.

The runtime profile contract now supports exactly one enabled fixed inspection capability:

- `callback_inspection`; or
- `module_registry_inspection`.

Both capabilities remain independently explicit. Enabling neither or both is rejected as a contradictory profile. The profile still maps only `workspace_root`, `workspace_id`, `reason`, and `max_results`, while arbitrary guard selection, workspace mutation, and repair execution remain prohibited.

The second fixed local endpoint is:

```text
POST /guard-inspector/module-registry
```

The endpoint validates the same narrow request field set and invokes only `ModuleRegistryVerticalSlice`.

`tests/test_module_registry_profile_end_to_end.py` proves:

1. callback and module-registry profiles remain independently valid;
2. multiple enabled inspection capabilities are rejected;
3. in-process module-registry profiles preserve all four verdicts;
4. temporary local HTTP invocation preserves the complete result unchanged;
5. authorization, evidence refs, validation refs, explanation, fingerprint, and `workspace_unchanged` remain intact;
6. arbitrary guard-selection fields are rejected;
7. missing factory and endpoint rejection remain structured;
8. timeout and cancellation remain deterministic;
9. transport failures are not retried;
10. temporary workspaces and ephemeral ports avoid environment assumptions;
11. target workspace state remains unchanged;
12. existing callback profile and endpoint tests remain green.

Validated at `b74f2c14b8f9409cf76b401961b5174e0fd3edf9`:

- focused Phase 19 suite: `54 passed`;
- full repository suite: `238 passed`;
- `git diff --check`: passed;
- working tree: clean;
- branch synchronized with `origin/feat/module-registry-profile-proof`.

## Current product position

The product now has:

- two deterministic guard paths;
- two narrow fixed local invocation surfaces;
- one runtime-neutral adapter;
- one generic runtime integration profile contract with mutually exclusive fixed capabilities;
- complete in-process and temporary local HTTP proofs for both guards;
- unchanged structured verdict and evidence contracts across both invocation paths.

The verdict contract remains:

- `PASS`;
- `FAIL`;
- `INSUFFICIENT_EVIDENCE`;
- `NOT_APPLICABLE`.

The model may select, hypothesize, and explain. It must not invent or reinterpret the verdict.

## Controlled integration checkpoint: deterministic project profiling

The audit controller now profiles one selected canonical project root before it
chooses an approved guard pack. A configured knowledge root is not treated as a
project identity: `workspace_id` is derived from the canonical project root,
and sibling projects are not used as profile evidence.

- approved signals currently include `package.json`, `pyproject.toml`,
  `CSXS/manifest.xml`, and `.lbe/module-registry.json`;
- one confident profile selects only its allowlisted guard packs and records
  the signal path/hash rationale in the audit report;
- the CEP manifest guard reads only `CSXS/manifest.xml` beneath the selected
  workspace root; it does not use a sibling project or the shared index as
  manifest proof;
- the remaining CEP and generic guards use bounded selected-workspace scans or
  the controller's selected-workspace inventory; callback and module-registry
  guards already use bounded live-workspace evidence;
- callback inspection now requires an exact `workspace_root`; absent scope is
  reported as `blocked` and never falls back to shared-index retrieval;
- zero or multiple confident profiles produce `insufficient_evidence` for
  automatic selection rather than guessing;
- a snapshot is persisted only under generated inspector state at
  `state/workspace-intelligence/<workspace_id>/snapshot.json`;
- snapshots record historical signal hashes and prior guard statuses, then
  report added, removed, and changed signals on the next audit;
- current filesystem profiling remains authoritative; a snapshot never acts as
  current workspace proof.

Validation for this checkpoint:

- focused controller and installed-package suite: `16 passed`;
- full repository suite: `283 passed`;
- `git diff --check`: passed.

## Indexed corpus integration checkpoint

The indexed corpus is global reference knowledge. It may contain examples from
the developer's repositories, but those records are never the target workspace
and never become current truth. The LLM uses them for cross-project,
request-time pattern specialization; this is retrieval-based specialization,
not model training.

The intended runtime is:

```text
curated cross-project corpus
-> pattern retrieval
-> candidate guards / likely failure domains
-> inspect the current arbitrary workspace
-> deterministic validation
-> verdict
```

PASS:

- corpus indexing;
- ranked retrieval;
- evidence metadata and exclusions;
- indexed/current evidence separation;
- LLM reasoning route;
- deterministic guard execution;
- automatic injection of bounded `indexed_reference_evidence` into
  `ReasoningRequest.reference_context`.

Historical open-defect proof, now resolved in the current worktree:

```text
INDEXED_EVIDENCE_COUNT=3
CURRENT_EVIDENCE_COUNT=3
REASONING_REFERENCE_CONTEXT_COUNT=0
```

The required implementation now runs bounded task-scoped reference retrieval
before `backend.plan()`, preserves path, hash, source classification, authority,
verification, and exclusion metadata, and injects only indexed reference
evidence. Current-workspace and validation evidence remain separate
deterministic inputs.

### Reasoning Context Contract

Before `backend.plan()` executes:

1. Perform bounded task-scoped retrieval.
2. Build an evidence package.
3. Inject only `indexed_reference_evidence` into
   `ReasoningRequest.reference_context`.
4. Never inject current workspace evidence into `reference_context`.
5. Never inject validation evidence into `reference_context`.
6. Preserve evidence IDs, hashes, provenance, authority metadata, and source
   classifications.
7. Excluded records must never enter the reasoning context.

Current proof:

```text
INDEXED_EVIDENCE_COUNT=5
REASONING_REFERENCE_CONTEXT_COUNT=5
injected evidence IDs/hashes match selected indexed records: PASS
excluded records absent: PASS
current workspace evidence remains separate: PASS
```

The next active implementation step, before Phase 20 release readiness, is a
cross-project retrieval proof on unfamiliar workspaces. It must resolve each
selected workspace independently, use corpus matches only as pattern
candidates, inspect current files before project-specific claims, bind verdicts
to current evidence and validation, and preserve corpus provenance and
authority metadata.

## Phase 6 — Governed workspace-rule proposals

The read-only proposal boundary is now the active implementation surface:

```text
verified finding
-> equivalent-rule check from the current profile
-> workspace-specific rule proposal
-> exact unified profile diff
-> explicit user approval record
```

Proposal generation and approval recording do not write the workspace, profile,
rule registry, or index. Automatic application and autonomous repair remain
disabled. Applying a proposal must remain a separate governed step with
activation validation, provenance, and rollback proof.

The governed apply slice now requires an `APPROVED` decision whose proposal
hash and workspace match, an injected LBE authorization check, and an injected
activation validator before reporting `APPLIED`. Rollback artifacts,
persistent provenance, and autonomous repair remain open follow-on work.

## Completed project-scoped audit proof

The end-to-end project-scoped chain is now proven through the installed
package:

```text
workspace resolver -> project profiler -> guard selector -> exact evidence
-> deterministic guard -> snapshot comparison -> evidence report
```

The public command is:

```powershell
lbe-guard-audit audit --workspace-root "<target-project-root>"
```

The installed-package smoke test proves the generic audit path as well as the
fixed callback and module-registry slices. The command remains deterministic,
read-only, project-scoped, and unable to accept arbitrary guard selection or
repair authority.

## Not yet completed

- remote GitHub Actions proof: the active `validate` workflow currently fails
  with `startup_failure` before any job is created; this is an external
  Actions scheduling/startup problem, not an audit-code defect;
- optional external-runtime integration packages;
- broader guard gallery coverage;
- complete UI beyond the minimum read-only proof surface.

## Integration policy

- Do not merge stale feature branches into `main` merely because they contain
  older slices of the implementation.
- Treat `main` as the only integration and release baseline.
- Resolve GitHub Actions startup failures separately from audit-code changes.

## No-drift boundary

This project is not building:

- a general chat or coding agent;
- unrestricted personal memory;
- model-authored truth;
- passive learning from every conversation;
- a replacement for Git or current workspace inspection;
- cross-project truth sharing;
- broad autonomous repair;
- automatic global-rule creation;
- unrestricted mutation;
- hardcoded runtime, workspace, path, port, application, company, vendor, or environment assumptions.
