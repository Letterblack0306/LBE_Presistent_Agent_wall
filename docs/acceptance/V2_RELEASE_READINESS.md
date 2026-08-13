# LBE V2 Release Readiness

Updated: 2026-08-13
Status: **PUBLIC NPM RELEASE PUBLISHED AND PUBLIC LAUNCHER INSTALL VERIFIED**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Verified candidate commit: `5d94bd51fcd6b9f6265f4b618d78fb34ae46e843`
Release pair:

```text
@letterblack/lbe@2.0.0
lbe-guard-inspector==2.0.0
```

## Release decision

V2.0 intentionally freezes the professional persistent-agent runtime at the currently verified scope rather than waiting for every later 2.x feature.

Included in V2.0:

- P0 provider-event normalization contract;
- P1 professional runtime capability contract;
- P2 provider/model capability discovery and negotiation;
- P3 provider-native streaming/tool-call adapters;
- P4 persistent Session/Turn/Item/Event substrate;
- P5 professional capability backends implemented truthfully at this milestone;
- P6 live command/tool event production and persistence;
- P7 governed provider continuation, effective tool projection, evidence-gated completion, and canonical stop boundaries;
- P8 typed bidirectional control-protocol contract plus verified initialization/read-only session/status/event-list handlers.

Deferred to later 2.x releases rather than claimed in V2.0:

- live control-protocol event subscription delivery;
- session create/resume control handlers;
- active turn steering;
- interrupt/cancel control execution;
- stdio/JSONL bidirectional server transport;
- MCP external-agent surface;
- transcript renderer/TUI/IDE client;
- browser capability and broader capability backends;
- cooperative/strict external-agent acceptance and final professional E2E acceptance.

The deferred items are not regressions in V2.0 because this document does not advertise them as released functionality.

## Distribution boundary

The npm package remains a thin public launcher. It must not become a second runtime.

```text
npm / npx
  -> @letterblack/lbe@2.0.0
  -> managed runtime installer/launcher
  -> lbe-guard-inspector==2.0.0
  -> authoritative Python LBE runtime
```

The coordinated major version is deliberate. npm V2 accepts only managed Python `2.0.x` runtime metadata. Older managed Python `0.2.x` runtimes are reported as incompatible until the V2 wheel is installed; persistent user state remains outside the versioned runtime directory and must not be deleted by the upgrade.

## Release-verifier result

The exact candidate commit completed the release verifier successfully on 2026-08-13.

Observed proof:

```text
PYTHON_PACKAGE_VERSION=2.0.0
NPM_PACKAGE_VERSION=2.0.0
PYTHON_COMPAT_SERIES=2.0.x
816 passed
Successfully built lbe_guard_inspector-2.0.0.tar.gz and lbe_guard_inspector-2.0.0-py3-none-any.whl
WHEEL_EXISTS=True
SDIST_EXISTS=True
npm test: 8 passed, 0 failed
NPM_TARBALL_ALLOWLIST=PASS
PY_VERSION_EXIT=0
NPM_VERSION_EXIT=0
FULL_EXIT=0
PY_BUILD_EXIT=0
ARTIFACT_EXIT=0
NPM_TEST_EXIT=0
NPM_PACK_DRY_EXIT=0
NPM_ALLOWLIST_EXIT=0
NPM_PACK_EXIT=0
DIFF_EXIT=0
LBE_V2_RELEASE_READY_VERIFY=PASS
```

The npm allowlist remains the established eight-file bootstrap surface:

```text
README.md
bin/lbe.js
lib/launcher.js
lib/paths.js
lib/python-discovery.js
lib/runtime-discovery.js
lib/runtime-install.js
package.json
```

No Python runtime implementation is embedded in the npm tarball.

## Public npm publication proof

`@letterblack/lbe@2.0.0` was published to the public npm registry on 2026-08-13T07:38:28.509Z.

Registry/publication proof:

```text
package: @letterblack/lbe
version: 2.0.0
shasum: 5a2056b974839dc0c169dbb1f84973fcbc73568d
registry versions: 0.1.0, 2.0.0
latest: 2.0.0
LBE_V2_PUBLIC_REGISTRY_VERIFY=PASS
```

The published shasum matches the audited V2 npm tarball produced during the release run.

## Clean public launcher install proof

A fresh public install of `@letterblack/lbe@2.0.0` completed successfully from npm. The installed `lbe` launcher then executed `lbe --diagnose` successfully without source-checkout dependency.

Observed launcher diagnosis:

```text
python.state = PYTHON_SUPPORTED
selected Python = 3.14.6
runtime.state = LBE_RUNTIME_NOT_INSTALLED
```

This is the correct pre-bootstrap state: the public npm launcher is installed and functional, while the managed Python V2 runtime has not yet been installed into `LBE_HOME/runtime`.

The diagnosis also confirms that runtime, config, and persistent state remain separated under the user-scoped `LBE_HOME` layout rather than being bundled into the npm package.

## Remaining managed-runtime smoke proof

The remaining distribution proof is to install the exact `lbe_guard_inspector-2.0.0-py3-none-any.whl` through the public V2 launcher and verify:

1. `lbe --diagnose` reports the managed Python runtime as compatible;
2. `lbe --help` works through the public launcher;
3. the exact installed Python package version is `2.0.0`;
4. persistent state remains outside the versioned runtime directory and survives runtime replacement/reinstall.

This remaining smoke proof does not reopen npm publication. The public npm release itself is complete.

## GitHub release-candidate workflow

`.github/workflows/v2-release-candidate.yml` is a non-publishing proof workflow. It:

- verifies coordinated versions;
- runs the Python suite;
- builds Python wheel/sdist;
- runs npm tests;
- audits the npm tarball allowlist;
- creates the npm tarball;
- uploads the Python and npm artifact families.

It deliberately does not contain registry credentials or an automatic `npm publish` step.

## Historical compatibility

`@letterblack/lbe@0.1.0` remains the first public bootstrap release. Its publication record remains authoritative historical evidence and must not be rewritten.

V2.0 is a new major release. Fixes and extensions after this release belong in subsequent semantic versions (`2.0.x`, `2.1.x`, etc.) according to compatibility impact.

## Publication state

```text
V2_RELEASE_READY = true
V2_RELEASE_VERIFIER = PASS
V2_NPM_PUBLISHED = true
V2_NPM_LATEST = 2.0.0
V2_PUBLIC_LAUNCHER_INSTALL = PASS
V2_MANAGED_RUNTIME_SMOKE = pending
```
