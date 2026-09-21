# Machine Feature Test Report — 2026-09-21

Canonical workspace: `C:\Agents-Memory-Tool-v6-integration`
Branch: `main`
HEAD: `e448950`

## Verdict

`BLOCKED_FOR_LIVE_USE`

This is not a mock-based release claim. The real TUI rendered and restored the terminal correctly. Python and Rust regressions passed, but a live provider session was not available, so provider turns, authorization, completion evidence, and physical mouse outcomes remain unproven.

## Evidence

- Python regression: `856 passed`
- Rust TUI regression: `213 passed; 2 ignored`
- Real TUI PTY startup: observed
- Real launcher provider guard: observed and actionable
- Real runtime attachment: `FAIL` — `LBE_SESSION_ID is not configured`
- Keyboard semantic outcome: `UNVERIFIED`
- Mouse click/wheel outcome: `UNVERIFIED`
- Live provider turn: `UNVERIFIED`

The machine-readable record is in [MACHINE_FEATURE_TEST_REPORT_2026-09-21.json](MACHINE_FEATURE_TEST_REPORT_2026-09-21.json).

## Re-run

Create a real `reasoning-provider.json`, then run:

```powershell
.\launch-lbe.ps1
```

Do not promote this report to release-ready until the live session, provider turn, keyboard semantics, and physical mouse interactions produce observable evidence.
