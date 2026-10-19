# LBE terminal UI

Lockstep Boundary Engine (LBE) terminal client `apps/lbe-terminal`. Status record, rebuilt 2026-10-18
to the owner's binding spec `LBE_TUI_SCREEN_SPEC.md` (v3, Downloads). Earlier cockpit: rejected and
deleted without backup. Presentation and operator control only: the runtime owns identity,
authorization, execution, receipts and completion.

## Design sources

- `LBE_TUI_SCREEN_SPEC.md` v3 (adds the rule map, section 4a; binding; where the mocks show more than the spec allows, the spec wins),
  `LBE Terminal Options` (8 screens), `LBE terminal UI proposal` (5 boards),
  `Agents_Wall_LBE_CLI_Project_Brief` v2 (sections 4, 5, 7, 10).
- Skill guidance: pedronauck `tui-design`, NVIDIA OpenShell `tui-development` (GitHub).
- Product title on screen: **Lockstep Boundary Engine (LBE)** (launch splash, F1 help); the header
  keeps the short `[┃] LBE` mark.

## The one idea

The user sees what is happening, which rule LBE applied, and the result. Each LBE decision is one
transcript line `rule -> target -> result`; a block always carries one `next:` line; internals appear
only in the details pane (`d`) and the F8 receipts screen. The UI never decides: every state word
(connected, stopping, stopped, blocked) comes from the runtime or waits for it.

## Architecture

State, update, effect and view are separate. `view` only reads a `Model`; `update` turns input and
bridge messages into state and effects; only `app.rs` touches the terminal and the process.

| Module | Job |
|---|---|
| `model.rs` | State, `Rule`/`Verdict`/`Life`, bridge parsing (sanitized), no I/O |
| `update.rs` | Keys, commands, paste guard, rule/effect derivation, lifecycle, effects |
| `view/chrome.rs` | Header, composer, status word, rail (ACT/PLAN/AUDIT variants) |
| `view/cockpit.rs` | Transcript lines, rule collapse (max 3), approval prompt, splash, details |
| `view/screens.rs` | F2 providers, F3 models, F4 settings, F5 capabilities, F6 report, F7 sessions, F8 receipts |
| `rules.rs` | Rule map (spec 4a A/B/C): runtime rule id to screen name, result, reason, `next:` options |
| `theme.rs`, `text.rs` | Spec colour tokens, ASCII/NO_COLOR/no-motion; cell-width text, escape stripping |
| `bridge.rs`, `app.rs` | Spawn `lbe_guard_inspector.tui_bridge`; terminal guard, single input owner |

## Layout

Header (mark, workspace, `provider · model ● connected`, or `○ offline`; `AUDIT · read-only` and
`PLAN · nothing executes` replace the model text), transcript, 30-column rail, composer
`❯ Message LBE`, one status line `● act · ready` / `? help`. Tiers: wide >= 100 cols (rail), compact
60-99 (rail folds into `● act · task · 4.1k/8k · F1 keys`), very short < 20 rows (no header; mode at
the composer edge), below 60x18 a size message. Rail: TASK, SESSION, SCOPE, LAST RESULT, CONTEXT, KEYS
(AUDIT: SCOPE, READ, REPORT; PLAN adds PLAN STATE). F-screens reuse the frame; header reads
`F5 capabilities   esc back`.

Keys: `a` allow once / `d` deny / `v` view change (approval); `d` details of the last action;
`Ctrl+X` stop (asks once); `Ctrl+P` pause; `Esc` close details, back, or stop; `Ctrl+K` palette;
`F1` help; `F2`-`F8` screens.

## Bridge messages

Client to bridge: `turn`, `intent` (from `/intent <reason>`), `mode`, `decision`, `cancel`, `select`, `providers`, `models`,
`capabilities`, `status`, `quit`. Bridge to client: `ready`, `error`, `reply`, `activity`
(`name`, `event`, `status`, `receipt`, `detail`, plus `reason`, `next`, `rule`, `satisfiable_by`, `allowed_paths`, `proposed_paths`, and for a guard-selection stop `checked`, `missing`, `investigate`, `ask` when the runtime returns them), `effects`,
`context`, `permission` (adds `target`), `receipt`, `mode`, `providers`, `models`, `capabilities`,
`git{branch,diff}`, `done`. A `cancel` sent while a turn is still queued drops that turn
("stopped before the task started; nothing ran").

