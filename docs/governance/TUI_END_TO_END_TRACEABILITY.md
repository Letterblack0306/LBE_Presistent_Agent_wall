# LBE TUI End-to-End Traceability Map

Status date: 2026-09-21

This document maps the Rust/Ratatui TUI from product intent through input,
runtime authority, projection, testing, packaging, and live acceptance. A
passing unit test is not treated as proof of a live provider or installed
runtime result.

## 1. End-to-end ownership path

```text
User intent
  -> terminal event (keyboard or captured mouse)
  -> App::handle_key / App::handle_mouse / command parser
  -> UserRequest
  -> WrapperClient
  -> RealLbeWrapper or explicit MockLbeWrapper
  -> LBE-owned session, authorization, execution, evidence, receipt,
     validation, and completion services
  -> LbeEvent
  -> App::reduce_lbe_event
  -> transcript/activity/panel projections
  -> Ratatui renderer
  -> visible result + optional headless JSON/plain event stream
```

The TUI is a client and projection surface. It must not become a second
authorization owner, executor, persistence owner, receipt owner, or completion
owner.

Primary owners:

| Concern | Source owner | Current status |
| --- | --- | --- |
| Terminal lifecycle | `src/main.rs`, `src/ui.rs` | Implemented; release build passes |
| Input routing | `src/app.rs` | Keyboard and safe mouse/scroll paths implemented |
| Request vocabulary | `src/requests.rs` | Implemented |
| Runtime boundary | `src/wrapper.rs` | Real and explicit mock paths exist |
| Event vocabulary | `src/events.rs` | Implemented |
| State reduction | `src/app.rs` | Implemented and tested |
| Rendering | `src/ui.rs` | Implemented; compact/minimal pass complete |
| LBE authority | `lbe_guard_inspector/` | Existing backend owners reused |
| Integration proof | `tools/lbe_product_integration.ps1` | Structural/focused proof passes; external acceptance remains separate |

## 2. Development process from start to finish

| Phase | Required result | Evidence | Verdict |
| --- | --- | --- | --- |
| Intent and governance | Active slice, owner, non-goals, and gate are declared | `.lbe/governance/implementation-gates.json`, project ledger | Tracked; gate remains open |
| Architecture selection | Rust/Ratatui client owns presentation; LBE owns authority | `src/main.rs`, `src/wrapper.rs`, governance ledger | Implemented |
| Domain contracts | Requests, events, snapshots, sessions, receipts, and evidence have typed shapes | `requests.rs`, `events.rs`, `types.rs` | Implemented |
| Input implementation | User actions map to requests or local UI state | `app.rs` | Keyboard plus safe mouse/scroll implemented |
| Runtime implementation | Real attachment fails closed; mock mode is explicit | `wrapper.rs` | Implemented |
| Projection implementation | Authoritative events update transcript, panels, evidence, and receipts | `app.rs` reducers | Implemented and unit-tested |
| UI implementation | Landing, cockpit, composer, overlays, compact layout, and status surfaces render | `ui.rs` | Implemented |
| Accessibility | ASCII, no-color, reduced-animation, minimum-size fallback | `main.rs`, `ui.rs`, tests | Implemented/tested |
| Focused validation | Input/state/rendering contracts pass | `cargo test --locked` | 213 passed, 2 ignored |
| Build validation | Locked release binary is produced | `cargo build --release --locked` | Passed |
| Package integration | Launcher supplies runtime/session bootstrap and installed paths | `tools/lbe_product_integration.ps1` | Source fix implemented; package must be rebuilt to consume it |
| Installed live acceptance | Fresh installed PTY session, real provider, governed tool round trip, receipt/evidence, resume, clean exit | External PTY/ConPTY acceptance | Not re-proven for the current dirty worktree |
| Publication | Explicitly authorized release/publication | Governance gate | Not authorized |

## 3. Keyboard map

| Input | Context | Effect | Evidence level |
| --- | --- | --- | --- |
| `Enter` | Landing | Enter welcome surface | Tested |
| `Enter` | Composer | Submit or approve | Tested |
| `Enter` | Workspace/session/provider/model panels | Open, resume, validate, or apply selection | Tested in focused paths |
| `Esc` | Overlay/panel/approval | Close or reject/dismiss | Tested |
| `Tab` | Landing/workspace | Cycle Build/Plan/Audit mode | Tested |
| `F2` | Empty composer | Provider panel | Tested |
| `F3` | Empty composer | Model panel | Tested |
| `Ctrl+C` | Running | Abort governed task | Tested |
| `Ctrl+C` | Idle | Quit | Tested |
| `Ctrl+D` | Empty composer | Quit | Tested |
| `Ctrl+L` | Main surface | Clear rendered transcript | Implemented; focused behavior present |
| `Ctrl+P` | Empty composer | Command palette | Tested |
| `?` | Empty composer | Toggle shortcuts | Tested |
| `q` | Empty composer | Quit | Tested |
| `@` | Empty composer, no panel | Request authoritative workspace browser | Implemented/tested through workspace flow |
| `Up/Down` | Picker | Move provider/model/session/workspace cursor | Tested |
| `Up/Down` | Empty composer with transcript | Scroll transcript or recall input history | Tested |
| `Up/Down` | Audit/file view | Scroll projection | Tested |
| `PageUp/PageDown` | Transcript/audit/file | Page scroll | Tested |
| `Home/End` | Transcript/audit/file | Jump start/end | Tested |
| `Backspace` | Composer | Remove input character | Implemented |
| `Shift+Enter` / `Ctrl+Enter` | Composer | Insert newline when not running | Implemented |
| `c` | Changes/undo panel | Compare checkpoint | Tested |
| `r` | Undo panel | Request restore | Tested; still LBE-authorized |

