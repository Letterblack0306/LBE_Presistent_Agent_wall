# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — evidence reconciled through R6F acceptance

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
R6F PROVEN_COMPLETE
CLI PARTIALLY_PROVEN
R7  PARTIALLY_PROVEN
release/package readiness PARTIALLY_PROVEN
```

Current completed phase:

```text
phase: R6F_COMPLETION_VALIDATION_ACCEPTANCE
slice: PROVE_EVIDENCE_OWNED_TERMINAL_COMPLETION_THROUGH_PERSISTENT_CODING_RUNTIME
status: PASS
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
base_sha: fdb256c09f331610e596f12fdca008785b9518a4
acceptance_head: baeeea97d272a6575320605f26995a2732e1205c
release_path_authorized: true
publish_allowed_now: false
```

## 4. Accepted phases

R3 through R6F are `PROVEN_COMPLETE`. Do not reopen them without new contradictory current evidence.

## 5. R6F — Completion and validation

**Classification: `PROVEN_COMPLETE`.**

Accepted owner path:

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

Accepted invariants:

- provider/reasoning `COMPLETED` does not directly establish terminal task completion;
- completion contract is persisted and bound to the persistent runtime identity;
- producer-bound persisted evidence remains the validation input;
- stale required evidence yields BLOCKED and does not promote canonical task state;
- all required evidence must PASS and completion must be explicitly claimed before READY;
- READY alone promotes canonical task state to COMPLETED / VALIDATED_COMPLETION;
- no second completion, validation, evidence, or task-state authority was introduced.

Evidence:

```text
repository completion baseline: 34 passed
hash: 413212958DF86E82F1E8E3503E8DD4462802E876FD05608C8C6056EDDB92C885

provisional completion: PASS
hash: 1F770F3046BAAA87AA7A69D1C38C24F8D7AE044FC357B0172FE5103CB6B0F604

stale-evidence stop: PASS
hash: 3DC9440BF70342DD52A5F0C7E1E34CC43718A3F46E47230C6D1CF585FC251870

terminal evidence-owned completion: PASS
hash: F76048961D3079065D3C7F71949783AB4D266F4130154731AD0AC6B45D34BB13

focused regression: 91 passed
hash: 87BA55ECE0EED9BCE6732FF548C102AE5BD87CC324066CE11F2F33D26904313A

runtime/test source unchanged: PASS
diff check: PASS
worktree clean: PASS
acceptance scope: PASS
observed falsifier: NONE
```

Canonical records:

```text
docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_GATE.md
docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_CHECKPOINT.md
```

## 6. CLI control surface

**Classification: `PARTIALLY_PROVEN`.** Next required acceptance must prove accepted runtime services through normal non-interactive/installed CLI paths without CLI-owned authority.

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
