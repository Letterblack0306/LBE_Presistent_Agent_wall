# PROVENANCE — apps/lbe-terminal

Migration of the Rust/Ratatui LBE terminal client from the retired two-workspace
layout into the single consolidated LBE project.

Consolidation authorization: 2026-09-19 (one-time architecture consolidation of
the LBE product into the canonical repository
`C:\Agents-Memory-Tool-v6-integration`, origin
`Letterblack0306/LBE_Presistent_Agent_wall`, branch `main`).

Copy method: filesystem `copy /y` (byte-identical; verified with `fc /b`).
Copy timestamp (UTC-local): 2026-09-19 18:00 local (Sat 09/19/2026).

## Migrated files (source -> destination)

| Source (C:\LBE-TUI-Lab) | Destination (canonical repo) | Bytes |
| --- | --- | --- |
| `src/app.rs` | `apps/lbe-terminal/src/app.rs` | 102,744 |
| `src/browser_chat.rs` | `apps/lbe-terminal/src/browser_chat.rs` | 3,082 |
| `src/events.rs` | `apps/lbe-terminal/src/events.rs` | 9,413 |
| `src/main.rs` | `apps/lbe-terminal/src/main.rs` | 21,796 |
| `src/memory.rs` | `apps/lbe-terminal/src/memory.rs` | 5,780 |
| `src/requests.rs` | `apps/lbe-terminal/src/requests.rs` | 2,462 |
| `src/tests.rs` | `apps/lbe-terminal/src/tests.rs` | 171,619 |
| `src/types.rs` | `apps/lbe-terminal/src/types.rs` | 39,179 |
| `src/ui.rs` | `apps/lbe-terminal/src/ui.rs` | 92,245 |
| `src/wrapper.rs` | `apps/lbe-terminal/src/wrapper.rs` | 212,555 |
| `Cargo.toml` | `apps/lbe-terminal/Cargo.toml` | 411 |
| `Cargo.lock` | `apps/lbe-terminal/Cargo.lock` | 18,346 |

Byte-identity verified with `fc /b` for `app.rs`, `wrapper.rs`, `tests.rs`,
`Cargo.lock`, plus spot checks over all other copied files (copy exits with
`1 file(s) copied` per file).

## Migrated root launchers (source -> destination)

| Source (C:\LBE-TUI-Lab) | Destination (canonical repo root) | Notes |
| --- | --- | --- |
| `install-lbe-path.ps1` | `install-lbe-path.ps1` | Byte-identical; self-locating (`$PSScriptRoot`). |
| `launch-lbe.ps1` | `launch-lbe.ps1` | Path-rebound (see below). |
| `lbe-product.ps1` | `lbe-product.ps1` | Path-rebound: single-repo client topology. |
| `lbe-cli.ps1` | `lbe-cli.ps1` | Path-rebound: self-location, canonical DB/exe. |
| `lbe.bat` | `lbe.bat` | Byte-identical (delegates to `lbe-cli.ps1`). |
| `lbe.ps1` | `lbe.ps1` | Byte-identical (delegates to `lbe-cli.ps1`). |
| `run-lbe.bat` | `run-lbe.bat` | Path-rebound: self-location, `state/workspace.db`. |
| `tty-acceptance-test.ps1` | `tty-acceptance-test.ps1` | Path-rebound prerequisites; manual TTY test only (not run here). |
| `lbe` (entry shim) | `lbe` | Byte-identical. Real product entrypoint: runs `python -m lbe_guard_inspector.textual_tui`, which exists in the canonical runtime. |

### Path rebinding applied to launchers
- `LBE_WALL_ROOT` default = this repository root (launcher self-location `$PSScriptRoot`/`%~dp0`), env-overridable; no hardcoded `C:\Agents-Memory-Tool-v6-integration`.
- Rust binary default = `<root>\apps\lbe-terminal\target\release\lbe.exe`; `LBE_EXE` override; debug fallback `<root>\apps\lbe-terminal\target\debug\lbe.exe`; `cargo run` fallback.
- `LBE_WALL_DATABASE` default = `<root>\state\workspace.db` (authoritative DB used by `lbe-cli.ps1`, `launch-lbe.ps1`, and the runtime; reconciled away from the stale `state\lbe-runtime.db` and `state\lbe.sqlite3` references).
- `LBE_TARGET_WORKSPACE` = user-supplied workspace, defaulting to the canonical repo itself.
- `LBE_PROVIDER_CONFIG` default = `<root>\reasoning-provider.json` (absent config tolerated with a warning; no credentials fabricated).
- `LBE_CAPABILITY_REGISTRY` default = `<root>\state\capability-registry.json` (runtime reads this env var path; an absent file loads an empty registry — no new runtime file is invented).
- `LBE_WALL_PYTHON` default = `python` (verified interpreter; see Verification).
- `C:\LBE-TUI-Lab` appears only as an explicit retired-migration-source mention in this file and in legacy-history comments inside the migrated launchers; it is never an active path.

