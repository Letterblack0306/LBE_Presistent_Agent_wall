# R7 Installed End-to-End Acceptance Gate

Status: **OPEN — ACCEPTANCE PROOF ONLY — RELEASE PATH ACTIVE — NEXT PHASE LOCKED**

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: PROVE_INSTALLED_PERSISTENT_AGENT_NORMAL_PATH_OVER_ACCEPTED_AUTHORITIES
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: USER_VISIBLE_RUNTIME
release_path_authorized: true
publish_allowed_now: false
```

## Selection rationale

CLI normal-path acceptance is `PROVEN_COMPLETE`. The next release prerequisite is the installed end-to-end path. R7 must prove the shipped/installed surface composes the already accepted persistent runtime authorities without creating a second authority or relying on source-tree-only behavior.

## Existing authority chain to reuse

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

Reuse decision: `REUSE`.

Do not introduce a second session store, provider authority, authorization resolver, tool dispatcher, checkpoint owner, completion gate, or installed-only runtime architecture.

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

## Falsifier

R7 cannot PASS if the installed command imports the checkout accidentally, creates a second authority, loses session/task identity across processes, misses an external workspace change, allows read-only audit mutation, executes out-of-authority work, lets provider prose establish terminal completion, loses receipt correlation, leaks credentials/secrets, or differs materially from the accepted source/runtime ownership model.

## Evidence ladder

```text
installed package identity
-> isolated installed smoke
-> persistent installed session
-> one governed coding path
-> provider switch + fresh-process resume
-> external workspace drift revalidation
-> read-only audit stop
-> out-of-authority fail-closed stop
-> evidence-owned terminal completion
-> installed/runtime regression
-> secret/state + diff/worktree proof
-> checkpoint
```

## Forbidden work

- source/runtime/test/package implementation changes before a real falsifier;
- architecture changes;
- provider-specific authority outside accepted adapters;
- direct ungoverned workspace editing by the provider;
- version bump/tag/publish;
- release/package-readiness activation while R7 is OPEN.

## Completion predicate

PASS only when the installed normal path is proven end to end over accepted persistent authorities at user-visible/runtime evidence level. PASS does not auto-activate release/package readiness or publication.
