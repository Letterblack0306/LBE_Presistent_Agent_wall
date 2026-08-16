# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_6_EXTERNAL_WORKSPACE_CHANGE_REVALIDATION
status: PASS
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

observable 6 external workspace change revalidation: PASS
  decisive command hash: 4B11427423FE60EFD1E77271A424390F2E91813A9A1E80E961A3C5FDF0BB78CC
  pre-change sha256: 2c8d9f54650e903b63976d5f66332c069c8bfcb4c6cfb8febc1422bc971d154b
  external-change sha256: b4bfc4aa24ec334f1f29ff6db0f729377ccf26715303ad2b2d546fdb49093484
  post-change observed sha256: b4bfc4aa24ec334f1f29ff6db0f729377ccf26715303ad2b2d546fdb49093484
  external marker observed: PASS
  fresh-process resume: PASS
  task authority preserved: PASS
  source worktree: clean
```

## Observable 6 result

Question: after a bounded external workspace change between installed invocations, does the next installed invocation observe and revalidate current workspace truth rather than relying on stale persisted/checkpoint evidence?

Result: `PASS`.

The disposable installed R7 workspace file `test_smoke.py` was reset to a known pre-change state and retrieved through the installed `session evidence` surface. Its pre-change SHA-256 was:

`2c8d9f54650e903b63976d5f66332c069c8bfcb4c6cfb8febc1422bc971d154b`

After that invocation exited, the file was changed directly outside LBE with marker `R7_OBS6_EXTERNAL_CHANGE_V1`. The direct external-change SHA-256 was:

`b4bfc4aa24ec334f1f29ff6db0f729377ccf26715303ad2b2d546fdb49093484`

A fresh installed invocation resumed the same persistent session/task and LBE current-workspace evidence returned the external marker and the exact changed SHA-256. The persisted task authority remained `r7-task-create / running / AWAITING_VALIDATION`.

This proves that the installed evidence path re-reads current workspace bytes after an external change instead of treating pre-change evidence/checkpoint state as current truth.

## Harness and diagnostic failures excluded

```text
745BCDE8D77CC9C496D9752656CCE90459169ADCDE01F1FCCA319248BEA6E059
  TEST_HARNESS_ENVIRONMENT_OMISSION
  observable 6 did not reach revalidation because the probe omitted explicit config/governance/state environment paths.

85EE21AEED72A7E030FEC521EF2F8130AE56ABAA5BB50A50FB1B64D053E9738A
  TEST_HARNESS_QUERY_SHAPE_MISMATCH
  the two-term query split one match into the filename and one into file content; current retrieval requires two matches on one side for a two-term query.

916E894792AADBE99A378009CDFEC17E1AB1BC93CD4F75CFB595B4CBA9A21D93
  DIAGNOSTIC PASS
  direct file truth confirmed the changed marker/hash while the over-constrained two-term evidence query returned no matching evidence.
```

No production/runtime source change was justified by these harness/query-shape failures.

## Current classification

```text
external_workspace_change_revalidation: PASS
implementation_changes: FORBIDDEN
observable_7: LOCKED_PENDING_EXPLICIT_ADVANCE
release_publish_allowed_now: false
```

No product falsifier was observed in observable 6.
