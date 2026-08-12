# Agent End-to-End npm Implementation Plan

Updated: 2026-08-12
Status: **Executable post-V1 implementation plan**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Canonical architecture reference: `docs/POST_V1_NPM_DISTRIBUTION_AND_LOCAL_AGENT_MIGRATION_PLAN.md`
Accepted runtime baseline: C5/R7 V1 READY
Package-readiness baseline: `fce2566a784ac9029e10915823a9ad4510aae3b8`

This document is the implementation contract for local coding agents.

The agent should execute this track end to end without reopening settled architecture decisions or repeatedly asking for routine implementation choices.

---

# 1. Objective

Implement and prove the public-facing npm distribution path:

```text
npm / npx
   -> @letterblack/lbe
   -> thin installer / launcher
   -> one managed Python LBE runtime
   -> existing Python `lbe` CLI
   -> existing persistent LBE runtime
```

The npm package is a distribution/bootstrap layer only.

It must not become another LBE runtime.

---

# 2. Non-negotiable ownership boundary

Node/npm may own only:

- package installation;
- runtime discovery;
- managed Python environment creation;
- Python LBE artifact installation;
- version compatibility checks;
- command forwarding;
- installer diagnostics;
- upgrade/reinstall/uninstall behavior for installer-owned files.

Python LBE remains sole owner of:

- provider adapters;
- provider/model selection;
- persistent sessions/tasks;
- workspace identity;
- modes;
- permissions;
- governance;
- governed tools;
- evidence;
- validation;
- completion;
- resume/rehydration;
- runtime state.

Do not duplicate any Python LBE runtime semantics in Node.

---

# 3. Agent operating rules

Before changing code:

1. read this document;
2. read `docs/POST_V1_NPM_DISTRIBUTION_AND_LOCAL_AGENT_MIGRATION_PLAN.md`;
3. read `docs/IMPLEMENTATION_PLAN.md`;
4. read `docs/acceptance/C5_R7_ACCEPTANCE_RECORD.md`;
5. read `docs/acceptance/POST_V1_RELEASE_PACKAGE_READINESS.md`;
6. verify current branch, HEAD, diff, and existing npm-related files;
7. run the smallest relevant existing tests before editing.

General rules:

- extend existing authoritative owners;
- do not create parallel runtime authorities;
- do not use repo-relative assumptions in consumer code;
- do not persist secrets;
- do not destroy user state during install/uninstall;
- do not publish publicly unless explicitly authorized;
- when a proof fails, classify the failure before patching;
- fix the earliest proven authoritative owner;
- add regression coverage for every real defect found;
- continue independent work when one optional external proof is blocked.

Stop only for genuine external blockers such as public publish authorization, unresolved license choice, unavailable required external credentials, or unavailable required external service access.

---

# 4. Phase A0 — Baseline and scope lock

## Objective

Establish the exact accepted source state and confirm no npm distribution implementation already owns this responsibility.

## Required actions

- verify Git branch and HEAD;
- inspect current diff against `origin/main`;
- verify C5/R7 V1 remains READY;
- verify Python package-readiness remains READY;
- search for existing npm/package/bin/bootstrap logic;
- record current Python package name/version and supported Python evidence;
- identify current build command for wheel/sdist.

## Exit gate

Record:

```text
branch
HEAD
baseline package version
existing npm implementation: yes/no
supported Python evidence
known external blockers
```

No implementation begins until this is established.

---

# 5. Phase A1 — npm package skeleton

## Objective

Create the smallest valid `@letterblack/lbe` package.

## Required implementation

Use repository conventions if they already exist. Otherwise create a dedicated npm distribution area, for example:

```text
npm/
  package.json
  bin/
    lbe.js
  lib/
    paths.js
    python-discovery.js
    runtime-discovery.js
    runtime-install.js
    launcher.js
    diagnostics.js
  test/
```

Required package behavior:

- package name: `@letterblack/lbe`;
- expose executable: `lbe`;
- package must be packable with `npm pack`;
- launcher must fail cleanly before runtime installation exists;
- no Python runtime logic copied into JavaScript;
- no provider/session/policy/tool/evidence semantics in Node;
- no credentials in package source or fixtures.

## Required tests

At minimum:

- package metadata validation;
- executable mapping validation;
- clean missing-runtime error;
- no forbidden runtime-authority modules/classes introduced.

## Exit gate

```text
npm install
npm test
npm pack
```

all succeed for the wrapper skeleton.

---

# 6. Phase A2 — Deterministic platform and Python discovery

## Objective

Determine whether the machine can host the proven Python LBE runtime.

## Required states

The wrapper must distinguish at least:

