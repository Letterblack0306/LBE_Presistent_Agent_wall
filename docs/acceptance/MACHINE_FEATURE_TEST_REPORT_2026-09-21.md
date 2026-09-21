# Machine Feature Test Report — 2026-09-21

Canonical workspace: `C:\Agents-Memory-Tool-v6-integration`
Branch: `main`
HEAD: `5168763`

## Verdict

`BLOCKED_FOR_LIVE_USE`

This is not a mock-based release claim. The real TUI rendered and restored the terminal correctly. Python and Rust regressions passed. Real PTY SGR mouse input proved landing entry and command-palette selection; attached-session provider, authorization, completion, and remaining mouse paths remain unproven.

## Evidence

- Python regression: `856 passed`
- Rust TUI regression: `213 passed; 2 ignored`
- Real TUI PTY startup: observed
- Real launcher provider guard: observed and actionable
- Real runtime attachment: `FAIL` — `LBE_SESSION_ID is not configured`
- Keyboard semantic outcome: `UNVERIFIED`
- Mouse landing/palette outcome: `PASS` — observed in release PTY traces
- Mouse provider/model/session/workspace/approval/wheel outcome: `UNVERIFIED`
- Live provider turn: `UNVERIFIED`

The machine-readable record is in [MACHINE_FEATURE_TEST_REPORT_2026-09-21.json](MACHINE_FEATURE_TEST_REPORT_2026-09-21.json).

## Re-run

Create a real `reasoning-provider.json`, then run:

```powershell
.\launch-lbe.ps1
```

Do not promote this report to release-ready until the live session, provider turn, keyboard semantics, and attached-session mouse interactions produce observable evidence.
