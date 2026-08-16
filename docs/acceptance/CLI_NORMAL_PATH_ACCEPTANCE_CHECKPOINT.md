# CLI Normal-Path Acceptance Checkpoint

```text
phase: CLI_NORMAL_PATH_ACCEPTANCE
slice: PROVE_THIN_NONINTERACTIVE_CLI_OVER_ACCEPTED_PERSISTENT_RUNTIME_AUTHORITIES
status: UNVERIFIED
base_sha: d12f4d20a462047c0c451d8d1d734601fc1d45e9
implementation_sha: NOT_APPLICABLE_ACCEPTANCE_ONLY
required_evidence_level: INTEGRATION
next_phase_locked: true
```

## Requirements

- prove package `lbe` entry point resolves to the existing CLI owner;
- prove session create/continue/status/inspect use canonical persistent state;
- prove provider selection preserves workspace/mode/policy identity;
- prove invalid/missing/unknown inputs fail closed;
- prove evidence retrieval delegates to canonical EvidenceService;
- prove validation delegates to R6F completion runtime and accepts no CLI-authored evidence;
- prove normal separate-process CLI invocations preserve state;
- prove mode commands delegate through accepted gateway/provider owners;
- run focused CLI/runtime regression;
- record exact evidence, falsifiers, diff and clean-worktree proof.

## Existing owner

```text
pyproject.toml lbe -> lbe_guard_inspector.cli:main
lbe_guard_inspector.cli
SessionMemoryRuntimeBridge
GovernedAgentGateway
EvidenceService
CodingCompletionRuntime
provider registry/runtime adapters
```

## Reuse decision

```text
decision: REUSE
evidence: CLI is already explicitly thin and repository tests cover the constituent ownership boundaries; normal-path integrated acceptance is missing.
```

## Architecture change

```text
introduced: no
user_authorized: release progression only; no new architecture requested
canonical_docs_updated_first: yes
```

## Validation evidence

```text
source_owner_inspection: PASS
entrypoint_inspection: PASS
repository_cli_tests: NOT RUN ON CLI GATE HEAD
normal_process_lifecycle: NOT RUN
evidence_delegation: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
completion_delegation: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
provider_policy_preservation: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
fail_closed_errors: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
mode_gateway_delegation: NOT RUN
focused_regression: NOT RUN
git_diff_check: NOT RUN
worktree_clean: NOT RUN
```

## Falsifier state

```text
observed_falsifier: NONE YET
```

## Unverified

- normal separate-process CLI persistence on the exact gate head;
- integrated thin-control-plane lifecycle across CLI commands;
- focused regression and final scope/worktree proof.

## Readiness

```text
release_path_authorized: true
release_publish_allowed_now: false
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```
