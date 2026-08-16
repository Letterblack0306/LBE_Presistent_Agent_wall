# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — R7 installed end-to-end acceptance active on release path

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
- installed behavior must compose the same authorities proven in source/runtime acceptance;
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
R7  PARTIALLY_PROVEN — ACTIVE ACCEPTANCE
release/package readiness PARTIALLY_PROVEN
```

Current active phase:

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: PROVE_INSTALLED_PERSISTENT_AGENT_NORMAL_PATH_OVER_ACCEPTED_AUTHORITIES
status: OPEN
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
required_evidence_level: USER_VISIBLE_RUNTIME
release_path_authorized: true
publish_allowed_now: false
```

## 4. Accepted phases

R3 through R6F and CLI normal-path acceptance are `PROVEN_COMPLETE`. Do not reopen them without new contradictory current evidence.

## 5. R7 — Installed end-to-end persistent agent proof

**Classification: `PARTIALLY_PROVEN` — active acceptance.**

R7 is not a new architecture phase. It must prove that a clean isolated installation of the exact accepted repository head composes the accepted authorities through the normal installed command path.

Required proof includes:

```text
exact-head isolated install
installed lbe identity without source-tree leakage
persistent session/task across separate processes
one governed coding execution with receipts
provider/model switch with LBE policy identity preserved
fresh-process resume
external workspace change revalidation
read-only audit/investigation
out-of-authority fail-closed stop
receipt/provider-continuation correlation
evidence-owned terminal completion
fresh-process terminal-state persistence
credential/secret/state exclusion
focused installed/runtime regression
clean diff/worktree proof
```

Canonical records:

```text
docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md
docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md
```

## 6. Release/package readiness

**Classification: `PARTIALLY_PROVEN`.** Publication remains blocked. After R7 PASS, release/package readiness must separately prove clean installation, package contents, secret/state exclusion, supported runtime matrix, regressions, installed smoke, and release metadata before any version/tag/publish action.

## 7. Evidence-reconciled progression

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
 -> R7 installed end-to-end acceptance ACTIVE
 -> release/package readiness acceptance
 -> version/tag/publish
```

## 8. Final invariant

```text
Provider reasons and proposes.
Persistent runtime orchestrates.
LBE owns authority and execution.
Installed CLI exposes existing authority but does not own it.
Receipts carry governed evidence.
Validation proves.
Completion truth belongs to LBE.
Release claims require installed/runtime/package evidence, not lower-layer inference.
```
