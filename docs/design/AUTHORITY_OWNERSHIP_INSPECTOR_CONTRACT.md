# Authority Ownership Inspector Contract

## Status

- Design status: acceptance-ready contract
- Execution status: read-only design only
- Proposed inspector ID: `architecture.authority_ownership`
- Executable implementation available: `false`
- PASS/FAIL authorization: `false`

This document defines the deterministic evidence contract required before an Authority Ownership inspector may be implemented. It does not register or expose an executable guard.

## Purpose

The inspector is intended to determine whether one authoritative operation or canonical state has exactly one declared owner, while other participating components are correctly bounded as observers, subscribers, delegates, or projections.

It addresses failures such as:

- multiple components mutating the same canonical state;
- duplicate persistence writers;
- repeated command execution;
- UI and runtime state disagreement;
- adapters rewriting native runtime state;
- stale ownership declarations;
- undeclared lifecycle or approval authorities.

Reference knowledge may suggest this inspection, but only current workspace evidence may establish a finding.

## Non-goals

This design does not:

- modify workspace files;
- select or rewrite an owner automatically;
- disable duplicate components;
- create permanent workspace policy;
- register a global guard;
- treat indexed reference knowledge as proof of a defect;
- infer runtime behavior from filenames or keywords alone.

## Inspection unit

Every inspection must begin with one explicit `authoritative_operation`.

Examples include:

- session persistence;
- message persistence;
- task-state transition;
- command execution;
- browser lifecycle;
- workspace selection;
- approval decisions;
- compaction creation;
- context injection;
- validated-memory promotion;
- SQLite memory writes;
- completion verdict.

A single inspection must not combine unrelated operations into one verdict.

## Role model

Each participating component must be classified as exactly one primary role for the inspected operation.

### `authoritative_owner`

The single component permitted to create or mutate canonical state or produce the authoritative side effect.

### `delegate`

Executes a bounded action only under explicit authority from the owner. A delegate cannot independently decide ownership or persist competing canonical state.

### `observer`

Receives authoritative events and may collect evidence or derived data. It cannot rewrite canonical state.

### `subscriber`

Consumes authoritative events through a declared subscription boundary. It cannot become an alternative mutation path.

### `projection`

Displays or materializes state received from the authority. It cannot independently mutate the authoritative operation.

### `unknown`

Used when evidence does not support a reliable role classification. `unknown` must lead to `INSUFFICIENT_EVIDENCE`, not an inferred violation.

## Required evidence package

The inspector requires a workspace-bound evidence package with all of the following sections.

### 1. Inspection identity

```yaml
workspace_id: string
authoritative_operation: string
inspection_timestamp: RFC3339
inspector_id: architecture.authority_ownership
inspector_version: string
```

### 2. Canonical state or side effect

```yaml
canonical_target:
  kind: file | database | process | event_stream | API | runtime_state | external_side_effect
  identifier: string
  physical_location: string | null
  runtime_identity: string | null
```

The target must identify what is authoritative. A conceptual label without a concrete state or side effect is insufficient.

### 3. Owner declarations

```yaml
owner_declarations:
  - component_id: string
    source_path: string
    symbol: string
    declared_role: authoritative_owner | delegate | observer | subscriber | projection
    declaration_source: manifest | configuration | contract | code | runtime
    evidence_ref: string
```

A declaration is evidence of intent, not proof of runtime behavior.

### 4. Mutation and execution sites

```yaml
mutation_sites:
  - component_id: string
    source_path: string
    symbol: string
    operation: create | write | update | delete | execute | transition | approve | persist
    target_identifier: string
    callsite_ref: string
    source_hash: string
```

Every discovered writer or executor for the inspected operation must be represented. Search results alone are not enough; each candidate must be live-inspected.

### 5. Call and authority paths

```yaml
call_paths:
  - entrypoint: string
    caller_chain: [string]
    terminal_mutation_site: string
    authority_source: string | null
    evidence_refs: [string]
```

The inspector must distinguish two call paths reaching one owner from two independent authorities.

### 6. Persistence paths

```yaml
persistence_paths:
  - component_id: string
    storage_kind: file | sqlite | database | browser_storage | native_session | remote_service
    storage_location: string
    write_symbol: string
    read_symbol: string | null
    canonical: boolean
    evidence_refs: [string]
```

Two stores are not automatically duplicate authorities. One may be canonical and the other a derived validated-memory store. The relationship must be proven.

### 7. Relationship boundaries

```yaml
relationships:
  - component_id: string
    role: delegate | observer | subscriber | projection
    owner_component_id: string
    allowed_actions: [string]
    prohibited_actions: [string]
    evidence_refs: [string]
```

A component claiming a non-owner role but performing a prohibited mutation is evidence for `OWNER_CONTRACT_BROKEN`.

### 8. Runtime confirmation

```yaml
runtime_observations:
  - observation_id: string
    component_id: string
    operation_observed: string
    target_observed: string
    occurrence_count: integer | null
    timestamp: RFC3339
    evidence_ref: string
```

Runtime confirmation is required when the claimed defect concerns repeated execution, lifecycle ownership, active persistence, or UI/runtime disagreement and the runtime can be safely observed.

Static evidence may be sufficient only when the ownership conflict is explicit and deterministic, such as two independent direct writers to the same canonical file with no delegation boundary.

### 9. Contradictions

```yaml
contradictions:
  - claim_a: string
    claim_b: string
    evidence_refs: [string]
```

Unresolved contradictions must produce `INSUFFICIENT_EVIDENCE` unless one claim is disproved by stronger current evidence.

### 10. Validation evidence

```yaml
validation:
  checks_run: [string]
  checks_passed: [string]
  checks_failed: [string]
  unavailable_checks: [string]
  evidence_refs: [string]
```

