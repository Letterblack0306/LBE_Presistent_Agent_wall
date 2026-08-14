# LBE Persistent Agent Runtime

LBE is a persistent, provider-neutral local agent runtime with a CLI-first control surface.

V2 owns persistent sessions, provider-neutral model transport, governed tools, live tool/process events, evidence, validation, completion semantics, and the initial typed agent-control protocol.

The public installation/bootstrap surface is:

```text
npm / npx
  -> @letterblack/lbe
  -> thin Node installer / launcher
  -> exact approved public Python runtime
  -> managed Python environment
  -> `lbe` CLI
```

The Node/npm layer does **not** implement a second LBE runtime. It discovers Python, acquires and verifies the approved Python artifact, installs/launches/upgrades the managed runtime, and diagnoses installation state.

## Current V2 release line

Published V2.0 history:

```text
@letterblack/lbe 2.0.0
lbe-guard-inspector 2.0.0
```

V2.0 froze the verified professional runtime through P7 plus the verified P8 typed control-protocol contract and initialization/read-only session/event handlers.

The 2.0.2 correction keeps the same runtime ownership boundary but fixes the public end-user installation path:

```text
@letterblack/lbe 2.0.2
lbe-guard-inspector 2.0.2
```

A normal public user must not need the private repository or a manually copied wheel.

## Public install

Install the public launcher:

```powershell
npm install --global @letterblack/lbe@2.0.2
```

Install the managed runtime:

```powershell
lbe --install
```

The launcher acquires the exact configured `lbe-guard-inspector==2.0.2` universal wheel from the public Python registry, validates package identity/version, validates the approved HTTPS artifact host, verifies SHA-256, creates the managed environment, installs the runtime, verifies the installed version and `lbe` executable, and confirms runtime compatibility.

Then verify/use LBE:

```powershell
lbe --diagnose
lbe --help
lbe provider list
lbe provider check ...
lbe session create ...
lbe session status ...
lbe audit ...
lbe investigate ...
lbe code ...
```

Use `lbe --help` and command-level help as the executable source of truth for exact runtime arguments.

### Offline/developer override

A local wheel remains supported only as an explicit offline/developer path:

```powershell
lbe --install --wheel "C:\path\to\lbe_guard_inspector-2.0.2-py3-none-any.whl"
```

This is not the normal public-user workflow.

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

## Distribution boundary

The public npm package remains bootstrap/distribution infrastructure. It does not implement provider/session/governance/tool/evidence/completion behavior and does not embed user credentials, runtime databases, proof workspaces, or persistent state.

For the corrected 2.0.2 public flow, the matching Python runtime must be available from a public registry that requires no authentication to the private source repository. The npm launcher pins the exact Python version and fails closed if that public artifact is missing or fails integrity checks.

Canonical public-distribution contract:

- `docs/design/PUBLIC_RUNTIME_DISTRIBUTION_CONTRACT.md`
- `docs/acceptance/V2_0_1_PUBLIC_INSTALLER_READINESS.md`

## Runtime and state boundary

The npm launcher and Python runtime keep installation, configuration, and persistent state separate.

```text
LBE_HOME/
  runtime/   managed versioned Python environments and transient download cache
  config/    user-owned runtime/provider configuration
  state/     persistent SQLite/session state
```

`LBE_HOME` may be set to choose a controlled user-scoped location.

Provider credentials remain external user-owned configuration. They must not be embedded in npm package contents, Python package source, runtime databases, acceptance records, or Git history.

Runtime replacement must not delete user-owned `config/` or `state/`.

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

## Release history and scope

`@letterblack/lbe@0.1.0` remains the first public bootstrap release.

`@letterblack/lbe@2.0.0` is the first published V2 major release and remains historical evidence.

`2.0.2` is a patch correction to the public installation experience. It does not claim the later P8 mutation controls, live subscriptions, stdio transport, MCP/interactive clients, browser capability, or additional professional capability backends as completed.

Canonical evidence includes:

- `docs/design/PROFESSIONAL_AGENT_RUNTIME_CANONICAL_IMPLEMENTATION_PLAN.md`
- `docs/design/PUBLIC_RUNTIME_DISTRIBUTION_CONTRACT.md`
- `docs/acceptance/C5_R7_ACCEPTANCE_RECORD.md`
- `docs/acceptance/POST_V1_RELEASE_PACKAGE_READINESS.md`
- `docs/acceptance/POST_V1_NPM_CONSUMER_DISTRIBUTION_READINESS.md`
- `docs/acceptance/V2_RELEASE_READINESS.md`
- `docs/acceptance/V2_0_1_PUBLIC_INSTALLER_READINESS.md`

## Legacy Guard Inspector surfaces

The original deterministic Guard Inspector and audit surfaces remain installed compatibility/read-only capabilities:

```text
lbe-guard-inspector
lbe-guard-inspector-evidence
lbe-guard-audit
```

They are no longer the complete product identity or primary user control surface. The primary persistent-agent control surface is `lbe`.

## Python package

The 2.0.2 managed Python runtime package builds as:

```text
lbe-guard-inspector 2.0.2
```

with Python `>=3.11` and console entry point:

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

The `v2-release-candidate` workflow builds/tests the coordinated 2.0.2 artifacts. The `publish-python-runtime` workflow is the explicit public Python-registry publication path and requires the repository's `pypi` environment/trusted-publisher configuration.

For 2.0.2, npm publication is downstream of Python publication and clean public installation proof:

```text
exact source revision
-> Python tests/build
-> public Python registry publication
-> verify exact public wheel metadata/digest
-> npm tests/tarball audit
-> clean public `lbe --install`
-> npm publication
-> clean unauthenticated npm consumer proof
```

## Non-goals / invariants

Do not introduce:

- a second Node session/runtime implementation;
- a Node provider authority;
- a second permission/policy resolver;
- a second governed tool registry;
- a second evidence/completion system;
- unrestricted generic shell bypasses;
- provider credentials inside package/runtime state;
- private-repository authentication as a normal public-install requirement;
- unpinned or integrity-unverified runtime acquisition;
- memory as a replacement for current workspace/Git evidence.

The npm layer distributes LBE. The Python LBE runtime remains the single execution/governance authority.
