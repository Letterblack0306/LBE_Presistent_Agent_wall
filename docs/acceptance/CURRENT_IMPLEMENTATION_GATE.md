# Current Implementation Gate

> **CURRENT EVIDENCE OVERRIDE (2026-09-22):** This gate remains open and
> release-blocked until the current machine report proves live runtime,
> provider, keyboard, mouse, and installed-package behavior. Historical PASS
> records elsewhere in `docs/acceptance/` are retained but are not current
> acceptance evidence.

> **HISTORICAL BASELINE CLARIFICATION (2026-09-25):** R3–R7 remain accepted
> historical PASS records for their declared revisions and bounded observables.
> They are preserved, not revoked. Later source/product changes require the
> present installed `lbe` path to re-prove the relevant invariants; historical
> PASS cannot be promoted to current LIVE/WORKING/PROVEN status by itself.

Status: **OPEN — LBE-OWNED RUST TUI / INSTALLED PTY-CONPTY FINAL ACCEPTANCE**

This file is the human-readable projection of `.lbe/governance/implementation-gates.json`. The machine gate is authoritative.

## Current machine state

```text
active_plan      = docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md
active_phase     = INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE
active_slice     = MAIN_HEAD_CONSOLIDATION_AND_TRUTHFUL_ACCEPTANCE
status           = OPEN
implementation  = ALLOWED
architecture_changes_allowed = true
next_phase       = LOCKED UNTIL PASS
publication      = LOCKED
selected_agent   = engine-neutral provider binding (Cline supported adapter)
active_intent    = LBE-INTENT-MAIN-HEAD-CONSOLIDATION-TRUTHFUL-ACCEPTANCE-001

Current evidence override: the exact main worktree has a reproduced failure after selecting Qwen: the next provider turn rejects the selection because the configured endpoint model remains Gemma. The installed command-name path and full current-head governed loop are unverified. Machine acceptance is BLOCKED; historical PASS records below are not current proof.
```

The September 20, September 4, and August 26 Google Drive history was reconciled with the current local acceptance records on September 25, 2026. No architecture contradiction was found. The current OPEN gate remains authoritative because provider/model continuation, durable receipt/evidence correlation, exactly-once execution, continuation, restart/resume, artifact provenance, and final installed Rust/Ratatui proof are not all current and correlated.

## Explicit product-owner decision — 2026-09-18

```text
PRODUCT / BRAND               = LBE / LetterBlack
VISIBLE PRODUCT CLIENT        = LBE-owned Rust/Ratatui terminal UI
VISUAL / INTERACTION CONTRACT = existing LBE HTML/React work + canonical UI plan
REASONING / PROVIDER ENGINE   = engine-neutral LBE binding; Cline supported adapter behind LBE
RUNTIME / GOVERNANCE          = LBE Agent Wall
```

This supersedes the earlier assumption that the final visible product must be a copied/modified Cline CLI/OpenTUI surface. It retains Cline source and governed worker/provider mechanics as a supported adapter; it does not make Cline the required reasoning owner.

## Accepted architecture

```text
USER
  -> lbe
  -> LBE-owned Rust/Ratatui terminal shell
  -> RealLbeWrapper / LBE product-entry boundary
  -> engine-neutral reasoning/provider/model/continuation mechanics (Cline supported adapter)
  -> LBE session/workspace/turn identity
  -> mode/policy
  -> authorization
  -> governed execution
  -> ToolReceipt/evidence
  -> persistence/recovery
  -> deterministic validation/completion
  -> truthful terminal projection
```

Rust/Ratatui owns presentation/input mechanics only. The selected reasoning engine owns cognition, planning, provider/model interaction, tool proposals, continuation, and response composition. Cline is a supported adapter, not the required reasoning owner. LBE owns identity, policy, authorization, governed execution, receipts/evidence, persistence/recovery, validation, and completion truth.

## Product implementation owners

```text
canonical client source = C:\Agents-Memory-Tool-v6-integration\apps\lbe-terminal\
canonical client boundary = LbeWrapper / RealLbeWrapper
normal product entry = lbe
reasoning/provider owners = engine-neutral LBE bindings; Cline adapter under lbe_guard_inspector/runtime/cline_worker/ + provider adapters
HTML/React = visual/interaction reference only
Cline CLI/OpenTUI tree = reference/reuse only, not product requirement
Python/Textual = historical/diagnostic only
```

