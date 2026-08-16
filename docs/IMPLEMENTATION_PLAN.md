# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — R6F acceptance active on release path

## 1. Product goal

Build a persistent, provider-neutral LBE runtime where the provider reasons while LBE owns workspace/session identity, context/evidence authority, mode/policy, authorization, governed execution, receipts, validation/completion truth, and persistent state.

## 2. Non-negotiable invariants

- provider/model changes must not change LBE authority;
- current workspace/runtime evidence outranks memory/reference history;
- only registered governed tools may execute;
- operation IDs/receipts prevent unintended duplicate execution;
- provider continuation consumes receipts but owns no execution authority;
- terminal completion belongs to deterministic LBE validation, not provider/model prose;
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
R6F PARTIALLY_PROVEN — ACTIVE ACCEPTANCE
CLI PARTIALLY_PROVEN
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current active phase:

```text
phase: R6F_COMPLETION_VALIDATION_ACCEPTANCE
slice: PROVE_EVIDENCE_OWNED_TERMINAL_COMPLETION_THROUGH_PERSISTENT_CODING_RUNTIME
status: OPEN
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
base_sha: fdb256c09f331610e596f12fdca008785b9518a4
release_path_authorized: true
publish_allowed_now: false
```

## 4. Accepted phases

R3 through R6E are `PROVEN_COMPLETE`. Do not reopen them without new contradictory current evidence.

## 5. R6F — Completion and validation

**Classification: `PARTIALLY_PROVEN` — active acceptance.**

Existing owner path:

```text
provider/reasoning outcome
 -> CodingCompletionRuntime.run_reasoning
 -> COMPLETED remains provisional RUNNING/AWAITING_VALIDATION
 -> persisted TaskCompletionContract
 -> producer-bound CompletionEvidence
 -> evaluate_completion
 -> READY / BLOCKED / FAILED
 -> SessionMemoryRuntimeBridge canonical task state
```

Existing source/tests already establish independently:

- completion claim without required evidence -> BLOCKED;
- stale evidence does not satisfy completion;
- failed required validation -> FAILED;
- all required evidence must PASS before READY;
- passing evidence without an explicit completion request remains BLOCKED;
- reasoning `COMPLETED` remains provisional pending validation;
- missing validation persists BLOCKED / VALIDATION_INCOMPLETE;
- failed validation persists FAILED / VALIDATION_FAILED;
- READY persists COMPLETED / VALIDATED_COMPLETION.

R6F acceptance must prove these together through the persistent coding runtime, including session/task/workspace binding and producer-owned evidence classification.

Canonical records:

```text
docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_GATE.md
docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_CHECKPOINT.md
```

## 6. CLI control surface

**Classification: `PARTIALLY_PROVEN`.** After R6F PASS, prove accepted runtime services through normal non-interactive/installed CLI paths without CLI-owned authority.

## 7. R7 — End-to-end persistent coding/audit proof

**Classification: `PARTIALLY_PROVEN`.** After CLI acceptance, prove installed/normal-path coding, provider switch, resume after external workspace change, read-only audit, and out-of-authority stop behavior.

## 8. Release/package readiness

**Classification: `PARTIALLY_PROVEN`.** Release publication is explicitly authorized in intent, but is blocked by evidence prerequisites. Required before version/tag/publish:

```text
R6F PASS
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
 -> R6F acceptance ACTIVE
 -> CLI normal-path acceptance
 -> R7 installed end-to-end acceptance
 -> release/package readiness acceptance
 -> version/tag/publish
```

## 10. Final invariant

```text
Provider reasons and proposes.
Persistent runtime orchestrates.
LBE owns authority and execution.
Receipts carry governed evidence.
Validation proves.
Completion truth belongs to LBE.
Release claims require installed/runtime/package evidence, not lower-layer inference.
```
