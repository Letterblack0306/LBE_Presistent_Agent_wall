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

> Does a successful provider/Cline turn remain provisional until persisted deterministic completion validation satisfies the LBE-owned registered completion contract?

Required proof:

1. run installed `lbe code` from isolated site-packages against a deterministic local provider;
2. allow `GovernedAgentGateway` to establish the normal registered coding completion contract rather than injecting a synthetic replacement;
3. provider/Cline turn reaches its normal successful terminal state and may state that the task is complete;
4. provider-facing runtime remains `lbe_completion_truth=false`;
5. after reasoning success, persistent task remains `running / AWAITING_VALIDATION`, not completed;
6. verify the registered contract contains `source_change`, `focused_test`, and `git_status` requirements;
7. for the bounded no-mutation task, deterministic evidence must not satisfy the full contract: focused test may pass, while absent task-bound source change and unreconciled git-state requirements fail;
8. installed `session validate` must reject completion as `FAILED / VALIDATION_FAILED`, never `READY / VALIDATED_COMPLETION`;
9. source checkout stays clean and the disposable workspace remains unchanged apart from ignored validation cache artifacts.

Source contract used to define the discriminator:

- `GovernedAgentGateway._establish_coding_contract()` installs the registered policy only when no contract exists;
- the registered coding policy requires `source_change`, `focused_test`, and `git_status`;
- coding invokes the three trusted producers after reasoning;
- `CodingCompletionRuntime.run_reasoning()` records successful reasoning as `RUNNING / AWAITING_VALIDATION`;
- only `CompletionVerdict.READY` maps to `COMPLETED / VALIDATED_COMPLETION`;
- deterministic failed evidence maps to `FAILED / VALIDATION_FAILED`.

## Prior invocation classification

Command hash:

`D366A3D81B771F3CEA6377A37EAA2CE72391C6A8627C3FDA5D240D307AA68E9F`

Classification:

```text
TEST_HARNESS_COMPLETION_CONTRACT_INTERFERENCE
product falsifier: NOT REACHED
production change justified: NO
```

The probe pre-persisted a custom `focused_test`-only contract. Because task completion contracts are immutable and the gateway correctly preserves an existing contract, the production `source_change` producer then rejected its undeclared evidence kind before the provider-turn completion predicate was reached. The corrected probe removes this synthetic contract and uses the real registered policy.

## Falsifier

Any successful provider/Cline turn that directly persists completion, any `VALIDATED_COMPLETION` before deterministic validation, any provider truth accepted as LBE truth, or any `READY` verdict despite deterministic failed/unsatisfied registered requirements is a product falsifier.

Harness/provider/fixture failures that do not reach these predicates do not justify a production patch.

## Stop rule

Do not proceed to observable 11 until observable 10 is classified `PASS` and recorded. No production implementation change is authorized under this acceptance slice.
