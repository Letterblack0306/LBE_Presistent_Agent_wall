# Post-V1 npm Consumer Distribution Readiness

Updated: 2026-08-12
Status: **PUBLIC npm BOOTSTRAP RELEASE PUBLISHED AND CLEAN-CONSUMER INSTALL VERIFIED**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Package: `@letterblack/lbe@0.1.0`

This record covers the npm bootstrap distribution track after accepted C5/R7 V1. It does not replace the Python LBE runtime or reopen C5/R7.

## Ownership and supported matrix

`@letterblack/lbe` owns only runtime discovery, managed Python-environment creation, installation of an approved local wheel, diagnostics, version compatibility, and transparent process forwarding.

Python `lbe-guard-inspector` remains the only owner of provider connections, sessions, governance, tools, evidence, validation, and completion.

The wrapper requires Node `>=20` and discovers Python `>=3.11`. Local consumer proof used Node 24.15.0, npm 11.12.1, and managed Python 3.14.4. The existing Python package-readiness record supplies clean-install evidence on Windows Python 3.12.10 and 3.14.4; Python 3.11 and 3.13 remain declared/CI targets rather than freshly executed consumer installs in this record.

## Package surface and state boundary

The npm tarball is restricted to these eight files:

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

It contains no Python runtime, database, provider configuration, credentials, proof workspace, test tree, or development artifact.

The wrapper places versioned managed Python environments and runtime metadata below `LBE_HOME/runtime`; user-owned configuration and persistent SQLite state remain separately below `LBE_HOME/config` and `LBE_HOME/state`. No secret is copied into runtime metadata.

## Local consumer proof

An isolated consumer directory installed the packed local `@letterblack/lbe` tarball with no source checkout used for the normal command path.

The consumer completed:

```text
lbe --diagnose
-> explicit Python-supported / runtime-not-installed result

lbe --install --wheel <approved local lbe-guard-inspector wheel>
-> managed virtual environment
-> package/version verification
-> packaged memory_schema.sql verification
-> compatible runtime metadata

lbe --help
lbe provider list
lbe session create
lbe session status
-> installed CLI forwarding and persistent SQLite state
```

A controlled Git workspace was then resumed through the npm-launched CLI. The same session identity, workspace identity, current Git state, runtime policy, and permissions were readable after installation.

A non-Git resume failure had previously leaked a raw subprocess traceback; the Python CLI now returns the established structured error envelope instead, with focused coverage. This is a consumer error-reporting correction, not a new runtime owner.

Provider-backed coding/audit operations were intentionally not required for the initial local consumer packaging proof when no user-owned provider connection was supplied. That is an external configuration boundary, not a package defect.

## State lifecycle proof

The same persisted SQLite database survived:

```text
npm uninstall @letterblack/lbe
-> state database hash unchanged

npm install <same local tarball>
-> same session status readable

install temporary newer npm wrapper + temporary newer approved Python wheel
-> newer managed runtime selected
-> same state database hash unchanged and session status readable
```

The upgrade fixture was temporary and was not added to this repository. No automatic database migration or state deletion occurs during npm install, reinstall, or Python-runtime replacement.

## Validation evidence

The pre-publication local distribution track proved:

```text
python -m pytest -q tests/test_cli.py     19 passed
npm test (from npm/)                       8 passed
python -m pytest -q                        632 passed
npm pack --dry-run --json                  8-file allowlist passed
git diff --check origin/main...HEAD        passed
```

Package/authentication preflight later proved:

- `.env` remained gitignored and untracked;
- npm authentication resolved to `pravesh0306`;
- the authenticated user was owner of the `@letterblack` organization;
- exact-package `npm publish --dry-run --access public` for `@letterblack/lbe@0.1.0` passed;
- the dry-run tarball contained the expected eight audited files;
- no credential value was committed or recorded.

## Public release result

`@letterblack/lbe@0.1.0` was successfully submitted to npm with:

```text
npm publish --access public
-> registry PUT 200
```

npm publication receipt:

```text
package: @letterblack/lbe
version: 0.1.0
published: 2026-08-12T09:30:39.016Z
shasum: c884f5c018e5c9139e4fb00d0640042c4c2f88e1
```

After publication, the public registry resolved version `0.1.0` as `latest`, and a fresh unauthenticated consumer installed the public package successfully.

The installed public launcher reported the expected pre-bootstrap state:

```text
PYTHON_SUPPORTED
LBE_RUNTIME_NOT_INSTALLED
```

This proves the public npm distribution surface independently of the source checkout and independently of authenticated registry access.

No provider credential, npm token value, credential file, runtime database, or proof workspace was published in the npm package.

## Product identity after publication

The public product surface is now CLI-first:

```text
npm / npx
  -> @letterblack/lbe
  -> thin Node bootstrap / launcher
  -> managed Python LBE runtime
  -> `lbe` CLI
```

The historical Guard Inspector remains part of the Python implementation and legacy/read-only command surface, but it is no longer the complete product identity.

Primary user control is the `lbe` CLI. Node does not duplicate LBE runtime semantics.

## Current decision

The npm consumer distribution track is **COMPLETE for the first public bootstrap release**.

Public publication is no longer a deferred item for `0.1.0`; it has occurred and was externally verified by clean unauthenticated installation.

The known GitHub Actions startup/billing condition remains a separate hosted-CI verification limitation. It is not evidence that npm publication, local package readiness, or the accepted Python runtime failed.

## Deferred work

Remaining post-V1 work includes:

- representative-workspace provider capability (B2);
- broader real-workspace dogfooding through the npm-installed path;
- provider/model quality and performance evaluation;
- Cline integration;
- broader governed tools;
- UI/TUI work;
- hosted CI re-verification after GitHub account availability is restored;
- production hardening and future npm/Python runtime upgrade flows.

Do not reclassify `@letterblack/lbe@0.1.0` as unpublished or publication-pending in later status documents.
