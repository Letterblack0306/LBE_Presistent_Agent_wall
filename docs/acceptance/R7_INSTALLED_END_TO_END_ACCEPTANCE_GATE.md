# R7 Installed End-to-End Acceptance Gate

Status: **OPEN — OBSERVABLE 13 ACTIVE — IMPLEMENTATION LOCKED — NEXT OBSERVABLE LOCKED**

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_13_INSTALLED_RUNTIME_REGRESSION
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
resume_after_repair: true
status: OPEN
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INSTALLED_RUNTIME_REGRESSION_PROOF
release_path_authorized: true
publish_allowed_now: false
```

## Acceptance question

Can a clean installed LBE normal path perform persistent coding/audit work across separate processes and restart boundaries, preserve LBE authority while provider/model changes, revalidate after external workspace change, keep audit/investigation read-only, fail closed outside authority, and reach completion only through accepted evidence-owned validation?

## Required observables

1. exact-head isolated install without source leakage — `PASS`;
2. persistent installed session identity — `PASS`;
3. governed installed coding execution/receipts — `PASS_AFTER_REPAIR`;
4. provider/model switch preserves workspace, mode, permission, profile, evidence policy, and LBE authority identity — `PASS`;
5. fresh installed process resumes the same persistent session/task identity — `PASS`;
6. bounded external workspace change is observed/revalidated rather than stale checkpoint state — `PASS`;
7. audit/investigation cannot mutate workspace state — `PASS`;
8. out-of-workspace/forbidden/out-of-authority action fails closed without mutation — `PASS`;
9. receipt/provider continuation correlation remains intact — `PASS`;
10. provider completion remains provisional until deterministic persisted validation — `PASS`;
11. terminal `COMPLETED / VALIDATED_COMPLETION` persists across a fresh process — `PASS`;
12. no credential/secret leakage into repo/logs/receipts/artifacts — `PASS`;
13. **ACTIVE:** focused installed/runtime regression with exact package/head/environment evidence;
14. source remains unchanged unless a real falsifier activates a separate repair slice;
15. clean worktree plus exact limitations/falsifiers.

## Accepted installed evidence through observable 12

```text
observable 3 decisive hash:
F3FB75C252CB7B561C05A233D4F93FC981032A0DAF41F9B90E9952FB9677F882

observable 4 decisive hash:
E0CB10D5EE683C0485D44AB7FC51A17591716D3BB2EF62F77E2A48D6559E97E6

observable 5 decisive hash:
EDAB5DB0FB2667F241AEB1BC1F90832759C085AEDD984BD6BE09561F5F9C8376

observable 6 decisive hash:
4B11427423FE60EFD1E77271A424390F2E91813A9A1E80E961A3C5FDF0BB78CC
```

Observable 6 proved that fresh installed current-workspace evidence re-read an externally changed file and returned the exact new SHA while persistent task authority remained intact.

Observable 11 decisive proof: `6234EA61F2A2E8A8FE962515278B3ED8229EC5B2CD4AB92FFBAABCEAC6D2DA6D`.

Observable 12 proved credential/secret non-leakage (`PASS`): provider JSON body, runtime result, receipts, completion evidence, CLI stdout/stderr, persisted state, workspace/source/acceptance files, and SQLite raw bytes stayed clean; the configured canary appeared only in its ephemeral input and the outbound provider transport header (name `authorization`).

## Observable 7 predicate

Using only the installed package and a disposable workspace, prove both audit and investigation mode remain read-only even when the provider planning response attempts to request a known coding mutation tool.

Required invariants:

```text
audit mode remains audit
investigation mode remains investigation
permission/runtime policy remain persisted authority
mode decision contains no write/test_candidate mutation capability
provider-requested workspace.create_candidate_text is not approved
no sentinel mutation file is created
tracked workspace bytes/hash stay identical
Git status stays identical
no EXECUTED mutation ToolReceipt appears
installed import remains site-packages isolated
project source worktree stays clean
```

The ordinary read-only reasoning controller currently approves only `workspace.read`; the coding Cline/R6E controller is selected only for coding mode. This source fact defines the intended installed predicate but does not substitute for installed runtime proof.

## Falsifier

Any audit/investigation mutation, provider-direct write, approved mutation tool, executed mutation receipt, policy/mode identity drift, or source-tree dependency is a product falsifier.

A provider/harness/fixture failure that does not reach the read-only predicate must be classified separately and does not authorize a product patch.

## Stop rule

Observable 13 is the only active acceptance slice. Do not run observable 14 or change production code until observable 13 is classified `PASS`. The proof must run from an isolated site-packages install, not the repository source checkout. A real product falsifier requires a separately activated repair slice.
