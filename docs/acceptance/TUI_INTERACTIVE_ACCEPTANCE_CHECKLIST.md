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

## Keyboard - COMPLETE: 52 match arms in `app.rs::handle_key`

The earlier table in this document collapsed these 52 executed branches
into 24 rows by grouping Up/Down pairs, Home/End, and the Char family.
That was a defect in the checklist, not in the code. This section
replaces it with the complete arm-by-arm inventory. The arm count was
obtained by counting every `KeyCode::` match arm in the function body.

| # | Key | Guard | Action / owner | Auth | Live |
|---|---|---|---|---|---|
| 1 | Enter | Landing phase | phase -> Welcome | no | ___ |
| 2 | Tab | Landing phase | `set_mode` -> `UserRequest::SetMode` -> wrapper | YES | ___ |
| 3 | Esc | palette open | close command palette | no | ___ |
| 4 | Up | palette open | move_command_palette(-1) | no | ___ |
| 5 | Down | palette open | move_command_palette(+1) | no | ___ |
| 6 | Enter | palette open | `execute_command_palette` -> wrapper | YES | ___ |
| 7 | Char `p` | Ctrl held, input empty | toggle command palette | no | ___ |
| 8 | Char `q` | input empty | quit | no | ___ |
| 9 | Tab | default | `set_mode` -> wrapper | YES | ___ |
| 10 | Esc | default | `dismiss_or_reject` -> wrapper | YES | ___ |
| 11 | Char `?` | input empty | toggle shortcuts overlay | no | ___ |
| 12 | Enter | SHIFT or CONTROL held, not Running | push newline | no | ___ |
| 13 | Enter | default | `submit_or_approve` -> wrapper | YES | ___ |
| 14 | Char `d` | input empty, action gate pending | toggle diff (read-only) | no | ___ |
| 15 | F2 | input empty | `/provider` -> wrapper | YES | ___ |
| 16 | F3 | input empty | `/model` -> wrapper | YES | ___ |
| 17 | Char `@` | input empty, no panel | `ListWorkspace` -> wrapper (existing authority) | YES | ___ |
| 18 | Char `c` | panel is Undo or Changes | `compare_checkpoint` -> wrapper | YES | ___ |
| 19 | Up | Model panel | move_model_picker(-1) | no | ___ |
| 20 | Down | Model panel | move_model_picker(+1) | no | ___ |
| 21 | Up | Provider panel | move_provider_picker(-1) | no | ___ |
| 22 | Down | Provider panel | move_provider_picker(+1) | no | ___ |
| 23 | Up | Session panel | move_session_picker(-1) | no | ___ |
| 24 | Down | Session panel | move_session_picker(+1) | no | ___ |
| 25 | Up | input empty, no panel/file, workspace listing | move_workspace_cursor(-1) | no | ___ |
| 26 | Down | input empty, no panel/file, workspace listing | move_workspace_cursor(+1) | no | ___ |
| 27 | PageUp | workspace file open | scroll file -10 | no | ___ |
| 28 | PageDown | workspace file open | scroll file +10 | no | ___ |
| 29 | PageUp | AUDIT mode | scroll audit -10 | no | ___ |
| 30 | PageDown | AUDIT mode | scroll audit +10 | no | ___ |
| 31 | Home | workspace file open | file scroll -> 0 | no | ___ |
| 32 | Home | AUDIT mode | audit scroll -> 0 | no | ___ |
| 33 | End | workspace file open | file scroll -> end | no | ___ |
| 34 | End | AUDIT mode | audit scroll -> max | no | ___ |
| 35 | Up | workspace file open | scroll file -1 | no | ___ |
| 36 | Down | workspace file open | scroll file +1 | no | ___ |
| 37 | Up | AUDIT mode | scroll audit -1 | no | ___ |
| 38 | Down | AUDIT mode | scroll audit +1 | no | ___ |
| 39 | PageUp | default | scroll transcript -10 | no | ___ |
| 40 | PageDown | default | scroll transcript +10 | no | ___ |
| 41 | Home | default | transcript scroll -> 0 | no | ___ |
| 42 | End | default | transcript scroll -> none | no | ___ |
| 43 | Up | input empty, transcript non-empty | scroll transcript -1 | no | ___ |
| 44 | Down | input empty, transcript non-empty | scroll transcript +1 | no | ___ |
| 45 | Up | default (input has text) | `recall_history(True)` | no | ___ |
| 46 | Down | default (input has text) | `recall_history(False)` | no | ___ |
| 47 | Backspace | - | input.pop() | no | ___ |
| 48-50 | Char (any) | CONTROL not held, not Running | input.push(character) | no | ___ |
| 51 | Ctrl+C | phase == Running | `UserRequest::Abort` -> wrapper | YES | ___ |
| 52 | Ctrl+C | otherwise | `should_quit = true` | no | ___ |

Count reconciliation: Enter 4, Up 9, Down 9, Char 11, Home 3, End 3,
PageUp 3, PageDown 3, Escape 2, Tab 2, Function 2, Backspace 1 = 52.

Guarded cases worth noting because they are separate behaviours, not
duplicates:

- `Char('c')` and `Char('r')` are gated on the Undo panel. `Char('r')`
  when Connected is REFUSED by design: "restore is not exposed until
  the LBE restore owner is wired".