```text
PYTHON_NOT_FOUND
PYTHON_UNSUPPORTED
PYTHON_SUPPORTED
LBE_RUNTIME_NOT_INSTALLED
LBE_RUNTIME_COMPATIBLE
LBE_RUNTIME_INCOMPATIBLE
LBE_RUNTIME_BROKEN
```

## Requirements

- use actual project-supported Python evidence;
- do not claim unverified runtime support;
- do not depend on active project virtualenv;
- do not modify PATH globally merely for discovery;
- report detected executable/version/path as installer evidence;
- keep platform-specific logic isolated.

## Required tests

Mock or fixture each discovery state.

## Exit gate

All discovery states are deterministic and independently testable.

---

# 7. Phase A3 — LBE-owned managed Python runtime

## Objective

Create a user-scoped isolated environment owned by LBE distribution, not by arbitrary user projects.

## Requirements

Managed locations must separate:

```text
installer/runtime code
user configuration
persistent runtime state
```

Conceptual layout:

```text
<LBE_HOME>/runtime/<version>/
<LBE_HOME>/config/
<LBE_HOME>/state/
```

Exact OS-specific locations may follow existing product conventions, but ownership must remain explicit.

The installer must:

- create the isolated Python environment;
- install the approved Python LBE artifact;
- verify installed package version;
- verify required package data such as `memory_schema.sql`;
- verify the installed `lbe` executable exists;
- leave user config/state outside the managed code environment;
- avoid deleting persistent state during reinstall.

Initial artifact source:

- use the locally built proven wheel;
- do not invent a remote artifact host yet;
- do not require PyPI for initial proof.

## Required tests

- clean install;
- repeated install/idempotent outcome;
- corrupt managed runtime detection;
- incompatible installed runtime detection;
- state directory survives reinstall.

## Exit gate

From a clean consumer-style directory, the wrapper creates a managed environment and proves the installed Python LBE package is usable.

---

# 8. Phase A4 — Transparent command forwarding

## Objective

Make the npm-installed `lbe` command execute the existing Python CLI without semantic duplication.

Required path:

```text
user command
  -> npm `lbe`
  -> launcher
  -> managed Python `lbe`
  -> existing Python runtime
```

## Requirements

Forward:

- all arguments;
- stdout;
- stderr;
- exit code;
- environment where appropriate;
- cancellation/interrupt behavior where supported.

Node must not reinterpret runtime commands.

## Minimum installed command proof

```text
lbe --help
lbe provider list
lbe session create
lbe session status
```

Then prove additional accepted runtime commands through the same npm path where supported.

## Exit gate

The same Python CLI behavior is observable through npm launcher and direct managed-Python invocation.

---

# 9. Phase A5 — npm tarball consumer simulation

## Objective

Test the product exactly as a public npm user would receive it without publishing.

## Required workflow

1. build Python wheel from the accepted source revision;
2. run npm package tests;
3. run `npm pack`;
4. inspect npm tarball contents;
5. create a completely unrelated consumer root;
6. install only the generated `.tgz`;
7. do not execute from the source repository;
8. bootstrap the managed Python runtime through the installed npm package;
9. run installed CLI checks;
10. use external config/state paths;
11. exercise a controlled workspace.

Recommended root:

```text
C:\LBE-Consumer-Test
```

## Tarball audit

Reject package if it includes:

- API keys/tokens/secrets;
- runtime SQLite/state;
- machine-specific config;
- provider credential files;
- proof-workspace artifacts;
- unrelated build output;
- source-only temporary files.

## Consumer proof

At minimum:

```text
lbe --help
lbe provider list
lbe provider check
lbe session create
lbe session status
lbe audit
lbe investigate
lbe code
lbe session checkpoint
lbe session continue
lbe session validate
```

Use only actions supported by the accepted runtime and configured authority.

## Exit gate

No source checkout, editable install, or repo-relative path is required for normal consumer use.

---

# 10. Phase A6 — Persistence and state-boundary proof

## Objective

Prove installer lifecycle cannot accidentally own or destroy LBE runtime state.

## Required proof

```text
install npm wrapper
-> bootstrap Python runtime
-> create persistent session/state
-> remove/reinstall wrapper
-> rediscover/recreate managed runtime as required
-> prior persistent state still exists
-> session remains readable when schema/version compatibility permits
```

Also prove:

- npm cache removal does not define LBE state lifetime;
- Python runtime replacement does not delete provider config;
- configuration remains user-owned/external.

## Exit gate

Installer code lifetime and persistent runtime state lifetime are demonstrably independent.

---

# 11. Phase A7 — Upgrade proof

## Objective

Prove controlled upgrade behavior before publication.

## Required workflow

Create two locally versioned wrapper/runtime artifacts:

