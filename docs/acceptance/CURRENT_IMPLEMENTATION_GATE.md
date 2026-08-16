# Current Implementation Gate

Status: **OPEN — R7 INSTALLED END-TO-END ACCEPTANCE — OBSERVABLE 9 — IMPLEMENTATION LOCKED**

Current phase: `R7_INSTALLED_END_TO_END_ACCEPTANCE`

Current slice: `OBSERVABLE_9_RECEIPT_PROVIDER_CONTINUATION_CORRELATION`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md
status: OPEN
required_evidence_level: INSTALLED_RUNTIME_CORRELATED_RECEIPT_CONTINUATION_PROOF
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
observable 7: PASS
observable 8: PASS
```

Observable 8 decisive proof: `98B3EC987725DB5B103E6B11B64DD60C4C73EA2F249BC88F260403A52127FDEE`.

## Active observable 9

Question:

> Does the installed governed coding loop preserve exact provider tool-call, LBE call, operation, ToolReceipt, and same-turn provider continuation correlation without duplicate execution or identity substitution?

Required proof:

1. invoke installed `lbe code` from the isolated package against a deterministic local provider;
2. provider emits exactly one tool call with a fixed `tool_call_id`;
3. one R6E mutation receipt is returned and is `EXECUTED`;
4. receipt `operation_id` must be `<turn_id>:tool:<tool_call_id>`;
5. receipt has one non-empty unique `receipt_id`;
6. the second provider HTTP request must contain the same assistant tool-call identity and a tool-result message correlated by that same `tool_call_id`;
7. the governed result in the provider continuation must match the mutation result represented by the LBE receipt;
8. exactly two provider requests occur for the turn and the mutation executes exactly once;
9. final turn remains the same installed governed turn and completion truth remains provider-non-authoritative;
10. source checkout remains clean.

Source contract used to define the discriminator:

- Node derives `operation_id = <turn_id>:tool:<cline_tool_call_id>` and `lbe_call_id = <turn_id>:lbe:<cline_tool_call_id>`;
- Python R6E execution returns a `ToolReceipt` and sends `tool.result` with `cline_tool_call_id`, `lbe_call_id`, `operation_id`, and `receipt_id`;
- Node rejects mismatched session/turn/operation/LBE-call identity before resolving the pending provider tool call.

## Falsifier

Any missing/substituted identity, mismatched operation/receipt, duplicate mutation, provider continuation without the same tool-call identity, or cross-turn continuation is a product falsifier.

Harness/provider/fixture failures that do not reach these predicates do not justify a production patch.

## Stop rule

Do not proceed to observable 10 until observable 9 is classified `PASS` and recorded. No production implementation change is authorized under this acceptance slice.