- `Char('l')` with CONTROL is the palette toggle in one branch; the
  emitted trace names it `toggle_command_palette`.
- Home/End and PageUp/PageDown each have three distinct targets
  (file / audit / transcript) selected by guard, not repeated bindings.

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


---

# ADDENDUM A - Interaction contract from the resolved project skill

Added after resolving `letterblack-lbe-tui-interaction-design/SKILL.md`
through the MCP skills index. This is an ADDENDUM. Nothing above was
removed, replaced, or reworded. Every row above still stands.

Source, resolved complete and pinned for this task:

    path   letterblack-lbe-tui-interaction-design/SKILL.md
    sha256 3639af6fd2c7f4cd67252a0ea41f70124f6b5e07e76755a09e58b2fe7cc6daea
    lock   .skills/tasks/lbe-tui-acceptance-394345f38e.lock.json

## A.1 The skill does not replace the tables above

The skill states its own precedence rule:

    "Existing LBE bindings prevail; otherwise common conventions are
     q, ?, /, Esc, Tab, and Ctrl-P."

The keyboard table above was read from executed `app.rs::handle_key`
branches and remains the binding truth. The skill supplies a convention
list to check against, not an override. Nothing above is superseded.

## A.2 Convention cross-check - ONE discrepancy found

| Convention key | In skill | Present in app.rs | Finding |
|---|---|---|---|
| q | yes | yes, line 327 | matches |
| ? | yes | yes, line 331 | matches |
| Esc | yes | yes, lines 306 and 343 | matches |
| Tab | yes | yes, lines 282 and 338 | matches |
| Ctrl-P | yes | yes, line 291 | matches |
| / | yes | ABSENT - no Char('/') handler | DISCREPANCY |

The command palette opens on Ctrl-P, F2 and F3. `/` is documented in the
interaction contract and does not exist in the code.

This is NOT fixed here and is NOT assumed to be a defect. The skill says
existing bindings prevail, and whether `/` should also open the palette
is a product decision belonging to the TUI/product-surface owner. The
discrepancy is recorded so the decision is visible, not made silently.

## A.3 Core screens - none were in the checklist above

| Screen | Contract requirement | Live |
|---|---|---|
| Agent Cockpit | conversational center, task/session state, child runs, operational activity | ___ |
| Action Gate | exact capability, tool, target, input summary, risk, operation ID, approval ID, rationale, inspectable diff; approval is exact scope and allow-once; denial results in ZERO execution; resolution becomes an immutable event/receipt | ___ |
| Evidence/Receipt Inspector | session, turn, operation, provider tool-call, LBE call, receipt, evidence, authorization, execution, validation, ACTUAL provider/model IDs; distinguish proposed / authorized / executed / persisted / validated | ___ |
| Agent Wall | parent/child work WITHOUT implying children hold independent authorization authority | ___ |

The Action Gate row carries the strongest requirement in the skill:
denial must result in zero execution. That is a testable behavioral
claim and no row above covered it.

## A.4 Accessibility contract - entirely absent above

| Requirement | Live |
|---|---|
| red critical/high-impact | ___ |
| green VERIFIED SUCCESS ONLY | ___ |
| amber approval/risk/uncertainty | ___ |
| gray metadata/history | ___ |
| non-colour state and focus cues | ___ |
| keyboard-only operation for every interactive region | ___ |
| NO_COLOR support | ___ |
| ASCII mode | ___ |
| no-animation mode | ___ |
| wide layout | ___ |
| standard layout | ___ |
| compact layout | ___ |
| very-short layout, deliberate rather than clipping | ___ |

## A.5 Proof scope - FOUR behaviours were missing above

The skill states: "Screenshots and source-only tests are not
installed-product proof."

| Behaviour | Present above | Live |
|---|---|---|
| deterministic projection/render tests | partial | ___ |
| focus / navigation | no | ___ |
| command palette | yes | ___ |
| provider / model / session views | yes | ___ |
| diff inspection | yes | ___ |
| receipt inspection | no | ___ |
| ALLOW / DENY / CANCEL | no | ___ |
| RESIZE | no | ___ |
| alternate-screen restore | no | ___ |
| CANCELLATION | no | ___ |
| RAW-MODE CLEANUP | no | ___ |
| INSTALLED PTY/ConPTY journey incl. restart/resume | no | ___ |

The four rows in caps are the highest-risk behaviours in the TUI and
none had a row. Ctrl+C was listed above as a key binding, but
"cancellation reaches the runtime and the terminal is restored" is a
different claim.

## A.6 Evidence discipline carried from the skill

    "Missing data is unknown/unavailable, not inferred."
    "Never promote assistant prose to authority state."

A row may only be filled from direct observation of the running product.
A passing test, a screenshot, or this agent's own account are not
acceptance evidence. A blank Live cell is the correct state until a
human fills it.

## A.7 What this addendum does NOT do

- Does not modify, weaken, or re-scope any row above.
- Does not add a "/" binding; it records the discrepancy.
- Does not mark any Live cell.
- Does not claim the skill completes the TUI work. The skill defines the
  contract and the proof scope; only the installed PTY/ConPTY journey
  with a human operator can satisfy them.
