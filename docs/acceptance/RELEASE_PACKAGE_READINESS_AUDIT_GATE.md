# Release / Package Readiness Audit Gate

Status: **OPEN — AUDIT ONLY — IMPLEMENTATION LOCKED — PUBLISH LOCKED**

phase: `RELEASE_PACKAGE_READINESS_ACCEPTANCE`

slice: `AUDIT_CURRENT_DISTRIBUTION_CONTRACT`

required_evidence_level: `CURRENT_SOURCE_PLUS_LOCAL_BUILD_PLUS_ARTIFACT_CONTRACT`

## Entry condition

R7 installed end-to-end acceptance is `PASS`.

This phase is separate from R7 and must not inherit a publication claim from R7 success.

## Proven trigger

Canonical `main` currently contains a distribution-state conflict:

- `pyproject.toml` declares `lbe-guard-inspector` version `0.2.0`;
- `.github/workflows/publish-python-runtime.yml` asserts and publishes version `2.0.1`;
- that workflow is also tied to the historical branch `release/python-runtime-v2.0.1`;
- the current repository has no root `package.json` or `npm/package.json` distribution owner at canonical `main`.

Therefore release/package readiness is **not yet proven** and publication remains forbidden.

## Audit question

What is the current canonical distribution contract that can be proven from `main`, and which release/package assets are current, stale, missing, or contradictory?

## Allowed actions

- inspect canonical packaging metadata and release workflows;
- inspect current release/readiness documentation and historical records as evidence only;
- build the exact current Python package from canonical `main` without changing source;
- inspect wheel and sdist contents, metadata, entrypoints, bundled Cline worker dependencies, and package isolation;
- run existing package/release tests and installed smoke tests;
- identify stale version, branch, filename, workflow, or documentation assumptions;
- classify each finding as `CURRENT`, `STALE`, `MISSING`, `CONFLICT`, `HARNESS_FAILURE`, or `PROVEN`;
- define a smallest bounded repair gate if and only if a real release-readiness falsifier is proven.

## Forbidden

- changing package version;
- changing runtime/source/package/workflow implementation during this audit;
- creating tags or releases;
- publishing to PyPI or npm;
- activating a historical release branch;
- treating historical 2.0.1/2.0.2 evidence as current without exact-head proof;
- inventing an npm release path when no current canonical npm package owner exists;
- architecture changes.

## Initial known conflict

```text
canonical Python package version: 0.2.0
publish-python-runtime workflow expected version: 2.0.1
workflow branch trigger: release/python-runtime-v2.0.1
classification: DOCUMENT/WORKFLOW VS CURRENT PACKAGE CONFLICT
```

This conflict is an audit trigger, not authorization to choose a new public version.

## Validation ladder

```text
canonical main / clean tracked state
-> current package metadata inventory
-> current release workflow inventory
-> current release-document inventory
-> exact-head wheel + sdist build
-> artifact metadata/content inspection
-> isolated install + CLI/worker smoke
-> existing packaging/release tests
-> current-vs-stale classification
-> readiness verdict
```

## Advancement rule

- If the current distribution contract is internally consistent and all required artifact/install evidence passes, close this audit `PASS` and activate the next documented release-readiness slice.
- If a real conflict requires source/workflow/package changes, close this audit with the exact falsifier and activate a separate bounded repair implementation gate.
- Publication remains locked in either case until the full release/package readiness acceptance phase passes.
