# Current Implementation Gate

Status: **OPEN — R7 INSTALLED END-TO-END ACCEPTANCE — OBSERVABLE 10 — IMPLEMENTATION LOCKED**

Current phase: `R7_INSTALLED_END_TO_END_ACCEPTANCE`

Current slice: `OBSERVABLE_10_PROVIDER_COMPLETION_PROVISIONAL`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md
status: OPEN
required_evidence_level: INSTALLED_RUNTIME_PROVISIONAL_COMPLETION_AUTHORITY_PROOF
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
observable 9: PASS
```

Observable 9 decisive proof: `A323D6AB93CAFECC6A291F785614B92AE007CC0015B0DB959359F06747E044D9`.

## Active observable 10

Question:

> Does a successful provider/Cline turn remain provisional until persisted deterministic completion validation satisfies the LBE completion contract?

Required proof:

1. run installed `lbe code` from isolated site-packages against a deterministic local provider;
2. provider/Cline turn reaches its normal successful terminal state;
3. provider-facing runtime remains `lbe_completion_truth=false`;
4. after reasoning success, the persistent task is `running / AWAITING_VALIDATION`, not completed;
5. an explicit persisted completion contract contains at least one required evidence kind that is not satisfied;
6. installed `session validate` evaluates persisted contract/evidence and returns `BLOCKED`;
7. task becomes `blocked / VALIDATION_INCOMPLETE`, never `COMPLETED / VALIDATED_COMPLETION`;
8. no provider text or successful turn is accepted as completion evidence;
9. source checkout stays clean.

Source contract used to define the discriminator:

- `CodingCompletionRuntime.run_reasoning()` records successful reasoning as `RUNNING / AWAITING_VALIDATION`;
- `evaluate_completion()` returns `BLOCKED` when required evidence is missing or stale;
- only `CompletionVerdict.READY` maps to `COMPLETED / VALIDATED_COMPLETION`;
- `session validate` reloads the persisted contract and persisted evidence before finalization.

## Falsifier

Any successful provider/Cline turn that directly persists completion, any `VALIDATED_COMPLETION` before deterministic validation, or any `READY` verdict with required evidence missing is a product falsifier.

Harness/provider/fixture failures that do not reach these predicates do not justify a production patch.

## Stop rule

Do not proceed to observable 11 until observable 10 is classified `PASS` and recorded. No production implementation change is authorized under this acceptance slice.
