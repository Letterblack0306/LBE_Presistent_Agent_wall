# Post-V1 npm Distribution and Local-Agent Migration Plan

Updated: 2026-08-12
Status: **Canonical post-V1 distribution direction**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Accepted runtime baseline: C5/R7 V1 READY
Package-readiness baseline: `fce2566a784ac9029e10915823a9ad4510aae3b8`

This document defines the next product/distribution direction after C5/R7 V1 and package readiness.

The public install surface will move toward:

```text
npm / npx
   -> @letterblack/lbe
   -> thin installer / launcher
   -> installed Python LBE package
   -> one persistent LBE runtime
```

The npm layer is a distribution/bootstrap surface only. It must not become a second LBE runtime, second policy engine, second session owner, second provider controller, or second governance implementation.

---

## 1. Why move to npm as the public installation surface

The Python LBE runtime is already architecture-complete for V1 and package-ready for local installation. The next usability problem is distribution, not runtime ownership.

Using the existing Letterblack npm scope provides a simpler public installation path:

```powershell
npm install -g @letterblack/lbe
```

or:

```powershell
npx @letterblack/lbe
```

This direction is preferred because:

- `@letterblack` is already an established package/distribution identity;
- npm gives users a familiar cross-project installation surface;
- the npm package can be public and independently versioned;
- local consumer testing can use `npm pack` before public publication;
- npm can bootstrap the already-proven Python package without forcing users to understand the source repository layout;
- the npm surface can later provide one stable entry point for install, upgrade, doctor, and launch behavior;
- this avoids waiting on unrelated GitHub subscription/Actions state for local consumer testing;
- it allows the product to be tested exactly as a normal external user would install it.

The reason for choosing npm is **distribution convenience**, not a change of runtime language or architecture.

---

## 2. Why LBE must remain one runtime

The canonical invariant is:

```text
Provider reasons.
LBE runtime orchestrates.
LBE owns workspace authority.
LBE owns session/task persistence.
LBE governance authorizes.
LBE governed tools execute.
LBE evidence and validation prove completion.
```

Therefore the npm layer must never duplicate these responsibilities.

Correct architecture:

```text
@letterblack/lbe
    |
    +-- install/bootstrap
    +-- version resolution
    +-- local runtime discovery
    +-- launch existing `lbe` executable
    +-- optional installer diagnostics
    |
    v
Python LBE runtime
    |
    +-- provider adapters
    +-- persistent sessions
    +-- modes
    +-- permissions
    +-- governance
    +-- tools
    +-- evidence
    +-- validation
    +-- completion
```

Incorrect architecture:

```text
Node/npm LBE runtime
    + session logic
    + provider logic
    + policy logic
    + tool logic

PLUS

Python LBE runtime
    + session logic
    + provider logic
    + policy logic
    + tool logic
```

That would create dual ownership, contradictory state, duplicate bugs, and uncertainty about which layer is authoritative.

### Non-negotiable rule

> `@letterblack/lbe` may install, discover, launch, upgrade, or diagnose the Python LBE runtime. It must not reimplement LBE runtime semantics in JavaScript/Node.

If a feature requires session state, provider reasoning, authorization, governed execution, evidence, validation, or completion, it belongs in the Python LBE runtime unless current architecture explicitly assigns it elsewhere.

---

## 3. Public product shape

Target user experience:

```text
User
  -> installs @letterblack/lbe
  -> installer ensures compatible local runtime exists
  -> user runs `lbe`
  -> user configures provider/model connection
  -> LBE operates on selected workspace
```

The public package does **not** provide AI models or provider accounts.

Provider authentication remains user/provider-owned:

```text
user chooses provider
  -> API key / login / local endpoint / supported auth mechanism
  -> LBE consumes configured connection
```

The npm package must not bundle, extract, proxy, or silently reuse third-party credentials.

---

## 4. Initial npm package scope

Package identity:

```text
@letterblack/lbe
```

Initial responsibilities only:

1. detect supported operating system/runtime prerequisites;
2. detect a supported Python runtime;
3. create or locate an LBE-owned isolated Python environment;
4. install the approved LBE Python artifact into that environment;
5. expose/forward the `lbe` command;
6. support clean reinstallation/upgrade;
7. provide installer-level diagnostics when the runtime cannot launch;
8. preserve all user configuration/state outside the npm package and Python package source;
9. remove only installer-owned artifacts during uninstall unless the user explicitly chooses to remove persistent state.

Explicit exclusions:

- no duplicate session database;
- no Node provider adapter;
- no Node permission resolver;
- no Node workspace mutation layer;
- no Node completion gate;
- no generic shell bypass;
- no embedded provider credential;
- no model bundling;
- no Cline integration in the initial npm slice;
- no B2 benchmarking in the initial npm slice;
- no TUI redesign.

---

## 5. Runtime installation model

The npm package should install/manage Python LBE in an isolated LBE-owned location rather than modifying arbitrary project environments.

Conceptual layout:

