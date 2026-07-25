# Authoritative Patch Specification — Gatekeeper Proposal Service

## Status

Specification only. Do not implement this patch until the project-scoped guard retrieval branch has completed and its implementation commit has been reviewed.

## Repository

`Letterblack0306/LBE_Presistent_Agent_wall`

## Specification branch

`agent/gatekeeper-proposal-service-spec`

## Current specification base

`f5970b225cfb06680f7ee15a0e7d6c40843c7b81`

Before implementation, rebase or recreate the implementation branch from the accepted project-scoped retrieval commit. Do not implement from this old base if the retrieval branch has advanced.

## Objective

Implement the first governed, read-only rule-proposal service.

This patch must:

- inspect the selected target workspace;
- search registered workspace rules and deterministic guards for equivalence;
- detect direct contradictions;
- generate a complete workspace-specific rule proposal;
- produce an exact profile diff;
- require approval metadata;
- perform no profile, registry, workspace, index, or memory mutation.

This patch must not implement rule application.

## Non-goals

Do not implement:

- profile installation;
- approval state transitions;
- rule persistence;
- rollback execution;
- memory promotion;
- global guard promotion;
- autonomous repair;
- reasoning-model integration;
- repository cleanup or hygiene work unrelated to this service.

## Allowed files

Implementation may change only:

```text
lbe_guard_inspector/rule_gatekeeper.py
lbe_guard_inspector/proposal_service.py
lbe_guard_inspector/server.py
lbe_guard_inspector/contracts.py
schemas/rule_proposal.schema.json
schemas/rule_proposal_result.schema.json
rules/profiles.py
tests/test_rule_gatekeeper.py
tests/test_proposal_service.py
tests/test_server.py
acceptance/gatekeeper_acceptance_plan.json
tools/run_gatekeeper_acceptance.py
VALIDATION_GATEKEEPER.md
```

If one listed file does not exist, it may be created. Do not change any other file without stopping and reporting the blocker.

## 1. Separate gatekeeper outcomes from guard verdicts

The gatekeeper result status must be exactly one of:

```text
ALREADY_COVERED
CONFLICT
PROPOSAL_READY
INSUFFICIENT_EVIDENCE
```

These are not guard verdicts.

Do not use:

```text
PASS
FAIL
NOT_APPLICABLE
```

as gatekeeper proposal statuses.

## 2. Target workspace identity

Every request must include or resolve:

- canonical workspace root;
- stable project workspace ID;
- configured root ID;
- workspace-root fingerprint.

The workspace-root fingerprint must be derived from the normalized canonical project root.

A proposal must bind to both:

```text
workspace_id
workspace_root_fingerprint
```

Do not rely on configured root names such as `dev` as project identity.

## 3. Request contract

Add a typed request accepted by the proposal service:

```json
{
  "problem": "string",
  "workspace_root": "absolute project path",
  "workspace_id": "optional readable prefix",
  "candidate_rule": {
    "rule_id": "workspace-specific rule id",
    "trigger": "string",
    "rationale": "string",
    "scope": ["workspace-relative paths or patterns"],
    "required_action": "string",
    "severity": "info | warning | error | blocking",
    "exceptions": ["explicit structured exceptions"]
  },
  "target_profile_path": ".lbe/policy.json"
}
```

Reject empty problem, missing workspace root, invalid rule ID, absolute scope entries, traversal, and target profile paths outside the canonical workspace root.

## 4. Deterministic proposal identity

Do not use a random UUID.

Derive `proposal_id` from a normalized JSON payload containing:

- canonical workspace-root fingerprint;
- workspace ID;
- proposed rule ID;
- trigger;
- rationale;
- sorted scope;
- required action;
- severity;
- sorted exceptions;
- sorted evidence references;
- target profile path;
- exact normalized diff.

Use SHA-256 and expose:

```text
proposal_id = prop-<64 lowercase hex characters>
```

Identical inputs and evidence must produce the same proposal ID.

## 5. Evidence requirements

