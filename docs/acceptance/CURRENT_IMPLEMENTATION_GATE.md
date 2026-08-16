# Current Implementation Gate

Status: **OPEN — CLI NORMAL-PATH ACCEPTANCE — RELEASE PATH AUTHORIZED — NEXT PHASE LOCKED**

Current phase: `CLI_NORMAL_PATH_ACCEPTANCE`

Current slice: `PROVE_THIN_NONINTERACTIVE_CLI_OVER_ACCEPTED_PERSISTENT_RUNTIME_AUTHORITIES`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_CHECKPOINT.md
kind: acceptance proof, not implementation
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
status: OPEN
```

## Accepted baseline

```text
R3: PROVEN_COMPLETE
R4: PROVEN_COMPLETE
R5: PROVEN_COMPLETE
R6A: PROVEN_COMPLETE
R6B: PROVEN_COMPLETE
R6C: PROVEN_COMPLETE
R6D: PROVEN_COMPLETE
R6E: PROVEN_COMPLETE
R6F: PROVEN_COMPLETE
```

Final synchronized R6F closure baseline:

```text
HEAD: d12f4d20a462047c0c451d8d1d734601fc1d45e9
origin/main: d12f4d20a462047c0c451d8d1d734601fc1d45e9
R6F gate: PASS
next_phase_locked: true
LoopTool closure hash: 476F905A97BDFF464514F5030F3F478AE0EC3959B44733213634443834FAE1AC
```

## Why CLI acceptance is selected next

The release path remains explicitly authorized, while publication remains blocked. The existing package entry point is `lbe = lbe_guard_inspector.cli:main`, and the CLI source declares itself a thin control plane that must not become a second session, provider, permission, tool, evidence, or completion authority.

Existing CLI owner path:

```text
operator/process argv
 -> lbe package console entry point
 -> lbe_guard_inspector.cli.main
 -> existing SessionMemoryRuntimeBridge / EvidenceService / provider registry+runtime / GovernedAgentGateway / CodingCompletionRuntime
 -> structured JSON/text result
```

Reuse decision: `REUSE`.

## Acceptance question

Can the existing normal non-interactive CLI preserve persistent session/workspace identity across separate process invocations, expose accepted provider/evidence/completion/runtime services without owning their authority, and fail closed for invalid or unauthorized inputs?

## Required observables

1. package `lbe` entrypoint resolves to `lbe_guard_inspector.cli:main`;
2. session create persists explicit identity and policy fields;
3. session continue/status/inspect rehydrate/read canonical persistent state;
4. provider selection changes provider/model only and preserves policy identity;
5. missing session/unknown provider/invalid input returns structured non-zero failure;
6. session evidence delegates to the canonical EvidenceService;
7. session validate consumes persisted R6F contract/evidence through CodingCompletionRuntime;
8. mode commands delegate through GovernedAgentGateway/provider controller;
9. separate process CLI invocations preserve state;
10. output format changes presentation only, not persistent authority/state;
11. focused regression passes with runtime/test source unchanged and clean worktree.

## Release boundary

```text
release_path_authorized: true
publish_allowed_now: false
remaining: CLI normal-path -> R7 installed E2E -> release/package readiness
```

No version bump, tag, build-for-publish, or external publish is allowed while CLI acceptance is OPEN. A real falsifier must trigger a separate bounded repair slice before CLI/runtime/test source changes.
