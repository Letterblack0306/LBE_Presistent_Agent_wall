# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_11_VALIDATED_COMPLETION_FRESH_PROCESS
status: OPEN
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
required_evidence_level: INSTALLED_RUNTIME_VALIDATED_COMPLETION_FRESH_PROCESS_PROOF
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
observable 10: PASS
  decisive command hash: 3C5DCA411AF217AE301344B803B6D9BD1753CE52B66A5C746129C05BC889B946
```

## Observable 11 — active

Question:

> When the registered deterministic completion contract is fully satisfied, does installed LBE persist `COMPLETED / VALIDATED_COMPLETION`, and does a fresh installed process recover the same terminal task/session identity?

Required installed-runtime proof:

1. installed package resolves from isolated venv site-packages;
2. normal coding path establishes the registered contract `source_change`, `focused_test`, `git_status`;
3. deterministic provider requests one governed workspace mutation and then finishes the same turn;
4. R6C/R6E mutation succeeds exactly once;
5. trusted `source_change`, `focused_test`, and `git_status` evidence all persist as `PASS`;
6. provider completion remains non-authoritative and task stays `running / AWAITING_VALIDATION` before explicit validation;
7. installed `session validate` returns `READY` with all registered requirement IDs satisfied;
8. task persists as `completed / VALIDATED_COMPLETION`;
9. a distinct fresh installed process rehydrates the same session/task/workspace/provider/model identity and sees the same terminal state;
10. persisted completion contract/evidence remain present after restart;
11. project source checkout remains clean.

## Completion authority chain under test

```text
provider tool request
 -> governed R6E mutation
 -> trusted source_change PASS
 -> trusted focused_test PASS
 -> trusted git_status PASS
 -> provider turn terminal success with lbe_completion_truth=false
 -> task RUNNING / AWAITING_VALIDATION
 -> session validate
 -> CompletionVerdict.READY
 -> task COMPLETED / VALIDATED_COMPLETION
 -> fresh installed process
 -> same completed task/session identity
```

## Falsifiers

```text
all registered evidence PASS but session validate != READY
READY does not persist COMPLETED / VALIDATED_COMPLETION
fresh process loses or changes terminal task/session authority
persisted completion evidence/contract disappears across process restart
provider prose rather than deterministic evidence establishes completion
```

## Current classification

```text
validated_completion_fresh_process: PENDING
implementation_changes: FORBIDDEN
observable_12: LOCKED
release_publish_allowed_now: false
```

A product falsifier stops R7 and requires a separately activated repair slice. Harness/provider/fixture failures do not justify implementation changes.
