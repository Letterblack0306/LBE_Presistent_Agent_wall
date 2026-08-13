# LBE V2 Release Readiness

Updated: 2026-08-13
Status: **RELEASE CANDIDATE — PUBLICATION NOT YET CLAIMED**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
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

## Required pre-publication gates

Publication is authorized only after the exact candidate commit proves all of the following:

1. `pyproject.toml` reports `lbe-guard-inspector` version `2.0.0`.
2. `npm/package.json` reports `@letterblack/lbe` version `2.0.0`.
3. npm launcher compatibility series is exactly `2.0.`.
4. Full Python test suite passes.
5. `python -m build` produces:
   - `dist/lbe_guard_inspector-2.0.0-py3-none-any.whl`
   - `dist/lbe_guard_inspector-2.0.0.tar.gz`
6. `npm test` passes from `npm/`.
7. `npm pack --dry-run --json` contains only the established eight-file launcher allowlist.
8. A real npm tarball `letterblack-lbe-2.0.0.tgz` can be produced.
9. `git diff --check` is clean.
10. Clean managed-runtime smoke installs the exact V2 wheel through the V2 npm launcher and proves:
    - `lbe --diagnose` recognizes the installed runtime as compatible;
    - `lbe --help` works;
    - persistent session state remains outside runtime installation and survives upgrade/reinstall.
11. No provider credential, npm token, `.env`, runtime database, proof workspace, or development-only artifact is present in either public distribution artifact.
12. Registry publication is performed intentionally only after the above gates pass.

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

Until the exact V2 candidate passes the release verifier and an npm registry receipt exists:

```text
V2_RELEASE_READY = pending verification
V2_NPM_PUBLISHED = false
```

Do not report V2 as published solely because the GitHub branch is release-prepared.
