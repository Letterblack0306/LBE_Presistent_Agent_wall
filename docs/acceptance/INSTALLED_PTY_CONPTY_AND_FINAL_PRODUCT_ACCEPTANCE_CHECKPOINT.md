# Installed PTY/ConPTY and Final Product Acceptance Checkpoint

Status: **REOPENED — SOURCE CONTRADICTION / FINAL PRODUCT NOT PROVEN**

This checkpoint supersedes the earlier source-presence-only PASS claim.

## Current verdicts

```text
INSTALLED_PTY_CONPTY                  UNVERIFIED
FINAL_PRODUCT_SINGLE_COMMAND_LAUNCH   UNVERIFIED
REAL_RUNTIME_ATTACHMENT               FAIL
PROVIDER_MODEL_BINDING                UNVERIFIED
GOVERNED_CODING_FLOW                  FAIL
RECEIPT_EVIDENCE_PROJECTION           FAIL
CLEAN_TERMINAL_EXIT                   UNVERIFIED
INSTALLED_RESTART_RESUME              UNVERIFIED
FINAL_PRODUCT_ACCEPTANCE              BLOCKED
```

## Decisive canonical source evidence

- `lbe_guard_inspector/textual_tui.py` initializes `runtime = "PREVIEW"`.
- Its normal coding-turn handler emits synthetic `LBE governed`, `ToolReceipt`, and `Evidence` strings instead of invoking the authoritative governed runtime and projecting persisted records.
- `/memory` is explicitly preview behavior.
- `lbe_guard_inspector/product_entry.py` does not route a no-argument `lbe` invocation to `textual_tui.run_tui`; absent a product subcommand it delegates to `cli.main`.
- `lbe_guard_inspector/cli.py` records that the prior Python/Textual interface had been removed in favor of the Cline CLI/SDK surface, so the newly added Textual surface also requires explicit product-direction reconciliation.
- Source-level quit bindings do not prove installed PTY/ConPTY terminal restoration or restart/resume.

## Locked product contract

```text
USER
  -> lbe
  -> complete LBE coding IDE CLI/TUI
  -> embedded Cline provider/model/reasoning mechanics
  -> authoritative LBE runtime
  -> governed execution
  -> persisted ToolReceipt/evidence
  -> validation/completion
```

No final PASS may be recorded from module presence, source imports, color changes, or synthetic UI projection.

Publication remains locked.
