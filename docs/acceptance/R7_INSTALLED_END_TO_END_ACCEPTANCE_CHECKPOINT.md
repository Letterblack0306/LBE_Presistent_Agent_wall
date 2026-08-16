# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_8_FAIL_CLOSED_AUTHORITY_BOUNDARIES
status: OPEN
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: INSTALLED_RUNTIME_FAIL_CLOSED_AUTHORITY_PROOF
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
  decisive command hash: 1E59BF836E469E6652D839F076EE7A48E0D531796F39C0D35AB0F8974EADD576
```

## Observable 8 — active

Question:

> Do forbidden, out-of-workspace, and otherwise out-of-authority mutation attempts fail closed with no workspace mutation, while preserving the distinction between path-handler rejection and R6C DENY/ESCALATE receipts?

Required installed-runtime proof:

1. installed package resolves from isolated venv site-packages;
2. normal installed coding path receives a provider request to create a forbidden `.env` target and does not create it;
3. normal installed coding path receives a provider request using an out-of-workspace `../` path and does not create anything outside the workspace;
4. rejected normal-path attempts produce no `EXECUTED` mutation receipt;
5. installed R6E invocation with `explicitly_forbidden=true` returns authorization `DENY` and receipt `DENIED` without invoking the handler;
6. installed R6E invocation with `within_workspace_scope=false` returns authorization `ESCALATE` and receipt `ESCALATED` without invoking the handler;
7. baseline tracked workspace hash/Git state remain unchanged after all rejected attempts;
8. project source checkout stays clean.

## Layer distinction

The normal coding path passes provider path arguments to the governed mutation handler after R6C authorizes the `test_candidate` capability for coding mode. Path-specific forbidden/escape rejection is therefore expected to appear as fail-closed tool execution failure, not necessarily as R6C `DENY`/`ESCALATE`.

R6C `DENY` and `ESCALATE` are separately proven by invoking the installed R6E authority surface with explicit authority-context flags. These must not be conflated with path validation.

## Falsifiers

```text
forbidden path is created
out-of-workspace path escapes and is created
explicitly forbidden request is not DENY / DENIED
out-of-scope request is not ESCALATE / ESCALATED
denied/escalated request invokes handler
workspace or Git state changes after rejected attempts
```

## Current classification

```text
fail_closed_authority_boundaries: PENDING
implementation_changes: FORBIDDEN
observable_9: LOCKED
release_publish_allowed_now: false
```

A product falsifier stops R7 and requires a separately activated repair slice. Harness/provider/fixture failures do not justify implementation changes.
