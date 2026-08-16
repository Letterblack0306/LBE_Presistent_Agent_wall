# R6E Governed Tool Orchestration Acceptance Checkpoint

```text
phase: R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE
slice: PROVE_RECEIPT_BACKED_GOVERNED_TOOL_LIFECYCLE_WITH_IDEMPOTENCY_AND_PROVIDER_CONTINUATION
status: UNVERIFIED

base_sha: a237ac0184116a47fdc5b2efc782940faa065efb
implementation_sha: NOT_APPLICABLE_ACCEPTANCE_ONLY
required_evidence_level: INTEGRATION
next_phase_locked: true
```

## Requirements

- prove only registered tools execute;
- prove invalid arguments/precondition failures stop before service execution;
- prove R6C authorization gates handler invocation;
- prove authorized execution emits structured output/evidence receipt;
- prove operation-id idempotency prevents duplicate execution;
- prove real workspace reads delegate to existing EvidenceService;
- prove provider continuation is derived only from governed receipts;
- prove escalated receipts stop before continuation;
- prove provider continuation has no execution authority;
- run focused tool/authorization/continuation/runtime regression;
- record exact evidence, limitations, falsifiers, diff and clean-worktree proof.

## Existing owner

```text
ToolRegistry
GovernedToolOrchestrator
ToolRequest
ToolReceipt
resolve_authorization
build_workspace_read_handler
EvidenceService
continuation_from_receipt
continue_provider
```

## Reuse decision

```text
decision: REUSE
evidence: governed lookup/authorization/execution/receipt/idempotency and receipt-backed continuation already exist independently; combined lifecycle acceptance is missing.
```

## Architecture change

```text
introduced: no
user_authorized: no new architecture requested
canonical_docs_updated_first: yes
```

## Validation evidence

```text
source_owner_inspection: PASS
repository_tool_tests: PRESENT_NOT_YET_RUN_ON_GATE_HEAD
repository_authorization_tests: PRESENT_NOT_YET_RUN_ON_GATE_HEAD
repository_continuation_tests: PRESENT_NOT_YET_RUN_ON_GATE_HEAD
registered_authorized_execution: NOT RUN
invalid_or_unregistered_no_execution: NOT RUN
duplicate_operation_idempotency: NOT RUN
workspace_evidence_delegation: NOT RUN
receipt_backed_provider_continuation: NOT RUN
escalation_stops_continuation: NOT RUN
focused_regression: NOT RUN
git_diff_check: NOT RUN
worktree_clean: NOT RUN
```

## Falsifier state

```text
observed_falsifier: NONE YET
```

## Unverified

- combined governed execution -> receipt/evidence -> provider continuation lifecycle;
- duplicate-operation no-reexecution within the same lifecycle;
- escalation stop before provider continuation in the combined path;
- focused regression and final scope/worktree proof.

## Document conflicts

```text
none known at activation
```

## Readiness

```text
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```
