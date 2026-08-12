# Post-V1 Release / Package Readiness

Updated: 2026-08-12
Status: **PACKAGE WORKFLOW READY; PUBLIC RELEASE ACTION BLOCKED**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Baseline accepted runtime: `471fb2c3f7606f146e534431383408e66b107757`

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
wheel SHA-256: a758d3b3378f75057c7120ffca8aff1a12cd9196dd5ef1a11993cae7cdbfbbf1
wheel file count: 88

sdist: lbe_guard_inspector-0.2.0.tar.gz
sdist SHA-256: 5c856f5ad32168e6bae85498a795c9549af9e8b579fbdbc8c2d570c5785b5594
sdist file count: 105
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

## Migration boundary

No automatic migration is performed by package installation. New installed
runtime databases are initialized from packaged `memory_schema.sql`. Do not
overwrite an existing state database during installation. The historical
`migrate_legacy_state.py` path remains a separate operator migration for legacy
state and was not requalified as a package-upgrade migration in this track.

## Release decision

The clean build/install/package workflow is **READY** for an explicitly
authorized controlled distribution action. It is **BLOCKED** for a public
release action because:

1. the repository has no `LICENSE`/`LICENSE.md`/`COPYING` file, so a license
   decision cannot be invented during package readiness; and
2. the current environment could not authenticate to GitHub Actions, so the
   declared cross-platform CI matrix has not been freshly verified here.

No package was published, no tag was created, and no provider credential was
read, copied, or persisted by this track.

## Deferred post-V1 work

B2 representative-workspace provider capability, performance/model-quality
evaluation, Cline integration, broader governed tools, TUI work, and production
hardening remain outside this package-readiness track.
