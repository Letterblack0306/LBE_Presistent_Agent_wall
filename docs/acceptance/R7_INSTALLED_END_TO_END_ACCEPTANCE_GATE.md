# R7 Installed End-to-End Acceptance Gate

Status: **FAIL — INSTALLED CODING AUTHORITY COMPOSITION FALSIFIER — NEXT PHASE LOCKED**

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: PROVE_INSTALLED_PERSISTENT_AGENT_NORMAL_PATH_OVER_ACCEPTED_AUTHORITIES
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
status: FAIL
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: USER_VISIBLE_RUNTIME
release_path_authorized: true
publish_allowed_now: false
```

## Selection rationale

CLI normal-path acceptance is `PROVEN_COMPLETE`. R7 was activated to prove that the shipped/installed surface composes the already accepted persistent runtime authorities without creating a second authority or relying on source-tree-only behavior.

## Existing authority chain expected for reuse

```text
installed lbe entry point
 -> lbe_guard_inspector.cli.main
 -> persistent session/runtime owners
 -> provider controller/adapter
 -> GovernedAgentGateway
 -> governed authorization/tool orchestration
 -> receipt-backed provider continuation
 -> persistent task/checkpoint state
 -> CodingCompletionRuntime / deterministic validation
```

Reuse decision on activation: `REUSE`.

## Acceptance question

Can a clean installed LBE normal path perform persistent coding/audit work across separate processes and restart boundaries, preserve LBE authority while provider/model changes, revalidate after external workspace change, keep audit read-only, fail closed outside authority, and reach completion only through accepted evidence-owned validation?

## Required observables

1. build/install from the exact accepted repository head into a clean isolated environment and prove the installed `lbe` command resolves without source-tree import leakage;
2. create a persistent installed session bound to one explicit workspace/project/mode/provider/policy identity;
3. execute one bounded coding task through the normal installed command path and prove governed tool execution/receipts rather than direct provider workspace mutation;
4. prove provider/model switch does not change workspace, mode, permission, profile, evidence policy, or LBE authority identity;
5. terminate the invoking process and prove a fresh installed process resumes the same persistent session/task identity;
6. make one bounded external workspace change between invocations, then prove resume observes/revalidates current workspace truth rather than stale checkpoint state;
7. prove read-only audit/investigation mode cannot mutate workspace state;
8. prove an out-of-workspace, forbidden, or otherwise out-of-authority requested action stops fail-closed and produces no unauthorized workspace mutation;
9. prove receipt/provider continuation remains correlated across the accepted governed execution path;
10. prove provider/reasoning completion remains provisional until persisted completion evidence yields deterministic validation;
11. prove terminal `COMPLETED / VALIDATED_COMPLETION` persists and is visible from a fresh installed process;
12. prove installation/runtime execution does not leak credentials or persistent secrets into repository files, logs, receipts, or acceptance artifacts;
13. run focused installed/runtime regression and record exact package/head/environment/runtime evidence;
14. prove project source remains unchanged unless a real product falsifier requires a separately activated repair slice;
15. leave worktree clean and record exact limitations/falsifiers.

## Evidence reached before stop

```text
observable 1 exact-head isolated install: PASS
  package: lbe-guard-inspector 0.2.0
  import: isolated venv site-packages
  installed lbe entrypoint: exit 0
  checkout import leakage: none observed
  command_hash: 0D8A27FD810FF4068BD4F8DDBFDB1A6A3DC62E45BC2E0D6F8F9A9164DF1303F4

observable 2 persistent installed session: PASS
  create_hash: 27328C32D6F2BA14A68A6798819F32B583D49ED6E93A2FB3553020019C85D9E7
  fresh_process_status_inspect_hash: E748592638C757A490053E85BD51E649E20DCF110C81FFD336308A8E7A1445E3

observable 3 governed coding execution + receipts: FAIL
  installed code exit: 0
  runtime outcome: INSUFFICIENT_EVIDENCE
  task status: blocked
  response.read_only: true
  captured provider stage: planning
  captured provider approved_tools: workspace.read
  marker: R7_CODE_PROVIDER_AUTHORITY_READ_ONLY=PROVEN
  command_hash: A2B146E0501F096D870E2ED15A4331366FB954E8F137D7CD980EC97E2FBAE7B4
```

## Proven falsifier

The current installed `lbe code` normal path does not expose the required governed coding execution/receipt path. Runtime capture proves the provider receives only `workspace.read`, and the returned response is explicitly read-only. The required coding mutation/receipt composition was therefore not reached.

Observed composition:

```text
installed lbe code
 -> GovernedAgentGateway
 -> LBERequestController reasoning/inspection path
 -> provider approved_tools = [workspace.read]
 -> read_only response
 -> no governed coding execution/receipt continuation reached
```

This falsifies observable 3 and therefore R7 as a whole. It does **not** reopen or invalidate the accepted R6E lower-layer authority; it demonstrates an installed normal-path composition gap between the CLI/gateway and the accepted governed tool authority.

## Stop rule applied

Later R7 observables are intentionally not executed after this decisive falsifier. Provider switching, restart/resume, external-change revalidation, audit, fail-closed, receipt correlation, completion, secret-state and release readiness cannot compensate for the missing normal coding execution path.

## Repair boundary

No source/runtime/test/package patch is authorized by this failed acceptance gate itself. Before code changes, activate a separate bounded repair slice whose single question is why installed `lbe code` does not reach the accepted R6E governed tool orchestration/receipt path and what the smallest active-owner composition correction is.

## Evidence ladder result

```text
installed package identity                 PASS
isolated installed smoke                  PASS
persistent installed session              PASS
one governed coding path                  FAIL — decisive falsifier
remaining R7 evidence                     STOPPED
```

## Forbidden work while failed

- continuing R7 as if observable 3 passed;
- release/package-readiness activation;
- version bump/tag/publish;
- source/runtime/test/package implementation changes without a separately activated bounded repair slice;
- creating a second execution/session/provider/authorization/receipt authority instead of connecting the existing owners.

## Completion predicate

`FAIL`. R7 cannot PASS until a separately governed repair restores the installed normal coding composition and R7 is rerun from the appropriate installed evidence boundary.
