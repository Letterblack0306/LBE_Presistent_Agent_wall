# TUI Interactive Acceptance Checklist and Plan

Status: checklist open; no live row is filled.
Registered under `LBE-INTENT-TUI-INTERACTIVE-ACCEPTANCE-AND-CLEAN-CLONE-001`.

## Classification rule

```text
source presence     SOURCE-VERIFIED
tests               TESTED where covered
live interaction    UNVERIFIED until a human operates it
```

`docs/acceptance/VISUAL_MACHINE_ACCEPTANCE_POLICY.md` applies: automated
results are diagnostic only for visible UI. No row below may be filled
from a cargo or pytest result.

## Correction history

An earlier draft of this checklist claimed the TUI had no modifier
support, no `@file` mention, no slash commands, and that mouse support
was "scroll plus one click, no click on a menu". All four were wrong.
They came from grepping symbol names (`KeyModifiers::`, `MouseEventKind`)
instead of reading handler bodies. The mouse claim was contradicted by
`MACHINE_FEATURE_TEST_REPORT_2026-09-21.json`, which machine-proved two
click paths in a real PTY.

Retained here so the error is not repeated.

## Keyboard â€” read from executed branches of `app.rs::handle_key`

| Input | Guard | Action / owner | Auth | Live |
|---|---|---|---|---|
| Ctrl+C | phase==Running | `UserRequest::Abort` -> wrapper | YES | ___ |
| Ctrl+C | otherwise | `should_quit` | no | ___ |
| Ctrl+P | input empty | toggle command palette | no | ___ |
| Enter | SHIFT\|CONTROL | push newline | no | ___ |
| Enter | default | submit_or_approve | YES | ___ |
| Tab | landing / default | `UserRequest::SetMode` -> wrapper | YES | ___ |
| Esc | palette open | close palette | no | ___ |
| Esc | default | dismiss_or_reject | YES | ___ |
| Up/Down | palette open | move_command_palette | no | ___ |
| Up/Down | model/provider/session panel | move_*_picker | no | ___ |
| Up/Down | workspace listing | move_workspace_cursor | no | ___ |
| Up/Down | file / audit | scroll | no | ___ |
| Up/Down | input has text | recall_history | no | ___ |
| F2 / F3 | input empty | `/provider` / `/model` | YES | ___ |
| `@` | input empty, no panel | `ListWorkspace` -> wrapper (existing authority) | YES | ___ |
| `?` | input empty | toggle shortcuts overlay | no | ___ |
| `q` | input empty | quit | no | ___ |
| `d` | pending action gate | toggle diff (read-only by design) | no | ___ |
| `c` | Undo/Changes panel | compare_checkpoint | YES | ___ |
| `r` | Undo panel, connected | REFUSED: "restore is not exposed until the LBE restore owner is wired" | - | ___ |
| PageUp/Down, Home/End | file / audit / transcript | scroll | no | ___ |
| Backspace, Char | - | input edit | no | ___ |

Not present, and not expected: Ctrl+D and Ctrl+L specifically. The
capability exists via `q` and `/clear` under different keys.

## Mouse â€” 3 `MouseEventKind`s carrying 8 actions

| Event | Guard | Action | Live |
|---|---|---|---|
| Down | landing | `mouse_enter_landing` | **PASS** (real PTY, 5168763) |
| Down | command palette | `mouse_command_palette_select index=N` | **PASS** (real PTY, 5168763) |
| Down | approval row | `mouse_approval_allow` | UNVERIFIED |
| Down | approval row | `mouse_approval_deny` | UNVERIFIED |
| Down | shortcuts overlay | `mouse_close_shortcuts` | UNVERIFIED |
| Down | workspace row | `mouse_workspace_open index=N` | UNVERIFIED |
| ScrollUp/ScrollDown | - | `mouse_scroll delta=N` | UNVERIFIED |

The two PASS rows come from real SGR sequences captured through
`LBE_INPUT_TRACE_FILE` in a release PTY. They are limited to those two
paths and do not extend to any other row.

## AUDIT mode

| Check | Status |
|---|---|
| selection routes through existing mode-control path | SOURCE-VERIFIED (`app.rs::set_mode` -> `UserRequest::SetMode`) |
| resolves to the existing audit/read-only owner | SOURCE-VERIFIED (`mode_controller.py:105-114`, fail-closed) |
| cannot be overridden by `write_allowed` | SOURCE-VERIFIED (`mode_controller.py:112-113`) |
| visibly changes UI | SOURCE-VERIFIED (`ui.rs:433` label; `ui.rs:509,515` suppress welcome and split layout; `app.rs:430-437` audit scroll) |
| **refuses a mutation at execution time** | SOURCE-VERIFIED - mode resolution and R6C routing are composed into the production path; see `AUDIT_MODE_ENFORCEMENT_FINDING.md`. Residual is C0.5: absent typed policy defaults to read-only rather than surfacing an error |
| audit cannot gain coding capability via provider output | UNVERIFIED â€” C0 regression item 3 |

## Plan

1. Clean-clone cargo baseline. **DONE** â€” 251 passed, 0 failed, 2 ignored at 1874461.
2. Explain the 2 ignored tests. **DONE** â€” `real_wrapper_workspace_glob_*` and `real_wrapper_workspace_search_*`; need a real wrapper workspace with agent-wall receipts and evidence. Not counted as passing.
3. Derive the keyboard/mouse checklist. **DONE** â€” this document.
4. Register and activate the TUI intent. **DONE** â€” 1874461.
5. Commit the bounded TUI files. **DONE** â€” 1874461.
6. Clean-clone cargo recheck at the named commit. **DONE** â€” 251 passed.
7. Human live-terminal acceptance. **OPEN** â€” requires an operator.
8. Record only observed results. **OPEN** â€” no row may be filled from automation.

Prerequisite that changed during step 7: the configured provider endpoint
`localhost:1234` (LM Studio) is now reachable, so a live provider turn
is no longer blocked on provider setup. The 2026-09-21 report recorded it
UNVERIFIED only because no `reasoning-provider.json` was present.