```text
user machine
  |
  +-- npm global/cache package
  |     `-- @letterblack/lbe launcher
  |
  +-- LBE managed runtime
  |     +-- python environment
  |     +-- installed lbe_guard_inspector package
  |     `-- runtime version metadata
  |
  +-- LBE user config
  |     +-- provider references/config
  |     +-- runtime config
  |     `-- governance config
  |
  `-- LBE state
        `-- persistent SQLite/session state
```

Installer files, user configuration, and persistent runtime state must remain distinct.

Uninstalling/reinstalling the npm package must not silently destroy persistent session state.

---

## 6. Artifact source during migration

Initial local-development phase:

```text
LBE source repository
  -> build proven wheel
  -> npm wrapper references/install-tests that wheel locally
```

Do not require PyPI publication for the first npm consumer test.

The npm tarball can be tested locally against a local wheel artifact.

Later publication options may include:

- published Python package artifact;
- versioned release artifact downloaded from a trusted release location;
- another deterministic artifact source.

The npm package must verify that the installed Python runtime version matches the wrapper's supported contract.

Do not invent a remote artifact source before the local npm consumer workflow is proven.

---

# 7. End-to-end local-agent migration plan

This section is the execution plan for local coding agents. Agents should follow it without reopening settled architecture decisions.

## Phase N0 — Establish current authority and branch

Before editing:

1. read this document;
2. read `docs/IMPLEMENTATION_PLAN.md`;
3. read `docs/acceptance/C5_R7_ACCEPTANCE_RECORD.md`;
4. read `docs/acceptance/POST_V1_RELEASE_PACKAGE_READINESS.md`;
5. verify current Git branch, HEAD, PR state, and diff;
6. confirm C5/R7 V1 remains READY;
7. confirm Python package readiness remains READY.

Do not modify C5/R7 evidence unless an npm-distribution change exposes a real regression in the accepted runtime.

### Exit condition

Current runtime/package authority is understood and no duplicate distribution implementation already exists.

---

## Phase N1 — Create minimal npm wrapper skeleton

Create the smallest viable `@letterblack/lbe` package.

Required files should be limited to normal npm package/bootstrap concerns, for example:

```text
npm/
  package.json
  bin/
    lbe.js
  lib/
    runtime-discovery.js
    runtime-install.js
    launcher.js
  README.md
```

Exact paths may follow existing repository conventions if one already exists.

Requirements:

- package name `@letterblack/lbe`;
- executable mapping for `lbe`;
- Node code contains installer/launcher logic only;
- no runtime policy/session/provider semantics copied from Python;
- commands fail with actionable installer errors;
- no credentials are logged or persisted.

### Exit condition

`node`/npm can invoke the wrapper and the wrapper can locate or report the absence of a managed Python LBE runtime.

---

## Phase N2 — Python runtime discovery

Implement deterministic runtime discovery.

The wrapper should distinguish:

```text
Python absent
Python present but unsupported
Python supported but LBE runtime absent
LBE runtime installed and compatible
LBE runtime installed but incompatible/broken
```

Do not collapse these into one generic installation failure.

Use evidence from the current supported runtime record. Do not claim support for runtimes that have not been established by project evidence.

### Exit condition

Focused tests prove each discovery state and no source-repository-relative assumption is required.

---

## Phase N3 — Managed local installation

Implement installation into an LBE-owned isolated Python environment.

Requirements:

- never install into a random active project virtualenv by default;
- installation location is deterministic and user-scoped;
- persistent LBE state remains outside the managed runtime environment;
- provider configs remain external;
- install failure returns exact command/stage/error evidence;
- reinstall is idempotent where practical;
- upgrade replaces runtime code without deleting user state.

Initial artifact input may be the locally built V1 wheel.

### Exit condition

From a clean machine-style directory, the wrapper creates the managed environment and installs the known wheel successfully.

---

## Phase N4 — Command forwarding

Expose the existing Python CLI through npm.

Required path:

```text
user -> `lbe ...`
     -> npm launcher
     -> managed Python environment `lbe ...`
     -> existing Python CLI/runtime
