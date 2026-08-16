# R6E Governed Tool Orchestration Acceptance Gate

Status: **OPEN — ACCEPTANCE PROOF ONLY — NEXT PHASE LOCKED**

```text
phase: R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE
slice: PROVE_RECEIPT_BACKED_GOVERNED_TOOL_LIFECYCLE_WITH_IDEMPOTENCY_AND_PROVIDER_CONTINUATION
base_sha: a237ac0184116a47fdc5b2efc782940faa065efb
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

## Selection rationale

R6D is closed PASS. R6E is the next dependency boundary because provider reasoning/tool proposals must cross the existing LBE governed execution owner before any workspace action, and any provider continuation must be derived from the resulting LBE receipt rather than bypassing governance.

Current source/tests already prove the component contracts independently. This slice is acceptance-first and does not declare an implementation defect.

## Acceptance question

Can the existing LBE tool path take a bounded registered operation through argument validation, authorization, governed execution, structured receipt/evidence and receipt-backed provider continuation while preserving operation identity/idempotency, stopping escalation before continuation, and preventing any provider or unregistered tool bypass?

## Existing owners

```text
lbe_guard_inspector.runtime.tool_orchestration.ToolRegistry
lbe_guard_inspector.runtime.tool_orchestration.GovernedToolOrchestrator
lbe_guard_inspector.runtime.tool_orchestration.ToolRequest
lbe_guard_inspector.runtime.tool_orchestration.ToolReceipt
lbe_guard_inspector.runtime.tool_orchestration.build_workspace_read_handler
lbe_guard_inspector.runtime.authorization_resolver.resolve_authorization
lbe_guard_inspector.provider_continuation.continuation_from_receipt
lbe_guard_inspector.provider_continuation.continue_provider
EvidenceService
```

## Reuse decision

```text
REUSE
```

Do not introduce another tool dispatcher, operation store, receipt authority, provider-native executor, or continuation authority.

## Required observables

1. only an explicitly registered tool can execute;
2. argument validation and workspace/precondition failures stop before the underlying service is invoked;
3. R6C authorization is consumed before handler execution and `DENY`/`ESCALATE` do not execute;
4. an authorized registered tool produces one structured `EXECUTED` receipt with output/evidence;
5. the receipt preserves operation ID, tool ID and authorization provenance;
6. repeating the same operation ID returns the original receipt without re-execution;
7. real workspace read delegates to the existing `EvidenceService` rather than bypassing it;
8. provider continuation is constructed only from an existing governed receipt and preserves runtime-operation/receipt/tool identity;
9. an escalated receipt stops before provider continuation;
10. provider continuation has no execution authority and cannot invoke an unregistered/ungoverned tool;
11. focused tool/authorization/continuation/runtime regression passes on the exact acceptance head;
12. no runtime/test implementation source changes are required unless a real falsifier is proven.

## Falsifier

R6E cannot PASS if an unregistered or unauthorized operation executes, invalid/precondition-failing input reaches the underlying service, duplicate operation identity re-executes, receipt evidence/provenance is lost, provider continuation can occur from an escalated/non-governed path, provider code gains execution authority, or a parallel tool/receipt/continuation owner is required.

## Evidence ladder

```text
source owner inspection
-> repository-owned tool/authorization/continuation tests
-> combined governed execution + receipt discriminator
-> idempotent duplicate-operation discriminator
-> receipt-backed provider continuation discriminator
-> escalation stop discriminator
-> focused regression
-> diff/scope/worktree proof
-> checkpoint
```

## Allowed work

- GitHub inspection of current tool/authorization/evidence/continuation owners and tests;
- LoopTool execution of repository-owned tests and bounded runtime diagnostics;
- R6E acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- runtime/test implementation before a real defect is proven;
- R6F implementation;
- new tool dispatcher/receipt store/provider executor/continuation authority;
- unrestricted shell/filesystem bypass;
- CLI/TUI/MCP/release work;
- architecture changes.

## Completion predicate

PASS only when the existing registered/authorized governed execution path, structured receipt/evidence, operation-id idempotency, and receipt-backed provider continuation/stop behavior are proven together with no falsifier. PASS does not auto-activate R6F or another phase.
