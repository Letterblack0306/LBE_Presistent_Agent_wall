# Project Intent Ledger

Status: **CANONICAL PRE-MUTATION INTENT LEDGER**

Every meaningful repository mutation must resolve to exactly one intent record before staging.
The machine gate binds the active slice to the `INTENT_ID`, and the affected structure must exist
in `PROJECT_INDEX.md`.

## INTENT LBE-INTENT-WORKSPACE-HYGIENE-001

```text
INTENT_ID: LBE-INTENT-WORKSPACE-HYGIENE-001
STATUS: COMPLETED
REQUEST: Govern workspace document hygiene and bounded disposable deletion.
WHY: Prevent unexplained, stale, duplicate, generated, or abandoned workspace material from being
treated as current project authority.
AFFECTED_STRUCTURE: docs/, scripts/, .lbe/, .agent/, lbe_guard_inspector/, tests/, unused-in-repo/
EXISTING_OWNER: LBE governance, documentation, runtime orchestration, and validation owners.
DESIRED_RESULT: Every material document has an owner, intent, reachability classification, and safe
disposition; disposable deletion is governed and receipt-backed.
NON_GOALS: No new execution system, no unrestricted deletion, no destruction of unknown user work,
no publication, no provider/UI architecture change.
REUSE_DECISION: Reuse existing machine gate, tool orchestrator, receipt, evidence, and documentation
owners.
AUTHORITY_IMPACT: Strengthens pre-mutation checks without creating a second authority owner.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,docs/,scripts/check-implementation-gate.py,.lbe/governance/,.agent/,lbe_guard_inspector/,tests/,unused-in-repo/
REQUIRED_EVIDENCE: index/ledger match, staged-scope match, focused tests, diff check, protected-work preservation
MACHINE_SLICE: WORKSPACE_HYGIENE_GOVERNED_DELETION
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/WORKSPACE_HYGIENE_GOVERNED_DELETION_CHECKPOINT.md
```

## INTENT LBE-INTENT-MANDATORY-GOVERNED-MUTATION-DISPATCH-001

```text
INTENT_ID: LBE-INTENT-MANDATORY-GOVERNED-MUTATION-DISPATCH-001
STATUS: ACTIVE
REQUEST: Make LBE governed dispatch mandatory for the existing agent coding mutation path, covering bounded workspace text mutation, registered process execution, and main-only Git mutation while keeping arbitrary native mutation tools unavailable.
WHY: The LBE product requires providers to reason and request capabilities while LBE alone owns authorization, execution, receipts, and evidence. Direct filesystem, shell, or Git mutation exposure would bypass the product wall.
AFFECTED_STRUCTURE: lbe_guard_inspector/, tests/, docs/acceptance/, docs/governance/, docs/CURRENT_STATUS.md, .lbe/governance/
EXISTING_OWNER: R6C authorization resolver; R6E GovernedToolOrchestrator, ToolRegistry, ToolRequest, and ToolReceipt; GovernedProviderReasoningController; existing workspace/session identity; provider continuation; validation/completion owners.
DESIRED_RESULT: Provider-facing coding turns receive only LBE-generated tool definitions; bounded workspace mutation and Git mutation execute through existing R6C/R6E owners with receipts; arbitrary shell/native mutation remains unavailable; registered process commands are explicit and bounded.
NON_GOALS: No second executor, no second authorization owner, no second receipt/session/completion owner, no unrestricted shell, no branch/worktree creation, no push/publication, no TUI redesign, no lbe-core mutation, no direct Cline authority.
REUSE_DECISION: REUSE GovernedProviderReasoningController, R6C authorization, R6E orchestration/receipts, agent guidance, workspace governance helpers, provider continuation, and current session identity. ADAPT only tool specifications/handlers and provider registration. REJECT native filesystem/shell/Git exposure.
AUTHORITY_IMPACT: LBE authority remains unchanged; the agent-facing capability surface becomes stricter and more useful.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: provider-only LBE tool schema, contained write proof, stale-write denial, arbitrary-shell denial, bounded registered-process proof, primary-main Git proof, governed-staging proof, authorization-before-execution, correlated receipts, read-only audit/investigation preservation, duplicate-authority scan
MACHINE_SLICE: MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH
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