The displayed shortcut reference is in `ui.rs::shortcut_text`. The dispatch
implementation is in `app.rs::handle_key`. These two surfaces should remain
updated together.

## 4. Mouse map

Termina mouse capture is enabled for the interactive terminal and restored on
exit. `Event::Mouse` is routed to `App::handle_mouse`, which deliberately
reuses the keyboard-owned scroll state:

| Mouse operation | Context | Effect | Evidence level |
| --- | --- | --- | --- |
| Wheel up/down | Open file | Scroll read-only file projection | Tested through shared state path |
| Wheel up/down | Audit | Scroll audit projection | Implemented through shared state path |
| Wheel up/down | Transcript | Scroll transcript | Tested through shared state path |
| Left click | Landing | Enter the normal welcome/composer surface | Tested |
| Left click | Shortcuts overlay | Dismiss informational overlay | Implemented |
| Left click | Command palette | No command is guessed; use arrows + Enter | Explicitly fail-safe |
| Left click | Authorization gate | No approval is guessed; use Enter/Esc | Explicitly fail-safe |

Provider/model/workspace row hit-testing remains a follow-up. The current
mouse layer is therefore a convenience layer, not a claim of full mouse
feature parity; every unsafe or ambiguous click remains explicit.

## 5. Feature and output map

| Feature | Request/runtime path | Visible output | Current truth status |
| --- | --- | --- | --- |
| Conversation | `SubmitTask`, provider turn events, explicit `--prompt` startup submission | Transcript, deltas, completion | Real path exists; live provider needs acceptance proof |
| Build/Plan/Audit | `Tab`, mode policy mapping | Mode indicator and policy state | Implemented/tested |
| Provider discovery | `/provider`, `RefreshProviderCatalog` | Provider list and validation | Real projection path; mock fallback exists |
| Model selection | `/model`, `SelectModel` | Model picker and selected model | Real projection path; mock fallback exists |
| Session list/resume | `/sessions`, `ResumeSession` | Session identities and restored state | Implemented/tested |
| Workspace list/read | `@`, `/tree`, workspace requests | Entries, file content, hashes | Governed real path exists; mock mode rejects it |
| Workspace search/glob | `/find` and related requests | Results and evidence/receipt refs | Governed real path exists; live proof required |
| Workspace patch | `/patch`, approval gate | Diff, approval, receipt, evidence | Governed and fail-closed; tested |
| Registered processes | `/processes`, explicit process request | Activity and receipt/evidence | Governed path exists; not unrestricted shell |
| Tool projection | `/tools` | Capability, tool, risk, verdict | LBE-owned projection; no permission grant by display |
| Authorization | Approval events and Enter/Esc | Scope, decision, rationale, approval ID | Implemented/tested |
| Evidence | `/evidence` | Evidence references and source | Tracks received authoritative refs |
| Receipts | `/receipts` | Receipt IDs, status, evidence links | Tracks received authoritative receipts |
| Activity/timeline | `/activity` | Bounded event activity | Implemented |
| Audit | Audit mode, diagnostics, verdict events | Findings, checks, verdict | Read-only projection; live audit proof separate |
| MCP/extensions | `/mcp`, `/extensions` | Installed capability metadata | Registry projection; display does not execute |
| Memory/history | `/memory`, `/history` | Persisted/recalled records | Partial/mock fallback in some panels |
| Checkpoints/undo | `/changes`, `/undo` | Diff/restore request state | Request path exists; mutation remains LBE-owned |
| Browser agent | `/browser` | Browser state and receipt/evidence refs | Surface exists; live browser acceptance not proven here |
| Headless output | `--json`, `--plain` | Chronological machine/human events | Implemented/tested |
| Mouse operation | `Event::Mouse`, `App::handle_mouse` | Scroll and safe overlay/landing clicks | Partial; row hit-testing remains |

## 6. What “pass” currently means

The test suite proves deterministic local contracts such as:

- key dispatch changes the expected app state;
- invalid or foreign events are rejected or ignored;
- panels render without claiming authority;
- authorization gates do not release mutations without the required decision;
- evidence and receipt identities are retained;
- compact layouts do not overflow at tested sizes;
- real-wrapper attachment fails closed when configuration is missing or invalid.

It does not by itself prove:

- a live provider responds correctly;
- a real installed launcher has the current source build;
- every declared command has a live backend round trip;
- browser/MCP/process integrations are available in the current environment;
- a completion verdict is valid merely because a request returned `PASS`.

The UI distinguishes some of these states through `LIVE`, `PREVIEW`,
`MOCK`, `evidence`, `receipt`, `verdict`, and `not yet projected` labels. The
canonical completion signal must come from the LBE completion/validation path,
not from a local display counter.

## 7. Current closure decision

The TUI is keyboard-first, typed, fail-closed, and test-covered. It now has a
real, deliberately limited mouse layer; it is not valid to claim full live
feature parity from the current test pass alone.

The next implementation slice should be explicitly authorized and should
cover:

1. provider/model/workspace mouse hit regions and interaction tests;
2. per-feature live acceptance evidence rather than only panel rendering;
3. a single feature-status surface showing `implemented`, `mock`,
   `unavailable`, `live`, and `completed` separately;
4. rebuild/reinstall and repeat the external PTY/ConPTY acceptance after the
   current worktree changes.
