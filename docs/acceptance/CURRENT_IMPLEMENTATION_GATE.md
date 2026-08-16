# Current Implementation Gate

Status: **OPEN — R7 REPAIR IMPLEMENTATION — BOUNDED IMPLEMENTATION AUTHORIZED — NEXT PHASE LOCKED**

Current phase: `R7_REPAIR_IMPLEMENTATION`

Current slice: `COMPOSE_INSTALLED_CODING_WITH_EXISTING_GOVERNED_EXECUTION`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R7_REPAIR_IMPLEMENTATION_GATE.md
checkpoint: docs/acceptance/R7_REPAIR_IMPLEMENTATION_CHECKPOINT.md
status: OPEN
required_evidence_level: INTEGRATION_PLUS_INSTALLED_RUNTIME
implementation_allowed: true
architecture_changes_allowed: false
next_phase_locked: true
publish_allowed_now: false
```

## Trigger

R7 observable 3 remains failed. The installed runtime proved `lbe code` completed through read-only `reasoning.inspect` / `LBERequestController`, exposed only `workspace.read`, and never reached a governed coding `ToolReceipt`.

The completed investigation proved two adjacent gaps:

```text
Gap 1:
installed lbe code / GovernedAgentGateway
    X
existing GovernedClineWorker -> R6C -> R6E -> ToolReceipt -> same-provider continuation

Gap 2:
existing generic R6E ToolRegistry / GovernedToolOrchestrator
    X
production workspace mutation ToolSpec / handler
```

## Authorized implementation

Only the smallest repair required to close those two proven gaps is authorized:

1. compose installed coding through the existing `GovernedClineWorker` and existing R6E registry/orchestrator;
2. add one smallest safe workspace-bound mutation capability behind existing R6C/R6E authorization;
3. retain canonical ToolReceipt and correlation identity;
4. retain same-provider Cline continuation;
5. retain existing session/task and deterministic completion authority;
6. add claim-matched tests and rerun the installed R7 observable.

## Authority reuse

```text
SessionMemoryRuntimeBridge: retain
GovernedAgentGateway: retain
resolve_authorization: retain
ToolRegistry / GovernedToolOrchestrator / ToolReceipt: retain
GovernedClineWorker: retain
operational history correlation: retain
CodingCompletionRuntime: retain
```

## Forbidden

```text
second authorization resolver
second tool dispatcher
second session/provider/completion authority
provider-direct workspace mutation
native Cline mutation authority
architecture rewrite
release/version/tag/publish work
```

## Validation ladder

```text
source/diff review
 -> focused mutation authorization tests
 -> governed Cline/R6E integration
 -> deny/escalate/failure/idempotency regression
 -> completion-authority regression
 -> isolated wheel build/install with PYTHONPATH removed
 -> R7 observable 3 with real governed mutation + ToolReceipt + continuation
 -> exact-head clean-worktree proof
```

## Release boundary

```text
R7 overall: still FAIL until repaired installed observable 3 passes
release/package readiness: blocked
publish_allowed_now: false
next_phase_locked: true
```

A PASS on this repair slice does not automatically resume later R7 observables. The repaired installed observable must be recorded and the next gate must be explicitly advanced.
