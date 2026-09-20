# Release Scope Split Decision

Status: **DECISION — RELEASE READINESS SCOPE SEPARATION**

Purpose: Define the boundary between backend/package release readiness and the visible
LBE-owned Rust/Ratatui terminal client acceptance so that one may be closed for release without
the other, and so that the deferred client slice cannot be accidentally credited as accepted.

Effective at HEAD: `ea4acd14b0851494080d8514072c0a9f0bc0e59d` (main == origin/main, clean tree).

## 1. Track separation

### Track A: `BACKEND_PACKAGE_RELEASE_READY` (in scope for release readiness)

The backend/package track is composed of the recorded acceptance evidence that the release
machinery already consumes. Satisfied-by records (each PASS as recorded at its own SHA):

| Evidence source | Recorded result | Recorded SHA |
|---|---|---|
| `COMPLETE_LBE_AGENT_RUNTIME_GATE.md` | PASS — R3-R7 runtime/completion slices | historical |
| `R*_ACCEPTANCE_*` R3-R6 series | PASS (46/81/128/51/91) | historical gates + checkpoints |
| `CLI_NORMAL_PATH_ACCEPTANCE_CHECKPOINT.md` / `_GATE.md` | PASS (115 tests) | `0cdd2fa...` acceptance head |
| `INSTALLED_PACKAGE_END_TO_END_ACCEPTANCE_CHECKPOINT.md` | PASS (767 tests) | `aeb02b1e...` source head |
| `RELEASE_PACKAGE_READINESS_AUDIT_GATE.md` | PASS — publication still locked | as recorded |
| `PUBLICATION_PRECHECK_GATE.md` | PASS — `publish_allowed_now=false` | as recorded |
| `PUBLICATION_EXECUTION_AUTHORIZATION_GATE.md` | AUTHORIZED FOR 2.0.3 — publish locked pending version validation | as recorded |

This track is **in scope** for the current release-readiness reconciliation.

### Track B: `VISIBLE_TERMINAL_CLIENT_ACCEPTANCE` (deferred, NOT a release prerequisite)

| Evidence source | Status | Note |
|---|---|---|
| `INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_CHECKPOINT.md` | **REOPENED** (2026-09-16) | SOURCE CONTRADICTION / FINAL PRODUCT NOT PROVEN; verdicts UNVERIFIED/FAIL/BLOCKED |
| `INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md` | PASS (2026-09-19 18:09) | references client `58104bae...` |
| `apps/lbe-terminal/PROVENANCE.md` | migration record | 176 passed / 26 failed / 2 ignored in BOTH trees |
| `docs/CURRENT_STATUS.md:278` | claims 202 passed / 0 failed / 2 ignored | at `58104bae...` — contradicts PROVENANCE |

The accepted client commit `58104bae1cebd2be04fa1d5544b2ebfce90fe8ff` **does not exist** in the
local source repository `C:\LBE-TUI-Lab` (HEAD there is `5a49d87`, 2026-09-18 01:33). The test
counts recorded in PROVENANCE.md (176/26/2) and CURRENT_STATUS.md (202/0/2) are irreconcilable.

**DECISION:** `VISIBLE_TERMINAL_CLIENT_ACCEPTANCE` is **deferred and stays REOPENED**. It is
explicitly NOT a prerequisite for Track A. It must not be credited as accepted by this decision.

## 2. Canonical-client workspace selection: OUT OF SCOPE / UNDECIDED

The following sources disagree about the canonical visible-client workspace:

- `config.json`: retired `C:/LBE-TUI-Lab`
- `docs/CURRENT_STATUS.md:17`, `:109`
- `docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md:57`
- `docs/IMPLEMENTATION_PLAN.md:49`
- `.lbe/governance/implementation-gates.json:554` (`"canonical_client_workspace": "C:/LBE-TUI-Lab/src"`)

**DECISION:** canonical-client selection is declared **UNDECIDED / OUT OF SCOPE** for this release.
This decision does not pick a winner from the conflicting paths and does not resolve the 
`58104bae` provenance gap; both remain open items for explicit governance-level approval.