## Excluded from C:\LBE-TUI-Lab (not migrated)

| Item | Reason |
| --- | --- |
| `target/` | Build artifacts; rebuilt in-repo. |
| `lbe.exe` | Build artifact; rebuilt in-repo. |
| `build.log`, `build_errors.txt`, `*.log` | Build logs/side output. |
| `run-cline-lbe.ps1` | Depends on the cline/ reference tree, which is not migrating. |
| `README.md` | Retained as reference; agent-wall README is the canonical product README. |
| `Docs/` | Retained as reference (design/acceptance history, not runtime input). |
| `.lbe/`, `scripts/`, `.gitignore` | Workspace-local history/quality gates, not product surface. |

Nothing was deleted in `C:\LBE-TUI-Lab`; it is retained intact as a retired
migration/reference source.

## Config / tooling changes made as part of this migration
- `config.json` (canonical root): removed the `tui-workspace` knowledge root
  (`C:/LBE-TUI-Lab`); `$note` updated; `dev` and `lbe-workspace` roots preserved;
  `active_workspace_root`/`write_enabled`/`validation_enabled` untouched.
- `.gitignore` (canonical root): added `/apps/lbe-terminal/target/` and
  `/apps/lbe-terminal/*.log`; `*.exe` was already ignored globally (covers
  launcher-side executable outputs).
- `tools/lbe_product_integration.ps1`: default roots self-locate; the client
  repository expectation is now the canonical `LBE_Presistent_Agent_wall`; the
  origin-main staging path derives the client stage from
  `apps/lbe-terminal` inside the wall export.

## Verification summary (2026-09-19)
- `cargo build --locked` in `apps\lbe-terminal`: PASS (dev, 33.07s).
- `cargo build --release --locked` in `apps\lbe-terminal`: PASS (49.54s; needed
  so launcher release defaults resolve). Builds report 44 pre-existing
  unused/dead-code warnings from the unmodified migrated source.
- `cargo test --locked`, identical conditions in both trees:
  - Consolidated repo `apps\lbe-terminal` (no env preload): 176 passed,
    26 failed, 2 ignored.
  - Retired source `C:\LBE-TUI-Lab` (byte-identical source + lockfile, same
    toolchain, baseline): 176 passed, 26 failed, 2 ignored.
  The 26 failing tests are IDENTICAL in both runs (same names, same assertion
  failures: command palette / model picker / transcript & file scroll / tab
  cycling / quit shortcuts / compact-size + welcome-frame render expectations).
  They are PRE-EXISTING in the migration source, not introduced by migration.
- LIVE wall-integration tests (require a real persisted Agent Wall session in
  the database): `real_wrapper_attaches_configured_project_truth_without_mock_state`,
  `real_wrapper_refreshes_mcp_registry_through_authoritative_lbe`,
  `real_wrapper_attaches_session_only_without_task_identity` invoke the actual
  `python -m lbe_guard_inspector` runtime and fail with
  `AUTHORITATIVE_STATE_UNAVAILABLE` until a session is persisted; the test
  `real_wrapper_attach_requires_explicit_configuration` asserts the unset-env
  error and only passes with `LBE_WALL_ROOT` removed. These are environment
  fixtures, not migration defects.
- Python runtime import: `python` (3.14) and `py -3.12` both import
  `lbe_guard_inspector` and `lbe_guard_inspector.cli`; launchers default
  `LBE_WALL_PYTHON=python`.
- Non-interactive smoke (consolidated env preloaded):
  - `apps\lbe-terminal\target\release\lbe.exe --version` → `lbe 0.1.0`.
  - `...\lbe.exe --help` → LBE Usage/Options (help/version exit before TUI).
  - `lbe.bat --help` from the repo root → full launcher chain
    (lbe.bat -> lbe-cli.ps1 -> release exe) prints the same help header and
    exits before provider/session wiring, confirming self-locating execution
    against the consolidated repo.