Missing required validation can never be converted into `PASS`.

## Deterministic findings

### `SINGLE_OWNER_CONFIRMED`

Required conditions:

1. one authoritative operation is explicitly identified;
2. exactly one effective authoritative owner is proven;
3. every discovered mutation or execution path terminates at that owner or an explicitly bounded delegate;
4. observers, subscribers, and projections do not mutate canonical state;
5. persistence paths have a declared canonical/derived relationship;
6. required runtime or structural validation succeeds;
7. no unresolved contradiction remains.

This finding may map to `PASS` only after an executable inspector is implemented, registered, versioned, tested, and approved.

### `DUPLICATE_AUTHORITY`

Required conditions:

1. at least two independent components perform authoritative mutation or execution for the same operation and canonical target;
2. neither path is proven to be a bounded delegate of the other;
3. the paths are current and reachable, or runtime evidence confirms both;
4. required validation succeeds.

Shared helper calls, mirrored projections, backups, derived indexes, and test fixtures do not satisfy this finding without independent authority.

### `UNDECLARED_AUTHORITY`

Required conditions:

1. a component performs an authoritative mutation or side effect;
2. no current owner declaration or delegation contract authorizes it;
3. the operation and target match the inspected authority boundary;
4. the path is current and reachable.

### `OWNER_CONTRACT_BROKEN`

Required conditions:

1. the component is declared as observer, subscriber, delegate, or projection;
2. current code or runtime evidence proves it performs a prohibited authoritative action;
3. the action affects the canonical target or authoritative side effect.

### `STALE_OWNER_RECORD`

Required conditions:

1. an ownership declaration identifies a component or symbol as owner;
2. current workspace evidence proves that component or symbol no longer owns or performs the operation;
3. another current path performs the authoritative action, or no current owner exists.

### `INSUFFICIENT_EVIDENCE`

Required when any essential evidence is missing, ambiguous, stale, contradictory, unverified, or only reference-derived.

Examples:

- candidate writers were found but not inspected;
- the canonical target is unknown;
- caller reachability is unproven;
- runtime confirmation is required but unavailable;
- native and adapter stores exist but their relationship is unclear;
- reference knowledge is the only evidence.

### `NOT_APPLICABLE`

Required when no authoritative operation in scope can be identified or the project does not contain the relevant state, persistence, lifecycle, or execution boundary.

## Evidence precedence

Use this order when evidence conflicts:

1. current runtime observation tied to an exact process, operation, and target;
2. current inspected source and configuration with hashes;
3. current manifests and declared contracts;
4. current workspace index entries used only for discovery;
5. bundled reference knowledge used only for pattern selection;
6. historical memory or prior reports used only as leads.

Lower-precedence evidence cannot override contradictory higher-precedence evidence.

## Native runtime and memory adapter boundary

For runtime memory integrations:

- the native runtime owns native session persistence;
- the native runtime owns native message persistence;
- a session memory adapter may observe and promote validated memory;
- the adapter may own a dedicated validated-memory SQLite store;
- the adapter must not rewrite native session JSON;
- the adapter must not become a second native persistence authority;
- context injection must have one declared runtime owner;
- the user interface is a projection unless explicitly proven otherwise.

The existence of both native persistence and validated-memory storage is not itself a duplicate-authority finding.

## Safe inspection algorithm

1. Resolve and verify the workspace identity.
2. Select exactly one authoritative operation.
3. Retrieve the Authority Ownership reference pattern as guidance only.
4. Search for candidate owner declarations, mutation sites, persistence paths, and entrypoints.
5. Live-inspect every candidate file and symbol.
6. Build caller and authority paths.
7. Classify each component role.
8. Identify the canonical target.
9. Determine whether runtime confirmation is required.
10. Run safe read-only runtime observations when available.
11. Record contradictions and missing evidence.
12. Apply the deterministic finding conditions.
13. Run required validation.
14. Emit a finding with evidence references, never an unsupported narrative verdict.

## Output contract

```yaml
inspector_id: architecture.authority_ownership
inspector_version: string
workspace_id: string
authoritative_operation: string
finding: SINGLE_OWNER_CONFIRMED | DUPLICATE_AUTHORITY | UNDECLARED_AUTHORITY | OWNER_CONTRACT_BROKEN | STALE_OWNER_RECORD | INSUFFICIENT_EVIDENCE | NOT_APPLICABLE
verdict: PASS | FAIL | INSUFFICIENT_EVIDENCE | NOT_APPLICABLE
pass_fail_authorized: false
canonical_target: object | null
authoritative_owner: object | null
participants: [object]
mutation_sites: [object]
call_paths: [object]
persistence_paths: [object]
runtime_observations: [object]
contradictions: [object]
missing_evidence: [string]
validation: object
evidence_refs: [string]
timestamp: RFC3339
```

Until implementation is registered and approved, `pass_fail_authorized` must remain `false`, and any attempted PASS or FAIL must be downgraded to `INSUFFICIENT_EVIDENCE`.

## Implementation gate

Executable implementation may begin only after all of the following are approved:

- this evidence contract;
- exact inspector inputs and output schema;
- deterministic finding tests;
- safe runtime observation boundaries;
- guard registry entry design;
- versioning and migration behavior;
- project-scoped enablement rules;
- validation and rollback plan.

## Acceptance criteria for this design phase

- the inspected operation is singular and explicit;
- owner, writer, reader, caller, persistence, and relationship evidence are defined;
- runtime confirmation requirements are bounded;
- reference knowledge is explicitly non-probative;
- duplicate storage is distinguished from duplicate authority;
- every finding has deterministic minimum evidence;
- contradictions map safely to `INSUFFICIENT_EVIDENCE`;
- PASS/FAIL remains unavailable;
- no workspace mutation is authorized;
- no executable guard is registered.