**Flagged for explicit approval (not edited as a side effect):**
`.lbe/governance/implementation-gates.json:554` still records
`"canonical_client_workspace": "C:/LBE-TUI-Lab/src"` even though `config.json` retired that
workspace. Updating the machine gate is a governance-intent change and is NOT performed here.

## 3. Live verification at HEAD (drift report)

The full backend suite was executed against HEAD `ea4acd1` (`python -m pytest -q`):

**Result: 807 passed, 5 failed.**

Deterministic failures (4), verified against the actual commits:

| Test | Verified cause / classification |
|---|---|
| `tests/test_product_launcher_contract.py::test_product_launcher_binds_project_guard_runtime_without_site_packages_fallback` | Asserts a **phantom contract that never existed in the launcher script at any commit** (`$guardConfigPath = Join-Path $InstallRoot "config\config.json"`, `knowledge_roots`, `allowed_write_paths`, `lbe-client.exe`). `git log -S` proves these strings appear only in `ea4acd1` itself (the test file). The script's real, accepted contract is `config\runtime.json`; the accepted installed entrypoint is `bin\lbe.cmd`. **Classification: miswritten/stale test, not a feature gap — the accepted launcher contract is intact, and the test contradicts it.** |
| `tests/test_product_launcher_contract.py::test_product_launcher_owns_user_command_without_overwriting_npm` | Asserts `Set-Content -LiteralPath (Join-Path $InstallRoot "lbe.cmd")` — never existed in the script (`git log -S"guardConfigPath"`/`-S"lbe-client.exe"` show only `ea4acd1`). Real contract: `$binCmd = Join-Path $binDir "lbe.cmd"` inside `bin\`. **Classification: same as above — miswritten/stale test.** |
| `tests/test_user_state.py::test_cli_provider_add_and_use_local_profile_without_credential` | `provider add` subcommand never existed in `cli.py` at any commit (CLI exposes only `list/check/select`). The supporting modules exist — `user_state.py` (`ProviderProfile`, `UserStateStore`) and `credential_store.py` — but were never wired into `cli.py`. **Classification: feature-gap test — describes a `provider add`/local-profile CLI capability that was implemented at the module level but never exposed.** |
| `tests/test_user_state.py::test_cli_provider_migrate_uses_explicit_config_and_never_emits_secret` | `lbe_guard_inspector.cli.WindowsCredentialStore` never existed in `cli.py` (`git log -S"WindowsCredentialStore"` shows only the test file at `c281ba5`; the class exists in `credential_store.py:18` but is never imported into `cli`). **Classification: feature-gap test — describes a CLI migrate capability whose supporting module exists but whose wiring was never done.** All the `user_state`/`credential_store` modules were added in the same commit as the tests (`c281ba5`) with no CLI exposure. |

Non-deterministic (1): `tests/test_release_packaging.py::test_wheel_contains_only_runtime_modules_and_contracts`
fails inside the full-suite run but **passes in isolation** (26.05s) and in the combined
`test_product_launcher_contract.py + test_user_state.py + test_release_packaging.py` run.
Classified as environment/ordering flake, not a source defect; should be re-investigated under a
clean runner.

**Provenance of the failing tests (verified against commit diffs):**

- `tests/test_user_state.py` was introduced at `c281ba5` (2026-09-08, "Add LBE Textual TUI and
  gate docs") and exists in **none** of the recorded acceptance SHAs
  (`0cdd2fa`, `69c6ae76`, `aeb02b1e`, `49ca39b`). It tests CLI capabilities (`provider add`,
  `cli.WindowsCredentialStore`) that never existed in any commit of the product source.
- `tests/test_product_launcher_contract.py` was added **in the HEAD commit itself** (`ea4acd1`)
  and does not exist at any recorded acceptance SHA.
- The launcher script's contract was NOT rewritten at HEAD: `config\runtime.json` +
  `bin\lbe.cmd -> lbe-launch.ps1 -> lbe.exe` were already present at HEAD's parent and were
  introduced at `09b5c1c` (2026-09-18, "feat: publish installed single-command launcher contract").
- The strings the launcher-contract test asserts (`guardConfigPath`, `guardGovernancePath`,
  `guardStateDir`, `lbe-client.exe`, `Set-Content ... InstallRoot "lbe.cmd"`, `knowledge_roots`,
  `allowed_write_paths`) never appeared in `tools/lbe_product_integration.ps1` at any commit
  (`git log -S` over the file's full history returns only `ea4acd1`, the commit that added the
  test file itself). They describe a launcher design that does not exist in this repository.

Therefore the recorded Track A PASS counts (115, 767, ...) were collected on trees that did NOT
contain these tests and predate the current launcher-script contract. They remain valid for their
own recorded SHAs but **do not reproduce on current HEAD**. This is explicit drift — and the four
deterministic failures are all tests added after the recorded acceptances (two asserting a phantom
launcher contract, two asserting never-implemented CLI features), not regressions of previously
green product behavior.

**Verdict:** Track A recorded documents and test counts are preserved as historical evidence, but
**BACKEND_PACKAGE_RELEASE_READY is NOT green on HEAD** — the full suite reports 807 passed / 5
failed. The four deterministic failures are not product regressions: two are miswritten tests added
at HEAD asserting a phantom launcher contract (the accepted `bin\lbe.cmd` contract is intact), and
two are feature-gap tests added at `c281ba5` describing CLI capabilities whose supporting modules
(`user_state.py`, `credential_store.py`) exist but were never wired into `cli.py` (`provider add`,
migrate, `cli.WindowsCredentialStore`). Resolution requires the launcher tests to be corrected to
the current contract and a wiring-or-removal decision for the user-state CLI capability, not source
regression work on the launcher itself. `publish_allowed_now` remains `false`; no publication is
dispatched here.

## 4. Hygiene (non-blocking)

- `dist_reconcile_tmp/lbe_guard_inspector-2.0.3-py3-none-any.whl` (1,156,852 bytes, dated
  2026-09-13): committed build artifact with **no references anywhere** (`git grep` empty) and no
  `PROJECT_INDEX.md` row. **Decision: removed from tracking and `dist_reconcile_tmp/` added to
  `.gitignore`** — it is a build byproduct, not an indexed structure, and `dist/` is already ignored.
- `apps/lbe-cli/`: untracked leftover confirmed. It contains only `dist/` + `node_modules/`, both
  covered by `.gitignore` (`dist/` line 7, `node_modules/` line 101). **No tracked files — confirmed excluded.**
- `PROJECT_INDEX.md:12` `.ui-preview/` row: directory does not exist, has zero tracked files, and
  `server.py` carries no `.ui-preview/` route. **Decision: row removed** — the described surface is
  not present; only `docs/reference/ui/lbe_tui_research_preview.html` remains. Note:
  `docs/governance/PROJECT_INTENT_LEDGER.md:442/599/624` retain historical `.ui-preview/` mentions
  and are left unchanged per the "historical records are not rewritten" rule.

## 5. Unresolved items (require governance-level decision)

1. Provenance gap: accepted client `58104bae` missing from `C:\LBE-TUI-Lab` HEAD `5a49d87`;
   PROVENANCE counts (176/26/2) vs CURRENT_STATUS counts (202/0/2) irreconcilable.
2. Canonical client workspace conflict (`config.json` retired vs 4 sources still citing
   `C:\LBE-TUI-Lab` / `C:\LBE-TUI-Lab\src`) — declared OUT OF SCOPE, not resolved.
3. `implementation-gates.json:554` stale `canonical_client_workspace` — flagged for approval.
4. Two miswritten launcher-contract tests added at HEAD (`test_product_launcher_contract.py`) that
   assert a contract never present in `tools/lbe_product_integration.ps1`; must be corrected to the
   accepted `bin\lbe.cmd`/`config\runtime.json` contract or removed.
5. Two feature-gap tests at `c281ba5` (`test_user_state.py`) for CLI capabilities whose supporting
   modules exist (`user_state.py`, `credential_store.py`) but were never wired into `cli.py`
   (`provider add`, migrate, `cli.WindowsCredentialStore`); require a wiring/removal decision.
6. Intermittent wheel-contract test under full-suite conditions.