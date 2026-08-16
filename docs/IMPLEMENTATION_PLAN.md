# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-08-17
Status: Active canonical roadmap — R7 installed end-to-end acceptance failed on installed coding composition; repair required before release progression

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
R7  FAIL — INSTALLED CODING COMPOSITION FALSIFIER
release/package readiness BLOCKED_BY_R7
```

Current active phase:

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: PROVE_INSTALLED_PERSISTENT_AGENT_NORMAL_PATH_OVER_ACCEPTED_AUTHORITIES
status: FAIL
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
required_evidence_level: USER_VISIBLE_RUNTIME
release_path_authorized: true
publish_allowed_now: false
```

## 4. Accepted phases

R3 through R6F and CLI normal-path acceptance remain `PROVEN_COMPLETE`. The R7 failure does not reopen them; it identifies a missing installed composition from the normal coding command to the already accepted governed tool/receipt authorities.

## 5. R7 — Installed end-to-end persistent agent proof

**Classification: `FAIL` — decisive observable-3 falsifier.**

Evidence reached:

```text
exact-head isolated install                         PASS
installed lbe identity without source-tree leakage PASS
persistent installed session across fresh process PASS
one governed coding execution with receipts        FAIL
```

Decisive runtime evidence:

```text
command_hash: A2B146E0501F096D870E2ED15A4331366FB954E8F137D7CD980EC97E2FBAE7B4
installed lbe code exit: 0
outcome: INSUFFICIENT_EVIDENCE
task status: blocked
response.read_only: true
provider approved_tools: workspace.read
marker: R7_CODE_PROVIDER_AUTHORITY_READ_ONLY=PROVEN
```

Expected composition:

```text
installed lbe code
 -> GovernedAgentGateway
 -> R6C authorization
 -> R6E GovernedToolOrchestrator
 -> ToolReceipt
 -> provider continuation
 -> persisted task/completion owners
```

Observed composition:

```text
installed lbe code
 -> GovernedAgentGateway
 -> LBERequestController reasoning/inspection path
 -> provider approved_tools = [workspace.read]
 -> read_only response
 -> governed coding execution/receipt path not reached
```

Later R7 observables are stopped because they cannot compensate for the missing required normal coding execution path.

Canonical records:

```text
docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md
docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md
```

## 6. Required bounded repair before R7 rerun

No implementation is authorized by the failed R7 gate itself. The next engineering slice must be separately activated and bounded to one question:

```text
Why does installed lbe code / GovernedAgentGateway stop in the read-only
LBERequestController path instead of composing the already accepted R6E
governed tool orchestration + receipt continuation path, and what is the
smallest active-owner correction?
```

Repair constraints:

```text
reuse R6C authorization_resolver
reuse R6E GovernedToolOrchestrator / ToolRegistry / ToolReceipt
reuse provider continuation
reuse SessionMemoryRuntimeBridge
reuse CodingCompletionRuntime
no second tool dispatcher
no second authorization owner
no second session/provider/completion authority
map connecting flow before patch
state one falsifier before test
one bounded correction only after owner/source/runtime evidence
```

After repair validation, R7 must be rerun from the installed coding-composition boundary and then continue the remaining required observables.

## 7. Release/package readiness

**Classification: `BLOCKED_BY_R7`.** Publication remains blocked. Release/package readiness cannot activate until repaired R7 returns PASS.

## 8. Evidence-reconciled progression

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
 -> R7 installed E2E FAIL
 -> bounded installed-coding composition repair REQUIRED
 -> rerun R7 installed E2E
 -> release/package readiness acceptance
 -> version/tag/publish
```

## 9. Final invariant

```text
Provider reasons and proposes.
Persistent runtime orchestrates.
LBE owns authority and execution.
Installed CLI must expose existing authority but must not own or bypass it.
Receipts carry governed evidence.
Validation proves.
Completion truth belongs to LBE.
Release claims require installed/runtime/package evidence, not lower-layer inference.
```
