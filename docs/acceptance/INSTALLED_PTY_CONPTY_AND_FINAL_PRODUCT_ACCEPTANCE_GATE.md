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


## Current candidate archive verification — 2026-10-08

The Windows package pipeline was repaired within its existing
`tools/lbe_product_integration.ps1` owner. It now uses atomic .NET ZIP
creation and bounded fail-closed checksum enumeration retry. The verifier
checks SHA-256 and byte sizes **inside the ZIP itself**, without extracting
thousands of `node_modules` files with Windows `Expand-Archive`.

Current evidence from the canonical `-Mode package -SourceMode worktree -NoFetch`:
- source runtime HEAD during build: `6261de6`, canonical `main`;
- candidate: `%TEMP%\lbe-package-final-34840\LetterBlack-LBE-2.0.3-win-x64-candidate.zip`;
- candidate size: **35,791,288 bytes**;
- ZIP SHA-256: `820e93c6fc9340bec10a1e3e22a39a9e3ae08f33feb8def5e5cb6b1d70e57655`;
- archive package-verification.json: **PASS, 18,659 checksum entries, zero errors**;
- independent streaming verifier: **PASS on candidate**;
- negative verification: known-good fixture **PASS**, changed-content fixture **FAIL** (both byte size and SHA-256 mismatches).

This proves the bounded package/archive integrity and rejection semantics.
It does **not** prove that the candidate is installed, that provider/model
inference is healthy, or that current installed end-to-end authorization and
receipts have completed. Those retain their independent machine gate status.

## Isolated staged installer acceptance — 2026-10-09

An opt-in `-SkipUserPath` switch is now supported by the **canonical generated installer**. Without the switch, default PATH installation behavior is unchanged.

The staged installation in `%TEMP%\lbe-isolated-installed-20261009` was executed against `%TEMP%\lbe-accept-run-20261009-single\LetterBlack-LBE\install.ps1`:
- isolated `venv/Scripts/python.exe`, `lbe.exe`, and `bin/lbe.cmd` exist;
- installed `lbe.exe` SHA256 `F8752CAA379B0F0F867B9EFEE2CF6C9D216CD4F4710BC868CA25CAA8C9762AFF` matches staged `client/lbe.exe`;
- existing installed production client remained at SHA256 `D8655AC0C196BC05F0A4B163FB835D706EA2999A33498C8EC708209F66A50E6D`;
- the user PATH does not contain the isolated installation;
- five real ConPTY input cases **PASS**, including mouse handshake, keyboard, clean exit and terminal restore.

**Evidence boundary:** This was a staged install, **not** an archive-extracted candidate acceptance. The current isolated package run's ZIP verification failed (missing archive checksums; parallel runner interference was observed). The independently verified archive from 2026-10-08 remains historic evidence, and a fresh `-Mode package` ZIP must pass verification before claiming candidate-archive installation. Live provider-backed inference and tool authorization acceptance remain unproven.

## 2026-10-09 — Historical chat reconciliation and live provider-pipeline position

Historical requirement material was inspected **read-only** at
`I:\Other computers\My Computer\GPT_Local\chat_Print`:
31 ChatGPT JSON exports, 27 byte-distinct exports (2026-08-20 through
2026-09-20). These are **history/requirements**, not proof of currently
shipping features. Salient repeated requirements: engine-neutral LBE-owned
runtime; autonomous coding and genuine tool receipts; Cline as an adapter;
task-matched skill activation; provider/model independence; child-agent
continuation; restart persistence; and governed development without
unnecessary stops. Source/runtime evidence outranks the archived discussion.

Verified delivered, current main:
- `394f6cc`: the backend selects an existing matching provider profile for a
  provider-specific check without silently switching the active profile.
  Python provider registry + health regressions: 37 passing.
- `9cc63cc`: project Cline/Agent Skills-compatible `SKILL.md` metadata is
  discovered and bounded task-relevant bodies are added to the *reasoning
  context only*, not LBE execution authority. Only hashes/selection metadata
  persist. 75 focused provider/agent tests passed.
- `4cf42ab`: Rust provider validation only supplies a session's legacy
  provider configuration for that session's provider; other picker rows use
  their own saved provider profiles. Rust regressions passed.
- `2415aa3`: delayed session restoration no longer dismisses the active
  provider picker. Actual Windows ConPTY confirmed F2 panel remained open
  after delayed session resume; model/provider readiness is not implied.

Observed external conditions during this checkpoint:
- The LBE terminal was previously observed **CONNECTED** and projecting 17
  registered providers. Registry discovery is not authorization, credential
  configuration, inference readiness, or successful provider selection.
- Python CLI `provider check --provider lmstudio` returned a loopback
  connection-refused error. `openai` and `anthropic` each returned
  provider-not-configured. These are **provider-specific**, not product-wide
  bans and not statements about all 17 providers.
- Follow-up ConPTY tests exposed a session-restoration/picker race, now patched,
  but did **not** establish successful real provider selection or a complete
  provider-backed coding turn. Do not reinterpret Rust/pytest PASS as proof.
- Previous unrelated untracked workspace files remained untouched.

**Current acceptance classification:** provider-profile matching and task-skill
prompt injection are test-proven at their owning code paths; exact installed
provider-backed selection, inference, coding/tool effect, receipt, child-agent
continuation, and restart resilience across the *current installed product*
remain unverified. Continue independent authorized work; an unavailable
provider is not a blanket work blocker.
