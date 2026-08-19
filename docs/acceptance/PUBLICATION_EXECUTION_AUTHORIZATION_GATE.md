# Publication Execution Authorization Gate

Status: **OPEN — EXPLICIT USER AUTHORIZATION REQUIRED — PUBLISH LOCKED**

phase: `PUBLICATION_EXECUTION_AUTHORIZATION`

slice: `AUTHORIZE_PYPI_0_2_0_WORKFLOW_DISPATCH`

required_evidence_level: `EXPLICIT_USER_AUTHORIZATION_PLUS_LIVE_WORKFLOW_EXECUTION`

## Proven prerequisite

`PUBLICATION_PRECHECK=PASS`.

## Exact publication target

- repository: `Letterblack0306/LBE_Presistent_Agent_wall`
- canonical ref: `main`
- distribution: `lbe-guard-inspector`
- version: `0.2.0`
- workflow: `.github/workflows/publish-python-runtime.yml`
- GitHub environment: `pypi`
- authentication: OIDC trusted publishing

## Already proven

- release/package readiness: PASS;
- repaired distribution contract: PASS;
- PyPI namespace exists;
- PyPI versions `2.0.1` and `2.0.2` exist;
- version `0.2.0` has no collision;
- GitHub `pypi` environment exists;
- workflow OIDC contract is present;
- workflow is manual-only;
- canonical tracked source is clean.

## Remaining uncertainty

The PyPI-side trusted-publisher binding cannot be conclusively tested without entering the actual publish flow. Historical publish runs provide no successful binding proof.

## Authorization boundary

No workflow dispatch is permitted merely because technical prechecks passed.

The user must explicitly authorize publication of **`lbe-guard-inspector==0.2.0` to PyPI from canonical `main`**.

Only after that explicit authorization may `publish_allowed_now` be set true for the single bounded execution.

## Execution requirements after authorization

1. re-confirm `main == origin/main`;
2. re-confirm canonical version is exactly `0.2.0`;
3. re-query PyPI and prove `0.2.0` is still absent immediately before dispatch;
4. dispatch only `.github/workflows/publish-python-runtime.yml` on `main`;
5. observe the exact workflow run to completion;
6. if any step fails, stop and classify the failure; do not retry blindly;
7. if publish succeeds, query PyPI and prove `0.2.0` exists;
8. record workflow run ID, commit SHA, published artifact state, and final gate closure.

## Forbidden

- implicit publication authorization;
- version changes;
- publication of `2.0.1` or `2.0.2`;
- alternate branches/worktrees;
- API-token fallback without a separate authorized security decision;
- repeated publish attempts after a failure without diagnosis;
- tags or GitHub releases unless separately authorized.
