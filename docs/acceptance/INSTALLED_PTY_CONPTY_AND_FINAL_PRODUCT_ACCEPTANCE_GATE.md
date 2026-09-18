# Installed PTY/ConPTY and Final Product Acceptance Gate

Status: **OPEN — SINGLE-COMMAND INSTALLED LAUNCH ONLY BLOCKER**

## Machine-selected state

```text
phase: INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE
slice: LBE_OWNED_RUST_TUI_PRODUCT_SURFACE
status: OPEN
implementation_allowed: true — final acceptance only
next_phase_locked: true
required_status_for_advance: PASS
publication: LOCKED / NOT AUTHORIZED
```

## Acceptance target

```text
fresh installed environment
-> open terminal
-> type: lbe
-> full LBE Rust/Ratatui coding IDE CLI/TUI renders
-> headless Cline provider/auth/model mechanics are available underneath
-> selected provider/model is bound to the authoritative LBE session
-> normal conversational/tool turn uses the real governed runtime
-> authority-bearing capabilities pass through LBE authorization
-> real persisted ToolReceipt/evidence are projected
-> quit restores terminal cleanly
-> restart
-> lbe
-> same session/workspace resumes correctly
```

## Runtime acceptance evidence — 2026-09-18

Real Windows PTY acceptance was executed against the canonical Rust/Ratatui release binary:

```text
C:\Users\prave\AppData\Local\Temp\opencode\lbe-tui-canon-clone\target\release\lbe.exe
```

Session:

```text
session   = sess_lbe_accept_001
workspace = workspace_fac63b08febbb29c
mode      = coding
permission= write_allowed
policy    = permissive
provider  = LM Studio
model     = google/gemma-4-e4b
```

Proven:

1. Real PTY render: `LETTERBLACK ENGINE · CONNECTED · AGENT WALL · ACT LIVE`.
2. Authoritative workspace/session/runtime policy projection.
3. Live provider/model projection and 11-provider discovery.
4. Real governed conversational turn through `workspace.read`.
5. Real persisted ToolReceipt/evidence projection.
6. Interactive approval -> ALLOW.
7. Interactive rejection -> DENY.
8. Clean Ctrl+D PTY exit.
9. Restart/resume of the same persisted session.
10. Persisted DB rows for session/turn/completion evidence.

The test turn intentionally requested only a read. Deterministic completion later returned `VALIDATION_FAILED` because no source change existed. This is valid LBE completion behavior and does not negate the successful governed tool round trip.

## Required final verdicts

| # | Verdict | Status | Evidence |
|---:|---|---|---|
| 1 | INSTALLED_PTY_CONPTY | PASS | Real Windows PTY capture |
| 2 | FINAL_PRODUCT_SINGLE_COMMAND_LAUNCH | **UNVERIFIED** | Direct release-binary path was used; fresh terminal `lbe` resolution still required |
| 3 | REAL_RUNTIME_ATTACHMENT | PASS | CONNECTED / AGENT WALL / authoritative session |
| 4 | PROVIDER_MODEL_BINDING | PASS | LM Studio / google/gemma-4-e4b |
| 5 | GOVERNED_CODING_FLOW | PASS | Real governed `workspace.read` round trip |
| 6 | RECEIPT_EVIDENCE_PROJECTION | PASS | Persisted receipt/evidence identifiers projected |
| 7 | CLEAN_TERMINAL_EXIT | PASS | Ctrl+D clean exit |
| 8 | INSTALLED_RESTART_RESUME | PASS | sess_lbe_accept_001 restored |
| 9 | FINAL_PRODUCT_ACCEPTANCE | BLOCKED | Only verdict #2 remains |

## Sole remaining proof

From a fresh terminal, prove:

```powershell
Get-Command lbe -All
lbe
```

The resolved installed `lbe` entrypoint must launch the same canonical LBE-owned Rust/Ratatui product surface and reach the authoritative runtime. A direct invocation of `target\release\lbe.exe` is not enough for this one verdict.

No additional runtime/UI implementation defect is currently proven.


## Installed command acceptance update — 2026-09-18

Machine acceptance now proves the desired installed command path:

```text
fresh terminal
-> lbe
-> C:\Users\prave\AppData\Local\LetterBlack\LBE\bin\lbe.cmd
-> lbe-launch.ps1
-> installed lbe.exe
-> Rust/Ratatui
-> authoritative LBE runtime
```

Observed PASS:
- stale global npm `@letterblack/lbe` removed;
- `LetterBlack\LBE\bin` is first effective LBE PATH entry;
- bare `lbe` launches the Rust/Ratatui product;
- authoritative session/provider/model state projects correctly;
- session `sess_lbe_accept_001` resumes from installed state;
- no retained `lbe.exe` process remains after teardown.

This closes the **machine installed-command behavior** requirement.

Canonical source provenance remains open. Current GitHub `main` at the time of this update does not yet contain the installer logic that creates `bin\lbe.cmd`, prepends the user PATH, and provides the tested durable zero-argument launcher contract. Because the governance rule requires the accepted implementation to equal canonical `main`, final canonical acceptance remains blocked only on publishing that already-proven installer behavior and reproducing the smoke test from that exact head.

