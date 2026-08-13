# @letterblack/lbe

`@letterblack/lbe` is the public npm bootstrap/launcher for the managed Python LBE persistent-agent runtime.

It is intentionally thin. It does **not** implement provider, session, governance, tool, evidence, validation, or completion behavior in Node.

The ownership boundary is:

```text
@letterblack/lbe
  -> install / discover / launch / upgrade / diagnose

Python LBE runtime
  -> provider / sessions / governance / tools
  -> evidence / validation / completion
```

## Install

```powershell
npm install --global @letterblack/lbe@2.0.0
```

Then inspect the local runtime state:

```powershell
lbe --diagnose
```

The npm package does not bundle a Python runtime, model, provider account, API key, or persistent workspace state.

## Install the managed Python runtime

V2 accepts an approved local LBE 2.0.x wheel:

```powershell
lbe --install --wheel C:\artifacts\lbe_guard_inspector-2.0.0-py3-none-any.whl
```

After the managed runtime is installed, the launcher transparently forwards the normal Python CLI:

```powershell
lbe --help
lbe provider list
lbe session create ...
lbe session status ...
lbe audit ...
lbe investigate ...
lbe code ...
```

Use `lbe --help` and command-level help for exact arguments.

## V2.0 scope

V2.0 is the first major persistent-agent runtime release. It includes the verified provider event contract, capability discovery, provider adapters, persistent Session/Turn/Item/Event substrate, governed professional capability backends, live command/tool events, governed provider continuation with evidence-gated completion, and the initial typed bidirectional control-protocol contract with verified initialization/read-only session/event handlers.

Later 2.x releases may extend the control protocol with live subscriptions, session create/resume control handlers, turn steering, interrupt/cancel, stdio transport, MCP/interactive clients, and additional capability backends without redefining the V2.0 ownership boundary.

## State and configuration

Managed runtime code is stored under `LBE_HOME/runtime`.

User configuration and persistent state remain separate:

```text
LBE_HOME/
  runtime/
  config/
  state/
```

`LBE_HOME` may be set to choose a controlled user-scoped installation location.

Provider credentials remain external user-owned configuration and are never stored by the npm wrapper.

Uninstalling or reinstalling the npm package must not silently destroy persistent LBE session state.

## Requirements

- Node.js `>=20`
- supported Python runtime discoverable by the launcher for managed-runtime installation
- Python LBE requires Python `>=3.11`
- npm V2 supports managed Python package series `2.0.x`

## Public package status

`@letterblack/lbe@0.1.0` remains the first public bootstrap release.

`@letterblack/lbe@2.0.0` is the V2 release candidate. Publication should occur only after the exact release commit passes the Python suite, npm tests, Python wheel build, npm tarball audit, and clean managed-runtime smoke verification.

The npm package contains only the allowlisted launcher/bootstrap files and does not contain Python runtime code, provider credentials, runtime databases, proof workspaces, or development-only artifacts.

## Architecture rule

If a feature needs reasoning-provider behavior, persistent sessions, workspace authorization, governed execution, evidence, validation, or completion semantics, it belongs in the Python LBE runtime—not in this npm wrapper.
