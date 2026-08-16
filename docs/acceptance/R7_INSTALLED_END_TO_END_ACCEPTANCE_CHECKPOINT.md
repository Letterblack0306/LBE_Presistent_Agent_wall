# R7 Installed End-to-End Acceptance Checkpoint

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: PROVE_INSTALLED_PERSISTENT_AGENT_NORMAL_PATH_OVER_ACCEPTED_AUTHORITIES
status: FAIL
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
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
decision: REUSE ATTEMPTED — INSTALLED COMPOSITION FALSIFIER OBSERVED
evidence: lower layers R3-R6F and CLI remain accepted, but installed `lbe code` does not expose the required governed coding execution path.
```

## Architecture change

```text
introduced: no
user_authorized: release progression and explicit R7 activation only
canonical_docs_updated_first: yes
repair_authorized: no — separate bounded repair slice required before source changes
```

## Validation evidence

```text
installed_package_identity: PASS
  evidence: package 0.2.0 imported from isolated venv site-packages
  command_hash: 0D8A27FD810FF4068BD4F8DDBFDB1A6A3DC62E45BC2E0D6F8F9A9164DF1303F4

isolated_install_smoke: PASS
  evidence: installed lbe entrypoint exit 0; no checkout import leakage; project worktree clean
  command_hash: 0D8A27FD810FF4068BD4F8DDBFDB1A6A3DC62E45BC2E0D6F8F9A9164DF1303F4

persistent_installed_session: PASS
  evidence: installed session create + fresh-process status/inspect preserved session/workspace/mode/provider/profile/permission/evidence-policy identity
  create_hash: 27328C32D6F2BA14A68A6798819F32B583D49ED6E93A2FB3553020019C85D9E7
  persistence_hash: E748592638C757A490053E85BD51E649E20DCF110C81FFD336308A8E7A1445E3

governed_coding_execution: FAIL
  evidence: installed `lbe code` returned exit 0 but response was `INSUFFICIENT_EVIDENCE`, task status `blocked`, and response `read_only: true`; captured provider planning request advertised only `workspace.read`
  decisive_provider_tools: workspace.read
  decisive_marker: R7_CODE_PROVIDER_AUTHORITY_READ_ONLY=PROVEN
  command_hash: A2B146E0501F096D870E2ED15A4331366FB954E8F137D7CD980EC97E2FBAE7B4

provider_switch_policy_stability: NOT RUN — STOPPED AFTER FALSIFIER
fresh_process_resume: NOT RUN — STOPPED AFTER FALSIFIER
external_workspace_change_revalidation: NOT RUN — STOPPED AFTER FALSIFIER
read_only_audit: NOT RUN — STOPPED AFTER FALSIFIER
out_of_authority_fail_closed: NOT RUN — STOPPED AFTER FALSIFIER
receipt_continuation_correlation: NOT RUN — REQUIRED CODING EXECUTION PATH NOT REACHED
evidence_owned_terminal_completion: NOT RUN — REQUIRED CODING EXECUTION PATH NOT REACHED
secret_state_exclusion: NOT RUN
focused_installed_runtime_regression: NOT RUN
git_diff_check: PASS THROUGH DECISIVE PROBE
worktree_clean: PASS THROUGH DECISIVE PROBE
```

## Harness failures excluded from product conclusions

```text
D6AA248185F3AC186B57686390CEF6B814A516A62241FBBDAE66EEB490C3E37E
  TEST_HARNESS_NATIVE_PIPE_TERMINATION after successful install/help output

68FA21D7166BDFEEB01A985558740FDFE7CAF3FE18E3BBC811F605C541AF9049
  TEST_HARNESS_COMMAND_TRUNCATION / PowerShell parse failure

FE7CA1177EE05E097DEFC68CA1B549DC9FFBCCC92ACDD8024011863E8BF975AC
  TEST_HARNESS_SCRIPT_GENERATION quoting failure

E9DC7DD94830111504618F148CF9F04D4C72A78E2237A504C08B2F82CDF6C173
  TEST_HARNESS_FIXTURE_ENCODING (UTF-8 BOM); corrected by 417C4EC5A9CCE98A792B8F1FCEC89DD24F7959FA1B63AC52F2A856CAE2ABAF69
```

## Falsifier state

```text
observed_falsifier: YES
classification: INSTALLED_NORMAL_PATH_AUTHORITY_COMPOSITION_MISMATCH

expected:
installed lbe code
 -> GovernedAgentGateway
 -> authorization + GovernedToolOrchestrator
 -> governed coding tool execution
 -> receipts
 -> provider continuation

observed:
installed lbe code
 -> GovernedAgentGateway
 -> LBERequestController planning/inspection path
 -> provider approved_tools = [workspace.read]
 -> read_only response
 -> no governed coding mutation/receipt path reached
```

This directly falsifies required observable 3 and the gate completion predicate. It does not invalidate the already accepted lower-layer R6E tool orchestration authority; it proves the installed normal coding composition does not currently reach that authority.

## Unverified

R7 cannot continue to later observables because the required normal installed governed coding path is absent from the observed composition. Later provider-switch/resume/audit/completion/release checks are intentionally not used to mask this earlier falsifier.

## Document conflicts

```text
NONE REQUIRED TO CLASSIFY FALSIFIER
```

## Readiness

```text
release_path_authorized: true
release_publish_allowed_now: false
project_user_ready: NO
release_ready: NO
next_phase_locked: true
repair_slice_required: true
```
