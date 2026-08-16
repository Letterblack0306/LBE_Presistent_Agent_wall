# Current Implementation Gate

Status: **OPEN — R7 INSTALLED END-TO-END ACCEPTANCE — OBSERVABLE 7 — IMPLEMENTATION LOCKED**

Current phase: `R7_INSTALLED_END_TO_END_ACCEPTANCE`

Current slice: `OBSERVABLE_7_AUDIT_INVESTIGATION_READ_ONLY`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md
status: OPEN
required_evidence_level: INSTALLED_RUNTIME_READ_ONLY_NEGATIVE_PROOF
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
publish_allowed_now: false
```

## Accepted R7 baseline

```text
observable 1: PASS
observable 2: PASS
observable 3: PASS_AFTER_REPAIR
observable 4: PASS
observable 5: PASS
observable 6: PASS
```

Observable 6 decisive proof: `4B11427423FE60EFD1E77271A424390F2E91813A9A1E80E961A3C5FDF0BB78CC`.

## Active observable 7

Question:

> Do installed audit and investigation execution remain read-only and reject provider-requested mutation without changing workspace state?

Required proof:

1. run from the isolated installed package, not the source checkout;
2. create bounded disposable audit and investigation sessions with read-only policy identities;
3. capture tracked workspace bytes/hash/Git state before each invocation;
4. use a local deterministic provider response that attempts to request `workspace.create_candidate_text`;
5. prove the normal installed audit and investigation controllers do not approve or execute that mutation tool;
6. prove no target mutation file is created and tracked workspace hash/Git state remain unchanged;
7. prove no `EXECUTED` mutation ToolReceipt is returned;
8. prove persisted mode/permission/runtime-policy identity remains unchanged;
9. project source worktree stays clean.

Source inspection supporting the discriminator:

- `LBERequestController` is explicitly a read-only planning/inspection controller and has `_APPROVED_TOOLS = {"workspace.read"}`;
- `_validate_plan()` rejects any evidence request whose `tool_id` is not in that set with `UNKNOWN_TOOL`;
- `GovernedAgentGateway` uses the ordinary reasoning controller for audit/investigation and only swaps in `GovernedClineReasoningController` for coding;
- R6B removes write/test-candidate capabilities from audit and investigation mode decisions.

## Falsifier

Any audit/investigation workspace mutation, approved write tool, executed mutation receipt, provider-direct write, or policy identity drift is a product falsifier and stops R7.

Harness/provider/fixture failures that do not reach the read-only predicate do not justify a product patch.

## Stop rule

Do not proceed to observable 8 until observable 7 is classified `PASS` and recorded. No production implementation change is authorized under this acceptance slice.
