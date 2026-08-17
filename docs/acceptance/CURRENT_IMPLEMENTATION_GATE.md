# Current Implementation Gate

Status: **OPEN — R7 INSTALLED END-TO-END ACCEPTANCE — OBSERVABLE 11 — IMPLEMENTATION LOCKED**

Current phase: `R7_INSTALLED_END_TO_END_ACCEPTANCE`

Current slice: `OBSERVABLE_11_VALIDATED_COMPLETION_FRESH_PROCESS`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md
status: OPEN
required_evidence_level: INSTALLED_RUNTIME_VALIDATED_COMPLETION_FRESH_PROCESS_PROOF
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
observable 10: PASS
```

Observable 10 decisive proof: `3C5DCA411AF217AE301344B803B6D9BD1753CE52B66A5C746129C05BC889B946`.

## Active observable 11

Question:

> When the registered deterministic completion contract is fully satisfied, does installed LBE persist `COMPLETED / VALIDATED_COMPLETION`, and does a fresh installed process recover the same terminal task/session identity?

Required proof:

1. use isolated installed `lbe` / site-packages only;
2. create a fresh disposable Git workspace with a passing pytest baseline;
3. run normal installed coding against a deterministic provider that requests one governed candidate-text mutation;
4. let the normal gateway establish the registered `source_change`, `focused_test`, and `git_status` completion contract;
5. require all three trusted completion evidence kinds to persist as `PASS`;
6. before explicit validation, require persistent task state `running / AWAITING_VALIDATION` and provider `lbe_completion_truth=false`;
7. invoke installed `session validate` and require completion verdict `READY`;
8. require persisted task state `completed / VALIDATED_COMPLETION`;
9. start a fresh installed process and require it to recover the same session ID, task ID, workspace identity, provider/model identity, and terminal task state;
10. require completion contract/evidence still present and consistent after restart;
11. source checkout remains clean.

## Falsifier

Any fully passing registered contract that does not produce `READY`, any `READY` result that does not persist `COMPLETED / VALIDATED_COMPLETION`, or any fresh installed process that loses/substitutes the terminal session/task identity is a product falsifier.

Harness/provider/fixture/environment failures that do not reach these predicates do not justify a production patch.

## Stop rule

Do not proceed to observable 12 until observable 11 is classified `PASS` and recorded. No production implementation change is authorized under this acceptance slice.