## Run

`lbe-terminal` with `LBE_PYTHON` (>= 3.11), `LBE_REPO`, `LBE_TARGET_WORKSPACE`; `LBE_BRIDGE=off` for UI
only; `NO_COLOR`, `LBE_ASCII`, `LBE_NO_MOTION` for the accessibility modes. `lbe` still opens the Python
terminal; which client is canonical and installed stays a product-owner decision.

## Rule map (spec v3, section 4a)

Rule lines are looked up in `src/rules.rs` by the id the runtime returns (`rule` on the `activity`
message; the bridge reads `rule_id`, `blocker_id`, `guard_id`, `audit_status` and similar keys and never
guesses one). Results: `passed`, `blocked` (stopped before any effect), `failed` (a check after a change,
glyph `✗`, `next:` offers the rollback), `needs you`. The first option is shown as `next:`, the rest sit
behind `o more options`. Unknown ids show as plain words, blocked, `next: ask LBE why (d)`. "Expand scope"
and "update scope" are text only: the client has no operation that widens scope.

Added by this hand-off because the runtime returns no governance id for them (spec 4a rule): tool-level
fallback names `read allowed`, `change allowed`, `command allowed`, `action allowed`, and kebab-case keys for
the section C template rules (`no-task-contract`, `file-not-in-allowed-files`, `role-denies-path`,
`protected-zone-no-signoff`, `signoff-expired`). Section D (`lbe verify` exit codes) belongs to the plain
CLI, which this crate does not implement.

## Held back or changed from the spec (truth rule: the UI shows only what the runtime reports)

- **Pause/resume**: the runtime has no pause operation. `Ctrl+P` prints "pause is not available";
  `paused` is never shown. Stop works (`stopping…` until the runtime answers, then `stopped by you`).
- **Approval expiry** and **actor**: not reported; no countdown is shown, the actor is the provider.
- **Rule reasons and `next:`**: shown when the bridge supplies them, else `blocked by LBE` and
  `next: ask LBE why (d)`.
