# Post-V1 npm Consumer Distribution Readiness

Updated: 2026-08-12
Status: **LOCAL CONSUMER WORKFLOW READY; PUBLICATION NOT AUTHORIZED**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Implementation revision: `01fac7e9ada73991cb7a2e204544d00b2d5368bf`

This record covers the npm bootstrap distribution track after accepted C5/R7
V1. It does not replace the Python LBE runtime, reopen C5/R7, or publish an
npm package.

## Ownership and supported matrix

`@letterblack/lbe` owns only runtime discovery, managed Python-environment
creation, installation of an approved local wheel, diagnostics, and transparent
process forwarding. Python `lbe-guard-inspector` remains the only owner of
provider connections, sessions, governance, tools, evidence, validation, and
completion.

The wrapper requires Node `>=20` and discovers Python `>=3.11`. The local
consumer proof used Node 24.15.0, npm 11.12.1, and managed Python 3.14.4.
The existing Python package-readiness record supplies clean-install evidence on
Windows Python 3.12.10 and 3.14.4; Python 3.11 and 3.13 remain declared/CI
matrix targets rather than freshly executed consumer installs here.

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

It contains no Python runtime, database, provider configuration, credentials,
proof workspace, test tree, or development artifact. The wrapper places only
its versioned Python environments and metadata below `LBE_HOME/runtime`;
user-owned configuration and persistent SQLite state remain separately below
`LBE_HOME/config` and `LBE_HOME/state`. No secret is copied into metadata.

## Local consumer proof

An isolated consumer directory installed the packed local `@letterblack/lbe`
tarball with `npm install --ignore-scripts`; no source checkout was used for
the normal command path. The consumer then completed:

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

A controlled Git workspace was then resumed through the npm-launched CLI.
The same session identity, workspace identity, current Git state, runtime
policy, and permissions were readable after installation. A non-Git resume
failure had previously leaked a raw subprocess traceback; the Python CLI now
returns the established structured error envelope instead, with focused
coverage. This is a consumer error-reporting correction, not a new runtime
owner.

Provider-backed coding/audit operations were intentionally not attempted in
this consumer proof because no user-owned provider connection was supplied.
That is an external configuration boundary, not a package defect.

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

The upgrade fixture was temporary and was not added to this repository. No
automatic database migration or state deletion occurs during npm install,
reinstall, or Python-runtime replacement.

## Final package and validation evidence

The final local artifacts were built outside the repository:

```text
@letterblack/lbe 0.1.0 tarball SHA-256:
cbde290afbfe2606f3e6ac4005497770f384483496ae22c2c18eb07f26e6b9d7

lbe-guard-inspector 0.2.0 wheel SHA-256:
86aca0bd37f9ee94fe96036c025de4d0c85c77ac96421899266db4ce071fe3fc
```

The isolated consumer reinstalled those final artifacts, reported a compatible
runtime, listed the installed `openai-compatible` adapter, and read the
existing persistent session. Validation on revision
`c207a0a87e373252ebc1df015ed35f2d66e9dc22` passed:

```text
python -m pytest -q tests/test_cli.py     19 passed
npm test (from npm/)                       8 passed
python -m pytest -q                        632 passed
npm pack --dry-run --json                  8-file allowlist passed
git diff --check origin/main...HEAD        passed
```

## Release decision

The local npm consumer distribution workflow is **READY** for an explicitly
authorized controlled distribution action. It is **BLOCKED** for public
publication because a license decision has not been supplied. No npm
publication, tag, release, credential lookup, or credential persistence
occurred in this track.

The known GitHub Actions startup/billing condition remains an external
verification limitation; it is not evidence that the npm package or Python
runtime failed locally. Rerun the existing workflow after account availability
is restored before treating hosted CI as green.

## Deferred work

Representative-workspace provider capability (B2), provider/model quality,
Cline integration, broader tools, UI/TUI work, and public publication remain
outside this completed consumer-distribution proof.
