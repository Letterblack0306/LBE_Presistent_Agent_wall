# Project Intent Ledger

Status: **CANONICAL PRE-MUTATION INTENT LEDGER**

Every meaningful repository mutation must resolve to exactly one intent record before staging.
The machine gate binds the active slice to the `INTENT_ID`, and the affected structure must exist
in `PROJECT_INDEX.md`.

## INTENT LBE-INTENT-WORKSPACE-HYGIENE-001

```text
INTENT_ID: LBE-INTENT-WORKSPACE-HYGIENE-001
STATUS: ACTIVE
REQUEST: Govern workspace document hygiene and bounded disposable deletion.
WHY: Prevent unexplained, stale, duplicate, generated, or abandoned workspace material from being
treated as current project authority.
AFFECTED_STRUCTURE: docs/, scripts/, .lbe/, .agent/, lbe_guard_inspector/, tests/
EXISTING_OWNER: LBE governance, documentation, runtime orchestration, and validation owners.
DESIRED_RESULT: Every material document has an owner, intent, reachability classification, and safe
disposition; disposable deletion is governed and receipt-backed.
NON_GOALS: No new execution system, no unrestricted deletion, no destruction of unknown user work,
no publication, no provider/UI architecture change.
REUSE_DECISION: Reuse existing machine gate, tool orchestrator, receipt, evidence, and documentation
owners.
AUTHORITY_IMPACT: Strengthens pre-mutation checks without creating a second authority owner.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,docs/,scripts/check-implementation-gate.py,.lbe/governance/,.agent/,lbe_guard_inspector/,tests/
REQUIRED_EVIDENCE: index/ledger match, staged-scope match, focused tests, diff check, protected-work preservation
MACHINE_SLICE: WORKSPACE_HYGIENE_GOVERNED_DELETION
SUPERSEDES: none
RESULT: IN_PROGRESS
```

## INTENT LBE-INTENT-CLINE-AGENTRUNTIME-001

```text
INTENT_ID: LBE-INTENT-CLINE-AGENTRUNTIME-001
STATUS: ACCEPTED_PRODUCT_DIRECTION
REQUEST: Use Cline AgentRuntime interaction and continuation mechanics behind an LBE-owned governance adapter.
WHY: Reuse the mature agent loop without creating a second LBE authority/runtime.
AFFECTED_STRUCTURE: lbe_guard_inspector/, docs/design/, docs/research/, .cline/
EXISTING_OWNER: LBE workspace/session identity, authorization, dispatch, receipts, evidence,
persistence, validation, and completion owners.
DESIRED_RESULT: Cline mechanics are adapted behind LBE authority; native Cline mutation/execution is
not canonical.
NON_GOALS: No direct Cline mutation authority, no second session authority, no React runtime before
the adapter boundary is proven.
REUSE_DECISION: REUSE continuation/event/tool mechanics; ADAPT provider and presentation mechanics;
REJECT native overlapping mutation/execution.
AUTHORITY_IMPACT: LBE authority remains unchanged.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,docs/design/,docs/research/,.cline/
REQUIRED_EVIDENCE: deny-before-execute, allow-exactly-once, receipt-backed continuation, event mapping,
native mutation disabled, canonical LBE session ownership
MACHINE_SLICE: FUTURE_SLICE_NOT_ACTIVE
SUPERSEDES: none
RESULT: NOT_ACTIVE
```

## Ledger law

```text
NO INTENT -> NO CHANGE
NO OWNER -> NO CHANGE
NO INDEX ENTRY -> NO CHANGE
NO MACHINE-GATE MATCH -> NO CHANGE
```

Completed intents must update `RESULT` and retain the evidence/commit reference. Proposed intents
remain non-authorizing until explicitly bound to the machine gate.
