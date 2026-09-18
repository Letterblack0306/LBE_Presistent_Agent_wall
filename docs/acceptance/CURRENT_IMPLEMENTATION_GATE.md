# Current Implementation Gate

Status: **OPEN — LBE-OWNED RUST TUI / INSTALLED PTY-CONPTY FINAL ACCEPTANCE**

This file is the human-readable projection of `.lbe/governance/implementation-gates.json`. The machine gate is authoritative.

## Current machine state

```text
active_plan      = docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md
active_phase     = INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE
active_slice     = LBE_OWNED_RUST_TUI_PRODUCT_SURFACE
status           = OPEN
implementation  = ALLOWED
architecture_changes_allowed = true
next_phase       = LOCKED UNTIL PASS
publication      = LOCKED
selected_agent   = Cline (headless reasoning/provider mechanics)
active_intent    = LBE-INTENT-LBE-OWNED-RUST-TUI-PRODUCT-SURFACE-001
```

## Explicit product-owner decision — 2026-09-18

```text
PRODUCT / BRAND               = LBE / LetterBlack
VISIBLE PRODUCT CLIENT        = LBE-owned Rust/Ratatui terminal UI
VISUAL / INTERACTION CONTRACT = existing LBE HTML/React work + canonical UI plan
REASONING / PROVIDER ENGINE   = headless Cline mechanics behind LBE
RUNTIME / GOVERNANCE          = LBE Agent Wall
```

This supersedes the earlier assumption that the final visible product must be a copied/modified Cline CLI/OpenTUI surface. It does **not** supersede the selected Cline reasoning-agent source or governed Cline worker/provider mechanics.

## Accepted architecture

```text
USER
  -> lbe
  -> LBE-owned Rust/Ratatui terminal shell
  -> RealLbeWrapper / LBE product-entry boundary
  -> headless Cline reasoning/provider/model/continuation mechanics
  -> LBE session/workspace/turn identity
  -> mode/policy
  -> authorization
  -> governed execution
  -> ToolReceipt/evidence
  -> persistence/recovery
  -> deterministic validation/completion
  -> truthful terminal projection
```

Rust/Ratatui owns presentation/input mechanics only. Cline owns headless cognition/provider/continuation mechanics only. LBE owns identity, policy, authorization, governed execution, receipts/evidence, persistence/recovery, validation, and completion truth.

## Product implementation owners

```text
canonical client source = C:\LBE-TUI-Lab\src\
canonical client boundary = LbeWrapper / RealLbeWrapper
normal product entry = lbe
headless Cline owner = lbe_guard_inspector/runtime/cline_worker/ + provider adapters
HTML/React = visual/interaction reference only
Cline CLI/OpenTUI tree = reference/reuse only, not product requirement
Python/Textual = historical/diagnostic only
```

## Current implementation target

The product decision is settled. The remaining defect is source/build/package/installed acceptance alignment.

```text
Rust/Ratatui selected product technology   ACCEPTED
existing Rust client implementation        IMPLEMENTED / NEEDS CANONICALIZATION
headless Cline reasoning mechanics          PRESENT / RETAIN
HTML/React visual contract                  REFERENCE / RETAIN
product integration script                  NEEDS RECONCILIATION
installed one-command product               UNVERIFIED
real PTY/ConPTY acceptance                  UNVERIFIED
FINAL_PRODUCT_ACCEPTANCE                    BLOCKED
```

## Current single job

```text
LBE_OWNED_RUST_TUI_PRODUCT_SURFACE
```

Required sequence:

1. Reconcile `tools/lbe_product_integration.ps1` so its contract/proof/build/package/launcher targets all match the selected Rust LBE client plus headless Cline worker composition.
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
