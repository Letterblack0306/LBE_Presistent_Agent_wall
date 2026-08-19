# Publication Precheck Gate

Status: **OPEN — AUDIT ONLY — PUBLISH LOCKED — IMPLEMENTATION LOCKED**

phase: `PUBLICATION_PRECHECK`

slice: `VERIFY_PYPI_NAMESPACE_VERSION_AND_TRUSTED_PUBLISHING`

required_evidence_level: `LIVE_REGISTRY_PLUS_GITHUB_PUBLISHING_CONFIGURATION`

## Entry condition

`RELEASE_PACKAGE_READINESS_ACCEPTANCE=PASS`.

## Purpose

Determine whether the already-validated canonical Python package may be published without guessing about public registry state or trusted-publishing configuration.

## Canonical package target under audit

- distribution: `lbe-guard-inspector`
- canonical version authority: `pyproject.toml`
- currently proven canonical version: `0.2.0`
- publication workflow: `.github/workflows/publish-python-runtime.yml`
- trigger: manual `workflow_dispatch` only

The version must not be changed during this precheck.

## Required live proof

1. query PyPI directly for `lbe-guard-inspector`;
2. classify the project namespace as absent, present-owned, present-foreign, or unresolved;
3. if present, enumerate published versions and prove whether `0.2.0` is already used;
4. inspect the GitHub `pypi` environment / workflow requirements available to the repository;
5. prove that the workflow still uses OIDC trusted publishing (`id-token: write` and `pypa/gh-action-pypi-publish`);
6. do not execute the workflow or publish anything during precheck.

## PASS condition

PASS requires all of the following:

- live PyPI namespace state is resolved;
- canonical version availability is resolved;
- no version collision exists for the intended publication;
- repository/workflow trusted-publishing requirements are resolved sufficiently to execute a later explicitly authorized publish action;
- canonical `main` and tracked source remain unchanged;
- publication remains locked during this gate.

## Blocking classifications

- `PYPI_NAMESPACE_UNRESOLVED`
- `PYPI_NAMESPACE_FOREIGN`
- `PYPI_VERSION_ALREADY_EXISTS`
- `TRUSTED_PUBLISHING_UNVERIFIED`
- `TRACKED_SOURCE_DIRTY`
- `PACKAGE_VERSION_CONFLICT`

## Forbidden

- publishing to PyPI;
- changing `pyproject.toml` version;
- choosing a replacement version by inference;
- creating tags or GitHub releases;
- adding an npm publication path;
- changing runtime/package/workflow implementation;
- weakening trusted-publishing permissions or environment controls.

## Advancement rule

If this precheck passes, record the exact target/version and trusted-publishing evidence, then require a separate explicit publication execution authorization before dispatching the publish workflow.

If any blocking classification is reached, stop and resolve it through a separately authorized gate; do not publish.
