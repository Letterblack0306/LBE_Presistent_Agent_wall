# LBE V2.0.2 Public Installer Readiness

Updated: 2026-08-13
Status: **IMPLEMENTED — VERIFICATION AND PUBLIC PYTHON ARTIFACT PENDING**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Correction pair:

```text
@letterblack/lbe@2.0.2
lbe-guard-inspector==2.0.2
```

## Why this patch exists

`@letterblack/lbe@2.0.0` is publicly published and its launcher installation was verified from a clean consumer machine. However, the default managed-runtime installation path still required the user to manually obtain and supply a local Python wheel.

That requirement conflicts with the documented public-bootstrap product intent. A normal public user must not need access to the private source repository, a development-machine artifact, or knowledge of Python wheel paths.

V2.0.2 corrects the distribution path without moving runtime authority into Node.

## Correct public flow

```text
npm install --global @letterblack/lbe@2.0.2
lbe --install
lbe --diagnose
lbe --help
```

`lbe --install --wheel <path>` remains an offline/developer override only.

## Implemented correction

The npm launcher now:

1. pins the public Python runtime exactly to `lbe-guard-inspector==2.0.2`;
2. requests exact-version metadata from PyPI over HTTPS;
3. requires exactly one universal `py3-none-any.whl` artifact;
4. requires a valid SHA-256 digest in registry metadata;
5. accepts the wheel only from the approved HTTPS Python package file host;
6. downloads the wheel without private-repository credentials;
7. calculates the downloaded SHA-256 and rejects mismatch;
8. creates/updates the managed Python environment;
9. installs the verified wheel;
10. verifies installed package version `2.0.2`;
11. verifies packaged memory schema and the installed `lbe` executable;
12. verifies resulting runtime compatibility;
13. records non-secret installation-source metadata;
14. removes the transient downloaded wheel after success/failure.

The public npm tarball remains launcher-only; Python runtime authority remains entirely in the Python package.

## Public Python distribution requirement

The private GitHub repository is not a valid anonymous artifact source. Therefore `lbe-guard-inspector==2.0.2` must be published to the public Python Package Index before `@letterblack/lbe@2.0.2` may be marked release-ready.

GitHub workflow:

```text
.github/workflows/publish-python-runtime.yml
```

is the explicit Python publication path. It uses PyPI Trusted Publishing/OIDC through the repository `pypi` environment and intentionally stores no PyPI token in source.

Required external setup before the first run:

- configure the PyPI project/pending trusted publisher for this repository/workflow/environment;
- keep the GitHub environment name exactly `pypi` unless both workflow and PyPI publisher configuration are intentionally changed.

## Required verification gates

The exact 2.0.2 candidate must prove:

### Source/package consistency

- `pyproject.toml` package version is `2.0.2`;
- `npm/package.json` version is `2.0.2`;
- npm public runtime pin is exactly `2.0.2`;
- supported runtime series remains `2.0.x`.

### Unit/build proof

- full Python test suite passes;
- Python wheel/sdist build succeeds;
- `npm test` passes including public acquisition/integrity tests;
- npm tarball allowlist remains the established launcher-only surface;
- `git diff --check` passes.

### Public Python artifact proof

After Python publication:

- public registry resolves `lbe-guard-inspector==2.0.2` anonymously;
- metadata identity/version match exactly;
- exactly one universal wheel is available;
- registry SHA-256 is present;
- anonymous wheel download succeeds.

### Clean public end-to-end proof

On a machine without source checkout/runtime artifacts:

```text
npm install --global @letterblack/lbe@2.0.2
lbe --diagnose
  -> Python supported
  -> runtime not installed (before bootstrap)

lbe --install
  -> public registry acquisition
  -> SHA-256 verification
  -> managed runtime installation

lbe --diagnose
  -> LBE_RUNTIME_COMPATIBLE
  -> pythonPackageVersion = 2.0.2
  -> installSource = pypi

lbe --help
  -> exits successfully through managed Python runtime
```

The test must also prove `LBE_HOME/config` and `LBE_HOME/state` are not deleted by install/reinstall.

### Release ordering

Do not publish npm 2.0.2 before the matching Python artifact and clean public `lbe --install` proof exist.

```text
Python 2.0.2 verified
-> Python 2.0.2 publicly published
-> public Python metadata/download verified
-> clean npm-tarball + public-runtime install verified
-> npm 2.0.2 published
-> clean unauthenticated npm install verified
```

## Historical state

Do not rewrite the V2.0 publication record.

```text
@letterblack/lbe@2.0.0 = published historical V2 release
@letterblack/lbe@2.0.2 = public-installer correction, not yet published
```

## Current state

```text
V2_0_1_PUBLIC_INSTALLER_IMPLEMENTED = true
V2_0_1_SOURCE_VERIFIED = pending
V2_0_1_PYPI_PUBLISHED = false
V2_0_1_PUBLIC_INSTALL_SMOKE = pending
V2_0_1_NPM_PUBLISHED = false
```

Canonical design contract:

`docs/design/PUBLIC_RUNTIME_DISTRIBUTION_CONTRACT.md`
