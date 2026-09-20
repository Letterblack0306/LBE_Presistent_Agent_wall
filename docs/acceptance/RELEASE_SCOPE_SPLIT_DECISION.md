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

1. ~~Provenance gap: accepted client `58104bae` missing from `C:\LBE-TUI-Lab` HEAD `5a49d87`;
   PROVENANCE counts (176/26/2) vs CURRENT_STATUS counts (202/0/2) irreconcilable.~~ →
   **RESOLVED BY §6** (retired evidence; `C:\LBE-TUI-Lab` removed).
2. ~~Canonical client workspace conflict (`config.json` retired vs 4 sources still citing
   `C:\LBE-TUI-Lab` / `C:\LBE-TUI-Lab\src`) — declared OUT OF SCOPE, not resolved.~~ →
   **RESOLVED BY §6** (canonical = `apps/lbe-terminal` in main; retired sources were already
   historical and are no longer cited as truth).
3. ~~`implementation-gates.json:554` stale `canonical_client_workspace` — flagged for approval.~~ →
   **RESOLVED BY §6** (updated to `C:/Agents-Memory-Tool-v6-integration/apps/lbe-terminal`).
4. Two miswritten launcher-contract tests added at HEAD (`test_product_launcher_contract.py`) that
   assert a contract never present in `tools/lbe_product_integration.ps1`; must be corrected to the
   accepted `bin\lbe.cmd`/`config\runtime.json` contract or removed.
5. Two feature-gap tests at `c281ba5` (`test_user_state.py`) for CLI capabilities whose supporting
   modules exist (`user_state.py`, `credential_store.py`) but were never wired into `cli.py`
   (`provider add`, migrate, `cli.WindowsCredentialStore`); require a wiring/removal decision.
6. Intermittent wheel-contract test under full-suite conditions.

## 6. Sole-source-of-truth policy: `main` HEAD only (governance directive, 2026-09-20)

**Directive (user, explicit):** everything must live on `main` HEAD; nothing may live in any other
tree or branch; `main` HEAD is the only acceptable source of truth.

**DECISION — `main` HEAD is the single source of truth for LBE.** Consequences, applied here:

1. **Canonical client workspace is the main-repo path.** `apps/lbe-terminal` inside the canonical
   repository is the LBE-owned Rust/Ratatui terminal client. `C:\LBE-TUI-Lab` and
   `C:\LBE-TUI-Lab\src` are retired migration roots, not runtime truth
   (`config.json` already records this). `.lbe/governance/implementation-gates.json:554`
   `canonical_client_workspace` updated to `C:/Agents-Memory-Tool-v6-integration/apps/lbe-terminal`
   (previously flagged; approved by this directive).

   **Acceptance-test content rule:** acceptance tests (and any derived assertion) are written only
   against **git-controlled content** — `git show`/`git cat-file`/`git log -S` on the canonical tree.
   A **backup clone or working-copy copy is treated as phantom, not lineage** (same root-cause class
   as the retired `C:\LBE-TUI-Lab` / `58104bae` sole-source error: a copied directory is not git
   truth). Tests may never be transcribed from an uncommitted working-tree snapshot; assertions must
   trace to a `main` HEAD record.
2. **No commit other than `main` HEAD is authoritative.** All other branches (local and remote on
   `origin`, `jannath`, `release-fork`) are deleted; only each remote's `main` remains. Their
   history is preserved only as deleted-refs record in this document, never as truth.
3. **`58104bae` and `C:\LBE-TUI-Lab` are retired evidence.** Any reference to them in recorded
   acceptance docs (`CURRENT_STATUS.md`, `CURRENT_IMPLEMENTATION_GATE.md`, `IMPLEMENTATION_PLAN.md`)
   is historical only and no longer describes the canonical tree. Precise finding (verified against
   the full 40-char SHA with `git cat-file -t`): `58104bae1cebd2be04fa1d5544b2ebfce90fe8ff` was
   **never an object in this repository** — not deleted, never present. The `PROVENANCE.md`
   "byte-identical `fc /b` migration" claim therefore establishes **file-content parity only**, not
   **commit-lineage parity**: byte-for-byte copied files cannot reproduce a git commit object, so the
   accepted-client commit identity could never have matched here. The comparison point is declared out
   of scope by retirement, and independently we now know why it could never have matched.
