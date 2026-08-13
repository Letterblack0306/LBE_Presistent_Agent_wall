# LBE V2 Release Readiness

Updated: 2026-08-13
Status: **RELEASE READY — PUBLICATION NOT YET CLAIMED**
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

## Required publication sequence

The source/package candidate is release-ready. Publication remains a separate intentional action.

Recommended release sequence:

1. merge the verified candidate to the release branch/main without changing release files;
2. tag the exact release commit as `v2.0.0`;
3. build the Python wheel/sdist from that exact tagged commit;
4. produce the npm tarball from `npm/`;
5. install the exact V2 npm tarball and exact V2 Python wheel in a clean consumer location and run the managed-runtime smoke proof;
6. verify no credentials, `.env`, state database, proof workspace, or development-only artifact appears in either artifact;
7. publish `@letterblack/lbe@2.0.0` intentionally with public access;
8. verify the npm registry resolves `2.0.0` and a clean unauthenticated consumer can install it;
9. record the registry publication receipt separately.

The Python wheel is an approved managed-runtime artifact. PyPI publication is not required by the current npm bootstrap contract unless a later release explicitly chooses public Python-registry distribution.

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
V2_NPM_PUBLISHED = false
```

Do not report V2 as published until an npm registry receipt for `@letterblack/lbe@2.0.0` and clean public-install verification exist.
