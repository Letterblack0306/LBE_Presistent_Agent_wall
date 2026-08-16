# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — evidence reconciled through CLI normal-path acceptance

## 1. Product goal

Build a persistent, provider-neutral LBE runtime where the provider reasons while LBE owns workspace/session identity, context/evidence authority, mode/policy, authorization, governed execution, receipts, validation/completion truth, and persistent state.

## 2. Non-negotiable invariants

- provider/model changes must not change LBE authority;
- current workspace/runtime evidence outranks memory/reference history;
- only registered governed tools may execute;
- operation IDs/receipts prevent unintended duplicate execution;
- provider continuation consumes receipts but owns no execution authority;
- terminal completion belongs to deterministic LBE validation, not provider/model prose;
- CLI/TUI/API surfaces are control/projection layers, never duplicate authority owners;
- no second session/context/retrieval/mode/authorization/tool/receipt/completion/continuation/recovery owner.

## 3. Current roadmap state

```text
R3  PROVEN_COMPLETE
R4  PROVEN_COMPLETE
R5  PROVEN_COMPLETE
R6A PROVEN_COMPLETE
R6B PROVEN_COMPLETE
R6C PROVEN_COMPLETE
R6D PROVEN_COMPLETE
R6E PROVEN_COMPLETE
R6F PROVEN_COMPLETE
CLI PROVEN_COMPLETE
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current completed phase:

```text
phase: CLI_NORMAL_PATH_ACCEPTANCE
slice: PROVE_THIN_NONINTERACTIVE_CLI_OVER_ACCEPTED_PERSISTENT_RUNTIME_AUTHORITIES
status: PASS
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
base_sha: d12f4d20a462047c0c451d8d1d734601fc1d45e9
acceptance_head: 0cdd2fa025878f591334409237d0dca8bb615a32
release_path_authorized: true
publish_allowed_now: false
```

## 4. Accepted phases

R3 through R6F and CLI normal-path acceptance are `PROVEN_COMPLETE`. Do not reopen them without new contradictory current evidence.

## 5. R6F — Completion and validation

**Classification: `PROVEN_COMPLETE`.** Terminal completion is evidence-owned through the accepted persistent coding runtime. Provider/reasoning `COMPLETED` remains provisional until persisted completion requirements and producer-bound evidence yield deterministic `READY`, which alone promotes canonical task state to `COMPLETED / VALIDATED_COMPLETION`.

Canonical records:

```text
docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_GATE.md
docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_CHECKPOINT.md
```

## 6. CLI control surface

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

```text
pyproject.toml lbe entry point
 -> lbe_guard_inspector.cli.main
 -> SessionMemoryRuntimeBridge / EvidenceService / provider registry+runtime / GovernedAgentGateway / CodingCompletionRuntime
 -> structured JSON/text output
```

Accepted invariants:

- session create/status/inspect persist and rehydrate canonical session/workspace state across separate processes;
- provider/model selection preserves workspace, mode, profile, permission, runtime and evidence-policy identity;
- session continue rehydrates the same persistent authority boundary;
- completion validation consumes persisted R6F contract/evidence and persists canonical COMPLETED / VALIDATED_COMPLETION;
- missing completion contract fails closed with structured non-zero output;
- CLI validation surface exposes identity inputs only and no completion-evidence/verdict/proof injection path;
- acceptance completed with no CLI/runtime/test/package source changes.

Evidence:

```text
repository baseline: 78 passed
hash: F99F0C0A9857AA1322E51D60488A42A6FD0D74FB511C47A88EDE154B022486C0
separate-process persistence: PASS
hash: 9FFA8D1A831C394B836DC09CA5D7B15F501D5F141F5499BD7A3CAEA3D766E8FB
provider-policy stability + continue: PASS
hash: C0FCE90E0449A2063EE195634F182D42EAB7BC0646CB291BCC15CE8470DA3437
persisted completion validation: PASS
hash: 313468EAD033D330FA260E1A5A50B54A445E8139CE6E2534BD78B51E2B98342B
missing contract fail closed: PASS
hash: E136BE394882256738CCAADF905E034BBA251416F5085C963591ABF47B029CE5
no evidence injection surface: PASS
hash: 8D13866680263DCE566E737BA1E28D5D70115EE95C76C0F5BC1FA93819665CE4
focused regression: 115 passed
hash: 7E0351B681A14F14264C066EF7809C4092817ABE10D5794B8AE97AB0EB2C85D2
runtime/test/package source unchanged: PASS
diff check: PASS
worktree clean: PASS
observed product falsifier: NONE
```

Canonical records:

```text
docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_GATE.md
docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_CHECKPOINT.md
```

## 7. R7 — End-to-end persistent coding/audit proof

**Classification: `PARTIALLY_PROVEN`.** This is the next release prerequisite, but it is not auto-activated by CLI PASS. Its acceptance must prove the installed/normal-path system across coding, provider switch, resume after external workspace change, read-only audit, and out-of-authority stop behavior without introducing new authority.

## 8. Release/package readiness

**Classification: `PARTIALLY_PROVEN`.** Release publication is authorized in intent but remains blocked by evidence prerequisites. Required before version/tag/publish:

```text
R7 installed E2E PASS
clean installation
package-content audit
secret/state exclusion
supported runtime matrix
full/focused regression
installed smoke proof
```

Package metadata currently declares `lbe-guard-inspector` version `0.2.0` with Python `>=3.11`; existence of packaging metadata does not prove release readiness.

## 9. Evidence-reconciled progression

```text
R3 PASS
 -> R4 PASS
 -> R5 PASS
 -> R6A PASS
 -> R6B PASS
 -> R6C PASS
 -> R6D PASS
 -> R6E PASS
 -> R6F PASS
 -> CLI normal-path PASS
 -> R7 installed end-to-end acceptance
 -> release/package readiness acceptance
 -> version/tag/publish
```

## 10. Final invariant

```text
Provider reasons and proposes.
Persistent runtime orchestrates.
LBE owns authority and execution.
CLI exposes existing authority but does not own it.
Receipts carry governed evidence.
Validation proves.
Completion truth belongs to LBE.
Release claims require installed/runtime/package evidence, not lower-layer inference.
```
