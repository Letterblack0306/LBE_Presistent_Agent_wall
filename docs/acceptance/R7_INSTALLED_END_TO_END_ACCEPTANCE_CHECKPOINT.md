# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_9_RECEIPT_PROVIDER_CONTINUATION_CORRELATION
status: OPEN
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: INSTALLED_RUNTIME_CORRELATED_RECEIPT_CONTINUATION_PROOF
implementation_allowed: false
next_phase_locked: true
```

## Accepted R7 evidence carried forward

```text
observable 1: PASS
observable 2: PASS
observable 3: PASS_AFTER_REPAIR
observable 4: PASS
observable 5: PASS
observable 6: PASS
observable 7: PASS
observable 8: PASS
  decisive command hash: 98B3EC987725DB5B103E6B11B64DD60C4C73EA2F249BC88F260403A52127FDEE
```

## Observable 9 — active

Question:

> Does the installed governed coding loop preserve exact provider tool-call, LBE call, operation, ToolReceipt, and same-turn provider continuation correlation without duplicate execution or identity substitution?

Required installed-runtime proof:

1. installed package resolves from isolated venv site-packages;
2. deterministic local provider emits one fixed tool call for `workspace.create_candidate_text`;
3. installed coding returns exactly one executed mutation receipt;
4. the receipt operation ID embeds the same provider tool-call ID under the current turn ID;
5. receipt ID is non-empty and unique;
6. second provider request contains the same assistant tool-call ID and the corresponding tool-result message with the same tool-call ID;
7. tool-result payload delivered to continuation matches the governed mutation output;
8. exactly two provider HTTP requests occur and only one workspace mutation occurs;
9. final provider turn completes in the same LBE turn with `lbe_completion_truth=false`;
10. project source checkout stays clean.

## Correlation chain under test

```text
provider tool_call_id
 -> Node cline_tool_call_id
 -> Node-derived lbe_call_id + operation_id
 -> Python ToolRequest(operation_id)
 -> R6E ToolReceipt(receipt_id, operation_id)
 -> Python tool.result with all correlation identities
 -> Node validates pending identity
 -> same provider continuation carries tool_call_id result
```

The provider-facing OpenAI continuation is expected to carry the provider `tool_call_id`; the LBE-only receipt/lbe-call identities are validated across the Python/Node bridge and need not be exposed to the provider HTTP API.

## Falsifiers

```text
receipt operation_id does not correspond to provider tool_call_id
second provider request lacks/mismatches tool_call_id
receipt missing or duplicated
more than one mutation for one provider tool call
governed output differs from continuation tool result
turn identity changes across the correlated flow
```

## Current classification

```text
receipt_provider_continuation_correlation: PENDING
implementation_changes: FORBIDDEN
observable_10: LOCKED
release_publish_allowed_now: false
```

A product falsifier stops R7 and requires a separately activated repair slice. Harness/provider/fixture failures do not justify implementation changes.
