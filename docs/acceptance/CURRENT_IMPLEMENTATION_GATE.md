# Current Implementation Gate

> **CURRENT EVIDENCE OVERRIDE (2026-10-10):** Historical Rust/Ratatui PASS records remain bounded evidence only. The visible product is now the LBE-owned Python terminal client. Current acceptance is derived from the active machine gate, exact canonical source/package, live provider/tool receipts, and final PTY/ConPTY interaction.

Status: **OPEN — LBE-OWNED TERMINAL PRODUCT / INSTALLED PTY-CONPTY FINAL ACCEPTANCE**

This file is the human-readable projection of `.lbe/governance/implementation-gates.json`. The machine gate is authoritative.

## Current machine state

```text
active_plan      = docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md
active_phase     = INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE
active_slice     = LBE_OWNED_TERMINAL_PRODUCT_SURFACE
status           = OPEN
implementation  = ALLOWED
next_phase       = LOCKED UNTIL PASS
publication      = LOCKED
selected_agent   = engine-neutral provider binding; Cline supported adapter
active_intent    = LBE-INTENT-LBE-OWNED-TERMINAL-SURFACE-20261010
```

## Current product decision

```text
PRODUCT / BRAND               = LBE / LetterBlack
VISIBLE PRODUCT CLIENT        = lbe_guard_inspector/terminal_ui.py
NORMAL PRODUCT ENTRY          = lbe
RUST/RATATUI                  = reference/integration only
REASONING / PROVIDER ENGINE   = engine-neutral LBE binding; Cline supported adapter
RUNTIME / GOVERNANCE          = LBE Agent Wall
```

The terminal client owns presentation/input only. Existing LBE owners remain authoritative for session/workspace identity, provider/model selection, mode/policy, authorization, governed execution, ToolReceipts/evidence, persistence/recovery, validation and completion.

## Current evidence

- Current source head before this gate update: `48004199b45367871afe68c9bee53e25da9f88cf`; focused terminal/product/launcher/Cline regression: **33 passed**; canonical product verifier: **structural integration True / proof pass True**.
- Exact installed candidate `1e31d208604406fbeabd1e4093cef7a895ce93a1` proved `lbe --version = 2.0.3`, bare `lbe` launch into `LBE | LETTERBLACK`, clean `/quit`, and correct propagation of launcher failures through `lbe.cmd`.
- The installed candidate completed a real provider turn through `openai-compatible / google/gemma-4-e4b`.
- A governed `workspace.read` in the registered canonical workspace completed with receipt `receipt-dda22b70674e4f01bef6d7d1e65802d5`, verified current-workspace evidence, and provider continuation reporting package version `2.0.3`.
- Current source adds `/providers`, `/models`, `/model <id>` by delegating to existing `provider.list`, `provider.models`, and `provider.select`. Live source proof projected 17 registered providers, five local endpoint models, and persisted `google/gemma-4-e4b` selection.

These are current bounded proofs, not final acceptance. The current source is newer than the last installed candidate, so exact-current package/install proof remains required.

## Current implementation target

```text
LBE Python terminal surface                 IMPLEMENTED / TESTED / LIVE SOURCE
provider/model controls                     IMPLEMENTED / TESTED / LIVE SOURCE
installed bare lbe / provider / read flow   PROVEN on 1e31d208
exact-current package parity                OPEN
real PTY/ConPTY interaction                 OPEN
approval DENY/ALLOW + safe mutation         OPEN
Python terminal restart/resume              PASS_BOUNDED_INSTALLED
deterministic current completion            OPEN
FINAL_PRODUCT_ACCEPTANCE                    BLOCKED
```

## Current single job

```text
LBE_OWNED_TERMINAL_PRODUCT_SURFACE
```

Required sequence:

1. Package and install the exact current canonical head.
2. Prove provider/model controls from that installed artifact.
3. Run real PTY/ConPTY interaction and terminal restoration.
4. In a disposable governed validation workspace, prove DENY zero execution and ALLOW one bounded mutation with correlated receipt/evidence.
5. Preserve the installed restart/resume proof for runtime/package source `75158f1`; repeat only after a runtime/package-affecting change.
6. Prove deterministic completion from the governed result.
7. Close final acceptance only if every required observable is current.

## Locked UI behavior

The canonical UI is the minimal LBE shell: compact authoritative header, one conversation/work timeline, bounded `ACTIVE PROCESS`, `[I]` composer, PLAN/ACT/AUDIT, provider/model controls, real context usage when supplied by runtime, concise approvals, and no permanent governance/debug dashboard. Missing runtime data remains unknown rather than fabricated.

## Final gate rule

```text
FINAL_PRODUCT_ACCEPTANCE remains BLOCKED
until the exact current Python-terminal package completes the real PTY/ConPTY governed lifecycle.
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

