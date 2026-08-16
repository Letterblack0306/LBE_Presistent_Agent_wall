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

> Does a successful provider/Cline turn remain provisional until persisted deterministic completion validation satisfies the LBE completion contract?

Required installed-runtime proof:

1. installed package resolves from isolated venv site-packages;
2. persist an explicit completion contract for the bounded task;
3. deterministic local provider completes one installed coding turn normally;
4. provider terminal output may state that the task is complete, but `lbe_completion_truth` must remain false;
5. installed coding response may report reasoning outcome `COMPLETED`, but persistent task state must be `running / AWAITING_VALIDATION`;
6. the persisted completion contract must contain at least one required evidence kind with no passing persisted evidence;
7. a fresh installed `session validate` must return completion verdict `BLOCKED`;
8. persisted task must become `blocked / VALIDATION_INCOMPLETE`, not `completed / VALIDATED_COMPLETION`;
9. source checkout remains clean.

## Completion authority chain under test

```text
provider/Cline terminal success
 -> response outcome COMPLETED
 -> CodingCompletionRuntime.run_reasoning
 -> task RUNNING / AWAITING_VALIDATION
 -> persisted completion contract/evidence
 -> session validate
 -> evaluate_completion
 -> BLOCKED when required evidence is missing
```

Only `READY` may establish `COMPLETED / VALIDATED_COMPLETION`.

## Falsifiers

```text
provider/Cline success directly makes task COMPLETED
provider text/prose establishes LBE completion truth
missing required evidence still yields READY
VALIDATED_COMPLETION appears before deterministic evidence satisfies the contract
```

## Current classification

```text
provider_completion_provisional: PENDING
implementation_changes: FORBIDDEN
observable_11: LOCKED
release_publish_allowed_now: false
```

A product falsifier stops R7 and requires a separately activated repair slice. Harness/provider/fixture failures do not justify implementation changes.
