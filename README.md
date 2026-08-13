# LBE Persistent Agent Runtime

LBE is a persistent, provider-neutral local agent runtime with a CLI-first control surface.

The current product is no longer only the historical Guard Inspector vertical slice. V2 owns persistent sessions, provider-neutral model transport, governed tools, live tool/process events, evidence, validation, completion semantics, and the initial typed agent-control protocol.

The public installation/bootstrap surface is:

```text
npm / npx
  -> @letterblack/lbe
  -> thin Node installer / launcher
  -> managed Python LBE runtime
  -> `lbe` CLI
```

The Node/npm layer does **not** implement a second LBE runtime. It only discovers, installs, launches, upgrades, and diagnoses the managed Python runtime.

## V2 release candidate

The coordinated V2 release pair is:

```text
@letterblack/lbe 2.0.0
lbe-guard-inspector 2.0.0
```

V2.0 freezes the currently verified professional runtime through P7 plus the verified P8 typed control-protocol contract and initialization/read-only session/event handlers. Later P8 mutation controls, live subscriptions, stdio transport, MCP/interactive clients, and additional capability backends are intentionally eligible for later 2.x releases rather than being claimed as V2.0 functionality.

## Current architecture

```text
User / external agent
        |
        v
`lbe` CLI / control protocol
        |
        v
Persistent LBE runtime
        |
        +-- session + workspace identity
        +-- provider/model selection
        +-- mode + permissions + policy
        +-- governed tool orchestration
        +-- live command/tool events
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

Install V2 globally after publication:

```powershell
npm install --global @letterblack/lbe@2.0.0
```

Then inspect the local runtime state:

```powershell
lbe --diagnose
```

The npm package is intentionally a thin bootstrap layer and does not bundle a Python runtime, provider account, model, API key, or workspace state.

Install the coordinated V2 Python wheel into the managed runtime:

```powershell
lbe --install --wheel C:\path\to\lbe_guard_inspector-2.0.0-py3-none-any.whl
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

The runtime includes first-party `openai`, `anthropic`, and `gemini` adapters plus `openai-compatible` for compatible endpoints. All adapters use the same persistent LBE session, governance, tools, evidence, validation, and completion owners; changing an adapter never transfers those authorities to a provider.

## Operating modes

The runtime exposes thin CLI mode commands over the same persistent runtime services:

- `lbe code` — governed coding workflow;
- `lbe audit` — read-only audit workflow;
- `lbe investigate` — investigation workflow.

These commands do not implement separate policy, provider, evidence, or completion systems.

## Persistent sessions

The CLI supports persistent session lifecycle operations including creation, status, checkpoint/resume/continue, and validation paths implemented by the runtime.

Resume is evidence-aware: persisted memory is not treated as live workspace truth. Current Git/workspace state is re-inspected and stale source-backed facts are invalidated before continued execution.

## Release history

`@letterblack/lbe@0.1.0` remains the first public bootstrap release and its acceptance record remains historical evidence.

V2.0 is a new major release; it does not rewrite the 0.1.0 publication history.

Canonical evidence includes:

- `docs/design/PROFESSIONAL_AGENT_RUNTIME_CANONICAL_IMPLEMENTATION_PLAN.md`
- `docs/acceptance/C5_R7_ACCEPTANCE_RECORD.md`
- `docs/acceptance/POST_V1_RELEASE_PACKAGE_READINESS.md`
- `docs/acceptance/POST_V1_NPM_CONSUMER_DISTRIBUTION_READINESS.md`
- `docs/acceptance/V2_RELEASE_READINESS.md`

## Legacy Guard Inspector surfaces

The original deterministic Guard Inspector and audit surfaces remain installed compatibility/read-only capabilities:

```text
lbe-guard-inspector
lbe-guard-inspector-evidence
lbe-guard-audit
```

They are no longer the complete product identity or primary user control surface. The primary persistent-agent control surface is `lbe`.

## Python package

The managed Python runtime package builds as:

```text
lbe-guard-inspector 2.0.0
```

with Python `>=3.11` and the console entry point:

```text
lbe = lbe_guard_inspector.cli:main
```

The historical Python distribution name does not change runtime ownership: `lbe` is the primary CLI and persistent LBE runtime surface.

## Development and release validation

Run the repository suite:

```powershell
python -m pytest -q
```

Build the Python release artifacts:

```powershell
python -m build
```

Run npm bootstrap tests and tarball audit from `npm/`:

```powershell
npm test
npm pack --dry-run --json
```

The `v2-release-candidate` GitHub workflow performs the coordinated Python/npm release-candidate build and uploads both artifact families without publishing them.

For release/consumer claims, unit tests alone are insufficient. Use the source-independent validation ladder: exact-version checks -> Python suite -> Python wheel/sdist build -> npm tests -> npm tarball allowlist -> managed-runtime install -> CLI smoke -> persistent session/workspace proof -> intentional registry publication.

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
