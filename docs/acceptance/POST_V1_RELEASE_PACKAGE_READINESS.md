# Post-V1 Release / Package Readiness

Updated: 2026-08-12
Status: **PACKAGE WORKFLOW READY; DIRECT REGISTRY PUBLISH BLOCKED BY 2FA**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Baseline accepted runtime: `471fb2c3f7606f146e534431383408e66b107757`
Release-readiness implementation revision: `7f32fb1167f4bc4ce583aed3d165cc78f8f2c702`

This is the canonical post-R7 package-readiness record. It does not reopen the
C5/R7 V1 acceptance proofs, add provider authority, or publish a release.

## Scope and supported-runtime evidence

`pyproject.toml` declares Python `>=3.11`. The repository CI configuration
targets Python 3.11, 3.12, 3.13, and 3.14 on Windows and Ubuntu. Local,
isolated installation evidence exists for:

| Runtime | Evidence |
|---|---|
| Python 3.12.10 / Windows | clean venv install, all console-entry help, provider/config load, persistent-session smoke: PASS |
| Python 3.14.4 / Windows | clean venv install, all console-entry help, provider/config load, persistent-session smoke: PASS |
| Python 3.11 and 3.13; Ubuntu | declared/CI-target matrix only; not re-executed locally in this record |

Remote Actions evidence was not available from this environment because the
local GitHub credential could not read Actions runs. Do not misstate CI-target
configuration as executed CI evidence.

## Dependencies and provider boundary

The runtime dependency set is limited to `jsonschema==4.23.0`. The current
OpenAI-compatible provider adapter uses the Python standard library transport;
no vendor SDK, provider account, API key, Cline integration, or model is
bundled in the package. Build/test tooling remains an optional `test` extra.

Provider connection files are external user-owned resources. A provider config
contains `endpoint`, `model`, and `timeout_seconds`; `api_key` is optional and
must never be placed in package source, runtime databases, documentation, or
tracked fixtures. The installed package can load the supplied
`reasoning-provider.example.json` without an API key.

## Installation and runtime configuration

Install into an isolated environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install lbe_guard_inspector-0.2.0-py3-none-any.whl
.\.venv\Scripts\lbe --help
```

Create persistent runtime state outside `site-packages` and outside package
source:

```powershell
.\.venv\Scripts\lbe session create `
  --database "C:\LBE\state\runtime.sqlite3" `
  --workspace "C:\Projects\controlled-workspace" `
  --project-workspace-id "controlled-workspace" `
  --session-id "operator-session" `
  --mode audit `
  --permission read_only `
  --runtime-policy audit
```

For installed workspace inspection and legacy server entry points, provide
machine-owned configuration outside the package:

```powershell
$env:LBE_GUARD_INSPECTOR_CONFIG_PATH = "C:\LBE\config\config.json"
$env:LBE_GUARD_INSPECTOR_GOVERNANCE_PATH = "C:\LBE\config\governance.json"
$env:LBE_GUARD_INSPECTOR_STATE_DIR = "C:\LBE\state"
```

`lbe` owns persistent-runtime control operations. `lbe-guard-inspector`,
`lbe-guard-inspector-evidence`, and `lbe-guard-audit` remain installed
read-only inspection/audit entry points. Help for all four entry points must
work before any runtime configuration is loaded.

## Package-content audit

The clean build produced:

```text
wheel: lbe_guard_inspector-0.2.0-py3-none-any.whl
wheel SHA-256: fe8fb3b8fe1c46f05e39dea06f488799a8482798a6f1cea2bf6a6e2742983fc9
wheel file count: 88

sdist: lbe_guard_inspector-0.2.0.tar.gz
sdist SHA-256: ae0677225d26899770e633346ce93e2d8360599628a2eb7e7b9d447b77762112
sdist file count: 94
```

Both archives contain the required
`lbe_guard_inspector/memory/memory_schema.sql` resource and no runtime state,
SQLite database, machine-specific `config.json`/`governance.json`/provider
config, credential file, acceptance artifact, test tree, build output, or
documentation tree. The `lbe_guard_inspector.memory` code module is required
package code and is not runtime state.

## Installed smoke evidence

In clean Python 3.12 and 3.14 virtual environments, the package installed with
its normal dependency resolution and proved:

- `lbe`, `lbe-guard-inspector`, `lbe-guard-inspector-evidence`, and
  `lbe-guard-audit` all rendered `--help` successfully;
- `lbe provider list` returned only the installed `openai-compatible` adapter;
- an external credential-free provider example loaded successfully;
- `memory_schema.sql` was available through `importlib.resources`;
- `lbe session create` created a non-empty persistent SQLite database; and
- `lbe session status` read the same persisted session.

The package test suite also builds wheel and source-distribution artifacts and
asserts that prohibited runtime/configuration/secret artifact names are absent.

## Validation

On the release-readiness implementation revision:

- focused package/install suite: **4 passed**;
- full repository suite: **631 passed**;
- clean wheel and source-distribution build: passed;
- isolated Windows install/smoke: passed on Python 3.12.10 and Python 3.14.4;
- wheel and source-distribution filename/content secret-pattern audit: passed;
- `git diff --check origin/main...HEAD`: passed.

## Migration boundary

No automatic migration is performed by package installation. New installed
runtime databases are initialized from packaged `memory_schema.sql`. Do not
overwrite an existing state database during installation. The historical
`migrate_legacy_state.py` path remains a separate operator migration for legacy
state and was not requalified as a package-upgrade migration in this track.

## Release decision

The clean build/install/package workflow is **READY** for an explicitly
authorized controlled distribution action. A license decision is not a
technical npm publication prerequisite; the current `UNLICENSED` metadata and
absence of a repository license file do not prevent a public npm publication.

The current environment could not authenticate to GitHub Actions, so the
declared cross-platform CI matrix has not been freshly verified here. This is
an external verification limitation, not a local package failure or a reason
to alter the workflow before account availability is restored.

No package was published, no tag was created, and no provider credential was
read, copied, or persisted by this track. A public npm publication still
requires explicit user authorization.

### Direct npm publication attempt

After explicit user authorization, direct publication of `@letterblack/lbe`
version `0.1.0` was attempted with the user-owned, ignored workspace token.
The package tarball audit passed and npm authenticated successfully, but the
registry rejected publication with `E403`: direct publishing requires account
2FA or a granular access token with bypass-2FA publishing permission. The
version was verified absent from the public registry afterward; no public
install receipt exists because no package was published. No token value,
credential file, tag, or release artifact was created by the attempt.

This is an external npm account/token capability blocker. Resolve it by
enabling the required account 2FA flow or providing an appropriately permitted
granular token, then explicitly authorize a retry.

## Deferred post-V1 work

B2 representative-workspace provider capability, performance/model-quality
evaluation, Cline integration, broader governed tools, TUI work, and production
hardening remain outside this package-readiness track.
