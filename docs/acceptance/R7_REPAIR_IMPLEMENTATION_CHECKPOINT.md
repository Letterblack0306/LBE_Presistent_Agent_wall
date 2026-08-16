# R7 Repair Implementation Checkpoint

```text
phase: R7_REPAIR_IMPLEMENTATION
slice: COMPOSE_INSTALLED_CODING_WITH_EXISTING_GOVERNED_EXECUTION
status: OPEN
base_sha: 9138b47b279c0f4207bda952fd30521a828c952a
implementation_sha: UNSET
required_evidence_level: INTEGRATION_PLUS_INSTALLED_RUNTIME
next_phase_locked: true
```

## Requirements

- compose installed coding into the existing governed Cline/R6E execution loop;
- add one smallest workspace-bound production mutation capability behind R6C/R6E;
- preserve ToolReceipt identity/correlation and same-provider continuation;
- keep SessionMemoryRuntimeBridge, GovernedAgentGateway, R6C, R6E, Cline continuation and CodingCompletionRuntime authoritative;
- do not introduce provider-direct mutation or duplicate authority;
- prove denied/escalated mutation does not execute;
- prove allowed mutation executes exactly once and produces a ToolReceipt;
- prove installed exact-head `lbe code` reaches governed coding execution;
- rerun R7 observable 3 before resuming later R7 acceptance.

## Existing owner

```text
session/task lifecycle: SessionMemoryRuntimeBridge
entry identity/mode: GovernedAgentGateway
authorization: resolve_authorization
execution/receipt: ToolRegistry + GovernedToolOrchestrator + ToolReceipt
provider tool continuation: GovernedClineWorker / typed tool.result
completion: CodingCompletionRuntime + deterministic completion evidence/gate
```

## Reuse decision

```text
decision: REUSE / EXTEND EXISTING OWNERS
new authority: forbidden
```

## Validation evidence

```text
source_review: PENDING
focused_tests: PENDING
cline_r6e_integration: PENDING
denied_escalated_regression: PENDING
completion_regression: PENDING
isolated_install: PENDING
r7_observable_3: PENDING
clean_worktree: PENDING
```

## Unverified

- exact smallest mutation primitive and file-level edit surface until current owner source is inspected under this active implementation gate;
- repaired installed runtime behavior.

## Document conflicts

None known at activation.

## Status

`OPEN`