A proposal may be `PROPOSAL_READY` only when current target-workspace evidence proves the relevant condition or missing protection.

The service must preserve separate evidence classes:

```text
indexed_reference_evidence
current_workspace_evidence
validation_evidence
```

Reference evidence may inform equivalence checks or proposal rationale. It cannot by itself justify a workspace-specific proposal.

Every proposal-ready result must include non-empty:

```text
evidence_refs
validation_plan
rollback_plan
provenance
```

When current evidence is absent, ambiguous, stale, contradictory, or outside the selected project, return `INSUFFICIENT_EVIDENCE`.

## 6. Equivalent-rule detection

Implement deterministic equivalence checking across:

- active workspace profile rules;
- registered deterministic guards;
- approved workspace rules visible to this repository.

Normalize and compare:

- trigger intent;
- required action;
- scope;
- exceptions;
- severity;
- target workspace applicability.

Exact rule ID equality is sufficient but not required for equivalence.

If an equivalent active rule exists, return:

```text
ALREADY_COVERED
```

The result must include:

- matching rule or guard ID;
- source path or registry source;
- normalized comparison fields;
- evidence references;
- no proposed diff.

## 7. Conflict detection

Return `CONFLICT` when an active rule or profile requirement directly contradicts the candidate rule.

A conflict must identify:

- existing rule ID;
- candidate rule ID;
- conflicting normalized fields;
- existing rule source;
- evidence references;
- explanation;
- no proposed diff.

Do not classify mere difference as conflict. The required actions or protected intent must be mutually incompatible within overlapping scope.

## 8. Proposal contract

Update or extend the rule proposal contract so `PROPOSAL_READY` includes:

```text
proposal_id
workspace_id
workspace_root_fingerprint
target_workspace_root
target_profile_path
rule_id
trigger
rationale
scope
required_action
severity
exceptions
equivalent_rule_checked
equivalent_rule_matches
conflict_checked
conflict_matches
evidence_refs
diff
validation_plan
rollback_plan
provenance
approval_required
created_at
```

Requirements:

- `approval_required` must be constant `true`;
- `diff` must be valid JSON Patch or a complete valid JSON merge diff, not prose;
- `target_profile_path` must be exact and workspace-relative;
- `exceptions` must be structured and deterministic;
- `provenance` must record source evidence and proposal generator version;
- `created_at` is informational and must not affect proposal ID.

## 9. Exact profile diff

The service must inspect the current target profile if it exists.

If absent, proposal generation may target creation of:

```text
.lbe/policy.json
```

The diff must:

- be syntactically valid JSON;
- contain no trailing commas;
- add exactly one workspace-specific rule;
- preserve unrelated existing profile content;
- include workspace identity binding;
- include rule provenance;
- include `approval_required: true` as metadata only;
- not apply the change.

Do not return placeholders such as:

```text
C:/.../.lbe/policy.json
```

## 10. Namespace-package evidence

Do not accept namespace-package exceptions from directory naming alone.

A namespace-package exception must be supported by current packaging configuration such as:

- `pyproject.toml`;
- `setup.cfg`;
- `setup.py`;
- package discovery configuration;
- another deterministic package declaration.

Without packaging evidence, treat the exception as unverified and return `INSUFFICIENT_EVIDENCE` where it affects the proposal.

## 11. Read-only enforcement

Proposal inspection and generation must not modify:

- target workspace files;
- target profile;
- rule registry;
- SQLite index;
- state files;
- memory files;
- Git working tree outside explicitly created validation reports.

Tests must snapshot paths and hashes before and after service execution.

The HTTP endpoint must not expose apply behavior.

## 12. HTTP endpoint

Add:

```text
POST /rule-proposal
```

The endpoint must:

- validate the request;
- call the read-only proposal service;
- return the gatekeeper result and optional proposal;
- return HTTP 400 for contract or boundary failures;
- return no mutation capability;
- preserve no server-side proposal state in this patch.

Do not add:

