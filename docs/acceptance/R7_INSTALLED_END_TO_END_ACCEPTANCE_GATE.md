# R7 Installed End-to-End Acceptance Gate

Status: **OPEN — OBSERVABLE 15 ACTIVE — IMPLEMENTATION LOCKED — NEXT PHASE LOCKED**

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_15_CLEAN_WORKTREE_LIMITATIONS_FALSIFIERS
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
resume_after_repair: true
status: OPEN
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: CLEAN_WORKTREE_PLUS_EXACT_LIMITATIONS_FALSIFIERS_PROOF
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
13. focused installed/runtime regression with exact package/head/environment evidence — `PASS_AFTER_REPAIR`;
14. source remains unchanged unless a real falsifier activates a separate repair slice — `PASS`;
15. **ACTIVE:** clean worktree plus exact limitations/falsifiers.

## Accepted installed evidence through observable 14

```text
observable 3 decisive hash:
F3FB75C252CB7B561C05A233D4F93FC981032A0DAF41F9B90E9952FB9677F882

observable 4 decisive hash:
E0CB10D5EE683C0485D44AB7FC51A17591716D3BB2EF62F77E2A48D6559E97E6

observable 5 decisive hash:
EDAB5DB0FB2667F241AEB1BC1F90832759C085AEDD984BD6BE09561F5F9C8376

observable 6 decisive hash:
4B11427423FE60EFD1E77271A424390F2E91813A9A1E80E961A3C5FDF0BB78CC

observable 13 decisive hash:
A2AC0D1058E3D817DF8E35A1540D6BC89D492C25F7D2D6A3936D54C44BD9A3AE

observable 14 decisive hash:
ED2E9D5763EEB5C57B073C002D616B3DC4298C067D5EFDBE3D463088E74DD054
```

Observable 6 proved that fresh installed current-workspace evidence re-read an externally changed file and returned the exact new SHA while persistent task authority remained intact.

Observable 11 decisive proof: `6234EA61F2A2E8A8FE962515278B3ED8229EC5B2CD4AB92FFBAABCEAC6D2DA6D`.

Observable 12 proved credential/secret non-leakage (`PASS`): provider JSON body, runtime result, receipts, completion evidence, CLI stdout/stderr, persisted state, workspace/source/acceptance files, and SQLite raw bytes stayed clean; the configured canary appeared only in its ephemeral input and the outbound provider transport header (name `authorization`).

Observable 13 proved the repaired installed package can build a self-contained wheel containing the locked Cline worker dependency tree, install into a fresh isolated venv, resolve `@cline/agents` without source-tree dependency state, execute the governed provider/tool/final continuation, persist receipts and completion evidence, preserve LBE-only completion authority, restore session/task state in fresh processes, prevent credential leakage, and avoid unexpected workspace/source mutation. The only intermediate failure after dependency provisioning was a stale probe assertion that compared completion requirement IDs against evidence kinds; the runtime behavior matched the canonical completion contract and the harness was corrected.

Observable 14 proved canonical `main` remained identical to `origin/main`, implementation and architecture remained locked, tracked source remained unchanged, and generated acceptance evidence remained untracked. The first Observable 14 command incorrectly invoked the implementation commit gate as a read-only validator; that was classified as a harness error and did not authorize a source change.

## Observable 15 predicate

Prove final R7 acceptance closure without overstating product or release readiness.

Required invariants:

```text
canonical branch remains main
HEAD equals origin/main
tracked canonical worktree is clean
no generated validation artifact is staged or tracked as product source
all remaining untracked/generated artifacts are enumerated and classified
implementation_allowed remains false
architecture_changes_allowed remains false
all known R7 harness failures remain recorded as harness failures
all known product limitations and remaining falsifiers are stated exactly
R7 acceptance completion does not itself imply package/release/publish readiness
publish_allowed_now remains false until separate release/package readiness acceptance passes
```

## Exact remaining limitations at Observable 15 entry

```text
R7 proves the accepted installed-runtime behaviors only for the bounded evidence and environments exercised by its observables.
The repaired Python wheel now carries the locked Cline worker dependency tree; this increases wheel size and requires the package build environment to provide the declared Node runtime/npm build dependency path.
Generated local validation directories and the standalone documentation instruction file are not accepted product source and must remain untracked or be removed before any clean-worktree claim that requires zero untracked files.
R7 acceptance is not release/package readiness acceptance and does not authorize versioning, tagging, or publishing.
```

## Observable 15 falsifier

Any tracked canonical worktree dirtiness, staged/generated evidence mistaken for source, HEAD/origin drift, omission or material understatement of known limitations/falsifiers, silent enabling of implementation/architecture changes, or claim of release/publish readiness before separate package/release acceptance is an Observable 15 falsifier.

## Stop rule

Observable 15 is the only active acceptance slice. No implementation, architecture, version, tag, release, or publish work is authorized by this gate. A real product falsifier requires a separately activated bounded repair slice. R7 may close only after Observable 15 is classified `PASS`; package/release readiness remains a separate acceptance step.