```text
install version A
-> create config/state/session
-> upgrade to version B
-> verify runtime version B
-> verify external config preserved
-> verify state preserved
-> verify CLI works
-> verify incompatible state fails explicitly rather than being silently destroyed
```

## Requirements

- no automatic destructive migration;
- record version metadata;
- upgrade failure must leave enough evidence for diagnosis;
- rollback strategy may be documented even if not automated in V1 npm distribution.

## Exit gate

Upgrade/reinstall behavior is deterministic and documented.

---

# 12. Phase A8 — Real-workspace dogfood

## Objective

Use the npm-installed product against representative real local workspaces to expose source-independent defects.

## Required classification for every finding

```text
npm installer defect
managed-runtime defect
Python packaging defect
Python runtime defect
provider/model limitation
workspace-specific issue
performance/hardening issue
```

Do not patch before classification.

## Required focus

Look for:

- Windows path problems;
- spaces/unicode paths;
- large workspace behavior;
- repo-relative assumptions;
- missing package files;
- config ownership mistakes;
- provider setup friction;
- state persistence problems;
- argument forwarding problems;
- CLI UX failures;
- upgrade/reinstall problems.

B2 evidence may be collected here, but B2 remains a separate acceptance track unless explicitly started.

## Exit gate

Remaining issues are hardening/performance/provider-quality issues rather than basic distribution/runtime failures.

---

# 13. Phase A9 — Final validation and readiness record

## Objective

Produce exact evidence for npm distribution readiness.

## Required validation ladder

Run, in order where applicable:

```text
source/static checks
-> focused npm tests
-> Python focused package tests
-> npm pack/content audit
-> clean consumer tarball install
-> managed Python install
-> installed CLI smoke
-> persistent session smoke
-> controlled workspace proof
-> reinstall proof
-> upgrade proof
-> full Python repository suite
-> git diff --check origin/main...HEAD
```

## Required final document

Create/update:

```text
docs/acceptance/POST_V1_NPM_CONSUMER_DISTRIBUTION_READINESS.md
```

Record:

- exact branch/HEAD;
- npm package version;
- Python runtime package version;
- supported/tested Node/npm versions;
- supported/tested Python versions;
- npm tarball filename/hash/content count;
- Python wheel filename/hash;
- consumer install root used;
- installed CLI receipts;
- state persistence receipts;
- upgrade/reinstall receipts;
- focused test results;
- full-suite results;
- diff-check result;
- unresolved blockers;
- publication readiness verdict.

## Readiness predicate

```text
npm tarball builds
AND clean tarball install works
AND managed Python runtime installs
AND npm `lbe` forwards to existing Python CLI
AND config/secrets remain external
AND persistent state survives installer lifecycle
AND upgrade/reinstall are safe
AND controlled workspace use succeeds
AND focused tests pass
AND full suite passes
AND package audits pass
AND diff check passes
```

If any required predicate is false, status is NOT READY.

---

# 14. Publication boundary

Do not publish automatically.

After A0-A9 pass, stop with status:

```text
NPM CONSUMER DISTRIBUTION: READY FOR EXPLICIT PUBLICATION AUTHORIZATION
```

Public publication is a separate user-authorized operation.

Before public publish, verify:

- npm account/scope access;
- package name availability/ownership;
- npm authentication/2FA/token readiness;
- package metadata;
- README/install instructions;
- license decision;
- final tarball audit;
- exact version/tag decision.

Only after explicit user authorization may an agent execute a public release command such as:

```text
npm publish --access public
```

---

# 15. Forbidden implementation shortcuts

Do not:

- rewrite LBE in Node;
- create Node session state;
- create Node provider routing;
- create Node permission/governance decisions;
- create Node governed tool execution;
- create Node completion logic;
- bundle provider credentials;
- couple state deletion to npm uninstall;
- install into arbitrary active project environments by default;
- rely on the LBE source checkout at runtime;
- mark readiness from unit tests alone;
- publish because local tests passed without explicit release authorization.

---

# 16. Agent completion report format

When the track is finished, report only the evidence needed to continue:

```text
STATUS: READY | NOT READY | BLOCKED
BRANCH:
HEAD:
NPM PACKAGE:
PYTHON RUNTIME PACKAGE:
FILES CHANGED:
LOCAL TARBALL:
CONSUMER INSTALL:
CLI SMOKE:
STATE PERSISTENCE:
UPGRADE/REINSTALL:
CONTROLLED WORKSPACE PROOF:
FOCUSED TESTS:
FULL SUITE:
PACKAGE AUDIT:
DIFF CHECK:
BLOCKERS:
PUBLICATION AUTHORIZATION REQUIRED: YES
```

Do not reopen C5/R7 or package-readiness architecture unless new evidence proves a regression.
