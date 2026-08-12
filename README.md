# LBE Persistent Agent Runtime

LBE is a persistent, provider-neutral local agent runtime with a CLI-first control surface.

The current product is no longer only the historical Guard Inspector vertical slice. The accepted V1 runtime now owns persistent sessions, workspace identity, provider selection, governed tools, evidence, validation, resume/revalidation, and completion semantics.

The public installation/bootstrap surface is:

```text
npm / npx
  -> @letterblack/lbe
  -> thin Node installer / launcher
  -> managed Python LBE runtime
  -> `lbe` CLI
```

The Node/npm layer does **not** implement a second LBE runtime. It only discovers, installs, launches, upgrades, and diagnoses the managed Python runtime.

## Current architecture

```text
User / external agent
        |
        v
`lbe` CLI
        |
        v
Persistent LBE runtime
        |
        +-- session + workspace identity
        +-- provider/model selection
        +-- mode + permissions + policy
        +-- governed tool orchestration
        +-- evidence + deterministic validation
        +-- checkpoint / resume / revalidation
        `-- validated completion persistence
        |
        v
replaceable reasoning provider
        |
        v
controlled workspace operations
```

Core ownership rule:

```text
Provider reasons.
LBE runtime orchestrates.
LBE governance authorizes.
Governed tools execute.
Workspace evidence supplies current facts.
Validation proves.
Persistent session state belongs to LBE.
```

## Public npm package

The public bootstrap package is:

```text
@letterblack/lbe
```

Install the launcher globally:

```powershell
npm install --global @letterblack/lbe
```

Then inspect the local runtime state:

```powershell
lbe --diagnose
```

The current npm package is intentionally a thin bootstrap layer and does not bundle a Python runtime, provider account, model, API key, or workspace state.

To install an approved Python LBE wheel into the managed runtime:

```powershell
lbe --install --wheel C:\path\to\lbe_guard_inspector-0.2.1-py3-none-any.whl
```

Then use the normal CLI:

```powershell
lbe --help
lbe provider list
lbe provider check ...
lbe session create ...
lbe session status ...
lbe audit ...
lbe investigate ...
lbe code ...
```

Use `lbe --help` and command-level help as the executable source of truth for exact arguments.

## Runtime and state boundary

The npm launcher and Python runtime keep installation, configuration, and persistent state separate.

Conceptually:

```text
LBE_HOME/
  runtime/   managed versioned Python environments
  config/    user-owned runtime/provider configuration
  state/     persistent SQLite/session state
```

`LBE_HOME` may be set to choose a controlled user-scoped location.

Provider credentials remain external user-owned configuration. They must not be embedded in npm package contents, Python package source, runtime databases, acceptance records, or Git history.

## Provider model

LBE does not provide or bundle AI models/accounts.

The user selects a supported provider/model connection. The provider performs reasoning; LBE remains authoritative for workspace scope, permissions, governed execution, evidence, validation, and persistent task/session state.

The installed runtime includes first-party `openai`, `anthropic`, and `gemini`
adapters plus `openai-compatible` for compatible endpoints. All adapters use the
same persistent LBE session, governance, tools, evidence, validation, and
completion owners; changing an adapter never transfers those authorities to a
provider. See [provider configuration](docs/PROVIDER_CONFIGURATION.md) for
user-owned connection files.

## Operating modes

The runtime exposes thin CLI mode commands over the same persistent runtime services:

- `lbe code` — governed coding workflow;
- `lbe audit` — read-only audit workflow;
- `lbe investigate` — investigation workflow.

These commands do not implement separate policy, provider, evidence, or completion systems. They route into the existing governed runtime.

## Persistent sessions

The CLI supports persistent session lifecycle operations including creation, status, checkpoint/resume/continue, and validation paths implemented by the runtime.

Resume is evidence-aware: persisted memory is not treated as live workspace truth. Current Git/workspace state is re-inspected and stale source-backed facts are invalidated before continued execution.

## Accepted V1 status

C5/R7 V1 is architecture-complete for the accepted milestone.

Installed-path proofs are recorded for:

- governed coding execution;
- provider/model switching while preserving LBE authority;
- resume after external workspace change with stale-state invalidation;
- read-only audit with zero workspace mutation;
- escalation/denial of operations outside active authority.

Canonical evidence:

- `docs/IMPLEMENTATION_PLAN.md`
- `docs/acceptance/C5_R7_ACCEPTANCE_RECORD.md`
- `docs/acceptance/POST_V1_RELEASE_PACKAGE_READINESS.md`
- `docs/acceptance/POST_V1_NPM_CONSUMER_DISTRIBUTION_READINESS.md`

## Legacy Guard Inspector surfaces

The original deterministic Guard Inspector and audit surfaces remain installed compatibility/read-only capabilities:

```text
lbe-guard-inspector
lbe-guard-inspector-evidence
lbe-guard-audit
```

They are no longer the complete product identity or primary user control surface. The primary persistent-agent control surface is now the `lbe` CLI.

Historical HTTP evidence/guard endpoints and their implementation remain part of the repository where still required by existing runtime behavior, but new product guidance should not describe LBE as only a read-only Guard Inspector service.

## Python package

The managed Python runtime package currently builds as:

```text
lbe-guard-inspector 0.2.1
```

with Python `>=3.11` and the console entry point:

```text
lbe = lbe_guard_inspector.cli:main
```

The historical Python distribution name does not change runtime ownership: `lbe` is the primary CLI and persistent LBE runtime surface.

## Development validation

Run the repository suite from the source workspace:

```powershell
python -m pytest -q
```

Run npm bootstrap tests from `npm/`:

```powershell
npm test
npm pack --dry-run --json
```

For release/consumer claims, unit tests alone are insufficient. Use the source-independent validation ladder recorded in the acceptance documents: package build -> isolated install -> npm tarball audit -> clean consumer install -> managed runtime -> CLI smoke -> persistent session/workspace proof.

## Non-goals / invariants

Do not introduce:

- a second Node session/runtime implementation;
- a Node provider authority;
- a second permission/policy resolver;
- a second governed tool registry;
- a second evidence/completion system;
- unrestricted generic shell bypasses;
- provider credentials inside package/runtime state;
- memory as a replacement for current workspace/Git evidence.

The npm layer distributes LBE. The Python LBE runtime remains the single execution/governance authority.
