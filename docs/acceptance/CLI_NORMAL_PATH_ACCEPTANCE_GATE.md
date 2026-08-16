# CLI Normal-Path Acceptance Gate

Status: **OPEN — ACCEPTANCE PROOF ONLY — RELEASE PATH ACTIVE — NEXT PHASE LOCKED**

```text
phase: CLI_NORMAL_PATH_ACCEPTANCE
slice: PROVE_THIN_NONINTERACTIVE_CLI_OVER_ACCEPTED_PERSISTENT_RUNTIME_AUTHORITIES
base_sha: d12f4d20a462047c0c451d8d1d734601fc1d45e9
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
release_path_authorized: true
publish_allowed_now: false
```

## Selection rationale

R6F completion/validation is now `PROVEN_COMPLETE`. The next release prerequisite is the CLI normal path. The existing `lbe` console entry point and `lbe_guard_inspector.cli` already expose session, provider, mode, evidence, policy, permissions, and validation operations as thin adapters over accepted runtime owners. This gate proves that existing path before R7 installed end-to-end acceptance.

## Existing owner

```text
pyproject.toml [project.scripts] lbe -> lbe_guard_inspector.cli:main
lbe_guard_inspector.cli
SessionMemoryRuntimeBridge
GovernedAgentGateway
EvidenceService
provider registry/runtime adapters
CodingCompletionRuntime
```

## Reuse decision

```text
REUSE
```

Do not introduce another CLI runtime, session store, provider selector, evidence authority, permission resolver, tool dispatcher, or completion gate.

## Acceptance question

Can the existing non-interactive `lbe` CLI create and rehydrate persistent sessions, inspect canonical state, switch provider/model without changing workspace policy, expose bounded evidence through the existing evidence owner, run governed mode commands through the existing gateway/provider boundary, and expose R6F completion validation without becoming an authority itself?

## Required observables

1. `lbe` package entry point resolves to `lbe_guard_inspector.cli:main`;
2. session create persists explicit workspace/session/mode/provider/policy identity;
3. session continue/status/inspect rehydrate/read existing state rather than creating parallel state;
4. provider select changes provider/model only and preserves workspace/mode/policy identity;
5. unknown provider/missing session/invalid input fails closed with structured non-zero CLI result;
6. session evidence delegates to canonical `EvidenceService` with persisted workspace identity;
7. session validate consumes persisted completion contract/evidence through `CodingCompletionRuntime` and cannot accept CLI-authored evidence;
8. normal mode commands delegate through `GovernedAgentGateway` and existing provider controller;
9. audit/investigation/coding remain mode contracts rather than CLI personalities;
10. text/JSON output formatting does not alter persistent state;
11. repository-owned CLI/runtime tests pass on the exact acceptance head;
12. one normal process-level CLI lifecycle proves state persists across separate CLI invocations;
13. runtime/test implementation source remains unchanged unless a real falsifier is proven;
14. worktree remains clean and diff scope is acceptance documentation only.

## Falsifier

CLI acceptance cannot PASS if the CLI creates a second runtime authority, mutates policy while only selecting a provider, accepts completion evidence directly from operator/model input, bypasses persistent session/workspace identity, reports success for a failed command, or normal separate-process CLI invocations do not preserve the accepted persistent state.

## Evidence ladder

```text
source/entrypoint owner inspection
-> repository-owned CLI tests
-> normal separate-process session create/status/continue/provider/validation discriminator
-> governed mode delegation discriminator where existing deterministic/provider fixture permits
-> focused CLI + runtime regression
-> diff/scope/worktree proof
-> checkpoint
```

## Forbidden work

- CLI/runtime/test implementation before a real defect is proven;
- new session/provider/evidence/authorization/completion authority;
- R7 installed E2E or release publication while this gate is OPEN;
- version bump/tag/publish;
- architecture changes.

## Completion predicate

PASS only when the existing `lbe` normal path is proven to be a thin persistent control surface over accepted authorities with fail-closed behavior and no second authority. PASS does not auto-activate R7 or release publication.
