# Current Implementation Gate

Status: **OPEN — R7 INSTALLED END-TO-END ACCEPTANCE — OBSERVABLE 5 — IMPLEMENTATION LOCKED**

Current phase: `R7_INSTALLED_END_TO_END_ACCEPTANCE`

Current slice: `OBSERVABLE_5_FRESH_PROCESS_SESSION_TASK_RESUME`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md
status: OPEN
required_evidence_level: INSTALLED_RUNTIME_SEPARATE_PROCESSES
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
publish_allowed_now: false
```

## Accepted R7 baseline

```text
observable 1 isolated installed package identity: PASS
observable 2 persistent installed session identity: PASS
observable 3 governed coding execution + receipt continuation: PASS_AFTER_REPAIR
observable 4 provider/model switch authority stability: PASS
```

Observable 3 decisive repaired proof: `F3FB75C252CB7B561C05A233D4F93FC981032A0DAF41F9B90E9952FB9677F882`.

Observable 4 decisive proof: `E0CB10D5EE683C0485D44AB7FC51A17591716D3BB2EF62F77E2A48D6559E97E6`.

## Active observable 5

Question:

> After the prior invoking process is gone, can a newly launched installed process recover the same persisted session and task identity/state from the database?

Required proof:

1. launch installed `lbe` in one process and capture session/task identity;
2. allow that process to exit;
3. launch a distinct installed process and re-read the same session/task;
4. prove session/workspace/mode/provider/policy identity is unchanged;
5. prove task identity and provisional state survive (`running / AWAITING_VALIDATION`);
6. no source-tree import leakage and source worktree stays clean.

Acceptance is evidence-only. No source/runtime/package implementation change is authorized. A product falsifier stops R7 and requires a separately activated repair slice.

## Stop rule

Do not proceed to observable 6 until observable 5 is classified `PASS` and recorded.
