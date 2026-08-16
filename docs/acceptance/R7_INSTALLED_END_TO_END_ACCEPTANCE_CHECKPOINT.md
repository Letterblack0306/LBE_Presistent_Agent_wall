# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_6_EXTERNAL_WORKSPACE_CHANGE_REVALIDATION
status: OPEN
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: INSTALLED_RUNTIME_EXTERNAL_CHANGE_REVALIDATION
implementation_allowed: false
next_phase_locked: true
```

## Accepted evidence carried forward

```text
observable 1 installed package identity/isolation: PASS
observable 2 persistent installed session identity: PASS
observable 3 governed coding execution + receipts: PASS_AFTER_REPAIR
  decisive command hash: F3FB75C252CB7B561C05A233D4F93FC981032A0DAF41F9B90E9952FB9677F882

observable 4 provider/model switch authority stability: PASS
  decisive command hash: E0CB10D5EE683C0485D44AB7FC51A17591716D3BB2EF62F77E2A48D6559E97E6

observable 5 fresh-process session/task resume: PASS
  decisive command hash: EDAB5DB0FB2667F241AEB1BC1F90832759C085AEDD984BD6BE09561F5F9C8376
  session: r7-session-repair
  provider/model: openai-compatible / r7-model-b
  task: r7-task-create / running / AWAITING_VALIDATION
```

## Observable 6 — active

Question: after a bounded external workspace change between installed invocations, does the next installed invocation observe and revalidate current workspace truth rather than relying on stale persisted/checkpoint evidence?

Required proof:

1. capture installed evidence for a known workspace file before the external change;
2. terminate that invocation;
3. mutate that file directly outside LBE with a unique marker and record its new SHA-256;
4. launch a fresh installed invocation against the same persisted session/task;
5. resume/reopen the same task identity;
6. retrieve bounded current workspace evidence for the changed file;
7. prove the new external marker and new SHA-256 are observed and the pre-change content/hash are not treated as current truth;
8. prove the persisted session/task authority remains intact;
9. installed package resolves from isolated venv site-packages;
10. project source worktree remains clean.

The external mutation is confined to the disposable R7 proof workspace under the installed-test root; it must not touch the project source checkout.

## Current classification

```text
external_workspace_change_revalidation: PENDING
implementation_changes: FORBIDDEN
observable_7: LOCKED
release_publish_allowed_now: false
```

Failure to observe the new workspace truth is a product falsifier and stops R7. Harness failures do not justify product changes.
