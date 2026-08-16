# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_4_PROVIDER_MODEL_SWITCH_AUTHORITY_STABILITY
status: OPEN
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: INSTALLED_RUNTIME_FRESH_PROCESS
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
```

## Observable 4 — active

Question: does normal installed provider/model switching alter only provider/model identity while preserving all LBE session/workspace/mode/policy authority fields?

Required invariants:

- session_id
- project_workspace_id
- canonical_workspace_root
- mode
- permission
- runtime_policy
- active_profile_id
- permission_policy_id
- evidence_policy_id

Required proof:

1. read installed session identity before switch;
2. switch to a different registered provider/model through installed `lbe provider select`;
3. compare all invariant fields before/after;
4. start a fresh installed process and prove switched provider/model plus unchanged invariants persist;
5. no source-tree import leakage;
6. project source worktree remains clean.

## Current classification

```text
provider_switch_policy_stability: PENDING
fresh_process_readback_for_observable_4: PENDING
implementation_changes: FORBIDDEN
observable_5: LOCKED
release_publish_allowed_now: false
```

Any invariant drift is a product falsifier and stops R7. Harness failures do not justify product changes.
