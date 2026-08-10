# C0 Runtime Policy Composition Roadmap

Updated: 2026-08-10
Status: Documentation-first implementation checkpoint

## Purpose

Define the smallest correct production slice that connects the already-implemented R6B mode controller, R6C authorization resolver, and R6E governed tool orchestrator to the normal persistent-agent/runtime path without creating a parallel authority system.

This roadmap follows the evidence recorded in `docs/reference/MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md` and must be completed before C1 task-completion-contract establishment.

## Evidence-backed finding

Current repository inspection shows:

```text
MODE_HIT_COUNT=0
AUTH_HIT_COUNT=0
```

for production consumers outside the standalone runtime components.

The persistent session currently stores:

- `mode`;
- `active_profile_id`;
- `permission_policy_id`;
- `evidence_policy_id`;
- provider/model identity.

Those profile/policy fields are durable references, but the repository contains no authoritative mapping from their opaque IDs to R6B's typed inputs:

```text
permission     = read_only | write_allowed | audit_only | elevated
runtime_policy = audit | development | strict | permissive
```

The existing `session_state` schema has no typed `permission` or `runtime_policy` fields. Therefore C0 must not infer authority from opaque IDs or provider/model output.

## Architectural decision

C0 introduces only the minimum explicit typed LBE session-policy state needed by the existing R6B contract.

The authority chain is:

```text
explicit persisted LBE session policy facts
        |
        +-- permission
        +-- runtime_policy
        +-- persisted/request mode identity
        +-- workspace/session identity
        v
existing R6B resolve_mode()
        v
ModeDecision
        |
        +-- canonical mode
        +-- allowed_behaviors
        +-- capabilities
        v
existing R6C authorization resolver
        v
existing R6E governed tool orchestrator
```

The provider remains advisory and replaceable. It cannot supply or widen these policy facts.

## Legacy-session rule

Legacy sessions that do not contain explicit typed `permission` and `runtime_policy` must not receive fabricated authority.

For governed execution requiring R6B resolution, they fail closed until authoritative policy state is supplied through a deliberate supported path.

This does not require a broad schema-migration framework. C0 should add only the bounded compatibility logic needed to read existing databases safely and preserve existing non-governed inspection/status behavior where appropriate.

## C0 code slice

### C0.1 Persist typed session-policy facts

Extend canonical session state with explicit typed:

- `permission`;
- `runtime_policy`.

Requirements:

- values must use the existing R6B vocabulary;
- defaults must not silently grant write authority;
- provider switching must preserve both values;
- opaque `permission_policy_id`, `active_profile_id`, and `evidence_policy_id` remain references and are not reinterpreted.

### C0.2 Resolve effective mode on the normal gateway/runtime path

At the authoritative runtime composition boundary:

1. load explicit typed session policy;
2. derive bounded intent from the registered operation/request path, not arbitrary provider prose;
3. call existing `resolve_mode(ModeRequest(...))`;
4. reject contradictions between the returned `ModeDecision.mode` and persisted/request mode identity;
5. retain the returned `ModeDecision` as runtime policy context for downstream consumers.

Do not create another mode controller.

### C0.3 Preserve R6C ownership

All capability authorization remains in `resolve_authorization()`.

C0 must not duplicate ALLOW/DENY/ESCALATE decisions in the CLI, gateway, provider adapter, or tool handler.

### C0.4 Preserve R6E ownership

Registered tool invocation remains owned by `GovernedToolOrchestrator`.

C0 supplies the authoritative `ModeDecision` required by `ToolExecutionContext`; it does not create a second execution path.

### C0.5 Fail closed for missing authority

If a normal governed request requires R6B resolution but the session lacks authoritative typed policy state, return a bounded policy-state error/escalation rather than:

- assuming `write_allowed` from `mode=coding`;
- interpreting opaque policy IDs;
- accepting provider-proposed authority;
- defaulting legacy sessions into writable execution.

## Non-goals

C0 does not:

- define task-completion evidence kinds;
- establish completion contracts;
- add `lbe session validate`;
- add unrestricted shell execution;
- create a generic policy registry;
- create a second permission system;
- change guard verdict ownership;
- let the model choose validation requirements;
- broaden persistent rule/profile authority.

## Required regression coverage

Focused tests must prove:

1. explicit `read_only`/`audit` session policy resolves to audit-only capabilities;
2. explicit `write_allowed`/`permissive` plus a coding intent resolves to coding mode through R6B;
3. audit/investigation requests cannot gain coding capability through provider output;
4. request mode contradicting resolved mode is rejected;
5. legacy sessions missing typed policy fail closed for governed execution;
6. provider/model changes preserve typed session policy;
7. opaque policy/profile IDs do not determine typed authority;
8. R6C remains the only ALLOW/DENY/ESCALATE owner;
9. R6E receives the resolved `ModeDecision` rather than reconstructing authority;
10. existing session/status/evidence functionality remains compatible.

## Acceptance gate before C1

C1 may begin only after the installed/normal path proves:

```text
session policy state
    -> R6B mode decision
    -> R6C capability authorization
    -> R6E governed execution context
```

and the following are all true:

- mode resolution is deterministic;
- policy inputs are persisted LBE facts;
- provider switching does not mutate policy;
- missing authority fails closed;
- no duplicate controller/permission/tool authority exists;
- audit/investigation remain non-writing;
- focused tests pass;
- full test suite passes;
- `git diff --check` passes;
- local Git/BirdEye diff shows only intended changes.

## Dependency order after C0

```text
C0  authoritative runtime-policy composition
    -> explicit typed session permission/runtime_policy
    -> R6B normal-path resolution
    -> R6C/R6E composition

C1  immutable task completion contract establishment

C2  trusted semantic validation producers

C3  thin session validation surface

C4  remaining CLI commands and operator surfaces

C5  installed/normal-path R7 proofs
```

No code PR should widen beyond this C0 boundary unless new evidence requires another documented design change first.
