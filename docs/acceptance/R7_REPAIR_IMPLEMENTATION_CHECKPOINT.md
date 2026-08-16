# R7 Repair Implementation Checkpoint

```text
phase: R7_REPAIR_IMPLEMENTATION
slice: COMPOSE_INSTALLED_CODING_WITH_EXISTING_GOVERNED_EXECUTION
status: OPEN
base_sha: 9138b47b279c0f4207bda952fd30521a828c952a
implementation_sha: 1ecaaea9c99ee17e711a4696717992cb0ad43b39
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

## Implemented repair

```text
installed coding composition:
  lbe code -> existing GovernedAgentGateway -> governed Cline-backed ReasoningController
  -> existing GovernedClineWorker -> existing R6E ToolRegistry/GovernedToolOrchestrator
  -> existing R6C authorization -> ToolReceipt -> typed tool.result continuation

production mutation capability:
  workspace.create_text
  -> workspace-relative only
  -> create-only; target must not already exist
  -> existing parent directory required
  -> capability: test_candidate
  -> forbidden/allowed write policy enforced from existing governance context
  -> hash-backed structured ToolReceipt evidence

completion:
  existing CodingCompletionRuntime remains authoritative;
  provider COMPLETED remains provisional / AWAITING_VALIDATION until deterministic validation.
```

## Validation evidence

```text
source_review: PASS
implementation_head: 1ecaaea9c99ee17e711a4696717992cb0ad43b39

focused source/contract validation:
  command_hash: 79E6E9BEEBC9D7F96DA0CCE37ACC05F047BB645CAAF4CB5BBC4D000243600DF3
  python_compile: PASS
  focused_tests: 23 passed
  diff_check: PASS
  worktree: clean

cline/r6e integration:
  command_hash: 8BBB9C0E246DE5054D1F0A863E2117D8A6CB37123F3E8B06E33322B9D24A147D
  tests: 29 passed
  classification: PASS
  note: same command later failed only because guessed completion-test filenames did not exist; this was a harness-path failure and does not invalidate the 29-test integration pass.

completion authority regression:
  command_hash: 4A0A7CB3E0B015B693AF643D21714F0E16E33ADAF2CD398ABB14F842C0CA5B56
  discovered_tests:
    - test_completion_contract_persistence.py
    - test_completion_evidence_persistence.py
    - test_completion_evidence_producers.py
    - test_completion_gate.py
    - test_task_completion_policy.py
  result: 34 passed

cli/gateway regression:
  command_hash: 4A0A7CB3E0B015B693AF643D21714F0E16E33ADAF2CD398ABB14F842C0CA5B56
  result: 23 passed

source_integration: PASS

installed dependency probe:
  command_hash: B7172DF55EB95403EE98A245D9D0E670936CC496C74C1E114A475FC991593B99
  worker_package_json: present
  worker_package_lock: present
  worker_node_modules_inside_wheel: absent
  @cline/agents resolution in installed environment: PASS

isolated_install: PENDING_FOR_REPAIRED_HEAD
r7_observable_3: PENDING
```

## Harness failures excluded

```text
- missing guessed completion test filenames in command hash 8BBB9C0E... = TEST_HARNESS_INVALID_TEST_PATH
- no product patch justified by that failure
- previously proven Cline/R6E integration remains valid
```

## Remaining unverified

- exact repaired wheel installs from `1ecaaea9c99ee17e711a4696717992cb0ad43b39` without checkout leakage;
- installed `lbe code` causes an actual governed `workspace.create_text` mutation through R6C/R6E;
- installed provider tool-call / LBE-call / operation / receipt IDs remain correlated end to end;
- same Cline turn resumes after `tool.result`;
- task remains provisional until deterministic completion validation;
- clean exact-head state after installed proof.

## Next evidence rung

```text
build exact repaired wheel
 -> fresh isolated venv
 -> remove PYTHONPATH
 -> prove package import/entrypoint identity
 -> execute installed coding task with provider tool proposal
 -> workspace.create_text through existing R6C/R6E
 -> prove actual file + hash-backed ToolReceipt + correlation + same-turn continuation
 -> prove AWAITING_VALIDATION rather than provider-owned terminal completion
 -> classify R7 observable 3
```

## Document conflicts

None known.

## Status

`OPEN`
