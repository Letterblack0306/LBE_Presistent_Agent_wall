# GitHub-First Local Verification Execution Workflow

Status: **AUTHORITATIVE EXECUTION WORKFLOW — ACTIVE**
Updated: 2026-08-13

This document defines the default implementation and verification workflow for the professional LBE runtime roadmap.

It complements, and does not replace:

- `docs/design/PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_CANONICAL_IMPLEMENTATION_PLAN.md`
- the active P0/P1 gates and later phase acceptance criteria.

## 1. Core operating rule

GitHub is the primary implementation, inspection, patch, and review surface.

The local ChatGPT terminal-loop / command relay is a verification and execution bridge. It is not the preferred place to perform small iterative debugging or source editing when GitHub inspection and patching can resolve the issue more directly.

Default flow:

```text
Canonical GitHub architecture
        ↓
GitHub-grounded implementation slice
        ↓
commit to the active implementation branch
        ↓
local agent fetches/pulls exact commit
        ↓
local execution / tests / runtime verification
        ↓
structured command/runtime evidence returned
        ↓
GitHub diff + evidence verification
        ↓
PASS -> continue to next bounded slice
FAIL -> patch the proven defect directly in GitHub when practical
        ↓
local pull + focused re-validation
```

The workflow is intended to reduce unnecessary conversational back-and-forth and prevent development from depending on one local agent's context or planning quality.

## 2. What GitHub owns in this workflow

Use GitHub directly for:

- reading authoritative architecture and current source;
- determining current implementation ownership;
- creating or updating bounded source changes;
- adding or correcting tests and fixtures;
- fixing small deterministic source defects;
- reviewing diffs and commits;
- maintaining canonical implementation plans and acceptance gates;
- comparing implementation state against architecture;
- recording accepted phase state.

For small, source-localized defects, prefer:

```text
inspect GitHub source
-> identify exact defect
-> patch GitHub
-> ask local runtime to pull and verify
```

rather than:

```text
send exploratory command to local agent
-> ask it to diagnose
-> ask it to edit
-> wait for another summary
-> repeat
```

## 3. What the local terminal-loop is for

Use the local execution bridge for operations that require the real local machine/worktree/runtime, including:

- verifying repository/worktree identity;
- fetching/pulling an exact GitHub commit;
- running unit/integration/regression tests;
- running package/build/install checks;
- executing the real CLI/runtime;
- validating provider/runtime behavior that cannot be proven from static source;
- checking local filesystem/workspace conditions;
- reproducing environment-specific behavior;
- collecting stdout/stderr, exit codes, runtime logs, hashes, and other execution evidence;
- confirming that a GitHub patch works after local pull.

The local bridge should return evidence, not become a competing source of architecture truth.

## 4. Do not use the local bridge as the default debugger

Do not route every small issue through the local agent.

Examples that should normally be solved directly through GitHub first:

- typo or wrong constant;
- incorrect branch in deterministic control flow visible in source;
- stale provider event mapping in documentation;
- missing test assertion that can be reasoned from current source contract;
- small schema/dataclass mismatch visible in current code;
- documentation/routing correction;
- localized import or ownership error that can be verified from repository source.

Use local execution only when verification is needed after the patch or when the defect depends on runtime/environment state.

## 5. Local-agent role

The local agent is an executor and verifier, not the canonical planner.

It must:

1. establish the exact repository/worktree before acting;
2. fetch/pull the requested GitHub commit without destroying unrelated local work;
3. execute the bounded validation packet;
4. return exact commands, exit codes, relevant stdout/stderr, changed local state if any, and test/runtime evidence;
5. stop on a proven blocker instead of inventing architecture;
6. not self-declare a roadmap phase accepted unless the canonical acceptance gate explicitly delegates that authority.

The local agent may identify a valid issue the canonical plan missed. Such a finding is comparison input and must be verified against live source/runtime evidence before the canonical GitHub plan is amended.

## 6. Assistant role

The GitHub-side architecture/implementation controller should:

1. inspect current GitHub source before each implementation slice;
2. make the smallest change consistent with the canonical architecture;
3. commit a bounded, reviewable slice;
4. give the local agent exact pull and validation instructions;
5. evaluate returned runtime evidence against the acceptance criteria;
6. patch deterministic failures directly in GitHub where practical;
7. repeat local verification only for the failed/changed boundary;
8. advance automatically to the next roadmap slice after acceptance passes.

Do not restart architecture planning after every implementation step.

## 7. Failure routing

Use this decision rule:

```text
Failure visible and provable from GitHub source?
    YES -> patch directly in GitHub -> local focused verification
    NO
      ↓
Failure depends on local runtime/environment?
    YES -> use terminal loop to collect focused evidence
    NO
      ↓
Architecture/contract conflict?
    YES -> reconcile canonical GitHub docs first
    NO -> inspect current source/evidence before making assumptions
```

The terminal loop must not be used for broad exploratory debugging when a direct repository inspection is more efficient.

## 8. Phase progression

For P2 onward, each phase should be delivered as bounded executable packets:

```text
phase contract already accepted
        ↓
GitHub implementation packet
        ↓
local verification packet
        ↓
acceptance result
        ↓
next implementation packet
```

Normal implementation decisions inside an already accepted phase do not require another planning conversation.

Stop progression only for:

```text
WRONG_WORKSPACE
PROVEN_ARCHITECTURE_CONFLICT
INSUFFICIENT_RUNTIME_EVIDENCE
EXTERNAL_DEPENDENCY_REQUIRED
ACCEPTANCE_TEST_FAILURE
```

A failed acceptance check causes a focused correction, not a restart of the entire roadmap.

## 9. Evidence rule

GitHub source proves repository implementation state.

Local runtime evidence proves execution behavior.

Neither a final agent narrative nor a documentation statement by itself proves runtime correctness.

Required completion evidence should prefer:

```text
exact GitHub commit
+ changed files/diff
+ exact local command
+ exit code
+ relevant stdout/stderr/runtime receipt
+ focused acceptance result
```

## Final rule

> **Build and patch in GitHub first. Pull locally to execute and verify. Use the local command loop for real runtime evidence, not as the default place to debug small source defects. Keep architecture and implementation truth durable in the repository so progress does not depend on one agent's context.**
