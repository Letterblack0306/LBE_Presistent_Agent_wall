# Current Implementation Gate

Status: **OPEN — R7 INSTALLED END-TO-END ACCEPTANCE — OBSERVABLE 6 — IMPLEMENTATION LOCKED**

Current phase: `R7_INSTALLED_END_TO_END_ACCEPTANCE`

Current slice: `OBSERVABLE_6_EXTERNAL_WORKSPACE_CHANGE_REVALIDATION`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md
status: OPEN
required_evidence_level: INSTALLED_RUNTIME_EXTERNAL_CHANGE_REVALIDATION
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
```

Observable 5 decisive proof: `EDAB5DB0FB2667F241AEB1BC1F90832759C085AEDD984BD6BE09561F5F9C8376`.

## Active observable 6

Question:

> After a bounded external workspace change between invocations, does a fresh installed invocation revalidate current workspace truth instead of trusting stale persisted/checkpoint evidence?

Acceptance proof must use the disposable installed R7 workspace, mutate one known file directly outside LBE, then start a fresh installed process and prove the new marker/hash is observed through LBE evidence while the persistent session/task authority remains intact.

No source/runtime/package implementation change is authorized. A product falsifier stops R7 and requires a separately activated repair slice.

## Stop rule

Do not proceed to observable 7 until observable 6 is classified `PASS` and recorded.