- **AUDIT questions, findings, phase crumbs, coverage**: no bridge data, so not drawn. The banner, header,
  rail (SCOPE, READ, REPORT) and exit line are. The exit line reads `AUDIT ended · F6 opens the report`
  (the spec's "report draft saved" would be untrue: nothing is saved).
- **PLAN body** (goal, assumed, steps, check): the bridge returns plain agent text, so the plan is shown as text with
  `[A] approve → ACT`; revise/answer/export keys are not offered.
- **F7 sessions**: only the current task; queued and past sessions are not reported. **Resume prompt on
  relaunch**: no session-continuity data, not drawn.
- **F8** is labelled `log` on the rail and header (the spec's NEVER SHOW list bans the word "receipt" in the
  default view); the screen itself is titled RECEIPTS. Time column replaced by a sequence number.
- **Agent label** `lbe` is bold white, not red (spec colour rule: red only for logo bar, active mode, AUDIT
  banner, blocked/stopped/offline). **Git** branch and changed count sit under SCOPE (owner's earlier
  header requirement); they are not in the header.
- Model context/tools columns show `—` (not reported). `t test`, `a add custom`, `c run checks`, `x export`,
  `/` filter keys are not offered.

## Evidence (2026-10-18)

- `cargo test`, `cargo clippy --all-targets`, rendered-frame tests for the spec acceptance list
  (see the ledger entry for counts): tiers at 120x40, 80x24, 60x18, NEVER SHOW search, one `next:` per block,
  <= 3 rule lines, AUDIT banner once, details open/close, NO_COLOR, ASCII only, red only where allowed.
- Real binary in a headless Windows ConPTY (no window): UI-only scenario and a scenario against the real
  bridge in scratch roots.
- Not proven: one real ALLOW and one real DENY end to end (no working provider here), a model reply,
  `Ctrl+X` through ConPTY (0x18 is a VT cancel byte; covered by unit and frame tests only), other
  terminal emulators, mouse wheel in a real window, captures from an installed build.

## Redesign brief: proposed, not implemented (2026-10-18)

Design only. No client or bridge code changed. Base: the Rust client and `LBE_TUI_SCREEN_SPEC.md` v3 stay binding unless the product owner says otherwise. Nothing proven is dropped: the rule-line transcript, one `next:` per block, the size tiers, the accessibility modes and the key map are kept. The earlier cockpit stays rejected and is not revived. The design only adds what the runtime capabilities now need and the client cannot show yet. Which client is canonical stays a product-owner decision (`docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md` and `AGENTS.md` disagree).

### Capability to surface map

| Proven capability (evidence) | What the user needs to see | Surface | Bridge data today |
|---|---|---|---|
| Owner-only denial with who/what/next (G1, G15, G19) | Why it stopped, that only they can resolve it, the exact action | **Stop card** (below) | `rule`, `target`, `reason`, `next` forwarded. `satisfiable_by`, `allowed_paths`, `proposed_paths` exist in the runtime receipt `output` but are **not forwarded**; the bridge uses `satisfiable_by` only for the G19 relay |
| Agent-fixable denial the model recovers from by itself (recovery case A) | Nothing extra: one collapsed rule line, no interruption | Transcript rule line (existing) | needs `satisfiable_by == agent` to stay collapsed |
| Approve/reject flow (G12) | Exact scope, allow once, deny, view change; approval never widens owner policy | Approval prompt (existing `a`/`d`/`v`) | existing; add `approval_id` and capability to the details pane |
| Doctrine reaches plan/audit turns (G14) | Which mode doctrine is active | Header banner, `AUDIT · read-only`, `PLAN · nothing executes` (existing) | existing |
| `INSUFFICIENT_EVIDENCE` / missing evidence request (G21, G21b) | What was checked, what is missing, what to ask or provide | **Stop card** with the same fields | not forwarded; today the client shows a `RuntimeError` string |
| Intent gate (G23) and AUDIT intent records (G22) | Which intent covers this change, its status, what is missing | Rail line `INTENT` plus Stop card on a block | none yet: **not drawn** until a bridge message exists |
| Stop / cancel | `stopping…` then `stopped by you` | existing | existing |

### The one new component: Stop card

Shown only for a block that needs a person, in place of a bare `next:` line. It is the shared response contract rendered as five labelled lines:

```text
STOPPED  <rule name>                      who can resolve: you | the agent
reason     <one sentence from the runtime>
checked    <what LBE inspected>
missing    <what is absent>
look at    <what can be investigated read-only (d opens it)>
ask        <the exact question or action>
```

Rules: every line comes from the runtime or is not drawn (a line without data is omitted, never invented); at most 6 lines at 80x24, folding `checked` and `look at` into the details pane (`d`) in compact tiers; one `ask` only, further options behind `o`; agent-fixable blocks never become a card; AUDIT shows the card but offers no key that writes code.

### Order of work (each step needs the previous one's proof)

1. **Bridge only:** forward `satisfiable_by`, `checked`, `missing`, `investigate`, `question` on `activity` when the runtime returns them, with unit tests in `tests/test_tui_bridge.py`. The runtime fields for G21b and G23 do not exist yet, so only the denial fields can be forwarded first.
2. **Client:** render the Stop card from those fields, with frame tests (80x24, 120x40, 60x18, NO_COLOR, ASCII) and the existing NEVER SHOW search.
3. **Live:** the held-back acceptance run (real LM Studio turn through the Rust client over ConPTY) proving the G19 relay line, the G14 guidance and an owner-only Stop card. This closes the "not proven" list above.
4. Intent rail line and AUDIT intent notes only after G22/G23 have a runtime and bridge message.

### Falsifiers

- A block with all five fields renders in at most 6 lines at 80x24 and none of the NEVER SHOW words appear.
- With the bridge fields removed, the client renders exactly today's output (no invented lines).
- An agent-fixable denial replayed in the live run never produces a card (recovery case A still passes).
- The card never shows a key that widens scope or writes code.