```

The wrapper should preserve:

- arguments;
- exit code;
- stdout/stderr behavior;
- cancellation/interrupt behavior where supported.

Do not parse runtime semantics in Node merely to mirror Python commands.

### Exit condition

At minimum these installed commands work through the npm-launched path:

```text
lbe --help
lbe provider list
lbe session create
lbe session status
```

Then validate existing accepted modes through the same installed runtime where practical.

---

## Phase N5 — Local public-user simulation with `npm pack`

Before publication:

1. run `npm pack`;
2. inspect tarball contents;
3. verify no secrets/config/runtime state/source-only artifacts are included;
4. create a completely unrelated consumer directory;
5. install only the `.tgz` package;
6. do not run from the LBE repository directory;
7. let the npm wrapper bootstrap the managed Python runtime;
8. configure provider externally;
9. exercise the product as a normal consumer.

Recommended consumer root:

```text
C:\LBE-Consumer-Test
```

Required consumer checks:

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

Use controlled workspaces and explicit authority policies.

### Exit condition

The product works without source checkout, editable install, repo-relative configuration, or development-only environment assumptions.

---

## Phase N6 — Upgrade/reinstall/uninstall behavior

Build a second local wrapper/runtime version and test:

```text
install v1
-> create config/state/session
-> upgrade wrapper/runtime
-> existing config remains external
-> existing session/state remains readable
-> CLI still works
```

Also test uninstall/reinstall.

Default uninstall must not silently remove persistent user state.

### Exit condition

Upgrade/reinstall behavior is deterministic and documented.

---

## Phase N7 — Real-workspace dogfood

Use the npm-installed consumer version against representative real workspaces.

Purpose:

- find path assumptions;
- find missing package/runtime files;
- find state/config ownership problems;
- find provider configuration friction;
- find CLI usability problems;
- find large-workspace/context issues naturally.

This dogfood can generate evidence for later B2 work, but it must not silently redefine B2 acceptance.

Every issue must be classified before source changes:

```text
installer defect
Python package defect
runtime defect
provider/model limitation
workspace/fixture issue
performance/hardening issue
```

Fix the earliest proven authoritative owner only.

### Exit condition

Representative local consumer use is stable enough that remaining findings are documented hardening work rather than basic installation/runtime breakage.

---

## Phase N8 — Publication readiness

Only after local npm consumer simulation passes:

- reconcile package versioning;
- verify package metadata;
- verify package tarball contents;
- verify public README/install instructions;
- verify npm authentication/2FA/token path;
- confirm no secrets in package/history intended for publication;
- document exact tested Node/npm/Python support;
- record final consumer smoke evidence.

Do not publish automatically merely because these checks pass.

A license decision is a separate legal/product decision, not a technical npm
publication prerequisite. Do not block a public npm publish solely because the
package remains `UNLICENSED` or the repository has no license file.

For direct scoped-public publication, npm must also accept either account 2FA
or a granular access token with bypass-2FA publishing permission. A token that
can authenticate but cannot publish is an external registry credential
limitation, not a package defect.

### Publication boundary

Public publication remains a separate explicit action:

```text
npm publish --access public
```

No agent should execute a public publish unless the user explicitly authorizes that release action.

---

# 8. Validation ladder for every npm slice

Use the smallest validation that matches the claim, then climb as needed:

```text
source/static checks
-> focused Node/npm tests
-> npm pack/content audit
-> local tarball install
-> managed Python runtime install
-> installed CLI smoke
-> persistent session smoke
-> controlled workspace runtime proof
-> upgrade/reinstall proof
-> representative dogfood
```

Do not claim public-consumer readiness from unit tests alone.

---

# 9. Required evidence for completion of the migration track

The npm distribution track is complete only when all of the following are proven from a source-independent consumer location:

```text
@letterblack/lbe tarball installs
-> managed Python runtime is created/discovered
-> existing Python `lbe` CLI launches
-> provider config remains user-owned/external
-> persistent state is created outside package/runtime code
-> existing C5/R7 runtime behavior remains authoritative
-> uninstall/reinstall does not silently destroy state
-> upgrade preserves compatible state/config
-> npm tarball contains no secrets/runtime state/proof artifacts
-> real controlled workspace can be operated through npm-installed path
```

---

# 10. Anti-duplication rules for all future agents

Agents working on npm distribution must obey these rules:

1. **Do not port LBE runtime logic to Node.**
2. **Do not create a second provider abstraction.**
3. **Do not create a second persistent session store.**
4. **Do not create a second policy/permission resolver.**
5. **Do not create a second governed tool registry.**
6. **Do not create a second evidence/completion system.**
7. **Do not persist provider secrets inside npm/package/runtime state.**
8. **Do not couple runtime state lifetime to npm package lifetime.**
9. **Do not treat installer diagnostics as runtime governance.**
10. **Do not redesign accepted C5/R7 behavior to make npm wrapping easier.**

Preference order remains:

```text
reuse existing Python runtime owner
> extend installer/launcher boundary
> fix proven packaging defect
> add new authority only if architecture explicitly requires it
```

---

# 11. Local-agent execution rule

A local coding agent receiving this migration track should execute it end to end without repeatedly asking for routine implementation decisions.

The plan already authorizes normal repository-scoped work required by phases N0-N8:

- inspect current source/Git/docs;
- create the npm wrapper;
- add focused tests;
- build Python artifacts;
- run `npm pack`;
- install local tarballs;
- create disposable local consumer environments;
- run local consumer smoke tests;
- fix proven defects;
- update this document/status records.

The agent should stop only for genuine external boundaries, such as:

- public npm publish authorization;
- missing npm account authentication required for publication;
- unresolved license choice;
- user-owned provider credentials when a live provider test specifically requires them;
- external service outage or unavailable repository access.

When an optional/live-provider test is blocked, continue independent migration phases where possible.

---

# 12. Final direction

The project now has one runtime and two layers of concern:

```text
Distribution layer
  @letterblack/lbe
  -> install / upgrade / launch / diagnose

Runtime layer
  Python LBE
  -> session / provider / governance / tools / evidence / validation / completion
```

This separation is intentional.

The npm migration is successful only if it makes LBE easier to install and use **without creating another LBE**.
