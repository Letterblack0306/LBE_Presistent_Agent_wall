# Current Implementation Gate

Status: **OPEN — R7 REPAIR INVESTIGATION — IMPLEMENTATION LOCKED — NEXT PHASE LOCKED**

Current phase: `R7_REPAIR_INVESTIGATION`

Current slice: `TRACE_INSTALLED_CODE_TO_EXISTING_GOVERNED_EXECUTION`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R7_REPAIR_INVESTIGATION_GATE.md
checkpoint: docs/acceptance/R7_REPAIR_INVESTIGATION_CHECKPOINT.md
kind: investigation-only repair localization after failed R7 composition acceptance
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: SOURCE_PLUS_RUNTIME_CORRELATION
status: OPEN
publish_allowed_now: false
```

## Trigger

R7 installed end-to-end acceptance failed on observable 3. The clean installed runtime probe proved:

```text
lbe code exit: 0
outcome: INSUFFICIENT_EVIDENCE
task status: blocked
response.read_only: true
provider stage: planning
provider approved_tools: workspace.read
marker: R7_CODE_PROVIDER_AUTHORITY_READ_ONLY=PROVEN
```

The failed R7 gate remains the release blocker. This investigation is allowed only to locate the exact missing composition seam and define the smallest repair; it does not convert R7 to PASS or authorize implementation.

## Accepted baseline retained

```text
R3:  PROVEN_COMPLETE
R4:  PROVEN_COMPLETE
R5:  PROVEN_COMPLETE
R6A: PROVEN_COMPLETE
R6B: PROVEN_COMPLETE
R6C: PROVEN_COMPLETE
R6D: PROVEN_COMPLETE
R6E: PROVEN_COMPLETE
R6F: PROVEN_COMPLETE
CLI: PROVEN_COMPLETE
R7:  FAIL — INSTALLED CODING COMPOSITION
```

Lower-layer PASS evidence remains valid for its bounded claims unless this investigation directly falsifies one of those layers.

## Current source trace

### Installed command path — PROVEN

```text
lbe code
 -> cli._run_mode_command
 -> build_provider_controller
 -> GovernedAgentGateway(runtime, reasoning_controller)
 -> operation_id = reasoning.inspect
 -> GovernedAgentGateway.invoke
 -> CodingCompletionRuntime.run_reasoning
 -> LBERequestController
```

The installed `code` command currently does not instantiate or invoke `GovernedClineWorker`, `ToolRegistry`, or `GovernedToolOrchestrator`.

### Existing governed provider tool loop — PROVEN

`runtime/cline_stdio_bridge.py::GovernedClineWorker.execute_turn` already implements:

```text
Cline/provider turn
 -> tool.proposed
 -> Python validates proposal identity
 -> GovernedToolOrchestrator.invoke(ToolRequest)
 -> ToolReceipt
 -> tool.result carrying receipt_id/operation_id
 -> same Cline continuation loop
```

The accepted Cline provider-continuation checkpoint proves this loop at integration evidence level. The Cline bridge performs receipt-backed continuation through its typed `tool.result` frame; the generic `provider_continuation.py` helper is not the only valid continuation implementation and must not be forced into this path merely for symmetry.

### Gateway capability — PROVEN

`GovernedAgentGateway` already knows how to derive the R6B-backed `ToolExecutionContext` and can construct an R6E `ToolRequest`, but its current `invoke()` coding path never invokes an R6E orchestrator.

### Production tool registration concern — OPEN

Current `runtime/tool_orchestration.py` visibly defines a production `workspace.read` spec/handler. R6E proves the generic registry/orchestrator lifecycle, but current inspected source has not yet proven a production coding/write tool registration. The investigation must resolve this before proposing that wiring the Cline loop alone is sufficient.

## Current classification

```text
PROVEN
- installed code path bypasses the existing Cline/R6E tool loop
- Cline/R6E receipt-backed tool continuation already exists independently
- gateway has ToolRequest/context construction helpers but does not use them in invoke()
- current visible builtin R6E tool is workspace.read

SUPPORTED
- the primary defect is missing composition into an already-built governed provider tool loop

HYPOTHESIS
- provider-turn composition should reuse GovernedClineWorker under the existing runtime/provider-turn ownership boundary rather than extend LBERequestController into an executor
- a separate concrete production coding/write capability may also be missing from the tool registry

UNKNOWN
- exact smallest implementation edit surface until all constructors/consumers/registrations are exhaustively traced
```

## Remaining investigation obligations

```text
- enumerate all ToolRequest producers/consumers
- enumerate all GovernedToolOrchestrator constructions/invocations
- enumerate all GovernedClineWorker constructions/execute_turn consumers
- enumerate all production ToolSpec/ToolRegistry registrations
- enumerate write/edit/process-capability implementations and determine whether any is production-active
- trace receipt/session/task/request/tool-call/operation correlation persistence
- prove whether another active coding execution route already exists
- identify earliest missing composition state
- state one bounded repair hypothesis and falsifier
- define focused + integration + installed-runtime validation
```

## Repair invariants

```text
reuse SessionMemoryRuntimeBridge
reuse R6C authorization_resolver
reuse R6E GovernedToolOrchestrator / ToolRegistry / ToolReceipt
reuse GovernedClineWorker/Cline continuation mechanics where applicable
reuse CodingCompletionRuntime
preserve provider-neutral LBE authority
no second tool dispatcher
no second authorization resolver
no second session/provider/completion authority
no provider-direct workspace mutation
no architecture rewrite before owner proof
```

## Release boundary

```text
R7 remains FAIL
release/package readiness remains blocked
publish_allowed_now: false
next_phase_locked: true
```

Investigation PASS will not automatically permit source changes. A separately activated repair implementation gate is required after the exact owner, edit surface, hypothesis, falsifier, and validation contract are recorded.
