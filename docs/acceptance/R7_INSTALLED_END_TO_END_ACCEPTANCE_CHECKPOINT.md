# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: PROVE_INSTALLED_PERSISTENT_AGENT_NORMAL_PATH_OVER_ACCEPTED_AUTHORITIES
status: UNVERIFIED
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
implementation_sha: NOT_APPLICABLE_ACCEPTANCE_ONLY
required_evidence_level: USER_VISIBLE_RUNTIME
next_phase_locked: true
```

## Requirements

- prove exact-head isolated installation and installed `lbe` identity without checkout import leakage;
- prove installed persistent session/task continuity across separate processes;
- prove one normal governed coding execution with receipts;
- prove provider/model switch preserves LBE workspace/mode/policy authority;
- prove fresh-process resume after external workspace change observes current workspace truth;
- prove audit/investigation read-only behavior;
- prove out-of-authority actions stop fail-closed without mutation;
- prove receipt/provider continuation correlation;
- prove completion remains evidence-owned and terminal validated state persists;
- prove no credential/secret leakage into repo/logs/receipts/artifacts;
- run focused installed/runtime regression;
- record exact environment, package, head, evidence, diff and clean-worktree proof.

## Existing owner

```text
installed lbe console entry point
lbe_guard_inspector.cli
SessionMemoryRuntimeBridge
provider controller/adapters
GovernedAgentGateway
authorization resolver
GovernedToolOrchestrator
provider continuation
checkpoint/persistent task state
CodingCompletionRuntime
```

## Reuse decision

```text
decision: REUSE
evidence: R3-R6F and CLI normal-path acceptance already prove the constituent authorities; R7 is missing installed end-to-end composition proof.
```

## Architecture change

```text
introduced: no
user_authorized: release progression and explicit R7 activation only
canonical_docs_updated_first: yes
```

## Validation evidence

```text
installed_package_identity: NOT RUN
isolated_install_smoke: NOT RUN
persistent_installed_session: NOT RUN
governed_coding_execution: NOT RUN
provider_switch_policy_stability: NOT RUN
fresh_process_resume: NOT RUN
external_workspace_change_revalidation: NOT RUN
read_only_audit: NOT RUN
out_of_authority_fail_closed: NOT RUN
receipt_continuation_correlation: NOT RUN
evidence_owned_terminal_completion: NOT RUN
secret_state_exclusion: NOT RUN
focused_installed_runtime_regression: NOT RUN
git_diff_check: NOT RUN
worktree_clean: NOT RUN
```

## Falsifier state

```text
observed_falsifier: NONE YET
```

## Unverified

All R7 installed end-to-end observables remain unverified on activation. Prior lower-layer PASS evidence is accepted baseline, not a substitute for installed/runtime proof.

## Document conflicts

```text
NONE KNOWN ON ACTIVATION
```

## Readiness

```text
release_path_authorized: true
release_publish_allowed_now: false
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```
