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
npm install --global @letterblack/lbe
```

Then inspect the local runtime state:

```powershell
lbe --diagnose
```

The npm package does not bundle a Python runtime, model, provider account, API key, or persistent workspace state.

## Install the managed Python runtime

The current bootstrap accepts an approved local LBE wheel:

```powershell
lbe --install --wheel C:\artifacts\lbe_guard_inspector-0.2.1-py3-none-any.whl
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
- Python LBE currently requires Python `>=3.11`

## Public package status

`@letterblack/lbe@0.1.0` is the first public npm bootstrap release.

The public package contains only the allowlisted launcher/bootstrap files and does not contain Python runtime code, provider credentials, runtime databases, proof workspaces, or development-only artifacts.

## Architecture rule

If a feature needs reasoning-provider behavior, persistent sessions, workspace authorization, governed execution, evidence, validation, or completion semantics, it belongs in the Python LBE runtime—not in this npm wrapper.
