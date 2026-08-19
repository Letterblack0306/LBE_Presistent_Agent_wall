# R7 Installed End-to-End Acceptance Gate

Status: **OPEN — OBSERVABLE 14 ACTIVE — IMPLEMENTATION LOCKED — NEXT OBSERVABLE LOCKED**

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_14_SOURCE_UNCHANGED_UNLESS_REAL_FALSIFIER
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
resume_after_repair: true
status: OPEN
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: SOURCE_UNCHANGED_UNLESS_REAL_FALSIFIER_PROOF
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
14. **ACTIVE:** source remains unchanged unless a real falsifier activates a separate repair slice;
15. clean worktree plus exact limitations/falsifiers.

## Accepted installed evidence through observable 13

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
```

Observable 6 proved that fresh installed current-workspace evidence re-read an externally changed file and returned the exact new SHA while persistent task authority remained intact.

Observable 11 decisive proof: `6234EA61F2A2E8A8FE962515278B3ED8229EC5B2CD4AB92FFBAABCEAC6D2DA6D`.

Observable 12 proved credential/secret non-leakage (`PASS`): provider JSON body, runtime result, receipts, completion evidence, CLI stdout/stderr, persisted state, workspace/source/acceptance files, and SQLite raw bytes stayed clean; the configured canary appeared only in its ephemeral input and the outbound provider transport header (name `authorization`).

Observable 13 proved the repaired installed package can build a self-contained wheel containing the locked Cline worker dependency tree, install into a fresh isolated venv, resolve `@cline/agents` without source-tree dependency state, execute the governed provider/tool/final continuation, persist receipts and completion evidence, preserve LBE-only completion authority, restore session/task state in fresh processes, prevent credential leakage, and avoid unexpected workspace/source mutation. The only intermediate failure after dependency provisioning was a stale probe assertion that compared completion requirement IDs against evidence kinds; the runtime behavior matched the canonical completion contract and the harness was corrected.

## Observable 14 predicate

Prove that the canonical source checkout remains unchanged by the installed-runtime acceptance flow itself and that no product/source patch is made merely because of a harness, fixture, provider, environment, or assertion failure.

Required invariants:

```text
canonical branch remains main
HEAD equals origin/main before and after the proof
tracked source diff remains unchanged across the bounded proof
no production/runtime/package source file is modified by installed execution
no repair slice is activated without a reproducible product falsifier
harness-only failures remain classified as harness failures
installed/runtime evidence is collected outside the canonical source implementation paths
any generated probe/wheel/venv artifacts remain untracked or otherwise outside accepted source state
implementation_allowed remains false throughout observable 14
architecture_changes_allowed remains false
```

## Falsifier

Any tracked source mutation caused by the installed/runtime proof, any source patch made without a reproducible product falsifier, any authority/policy drift that silently re-enables implementation, or any acceptance flow that depends on modifying canonical source state is an Observable 14 falsifier.

Generated local validation artifacts are not by themselves a source mutation, but they must be reported exactly and must not be misclassified as canonical source changes.

## Stop rule

Observable 14 is the only active acceptance slice. Do not run Observable 15 or change production code until Observable 14 is classified `PASS`. A real product falsifier requires a separately activated bounded repair slice. Harness, fixture, provider, environment, or assertion failures that do not prove a product/source defect do not authorize implementation changes.