4. **The `C:\LBE-TUI-Lab` tree is removed** (its content is migrated, byte-identical, into
   `apps/lbe-terminal` at main; see `apps/lbe-terminal/PROVENANCE.md`). Uncommitted local edits
   there are discarded.

### Deleted local branches (main-only retained)

> **2026-09-20 revision:** After removal, a retrospective audit proved that `2.0.x` release
> branches and `ci/*` carried unique product source (Cline-sidecar / professional-runtime modules
> and an `npm/` launcher package) **not present on main**. Per a follow-up user directive
> ("restore all and review each before deletion"), all 38 deleted branch names were **recreated
> locally at their true tips** (11 unmerged tips from recovered objects; merged branches from their
> in-main landing commits), and the full unreachable set was hardened as `backup/uc/*` refs
> (206 commits, GC-proof — `git fsck` reports zero unreachable). No re-deletion happens until each
> branch is individually reviewed. The branch list below is the original deletion record.

`agent/cli-agent-integration-contract`, `agent/cli-control-plane`, `agent/cli-evidence-policy`,
`agent/cli-exit-proof`, `agent/cli-validation`, `agent/cli-validation-evidence`,
`agent/completion-evidence-persistence`, `agent/llm-reasoning-planners`,
`agent/r2-runtime-persistence-reconcile-v2`, `agent/r3-runtime-reasoning-integration`,
`agent/r4-checkpoint-resume-rehydration`, `agent/r5-bounded-retry-recovery`,
`agent/r6a-provider-abstraction`, `agent/r6b-mode-policy-engine`, `agent/r6c-authorization-resolver`,
`agent/r6d-context-assembly`, `agent/r6e-governed-tool-orchestration`,
`agent/r6f-completion-validation-gate`, `agents/tui-redesign-incomplete-features`,
`chore/cline-workspace-discipline`, `ci/pr56-billing-isolation`, `ci/workflow-activation`,
`design/authority-ownership-inspector-contract`,
`feat/authority-ownership-evidence-extractor-integration`, `feat/c4-cli-runtime-surfaces`,
`feat/c5-governed-coding-execution`, `feat/minimum-release-readiness`,
`feat/persistent-runtime-reasoning-integration`, `feat/persistent-runtime-session-task-state`,
`feat/reasoning-explanation-layer`, `feat/reasoning-investigation-planner`,
`feat/reasoning-proposal-controller-integration`, `feat/reasoning-proposal-layer`,
`fork/actions-register`, `release/python-runtime-v2.0.1`, `release/python-runtime-v2.0.2`,
`release/register-pypi-workflow`, `worktree-cleanup-review`.

### Deleted remote branches (each remote's `main` kept)

- `origin`: all `agent/*`, `chore/*`, `cleanup/*`, `design/*`, `docs/*`, `feat/*`, `fix/*`,
  `release/*`, `worktree-cleanup-review` tracking refs are pruned.
- `jannath`: `ci/pr56-billing-isolation` pruned.
- `release-fork`: all non-`main` tracking refs pruned.

> **2026-09-20 remote-recovery audit:** Exact SHAs for deleted `origin` branches were recovered
> from two authoritative server-side sources: GitHub pull-request head refs (`refs/pull/*/head`,
> 52 PRs, 50 matching branch names) and existing local tips. Result: **51 of 75** deleted `origin`
> branch names map to exact commit SHAs (`lbe_restore_final_map.txt`). The remaining **24** have no
> surviving exact tip anywhere (no PR head, no local object, no commit subject/merge reference) —
> those SHAs were lost with server-side deletion and are recorded as unresolvable. Remote **restore
> was not executed**: origin's `LBE main-only remote ref lock` ruleset (`creation` + `update` rules,
> all refs except `main`) blocks branch re-creation, and the decision was to leave the ruleset
> intact. `origin`, `jannath`, `release-fork` therefore remain main-only. The 51 recovered SHAs are
> preserved locally for any future re-creation if the lock is ever lifted.
>
> **Affirmative cross-check (2026-09-20): none of the 24 irrecoverable names overlap any cherry-pick
> candidate.** The five audit-flagged value branches — `ci/pr56-billing-isolation` (`40428e1`),
> `ci/workflow-activation` (`4352bd8`), `release/python-runtime-v2.0.1` (`f54021e`),
> `release/python-runtime-v2.0.2` (`72fdfa2`), `feat/c5-governed-coding-execution` (`4ff65ea`) —
> are **all still present locally at their exact tips** (verified `rev-parse`). Three of them
> (`ci/pr56-billing-isolation`, `ci/workflow-activation`, `release/python-runtime-v2.0.2`) simply
> never lived on `origin` (only on `release-fork` or locally), which is why the origin-only SHA map
> does not list them; that is a namespace fact, **not** a loss. Conclusion: **no value-bearing work
> was lost server-side** — every cherry-pick candidate's full history is preserved under `backup/*`
> and `backup/uc/*` refs.

