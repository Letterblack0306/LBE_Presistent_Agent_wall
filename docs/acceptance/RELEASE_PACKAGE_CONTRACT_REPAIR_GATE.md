# Release Package Contract Repair Gate

Status: **OPEN — IMPLEMENTATION ALLOWED — PUBLISH LOCKED — ARCHITECTURE CHANGES FORBIDDEN**

phase: `RELEASE_PACKAGE_CONTRACT_REPAIR`

slice: `ALIGN_PUBLISH_WORKFLOW_WITH_CANONICAL_PACKAGE_METADATA`

required_evidence_level: `WORKFLOW_CONTRACT_PLUS_LOCAL_PACKAGE_PROOF`

## Trigger

The release-readiness audit proved a current distribution-contract conflict:

- canonical `pyproject.toml` declares `lbe-guard-inspector` version `0.2.0`;
- `.github/workflows/publish-python-runtime.yml` hard-codes `2.0.1` in version validation, artifact names, installed-version validation, and its historical push branch trigger;
- current-head packaging tests pass (`2 passed`) and build/install the current wheel successfully;
- no package/build/runtime files changed between the proven R7 Observable 13 installed-runtime package proof and the current release audit state.

The failed audit command after those tests is classified `HARNESS_TIMEOUT_AFTER_DECISIVE_TEST_PASS`; it is not a package failure.

## Authorized repair

Only align the existing Python publish workflow with the canonical package metadata owner:

1. retain `pyproject.toml` as the version authority;
2. derive the workflow version from `pyproject.toml` instead of embedding a historical version;
3. verify wheel/sdist names and installed metadata using the derived version;
4. remove the historical `release/python-runtime-v2.0.1` automatic push trigger;
5. retain explicit `workflow_dispatch` as the only publish trigger;
6. preserve Node 24 setup required by the locked Cline worker build;
7. preserve the existing PyPI trusted-publishing action and environment.

## Forbidden

- changing `pyproject.toml` version;
- selecting or inventing a new public version;
- publishing during this repair;
- creating a tag or release;
- adding an npm publication path;
- changing runtime, provider, tool, authorization, memory, or completion behavior;
- adding a second publication workflow;
- architecture changes.

## Repair hypothesis

If the existing publish workflow derives all version-sensitive checks from canonical `pyproject.toml` metadata and is manual-only, the stale 2.0.1/release-branch conflict is removed without choosing a new version or publishing anything.

## Falsifiers

- any literal `2.0.1` remains as the Python artifact/version authority in the workflow;
- the historical release branch remains an automatic publication trigger;
- workflow artifact validation can disagree with `pyproject.toml`;
- the repair changes package/runtime source or package version;
- publication occurs during repair validation.

## Validation ladder

`GitHub diff inspection`
→ `workflow YAML/static contract inspection`
→ `canonical pyproject version extraction`
→ `artifact filename derivation proof`
→ `existing package tests already PASS`
→ `tracked source/package diff remains limited to workflow/governance`
→ `repair checkpoint`

Publication remains locked after this repair. A separate release-readiness acceptance decision is required before any publish execution.
