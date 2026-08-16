# R7 Installed Coding Composition Repair Investigation Checkpoint

```text
phase: R7_REPAIR_INVESTIGATION
slice: TRACE_INSTALLED_CODE_TO_EXISTING_GOVERNED_EXECUTION
status: OPEN
base_sha: 677cb96471aaead50b30312aa16eeea04caa8084
implementation_sha: NOT_APPLICABLE_INVESTIGATION_ONLY
required_evidence_level: SOURCE_PLUS_RUNTIME_CORRELATION
next_phase_locked: true
```

## Trigger evidence

```text
R7 observable 3: FAIL
installed code response.read_only: true
provider approved_tools: workspace.read
governed coding ToolReceipt path reached: no
```

## Proven source findings

### Installed `code` producer path

```text
cli._run_mode_command
 -> build_provider_controller (reasoning controller)
 -> GovernedAgentGateway
 -> AgentRequestEnvelope(operation_id=reasoning.inspect)
 -> GovernedAgentGateway.invoke
 -> CodingCompletionRuntime.run_reasoning
 -> LBERequestController
```

No Cline worker, ToolRegistry, or GovernedToolOrchestrator is composed by this path.

### Existing governed tool producer/consumer path

`runtime/cline_stdio_bridge.py::GovernedClineWorker` is an existing production source owner for provider tool-call mediation:

```text
Cline AgentRuntime
 -> tool.proposed frame
 -> GovernedClineWorker._mediate_tool_proposal
 -> ToolRequest
 -> GovernedToolOrchestrator.invoke
 -> ToolReceipt
 -> typed tool.result frame with receipt_id + operation_id
 -> same Cline continuation loop
```

This flow is independently accepted by `LBE_CLINE_PROVIDER_CONTINUATION_CHECKPOINT.md` at integration evidence level.

### Gateway execution context

`GovernedAgentGateway` already derives the existing R6B mode decision into `ToolExecutionContext` and can construct a `ToolRequest`. Its current `invoke()` path does not call an orchestrator.

### Provider continuation distinction

For the Cline path, receipt-backed continuation is implemented directly by the typed bridge `tool.result` frame. `provider_continuation.py` remains an accepted generic receipt-continuation boundary but is not proven to be a mandatory extra hop in the Cline continuation path.

### Provider-turn owner

`provider_turn_runtime.py` currently implements non-streaming/background OpenAI-compatible turn execution and event projection but has no R6E/Cline tool mediation. Earlier Cline architecture records identify provider-turn behavior as an LBE runtime ownership concern, so repair must reconcile with this owner rather than create a second provider authority.

### Production tool registration concern

Current inspected `runtime/tool_orchestration.py` visibly supplies `workspace.read` as the concrete production `ToolSpec`/handler. Generic R6E execution is proven, but a concrete production write/edit/process coding capability has not yet been found. This must be resolved before concluding that connecting the existing Cline loop alone satisfies R7 coding acceptance.

## Current required findings

```text
provider_tool_request_producer:
  PROVEN — GovernedClineWorker receives Cline tool.proposed and constructs ToolRequest

r6e_executor_consumer:
  PROVEN — GovernedClineWorker._mediate_tool_proposal -> GovernedToolOrchestrator.invoke

tool_receipt_consumer:
  PROVEN — GovernedClineWorker converts ToolReceipt into correlated tool.result for same Cline continuation

provider_continuation_caller:
  PROVEN FOR CLINE PATH — typed bridge tool.result resumes same Cline AgentRuntime continuation
  NOTE — generic provider_continuation.py is not required to be inserted into this Cline path

session_task_operation_correlation_owner:
  PARTIALLY_PROVEN — bridge protocol preserves session_id/turn_id/cline_tool_call_id/lbe_call_id/operation_id/receipt_id; installed session/task linkage still requires composition trace

alternate_active_coding_path_scan:
  UNVERIFIED — repository-wide local symbol/registration scan still required

earliest_missing_composition_state:
  SUPPORTED — installed CLI/gateway selects reasoning.inspect + LBERequestController rather than composing existing governed Cline/R6E turn path

production_coding_tool_registration:
  UNVERIFIED — current visible concrete production ToolSpec is workspace.read

smallest_edit_surface:
  UNVERIFIED pending alternate-path + production-tool registration scan

repair_hypothesis:
  UNVERIFIED pending final structural scan

repair_falsifier:
  UNVERIFIED pending final structural scan

validation_contract:
  PARTIALLY_DEFINED — focused owner tests -> governed Cline/R6E integration -> isolated installed R7 observable 3; exact test surface waits on owner proof
```

## Evidence classification

```text
PROVEN
- installed code path bypasses existing governed Cline/R6E loop
- existing Cline bridge already owns provider tool proposal -> R6E -> ToolReceipt -> same-provider continuation
- gateway has R6E context/request helpers but invoke does not execute them
- current visible builtin production tool is workspace.read

SUPPORTED
- primary repair is composition of existing authorities, not replacement of R6C/R6E

HYPOTHESIS
- existing runtime/provider-turn/gateway seam should compose GovernedClineWorker for coding sessions
- a concrete production write/edit capability may additionally be required

UNKNOWN
- whether another active production coding path or write-tool registration exists elsewhere
- exact smallest edit surface
```

## Next discriminating evidence

Perform one repository-wide read-only symbol scan for:

```text
ToolSpec / registry.register
workspace.write / edit / patch / shell / process tool IDs
GovernedToolOrchestrator constructors/invocations
GovernedClineWorker constructors/execute_turn callers
ToolRequest constructors
continuation_from_receipt callers
```

This scan is investigation/debugging only and must not modify source.

## Existing owner reuse decision

```text
decision: REUSE unless current source/runtime evidence disproves ownership
R6C authorization owner: retained
R6E GovernedToolOrchestrator/ToolReceipt owner: retained
GovernedClineWorker continuation mechanics: retained
SessionMemoryRuntimeBridge owner: retained
CodingCompletionRuntime owner: retained
```

## Implementation boundary

```text
implementation_allowed: false
architecture_changes_allowed: false
source_changes: forbidden
```

## Completion rule

Close this investigation only after the exact active producer/consumer/correlation chain, alternate-path/tool-registration scan, earliest missing seam, smallest edit surface, one repair hypothesis, one falsifier, and validation plan are proven. Do not auto-activate implementation.
