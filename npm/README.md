# @letterblack/lbe

`@letterblack/lbe` is the public npm bootstrap/launcher for the managed Python LBE persistent-agent runtime.

It is intentionally thin. It does **not** implement provider, session, governance, tool, evidence, validation, or completion behavior in Node.

The ownership boundary is:

```text
@letterblack/lbe
  -> install / acquire / verify / discover / launch / upgrade / diagnose

Python LBE runtime
  -> provider / sessions / governance / tools
  -> evidence / validation / completion
```

## Public install

Install the launcher from npm:

```powershell
npm install --global @letterblack/lbe@2.0.2
```

Then install the managed Python runtime:

```powershell
lbe --install
```

The public installer acquires the exact configured `lbe-guard-inspector==2.0.2` wheel from PyPI, verifies the registry identity/version, requires the universal `py3-none-any` wheel, verifies its SHA-256 digest, creates the managed Python environment, installs it, and verifies the resulting `lbe` runtime.

Then verify and use LBE:

```powershell
lbe --diagnose
lbe --help
lbe provider list
lbe session create ...
lbe session status ...
lbe audit ...
lbe investigate ...
lbe code ...
```

Use `lbe --help` and command-level help for exact runtime arguments.

A normal public user does not need the private source repository or a locally built wheel.

## Offline/developer wheel override

For an offline environment or controlled development/release proof, an explicit local wheel remains supported:

```powershell
lbe --install --wheel "C:\artifacts\lbe_guard_inspector-2.0.2-py3-none-any.whl"
```

This is an override, not the normal public installation path.

## Distribution boundary

The npm tarball does not embed Python runtime implementation code, provider credentials, runtime databases, proof workspaces, or user state. Its job is to acquire and launch the approved Python runtime.

The default public runtime source must be publicly accessible without private GitHub authentication. For 2.0.2 the configured source is PyPI project `lbe-guard-inspector`, exact version `2.0.2`.

If that exact public Python artifact is unavailable or fails integrity checks, `lbe --install` fails closed rather than falling back to a source checkout, private GitHub asset, unpinned version, or arbitrary external URL.

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

Uninstalling/reinstalling the npm launcher or replacing the managed Python runtime must not silently destroy persistent LBE session state.

## Requirements

- Node.js `>=20`
- supported Python runtime discoverable by the launcher
- Python LBE requires Python `>=3.11`
- npm V2 supports managed Python package series `2.0.x`
- network access to the public Python registry for the default `lbe --install` path

## V2 release status

`@letterblack/lbe@2.0.0` is the published V2.0 release and remains historical release evidence.

`2.0.2` is the public-installer correction: the normal install path changes from manual wheel supply to automatic acquisition of the exact approved public Python runtime. Runtime authority remains unchanged.

The 2.0.2 npm launcher must not be published as ready until the matching `lbe-guard-inspector==2.0.2` artifact is publicly available and a clean machine proves:

```text
npm install --global @letterblack/lbe@2.0.2
lbe --install
lbe --diagnose
lbe --help
```

## Architecture rule

If a feature needs reasoning-provider behavior, persistent sessions, workspace authorization, governed execution, evidence, validation, or completion semantics, it belongs in the Python LBE runtime—not in this npm wrapper.
