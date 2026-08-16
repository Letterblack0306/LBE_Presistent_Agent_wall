# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_5_FRESH_PROCESS_SESSION_TASK_RESUME
status: OPEN
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
```

## Observable 5 — active

Question: after the prior invoking process is gone, can a newly launched installed process recover the same persisted session and task identity/state from the database?

Required invariants:

Session:
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

Task:
- task_id = r7-task-create
- status = running
- last_outcome = AWAITING_VALIDATION

Required proof:

1. first installed process reads session and task state;
2. first process exits;
3. a distinct installed process reads the same database;
4. all session authority fields and task identity/state match;
5. installed package resolves from isolated venv site-packages;
6. project source worktree remains clean.

## Current classification

```text
fresh_process_session_task_resume: PENDING
implementation_changes: FORBIDDEN
observable_6: LOCKED
release_publish_allowed_now: false
```

Any persisted identity/state loss is a product falsifier and stops R7. Harness failures do not justify product changes.
