# Installed PTY/ConPTY and Final Product Acceptance Gate

Status: **OPEN — FINAL PRODUCT SOURCE RECONCILIATION REQUIRED**

## Machine-selected state

```text
phase: INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE
slice: FINAL_PRODUCT_SOURCE_RECONCILIATION
status: OPEN
implementation_allowed: true — final-product reconciliation only
next_phase_locked: true
required_status_for_advance: PASS
publication: LOCKED / NOT AUTHORIZED
```

## Acceptance target

```text
fresh installed environment
-> open terminal
-> type: lbe
-> full LBE coding IDE CLI/TUI renders
-> Cline provider/auth/model mechanics are available underneath
-> selected provider/model is bound to the authoritative LBE session
-> normal coding turn uses the real governed runtime
-> authority-bearing tools pass through LBE authorization
-> real persisted ToolReceipt/evidence are projected
-> quit restores terminal cleanly
-> restart
-> lbe
-> same session/workspace resumes correctly
```

## Current blockers

1. The new Textual surface reports `RUNTIME: PREVIEW`.
2. Normal text input currently generates synthetic governed/receipt/evidence strings.
3. Provider/model binding is not demonstrated by the Textual product surface.
4. No-argument `lbe` does not currently dispatch to `textual_tui.run_tui` in `product_entry.py`.
5. `cli.py` still records the previous decision that Python/Textual was removed in favor of the Cline CLI/SDK surface, so the visible product technology/composition is internally contradictory.
6. Installed PTY/ConPTY clean exit and restart/resume require claim-matched live proof.

## Required final verdicts

| # | Verdict | Required evidence |
|---:|---|---|
| 1 | INSTALLED_PTY_CONPTY | Real installed PTY/ConPTY launch |
| 2 | FINAL_PRODUCT_SINGLE_COMMAND_LAUNCH | Fresh terminal: only `lbe` |
| 3 | REAL_RUNTIME_ATTACHMENT | Authoritative session/runtime state, not PREVIEW |
| 4 | PROVIDER_MODEL_BINDING | Live Cline provider/auth/model -> LBE session |
| 5 | GOVERNED_CODING_FLOW | Real coding/tool round trip through LBE |
| 6 | RECEIPT_EVIDENCE_PROJECTION | Persisted ToolReceipt/evidence IDs resolve |
| 7 | CLEAN_TERMINAL_EXIT | Terminal restored after exit |
| 8 | INSTALLED_RESTART_RESUME | Same workspace/session resumes |
| 9 | FINAL_PRODUCT_ACCEPTANCE | All required verdicts PASS |

## Product direction

```text
USER -> lbe
     -> LBE coding IDE CLI/TUI
     -> Cline mechanics underneath
     -> LBE runtime authority
```

A skin-only shell, preview runtime, source-presence check, or fabricated receipt/evidence display cannot satisfy this gate.
