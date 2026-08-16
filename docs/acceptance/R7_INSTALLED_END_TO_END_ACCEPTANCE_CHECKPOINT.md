# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_5_FRESH_PROCESS_SESSION_TASK_RESUME
status: PASS
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: INSTALLED_RUNTIME_SEPARATE_PROCESSES
implementation_allowed: false
next_phase_locked: true
```

## Accepted evidence carried forward

```text
observable 1 installed package identity/isolation: PASS
observable 2 persistent installed session identity: PASS
observable 3 governed coding execution + receipts: PASS_AFTER_REPAIR
  decisive command hash: F3FB75C252CB7B561C05A233D4F93FC981032A0DAF41F9B90E9952FB9677F882
  authorization: ALLOW
  receipt: EXECUTED
  provider continuation: PASS
  provider completion truth: false
  persisted task: running / AWAITING_VALIDATION
  source worktree: clean

observable 4 provider/model switch authority stability: PASS
  decisive command hash: E0CB10D5EE683C0485D44AB7FC51A17591716D3BB2EF62F77E2A48D6559E97E6
  before provider/model: openai-compatible / r7-model-a
  after provider/model: openai-compatible / r7-model-b
  authority invariants: PASS
  fresh-process readback: PASS
  source worktree: clean

observable 5 fresh-process session/task resume: PASS
  decisive command hash: EDAB5DB0FB2667F241AEB1BC1F90832759C085AEDD984BD6BE09561F5F9C8376
  process A exited before process B: PASS
  session resume: PASS
  task resume: PASS
  authority invariants: PASS
  persisted provider/model: openai-compatible / r7-model-b
  persisted task: r7-task-create / running / AWAITING_VALIDATION
  installed package: isolated venv site-packages
  source worktree: clean
```

## Observable 5 result

Question: after the prior invoking process is gone, can a newly launched installed process recover the same persisted session and task identity/state from the database?

Result: `PASS`.

Two distinct installed processes opened the same persistent database. Process A read the session/task and exited before process B was launched. Process B recovered the same persisted authority and task state.

Session invariants preserved:

- session_id
- project_workspace_id
- canonical_workspace_root
- mode
- permission
- runtime_policy
- provider_id
- provider_model
- active_profile_id
- permission_policy_id
- evidence_policy_id

Task invariants preserved:

- task_id = r7-task-create
- status = running
- last_outcome = AWAITING_VALIDATION

No source-tree import leakage was observed and the project source worktree remained clean.

## Current classification

```text
fresh_process_session_task_resume: PASS
implementation_changes: FORBIDDEN
observable_6: LOCKED_PENDING_EXPLICIT_ADVANCE
release_publish_allowed_now: false
```

No product falsifier was observed in observable 5.
