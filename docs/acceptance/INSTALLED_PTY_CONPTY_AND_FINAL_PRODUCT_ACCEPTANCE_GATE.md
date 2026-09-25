# Installed PTY/ConPTY and Final Product Acceptance Gate

> **HISTORICAL RECORD — NOT CURRENT AUTHORITY (2026-09-21).** The PASS claims
> below belong to the recorded 2026-09-18 installed artifact and revisions
> listed in this document. They do not prove the current workspace, current
> `main` HEAD, current release binary, provider, mouse, or installed package.
> Current evidence is tracked in `docs/governance/TUI_SURFACE_AUDIT_2026-09-21.md`
> and `docs/acceptance/MACHINE_FEATURE_TEST_REPORT_2026-09-21.json`.

Status: **HISTORICAL PASS — NOT CURRENT ACCEPTANCE**

## Canonical implementation

```text
backend main:
09b5c1cd28806d4381fabaa4723191494f2bc32f

visible Rust/Ratatui client:
58104bae1cebd2be04fa1d5544b2ebfce90fe8ff

installed product root:
C:\Users\prave\AppData\Local\LetterBlack\LBE

authoritative command:
C:\Users\prave\AppData\Local\LetterBlack\LBE\bin\lbe.cmd
```

## Accepted installed product path

```text
fresh terminal
-> lbe
-> LetterBlack\LBE\bin\lbe.cmd
-> lbe-launch.ps1
-> installed Rust/Ratatui lbe.exe
-> authoritative LBE runtime
-> live provider/model
-> governed execution
-> ToolReceipt/evidence
-> persistence/recovery
-> deterministic validation/completion
```

## Final evidence — 2026-09-18

PASS evidence includes:

- fresh-shell `Get-Command lbe -All` resolves the LetterBlack installed launcher first;
- obsolete npm `@letterblack/lbe` package/shims removed;
- installed `LetterBlack\LBE\bin` prepended to user PATH idempotently;
- canonical installer source published at backend commit `09b5c1cd28806d4381fabaa4723191494f2bc32f`;
- clean rebuild/reinstall performed from that exact canonical head;
- installed Rust binary SHA-256 matched the canonical built client:
  `6E794AF5E2F2E869D0F02F7CCB25EAD105956E9C05EC67ECE43F76F58B4BAB8F`;
- bare `lbe` launched the LBE-owned Rust/Ratatui surface;
- authoritative session `sess_lbe_accept_001` restored;
- LM Studio / `google/gemma-4-e4b` projected live;
- 11 providers discovered;
- governed `workspace.read` completed with real receipt/evidence;
- interactive authorization ALLOW and DENY both proven;
- PLAN/ACT/AUDIT mapping proven with no permission escalation;
- clean PTY lifecycle proven;
- restart/resume proven;
- no retained `lbe.exe` process after teardown.

## Final verdicts

| Verdict | Status |
|---|---|
| INSTALLED_PTY_CONPTY | PASS |
| FINAL_PRODUCT_SINGLE_COMMAND_LAUNCH | PASS |
| REAL_RUNTIME_ATTACHMENT | PASS |
| PROVIDER_MODEL_BINDING | PASS |
| GOVERNED_CODING_FLOW | PASS |
| RECEIPT_EVIDENCE_PROJECTION | PASS |
| CLEAN_TERMINAL_EXIT | PASS |
| INSTALLED_RESTART_RESUME | PASS |
| MODE_POLICY_PRODUCT_MAPPING | PASS |
| CANONICAL_INSTALLER_LAUNCHER_CONTRACT | PASS |
| FINAL_PRODUCT_ACCEPTANCE | **PASS** |

This document records the bounded 2026-09-18 artifact acceptance only. It does not establish current main readiness. The current machine gate is BLOCKED after a 2026-09-22 selected-provider/model continuation failure; see docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md and docs/CURRENT_STATUS.md.

Publication/release authorization remains governed separately and is not implied by this acceptance.