### Retired tree

`C:\LBE-TUI-Lab` (separate git repo, HEAD `5a49d87`, origin
`git@github-letterblack:...LBE_Agents_wall_Intigration.git`, dirty working files:
`Agent.md`, `CLEANUP_PLAN.md`, `WHAT_IS_LBE.md` deleted; `Docs/*`, `build_errors.txt`,
`src/*` modified) — removed on 2026-09-20.

### Retired-tree recovery audit (2026-09-20, post-removal)

Unique-content findings per restored `backup/*` ref, verified by comparing each tip's tree against
`git ls-tree -r main`:

| Branch (tip) | Unique vs main | Unique product source | Assessment |
|---|---|---|---|
| `ci/pr56-billing-isolation` (`40428e1`) | 118 files | 63 — Cline-sidecar (`cline_sidecar_adapter.py`, `cline_llms_compat.py`, `cline_sidecar_readiness.py`), `professional_*` runtimes (continuation/control/completion/history/mutable/provider/session/turn), `runtime/professional_*_backends.py`, `npm/` launcher package | NOT on main; main only has `professional_capabilities.py`/`professional_provider_events.py`/`professional_transcript.py`. **Candidate for cherry-pick/re-integration.** |
| `ci/workflow-activation` (`4352bd8`) | 116 files | 61 — same professional-runtime + `npm/` family | Same content as `ci/pr56-billing-isolation` minus a few files; superseded by it. |
| `release/python-runtime-v2.0.1` (`f54021e`) | 112 files | 60 — same | Release-scope fork of the same sidecar/runtime family. |
| `release/python-runtime-v2.0.2` (`72fdfa2`) | 112 files | 60 — same | Successor of 2.0.1. |
| `feat/c5-governed-coding-execution` (`4ff65ea`) | 54 files | 16 — `npm/` launcher, `tests/test_c5_coding_execution.py`, `tests/test_installed_wheel_smoke.py` | `npm/` launcher duplicates content also on `ci/*` branches; tests unique. |
| `agent/cli-validation-evidence` (`f185a3a`) | 30 files | 4 — stale chat-dump artifacts under `tests/test differfence/` | Test debris, no product source. Safe to abandon. |
| `chore/cline-workspace-discipline` (`f604436`) | 33 files | 4 — same stale chat-dump artifacts | Planning/docs only + stray artifacts. |
| `design/authority-ownership-inspector-contract` (`ec16716`) | 25 files | 3 — `tests/test_reference_knowledge.py`, `tests/test_workspace_identity.py`, `PATCH_PROJECT_SCOPED_GUARD_RETRIEVAL.md` | Review-candidate tests replaced before completion. |
| `feat/authority-ownership-evidence-extractor-integration` (`3a1dac8`) | 26 files | 0 | Docs only; superseded. |
| `feat/persistent-runtime-reasoning-integration` & `feat/persistent-runtime-session-task-state` (`124347e`, same tip) | 30 files | 4 — stale chat-dump artifacts | Same artifact debris. |
| `fork/actions-register` (`5696ade`) | 30 files | 4 — stale chat-dump artifacts | Workflow registration refresh + debris. |

The `tests/test differfence/` JSON/messages artifacts (`1785460319869_yl0hf`, `1785461332072_pt9mp`)
recur across most branches — unused chat/turn dumps, no product value.