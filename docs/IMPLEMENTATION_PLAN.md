# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — CLI normal-path acceptance active on release path

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
CLI PARTIALLY_PROVEN — ACTIVE ACCEPTANCE
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current active phase:

```text
phase: CLI_NORMAL_PATH_ACCEPTANCE
slice: PROVE_THIN_NONINTERACTIVE_CLI_OVER_ACCEPTED_PERSISTENT_RUNTIME_AUTHORITIES
status: OPEN
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
base_sha: d12f4d20a462047c0c451d8d1d734601fc1d45e9
release_path_authorized: true
publish_allowed_now: false
```

## 4. Accepted phases

R3 through R6F are `PROVEN_COMPLETE`. Do not reopen them without new contradictory current evidence.

## 5. R6F — Completion and validation

**Classification: `PROVEN_COMPLETE`.** Terminal completion is evidence-owned through the accepted persistent coding runtime. Provider/reasoning `COMPLETED` remains provisional until persisted completion requirements and producer-bound evidence yield deterministic `READY`, which alone promotes canonical task state to `COMPLETED / VALIDATED_COMPLETION`.

Canonical records:

```text
docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_GATE.md
docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_CHECKPOINT.md
```

## 6. CLI control surface

**Classification: `PARTIALLY_PROVEN` — active acceptance.**

Existing owner path:

```text
pyproject.toml lbe entry point
 -> lbe_guard_inspector.cli.main
 -> SessionMemoryRuntimeBridge / EvidenceService / provider registry+runtime / GovernedAgentGateway / CodingCompletionRuntime
 -> structured JSON/text output
```

Existing source/tests establish separately that:

- session create persists explicit workspace/session/mode/provider/policy identity;
- status/inspect/continue read or rehydrate persisted session state;
- provider selection preserves workspace/mode/policy fields;
- unknown provider/missing session/invalid input fails closed;
- evidence retrieval delegates to canonical EvidenceService;
- validation uses persisted completion contract/evidence through CodingCompletionRuntime;
- CLI does not accept operator-authored completion evidence;
- JSON/text formatting changes presentation only.

CLI acceptance must prove these through the normal non-interactive process path, including state persistence across separate CLI invocations and accepted mode-command delegation, with no second authority.

Canonical records:

```text
docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_GATE.md
docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_CHECKPOINT.md
```

## 7. R7 — End-to-end persistent coding/audit proof

**Classification: `PARTIALLY_PROVEN`.** After CLI acceptance, prove installed/normal-path coding, provider switch, resume after external workspace change, read-only audit, and out-of-authority stop behavior.

## 8. Release/package readiness

**Classification: `PARTIALLY_PROVEN`.** Release publication is authorized in intent but remains blocked by evidence prerequisites. Required before version/tag/publish:

```text
CLI normal-path PASS
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
 -> CLI normal-path acceptance ACTIVE
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