## Current implementation target

The product decision is settled. The remaining defect is source/build/package/installed acceptance alignment.

```text
Rust/Ratatui selected product technology   ACCEPTED
existing Rust client implementation        IMPLEMENTED / NEEDS CANONICALIZATION
 engine-neutral reasoning/provider binding   PRESENT / Cline adapter retained
HTML/React visual contract                  REFERENCE / RETAIN
product integration script                  SOURCE_RECONCILED / VALIDATION_PENDING
installed one-command product               UNVERIFIED
real PTY/ConPTY acceptance                  UNVERIFIED
FINAL_PRODUCT_ACCEPTANCE                    BLOCKED
```

## Runtime-proven mode-policy failure

Probe: `bounded-runtime-validation-001`

```text
ACT   expected coding        / effective audit = FAIL
PLAN  expected investigation / effective audit = FAIL
AUDIT expected audit         / effective audit = PASS
real SetMode supported                         = false
visible AUDIT distinct                         = false
```

The repair is now present on canonical GitHub main (backend `f7e09491c2142778ccead48611ed4c63d0da30d9`, TUI `7c41dfab251e2da6226d4682e9c5b1ea00afa3f6`). It is **UNVERIFIED on the exact canonical heads** until the focused backend/Rust checks and `bounded-runtime-validation-002` are rerun after fetching those revisions. Selecting ACT in the UI is still not itself permission to write.

## Current single job

```text
LBE_OWNED_RUST_TUI_PRODUCT_SURFACE
```

Required sequence:

1. Validate the `tools/lbe_product_integration.ps1` source reconciliation at `cebd8cf7751b2cdeb8a76fb0dcc2e0bc0c8f58e5`; copied Cline UI checks are reference-only/non-blocking and the build/package path targets the Rust LBE client plus headless Cline worker.
2. Preserve existing LBE runtime/session/provider/authorization/execution/receipt/evidence owners.
3. Adapt the locked LBE UI contract and existing HTML/React visual work into the Rust client without synthetic state.
4. Ensure PLAN/ACT/AUDIT maps explicitly to backend policy/mode/permission owners.
5. Remove normal-product dependence on a copied or system-installed visible Cline CLI.
6. Build/package/install the exact canonical Rust client composition.
7. Prove the complete installed real-terminal chain:

```text
lbe
-> Rust LBE shell
-> canonical session identity
-> provider/model
-> headless Cline reasoning
-> governed tool proposal
-> authorization
-> exactly-once LBE execution
-> ToolReceipt/evidence
-> continuation
-> persistence/resume
-> deterministic validation/completion
-> clean exit/terminal restoration
```

## Locked UI behavior

The canonical UI remains the minimal LBE shell defined by GPT-K: compact header, one conversation/work timeline, [I] composer, compact footer, PLAN/ACT/AUDIT, real context usage, concise approvals, and no permanent governance/debug dashboard.

## Final gate rule

```text
FINAL_PRODUCT_ACCEPTANCE remains BLOCKED
until the selected Rust/Ratatui LBE client is the actual packaged/installed `lbe` surface and the full real-terminal governed lifecycle is proven.
```

## Mode-policy exact-head closure

`MODE_POLICY_PRODUCT_MAPPING = PASS`

Proof:
- backend `cc0054950153a8c41a48ee0ba60f2675833f7cce`: 125/125 focused tests;
- TUI `58104bae1cebd2be04fa1d5544b2ebfce90fe8ff`: cargo check PASS, rustfmt check PASS, 202 passed / 0 failed / 2 ignored;
- `bounded-runtime-validation-003`: PASS;
- PLAN/read-only -> investigation;
- AUDIT/read-only -> audit;
- ACT/read-only -> permission required with no persisted mutation;
- ACT/write_allowed -> coding;
- visible AUDIT distinct;
- UI cannot grant permission.

This gate is closed. Final installed product acceptance is still open.

