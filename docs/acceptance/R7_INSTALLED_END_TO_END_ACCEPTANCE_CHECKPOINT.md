# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_4_PROVIDER_MODEL_SWITCH_AUTHORITY_STABILITY
status: PASS
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

observable 4 provider/model switch authority stability: PASS
  decisive command hash: E0CB10D5EE683C0485D44AB7FC51A17591716D3BB2EF62F77E2A48D6559E97E6
  installed package: isolated venv site-packages
  before provider/model: openai-compatible / r7-model-a
  after provider/model: openai-compatible / r7-model-b
  fresh-process readback: PASS
  source worktree: clean
```

## Observable 4 result

Question: does normal installed provider/model switching alter only provider/model identity while preserving all LBE session/workspace/mode/policy authority fields?

Result: `PASS`.

The installed `provider select` operation changed only the model selection from `r7-model-a` to `r7-model-b` under the same registered `openai-compatible` provider.

The following persisted authority fields remained identical before and after the switch and were re-read successfully from a fresh installed process:

- session_id
- project_workspace_id
- canonical_workspace_root
- mode
- permission
- runtime_policy
- active_profile_id
- permission_policy_id
- evidence_policy_id

The provider-selection response also reported unchanged policy state for:

- active_profile_id
- evidence_policy_id
- permission
- permission_policy_id
- runtime_policy

No source-tree import leakage was observed and the project source worktree remained clean.

## Harness failures excluded

```text
DF8532C422FD8422078B7CB41FCEE5491648FE924D1ECACFBFE76ACF0AA1BA41
  TEST_HARNESS_POWERSHELL_PARSE_ERROR
  product implication: NONE
  observable 4 did not execute in that invocation
```

## Current classification

```text
provider_switch_policy_stability: PASS
fresh_process_readback_for_observable_4: PASS
implementation_changes: FORBIDDEN
observable_5: LOCKED_PENDING_EXPLICIT_ADVANCE
release_publish_allowed_now: false
```

No product falsifier was observed in observable 4.