```text
/rule-apply
/rule-approve
/rule-install
/rule-rollback
```

## 13. Path safety

Required protections:

- reject absolute scope paths;
- reject `..` traversal;
- reject target profile paths outside the canonical workspace root;
- reject symlink escape;
- reject ambiguous duplicate profile files;
- use canonical path comparison;
- never follow a profile symlink outside the project.

## 14. Stale evidence behavior

Before emitting `PROPOSAL_READY`, revalidate every bound current-workspace evidence hash.

If a file changed between evidence collection and proposal synthesis:

```text
INSUFFICIENT_EVIDENCE
```

Do not regenerate silently from stale assumptions during the same call.

This patch does not implement apply-time stale-file checking because application is out of scope. It only guarantees proposal-time revalidation.

## 15. Required tests

Add deterministic tests for:

1. equivalent rule returns `ALREADY_COVERED`;
2. semantically equivalent rule with a different ID is detected;
3. conflicting rule returns `CONFLICT`;
4. unrelated rule is not treated as a conflict;
5. complete proposal returns `PROPOSAL_READY`;
6. missing current evidence returns `INSUFFICIENT_EVIDENCE`;
7. indexed-reference-only evidence cannot produce `PROPOSAL_READY`;
8. deterministic proposal ID;
9. `created_at` does not affect proposal ID;
10. complete governance fields;
11. valid exact JSON diff;
12. no trailing comma in generated JSON;
13. exact target profile path;
14. absolute scope rejection;
15. traversal rejection;
16. profile symlink escape rejection;
17. stale bound hash returns `INSUFFICIENT_EVIDENCE`;
18. valid namespace-package configuration exception;
19. directory naming alone does not prove a namespace-package exception;
20. no workspace mutation;
21. no profile mutation;
22. no registry mutation;
23. no index mutation;
24. repeated proposal idempotency;
25. HTTP endpoint contract;
26. endpoint exposes no apply route;
27. gatekeeper statuses remain separate from guard verdicts.

## 16. Acceptance runner

Create a committed deterministic acceptance plan and runner for the gatekeeper.

The runner must test:

- equivalent rule;
- conflicting rule;
- proposal generation;
- insufficient evidence;
- proposal ID idempotency;
- path traversal rejection;
- symlink escape rejection;
- stale hash rejection;
- namespace-package proof requirement;
- zero target mutation;
- HTTP endpoint response;
- absence of apply routes.

The acceptance runner must read and enforce every declared global invariant in its plan. Do not leave invariants as unused documentation.

Generated acceptance output must be written under ignored state output and must not be staged.

## 17. Validation commands

Run:

```powershell
python -m pytest -q
python tools\run_gatekeeper_acceptance.py
git diff --check
git status --short
```

Validation must report:

- complete pytest result;
- acceptance exit code;
- case-by-case status;
- global invariant results;
- mutation proof;
- generated report path;
- no state output staged.

## 18. Implementation branch procedure

After the project-scoped retrieval implementation commit is accepted:

1. create a new implementation branch from that accepted commit;
2. copy this specification unchanged into that branch;
3. verify no implementation files are already modified;
4. implement only this specification;
5. use path-explicit staging;
6. make one implementation commit;
7. push the branch;
8. stop without merging or opening a pull request.

Recommended implementation branch:

```text
agent/gatekeeper-proposal-service
```

Commit message:

```text
feat: add governed read-only rule proposals
```

## 19. Final report

The implementing agent must report:

- accepted starting commit;
- implementation commit;
- exact changed files;
- gatekeeper status contract;
- workspace identity binding;
- proposal ID derivation;
- equivalence strategy;
- conflict strategy;
- exact diff format;
- namespace-package evidence strategy;
- stale-hash behavior;
- HTTP endpoint behavior;
- pytest result;
- gatekeeper acceptance result;
- mutation proof;
- push result;
- confirmation that no rule was applied;
- confirmation that no proposal was persisted;
- remaining apply-profile lifecycle gaps.

After push, stop all repository modifications.
