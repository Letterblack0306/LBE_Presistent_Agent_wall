# Public Runtime Distribution Contract

Updated: 2026-08-13
Status: **AUTHORITATIVE DISTRIBUTION CONTRACT**

## Product intent

`@letterblack/lbe` is a public bootstrap/launcher for users installing LBE on machines that do not have the private source repository or locally built release artifacts.

A normal public user must not be required to:

- clone or authenticate to `Letterblack0306/LBE_Presistent_Agent_wall`;
- know what a Python wheel is;
- copy a wheel from a development machine;
- discover a private GitHub release asset;
- provide a source-checkout path.

The normal public flow is:

```text
npm install --global @letterblack/lbe
lbe --install
lbe --diagnose
lbe --help
```

`lbe --install --wheel <path>` remains supported only as an explicit offline/developer override.

## Authority boundary

Automatic acquisition does not move runtime authority into Node.

```text
public npm launcher
  -> discover supported Python
  -> acquire exact approved Python runtime artifact
  -> verify artifact identity/integrity
  -> create/update managed Python environment
  -> launch installed `lbe`

Python LBE runtime
  -> provider/session/workspace ownership
  -> governance/authorization
  -> governed tools
  -> evidence/validation/completion
  -> persistent runtime state
```

The Node package remains bootstrap/distribution infrastructure. It must not implement a second provider, policy, session, tool, evidence, or completion system.

## Public artifact source

The authoritative Python runtime must be available from a public package registry that does not require access to the private source repository.

For the 2.0.x correction track, the default public source is the Python Package Index (PyPI) project:

```text
lbe-guard-inspector
```

The npm launcher pins an exact Python package version. It must not install an unbounded `latest` Python runtime.

Release ordering is therefore:

```text
build + verify exact Python release
-> publish exact Python package to the public Python registry
-> verify public metadata and wheel availability
-> configure npm launcher to that exact version
-> verify clean public `lbe --install`
-> publish npm launcher
```

An npm launcher release must not be marked public-ready while its configured Python runtime artifact is unavailable publicly.

## Integrity requirements

Default public acquisition must:

1. request metadata for the exact configured Python package version over HTTPS;
2. select the universal `py3-none-any.whl` release artifact;
3. require a SHA-256 digest in registry metadata;
4. download the wheel over HTTPS from the registry's approved file host;
5. calculate the downloaded wheel SHA-256 locally;
6. reject the artifact if the digest differs;
7. install only after integrity verification;
8. verify the installed Python distribution version equals the configured exact version;
9. verify the installed `lbe` executable exists;
10. verify the resulting managed runtime is compatible with the npm launcher's supported Python-runtime series.

No credential is required for normal public acquisition.

## State boundary

Automatic installation may replace or add a versioned managed runtime below `LBE_HOME/runtime`, but must not delete or recreate user-owned configuration or persistent state:

```text
LBE_HOME/
  runtime/   versioned managed runtime environments and transient download cache
  config/    user-owned provider/runtime configuration
  state/     persistent sessions and SQLite state
```

Transient downloaded wheel files must be removed after installation succeeds or fails.

## Failure semantics

Public acquisition fails closed with an actionable installer error when:

- no supported Python is available;
- public package metadata cannot be retrieved;
- the exact configured release does not exist;
- the expected universal wheel is absent or ambiguous;
- registry metadata lacks SHA-256;
- the artifact URL is not HTTPS or is not from the approved registry file host;
- the downloaded artifact hash does not match metadata;
- managed environment creation fails;
- package installation fails;
- installed package version differs from the configured version;
- the installed `lbe` executable is missing;
- resulting runtime metadata is incompatible.

The launcher must never silently fall back to a source checkout, private GitHub asset, unpinned package version, or arbitrary external URL.

## Release correction

`@letterblack/lbe@2.0.0` proved the public npm launcher itself, but its default runtime installation path still required a manually supplied wheel. That behavior is retained as an offline override, not the public default.

The next 2.0.x release must implement and prove this contract before being described as the corrected public end-user installer.
