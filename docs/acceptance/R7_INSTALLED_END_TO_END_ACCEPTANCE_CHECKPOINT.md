# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_10_PROVIDER_COMPLETION_PROVISIONAL
status: OPEN
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: INSTALLED_RUNTIME_PROVISIONAL_COMPLETION_AUTHORITY_PROOF
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
observable 9: PASS
  decisive command hash: A323D6AB93CAFECC6A291F785614B92AE007CC0015B0DB959359F06747E044D9
```

## Observable 10 — active

Question:

> Does a successful provider/Cline turn remain provisional until persisted deterministic completion validation satisfies the LBE-owned registered completion contract?

Required installed-runtime proof:

1. installed package resolves from isolated venv site-packages;
2. normal installed coding establishes the registered completion contract itself;
3. contract requirements are exactly the registered coding kinds `source_change`, `focused_test`, and `git_status`;
4. deterministic local provider completes one installed coding turn normally and may state that the task is complete;
5. provider terminal state is successful but `lbe_completion_truth` remains false;
6. installed coding response may report reasoning outcome `COMPLETED`, but persistent task state remains `running / AWAITING_VALIDATION`;
7. the no-mutation task must not satisfy the full registered deterministic contract;
8. `session validate` must reject completion from persisted evidence, expected as `FAILED / VALIDATION_FAILED` when deterministic source-change/git-state evidence fails;
9. task must never become `completed / VALIDATED_COMPLETION` from provider prose or turn success;
10. source checkout remains clean.

## Completion authority chain under test

```text
provider/Cline terminal success
 -> response outcome COMPLETED
 -> lbe_completion_truth false
 -> CodingCompletionRuntime.run_reasoning
 -> task RUNNING / AWAITING_VALIDATION
 -> registered completion contract
 -> trusted source_change / focused_test / git_status evidence
 -> session validate
 -> evaluate_completion
 -> FAILED when required deterministic evidence fails
```

Only `READY` may establish `COMPLETED / VALIDATED_COMPLETION`.

## Prior failed invocation

Command hash:

`D366A3D81B771F3CEA6377A37EAA2CE72391C6A8627C3FDA5D240D307AA68E9F`

Observed before target predicate:

```text
R7_OBS10_PERSISTED_CONTRACT=PASS
installed code => ValueError: completion evidence kind is not declared by the persisted task contract
```

Classification:

```text
TEST_HARNESS_COMPLETION_CONTRACT_INTERFERENCE
product implication: NONE
observable 10 product predicate: NOT REACHED
```

Cause: the first harness pre-persisted a synthetic `focused_test`-only contract. The gateway correctly did not replace the immutable existing contract, then its first normal trusted producer (`source_change`) correctly rejected an undeclared evidence kind. The corrected harness uses the real registered completion policy and does not alter production code.

## Falsifiers

```text
provider/Cline success directly makes task COMPLETED
provider text/prose establishes LBE completion truth
registered deterministic requirements fail but session validate still yields READY
VALIDATED_COMPLETION appears before the full deterministic contract passes
task is not provisional after successful reasoning and before validation
```

## Current classification

```text
provider_completion_provisional: PENDING
implementation_changes: FORBIDDEN
observable_11: LOCKED
release_publish_allowed_now: false
```

A product falsifier stops R7 and requires a separately activated repair slice. Harness/provider/fixture failures do not justify implementation changes.
