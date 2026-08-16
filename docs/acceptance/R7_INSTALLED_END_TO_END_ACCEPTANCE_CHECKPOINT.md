# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_8_FAIL_CLOSED_AUTHORITY_BOUNDARIES
status: PASS
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: INSTALLED_RUNTIME_FAIL_CLOSED_AUTHORITY_PROOF
implementation_allowed: false
next_phase_locked: true
```

## Accepted R7 evidence

```text
observable 1: PASS
observable 2: PASS
observable 3: PASS_AFTER_REPAIR
observable 4: PASS
observable 5: PASS
observable 6: PASS
observable 7: PASS
  decisive command hash: 1E59BF836E469E6652D839F076EE7A48E0D531796F39C0D35AB0F8974EADD576
observable 8: PASS
  decisive command hash: 98B3EC987725DB5B103E6B11B64DD60C4C73EA2F249BC88F260403A52127FDEE
```

## Observable 8 result

The installed acceptance probe exercised both the normal coding path and the installed R6C/R6E authorization surface.

Observed:

```text
R7_OBS8_FORBIDDEN_PATH_FAIL_CLOSED=PASS
R7_OBS8_OUT_OF_WORKSPACE_PATH_FAIL_CLOSED=PASS
R7_OBS8_R6C_EXPLICIT_FORBIDDEN_DENY=PASS
R7_OBS8_R6C_OUT_OF_SCOPE_ESCALATE=PASS
R7_OBS8_REJECTED_AUTHORITY_HANDLER_NOT_INVOKED=PASS
R7_OBS8_NO_REJECTED_MUTATION_EXECUTED=PASS
R7_OBS8_WORKSPACE_UNCHANGED=PASS
R7_OBS8_FAIL_CLOSED_AUTHORITY_BOUNDARIES=PASS
R7_OBSERVABLE_8=PASS
R7_OBS8_SOURCE_WORKTREE_CLEAN=PASS
```

The normal installed coding path rejected a forbidden `.env` target and an out-of-workspace `../` target with zero mutation. Separately, R6C returned `DENY` for an explicitly forbidden request and `ESCALATE` for an out-of-scope request; R6E projected those as non-executing receipts, and neither rejected authority request invoked the mutation handler.

This preserves the layer distinction: path-specific validation may fail inside the bounded mutation handler after coding capability authorization, while explicit authority-scope decisions remain owned by R6C.

## Current classification

```text
fail_closed_authority_boundaries: PASS
implementation_changes: FORBIDDEN
observable_9: LOCKED_PENDING_EXPLICIT_ADVANCE
release_publish_allowed_now: false
```

No product falsifier was observed in observable 8.
