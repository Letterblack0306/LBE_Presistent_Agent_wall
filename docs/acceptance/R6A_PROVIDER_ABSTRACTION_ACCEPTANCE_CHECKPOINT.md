# R6A Provider Abstraction Acceptance Checkpoint

```text
phase: R6A_PROVIDER_ABSTRACTION_ACCEPTANCE
slice: PROVE_SAME_SESSION_PROVIDER_SWITCH_WITHOUT_LBE_AUTHORITY_DRIFT
status: UNVERIFIED

base_sha: 32a987971ff0ea6643f7ea9ff89df7f5132ef850
implementation_sha: NOT_APPLICABLE_ACCEPTANCE_ONLY
required_evidence_level: INTEGRATION
next_phase_locked: true
```

## Requirements

- prove provider A and provider B use the existing registered provider/controller path;
- prove equivalent logical requests can execute across A -> B in one persisted session/workspace contract;
- preserve session/task/workspace identity and LBE policy/permission state across provider change;
- allow only intended provider/model configuration fields to change;
- preserve provider-neutral LBE request/response/evidence semantics;
- prove no provider-specific governance/session/reasoning owner is introduced;
- run focused provider/session regression on the exact acceptance head;
- record exact evidence, limitations and falsifiers.

## Existing owner

```text
ProviderRegistry
build_provider_controller
reasoning_provider backend contract
LBERequestController
SessionMemoryRuntimeBridge
WorkspaceMemoryStore
```

## Reuse decision

```text
decision: REUSE
evidence: provider composition and session-provider persistence already exist independently; combined R6A acceptance is missing.
```

## Architecture change

```text
introduced: no
user_authorized: no new architecture requested
canonical_docs_updated_first: yes
```

## Validation evidence

```text
source_owner_inspection: PASS
generic_provider_composition_source_test: PRESENT_NOT_YET_RUN_ON_GATE_HEAD
persisted_provider_switch_source_test: PRESENT_NOT_YET_RUN_ON_GATE_HEAD
same_session_provider_a_then_b_integration: NOT RUN
workspace_session_task_identity_preserved: NOT RUN
mode_permission_policy_preserved: NOT RUN
provider_neutral_response_contract: NOT RUN
focused_regression: NOT RUN
git_diff_check: NOT RUN
worktree_clean: NOT RUN
```

## Falsifier state

```text
observed_falsifier: NONE YET
```

## Unverified

- combined same-session A -> B runtime behavior;
- exact provider/session invariants on the active R6A acceptance head;
- focused regression and final scope/worktree proof.

## Document conflicts

```text
none known at activation
```

## Readiness

```text
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```
