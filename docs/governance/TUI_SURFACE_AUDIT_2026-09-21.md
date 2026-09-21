# LBE TUI Surface Audit

Status date: 2026-09-21

This is the area-by-area audit requested for the normal coding-agent product
surface. It distinguishes a real user workflow from a rendered panel, a local
unit-test path, and a live installed-runtime proof.

## Verification baseline

| Check | Result | Meaning |
| --- | --- | --- |
| Rust TUI tests | 213 passed, 2 ignored | Deterministic client contracts pass |
| Rust release build | Passed | Release binary compiles |
| Python backend tests | 856 passed | Backend regression suite passes |
| Installed PTY/ConPTY acceptance | Not run/re-proven | Live installed behavior remains unverified |
| Live provider turn | Not proven here | Tests do not prove credentials/network/provider availability |
| Real release PTY launch | **FAIL / FIXED IN SOURCE** | Root launcher now bootstraps required variables/session; direct binary still fails closed without a session |
| Mouse injection | **FAIL / UNVERIFIED** | No usable computer-use terminal surface or mouse-capable PTY harness was available |

## Surface audit

| Area | Current implementation | Status | Remaining work |
| --- | --- | --- | --- |
| Home/landing | Landing gate, runtime/provider/model summary, Enter/click entry | Implemented | Live visual acceptance |
| Welcome/composer | Normal prompt composer, history, multiline input, submit | Implemented | Live provider acceptance |
| Build/Plan/Audit | Tab mode cycle and policy-aware submission | Implemented | Live mode-specific acceptance |
| Transcript/activity | Assistant/user transcript, bounded activity, scrolling | Implemented | Mouse hit regions |
| Provider catalog | F2 or `/provider`; authoritative projection when connected | Implemented as panel | Dedicated setup/provider page and mouse row selection |
| Provider setup | `/provider-config`, `/provider-validate`, `/provider-remove` commands | Partial | Visual setup form, safe credential-reference entry, success/error flow |
| Model selection | F3 or `/model`; keyboard picker and runtime SelectModel | Implemented as panel; mouse route added | Live provider proof |
| Sessions | `/sessions`, resume, close, history panel | Implemented as panels | Dedicated session/home navigation and live restart proof |
| Workspace browser | `@`, `/tree`, list/read/search/glob | Implemented as governed panels; mouse row route added | Richer file navigation and live proof |
| Coding changes | Patch review, authorization gate, receipt/evidence projection | Implemented | Live governed patch round trip |
| Processes | Registered-process requests and activity projection | Implemented as governed panel | Live registered-command acceptance |
| Tools/authorization | Tool projection plus explicit Enter/Esc authorization | Implemented | Live authorization round trip |
| Evidence/receipts | Panels track received authoritative references | Implemented as panels | End-to-end live evidence/receipt proof |
| MCP/extensions/skills/plugins | Metadata refresh and projection | Partial | Real capability management surface; no execution from display |
| Memory/history | Commands and panels exist; some paths are mock/partial | Partial | Complete persisted-memory UX and live persistence proof |
| Checkpoints/undo | Compare and restore request paths | Implemented as panels | Live restore acceptance |
| Browser agent | Browser state/chat panel and governed request vocabulary | Partial | Live browser adapter acceptance |
| Headless CLI | `run`, `--json`, `--plain`, explicit prompt path | Implemented | Installed CLI acceptance |
| Mouse | Capture, wheel scrolling, landing/help, provider/model/session/workspace/palette/approval hit regions | Implemented in source; physical terminal proof pending | Real mouse-capable terminal acceptance |
| Accessibility | Compact layout, ASCII, no-color, reduced motion, minimum-size fallback | Implemented/tested | Live terminal-size matrix |
| Packaging | Release binary, canonical launcher, `lbe-cli.ps1`, `.bat`, and TTY prerequisite script | Implemented in source; installed artifact not proven | Reinstall and verify exact installed artifact |

## Observed live run

The previous direct release-binary run was launched in a real PTY with mock
mode disabled. The visible screen rendered, then the runtime reported:

```text
LBE WRAPPER ERROR  LBE_WALL_ROOT is not configured
```

The source launcher has since been added and now creates the governed session
before launching the binary when a real provider configuration is available.
The direct binary remains intentionally fail-closed when no session is passed.
No live provider/session attachment has yet been observed in the current build.

The earlier mock PTY run is intentionally excluded from evidence. It showed
preview rendering only and is not evidence of provider, session, keyboard,
mouse, authorization, execution, receipt, evidence, or completion behavior.

## Conclusion

The product is not page-complete. The runtime and typed contracts are broad and
healthy, but “implemented as a panel” must not be reported as a complete setup,
home, provider, session, or extension page. The highest-priority completion
slice is:

1. build a real home/navigation surface;
2. build a visual provider setup flow using opaque credential references only;
3. add provider/model/workspace mouse hit regions;
4. complete partial memory, extensions, and browser surfaces;
5. rebuild/reinstall and run installed PTY/ConPTY acceptance;
6. attach live provider and governed coding evidence to the release report.

Until those are closed, the correct release statement is:

> Runtime regression healthy; TUI surface implementation incomplete and live
> installed acceptance unverified.

## Reference versus current evidence

| Reference claim | What it actually proves | Current side-by-side result | Truth label |
| --- | --- | --- | --- |
| `COMPLETE_LBE_TUI_IMPLEMENTATION_GATE.md` requires installed interactive proof | Defines the acceptance contract and explicitly says source/tests/mocks are insufficient | Current source has not produced the required installed evidence for this worktree | Requirement, not proof |
| `INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md` says final installed product PASS on 2026-09-18 | Historical evidence for a different recorded backend/client revision and installed artifact | Documented installed `lbe.exe` is currently missing; current HEAD is dirty and `f32b71f…` | Historical/superseded evidence |
| `cargo test --locked` | Exercises deterministic Rust state/rendering contracts | 213 passed, 2 ignored | Tested only |
| `py -m pytest -q` | Exercises backend regression tests | 856 passed | Tested only |
| Release build | Proves current source compiles into a release binary | Current worktree binary built successfully | Built only |
| Mouse unit test | Calls `App::handle_mouse` directly | Does not prove a terminal emitted mouse events or a user click hit the intended visible control | Contract-only |
| Keyboard unit tests | Call key handlers/state transitions | Do not prove every shortcut was observed in a real terminal at every layout | Contract-only |

## Audit rule

No row is considered working merely because it says `PASS`, compiles, renders a
panel, or has a unit test. A surface becomes `WORKING` only after an observed
interactive scenario proves: the control is visible, the input reaches the
running artifact, the correct state changes, the authoritative output appears,
and the result remains correct after restart/resume where applicable.
