# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_7_AUDIT_INVESTIGATION_READ_ONLY
status: OPEN
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: INSTALLED_RUNTIME_READ_ONLY_NEGATIVE_PROOF
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
  external/post-change sha256: b4bfc4aa24ec334f1f29ff6db0f729377ccf26715303ad2b2d546fdb49093484
  current marker/hash observed: PASS
  fresh-process resume: PASS
  task authority preserved: PASS
  source worktree: clean
```

## Observable 7 — active

Question: do installed audit and investigation execution remain read-only and reject provider-requested mutation without changing workspace state?

Required installed-runtime proof:

1. use a disposable workspace separate from the project source checkout;
2. create one audit session and one investigation session through installed `lbe session create`;
3. audit session authority must resolve as audit/read-only;
4. investigation session authority must resolve as investigation/read-only;
5. local provider response deliberately requests `workspace.create_candidate_text` targeting a sentinel file;
6. installed audit/investigation must reject the unapproved mutation tool at the LBE controller boundary;
7. sentinel file must not be created;
8. baseline tracked file hash and Git status must remain unchanged;
9. no governed mutation receipt with status `EXECUTED` may appear;
10. session mode/permission/runtime-policy identity must remain unchanged after the invocation;
11. installed import must resolve from isolated venv site-packages;
12. project source worktree must remain clean.

Expected safe failure for the provider's write request is an LBE-owned read-only rejection such as `UNKNOWN_TOOL`; the precise result must come from installed runtime evidence rather than be assumed.

## Source contract used only to define the falsifier

```text
LBERequestController._APPROVED_TOOLS = {workspace.read}
_validate_plan rejects other provider-requested tools
GovernedAgentGateway swaps to GovernedClineReasoningController only for coding
R6B removes write/test_candidate capabilities in audit/investigation
```

## Current classification

```text
audit_investigation_read_only: PENDING
implementation_changes: FORBIDDEN
observable_8: LOCKED
release_publish_allowed_now: false
```

Any real workspace mutation, approved mutation tool, executed mutation receipt, provider-direct write, or policy identity drift is a product falsifier and stops R7. Harness failures do not justify production changes.
