# C5 / R7 Acceptance Record

Updated: 2026-08-12
Status: **ACTIVE ACCEPTANCE RECORD — C5/R7 overall NOT READY**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
Current implementation branch: `feat/c5-governed-coding-execution`
Latest proven Proof A head: `e9874dca1504aeef153de0e5e15cbcb33ee7a50f`

This document is the canonical project-specific record for C5/R7 installed-path acceptance work.

It exists to prevent future agents from repeating already-completed investigation, reintroducing rejected assumptions, or claiming C5/R7 readiness from lower-level evidence.

When this document conflicts with live repository state, current Git state, current installed package behavior, or fresh runtime evidence, live evidence wins and this record must be updated.

---

## 1. Final C5/R7 acceptance target

C5/R7 is not another architecture slice. It is the installed/normal-path proof milestone for the persistent LBE runtime.

The required proof families are:

| Family | Required installed-path proof | Current status |
|---|---|---|
| A. Coding session | governed edit -> trusted evidence -> validation -> persisted completion | **PROVEN** |
| B. Provider switch | change provider/model while preserving workspace authority, policy, permissions, evidence semantics, and lifecycle | **BLOCKED — Provider-B quota** |
| C. Resume after workspace change | checkpoint -> external workspace change -> restart/resume -> stale invalidation/current evidence precedence | **PROVEN** |
| D. Read-only audit | real controlled-workspace audit with zero mutation and deterministic evidence/result | **PROVEN** |
| E. Escalation / denial | installed-path rejected request, provider-bypass resistance, explicit authority change, permitted retry | **PROVEN** |

**C5/R7 overall is NOT READY until A-E each have installed-path receipts.**

---

## 2. Architecture boundary that must not change during acceptance

```text
Provider reasons.
External agent proposes and interacts.
LBE runtime orchestrates.
CLI/API transport requests capabilities.
Guards detect.
Workspace evidence supplies current facts.
LBE governance authorizes.
Validation proves.
Persistent session state belongs to LBE.
User-configured policy decides when another confirmation is required.
```

Additional invariant:

> Agents reason; bridges transport. Governance constrains authority, but must not become a second reasoning engine.

Do not introduce a parallel session controller, permission resolver, completion gate, evidence authority, generic shell, or TUI-owned runtime authority to make acceptance pass.

---

## 3. Baseline already complete before C5 Proof A

The runtime architecture had already progressed through R2-R6F and C0-C4 before this acceptance work.

Relevant merged/implemented milestones include:

- persistent session/task lifecycle;
- runtime -> reasoning wiring;
- external-agent integration;
- checkpoint/resume;
- recovery/retry primitives;
- provider abstraction;
- typed execution modes;
- authorization resolver;
- context assembly;
- governed tool orchestration;
- completion gate;
- CLI/session/provider surfaces;
- persisted completion contracts;
- trusted completion evidence;
- runtime mode-policy composition;
- task completion policy;
- trusted source-change / focused-test / Git-status producers;
- `lbe session validate`;
- `lbe provider check`, `lbe code`, `lbe audit`, `lbe investigate`.

Do not restart these slices merely because C5 acceptance reveals a later wiring or evidence defect.

---

## 4. C5 Proof A chronology and failures

### Attempt 0 — provider readiness

Controlled workspace:

`G:\Developments\lbe-p1-002-proof`

Provider config:

`G:\Developments\lbe-p1-002-proof\provider-local.json`

Installed provider check result:

```text
provider_id: openai-compatible
provider_model: qwen/qwen3-coder-30b
status: READY
```

Conclusion: provider health was not the C5 blocker.

### Attempt 1 — installed coding request timed out with no mutation path

Observed:

- installed `lbe code` exceeded 180 seconds;
- exact `lbe.exe` and Python child were stopped;
- tracked `README.md` remained unchanged;
- no completion evidence/checkpoint was created;
- task remained `running`;
- source trace showed `lbe code` only allowed reasoning inspection and no governed write dispatch existed.

Correct classification:

```text
C5 Proof A blocked by implementation:
- no governed bounded coding mutation path;
- process termination did not produce a terminal cancellation receipt.
```

Important lesson: this was not a reason to add a generic shell. The existing R6E/R6C owners had to be extended.

### Repository/branch check before implementation

Remote branches, PR history, and commits were checked for an existing write implementation.

Result:

- R6E intentionally implemented `workspace.read` only;
- generic shell and writes were explicitly deferred;
- no later branch already contained the missing C5 governed-write path;
- cancellation primitives already existed in recovery code and must be reused rather than replaced.

### PR #53 — governed coding mutation execution

Branch:

`feat/c5-governed-coding-execution`

Purpose:

- add one bounded governed mutation path;
- keep existing R6B/R6C/R6E ownership;
- no generic shell;
- no second controller/permission/completion subsystem.

Implemented tool:

```text
workspace.replace_text
```

Required properties:

- workspace-relative path;
- existing regular UTF-8 file;
- non-symlink target;
- `old_text` occurs exactly once;
- atomic replacement;
- structured receipt containing path, before SHA-256, after SHA-256, replacement count;
- coding-mode `modify` capability only;
- audit/investigation remain non-modifying;
- provider sees the write tool only after resolved coding authority exposes it.

### Packaging failure discovered after source validation

PR head `1f541da...` validated in an isolated worktree:

- focused suite: 90 passed;
- full suite: 625 passed;
- `git diff --check`: passed.

But the wheel omitted:

`lbe_guard_inspector/memory/memory_schema.sql`

Installed `lbe session create` failed with `FileNotFoundError`.

Correct classification: **packaging defect**, not governed-write runtime failure.

Fix:

```toml
[tool.setuptools.package-data]
schemas = ["*.json"]
"lbe_guard_inspector.memory" = ["memory_schema.sql"]
```

Regression added:

`tests/test_installed_wheel_smoke.py`

The smoke test must build the actual wheel, install it into an isolated environment, verify the SQL package resource, run installed `lbe session create`, and verify a non-empty persistent DB.

### Installed Proof A attempts after packaging fix

PR head `fbf1e598...` passed:

- installed-wheel smoke: 1 passed;
- focused C5 suite: 90 passed;
- full suite: 626 passed;
- branch diff check: passed;
- installed wheel included `memory_schema.sql`;
- installed session creation succeeded;
- live provider check succeeded.

Proof attempts then exposed additional evidence-contract problems:

#### Task 001

Failed closed on missing runtime config.

Interpretation: fixture/config incompleteness, not proof of successful coding.

#### Task 002

Provider returned no `workspace.replace_text` request.

`README.md` remained unchanged.

But `source_change` incorrectly passed because generated `c5-runtime-state/` appeared after the Git baseline.

This was a **false-positive evidence defect**.

#### Task 003

Failed closed with `MISSING_EVIDENCE_REQUEST`.

No governed edit occurred.

### Source-change evidence correction

The old C2 source-change producer classified any Git-visible path appearing after the baseline as task-bound source change.

That was insufficient because LBE-generated runtime/config artifacts could satisfy the completion evidence without a governed source mutation.

Corrected rule:

```text
workspace.replace_text EXECUTED receipt
  -> task/operation identity
  -> path
  -> before_sha256
  -> after_sha256
  -> current live file hash must equal after_sha256
  -> source_change PASS
```

No executed receipt:

```text
source_change FAIL
```

A later modification after the receipt must make the evidence stale/fail according to the existing evidence semantics.

Regressions were added for:

- runtime artifacts alone must not pass source-change evidence;
- unrelated workspace changes must not be attributed to the task;
- a successful receipt with matching live after-hash may pass;
- a post-receipt file change must invalidate the proof.

### Proof fixture correction

The earlier disposable workspace had no applicable tests, so the fixed validation policy (`pytest -q`) returned exit code 5.

Do not weaken production validation to make an unsuitable proof fixture pass.

A clean controlled fixture was created instead:

`G:\Developments\lbe-p1-002-proof\c5-proof-project-v3`

Requirements for this fixture class:

- clean tracked source baseline;
- recognized project/profile;
- meaningful deterministic validation test;
- `.gitignore` excludes Python bytecode/runtime noise;
- runtime DB/config/state are not allowed to masquerade as task source changes.

---

## 5. C5 Proof A final proof

Latest proven PR head:

`e9874dca1504aeef153de0e5e15cbcb33ee7a50f`

Validation:

- focused tests: **38 passed** for the evidence correction slice;
- full repository suite: **628 passed**;
- installed provider check: **READY**;
- governed `workspace.replace_text`: **EXECUTED**;
- `source_change`: **PASS**, explicitly receipt-bound;
- `focused_test`: **PASS**;
- `git_status`: **PASS**;
- `session validate`: **READY**;
- persisted task: **completed / VALIDATED_COMPLETION**.

Proof chain:

```text
installed wheel
  -> persistent session
  -> provider READY
  -> coding reasoning
  -> governed workspace.replace_text EXECUTED
  -> receipt-bound source_change PASS
  -> focused_test PASS
  -> git_status PASS
  -> session validate READY
  -> persisted completed / VALIDATED_COMPLETION
```

**Verdict: C5 Proof Family A — PROVEN.**

Do not rerun or redesign Proof A unless later source/runtime changes invalidate this evidence or a regression appears.

---

## 6. What must not be repeated

Future agents must not:

1. treat the C5 milestone as another generic vertical-slice implementation;
2. infer a missing feature before checking current branches/PR history;
3. add a generic shell to satisfy coding acceptance;
4. create a second authorization, completion, session, or evidence system;
5. treat provider configuration as provider health;
6. treat source/unit tests as installed-path proof;
7. treat wheel build success as proof that required package data is present;
8. treat arbitrary Git dirt as task-bound source-change evidence;
9. allow LBE-generated runtime/config artifacts to manufacture completion evidence;
10. weaken validation policy because a disposable proof workspace lacks an applicable test;
11. claim completion from exit code alone;
12. claim C5/R7 readiness because Proof A passed;
13. use stale `docs/CURRENT_STATUS.md` as higher authority than live Git/runtime evidence;
14. rely on chat history instead of this record + current source/runtime verification.

---

## 7. Evidence/claim discipline for future work

For every C5 proof family:

```text
claim
  -> exact installed command/runtime action
  -> exact workspace/session/task identity
  -> structured receipts
  -> deterministic validation evidence
  -> persisted terminal state
  -> current Git/runtime verification
```

Lower-level evidence cannot justify a higher-level claim.

Examples:

```text
unit tests pass
  != installed path works

provider listed
  != provider healthy

file changed
  != governed mutation executed

Git dirty
  != task source change

command exit 0
  != feature complete

Proof A pass
  != C5/R7 pass
```

---

## 8. Next acceptance work

Proof A is frozen as proven.

Next family: **B — Provider switch installed-path proof**.

Required proof should establish, at minimum:

```text
persistent installed session
  -> baseline workspace identity / mode / permission / runtime policy / evidence semantics
  -> healthy provider/model A
  -> supported provider/model switch
  -> same session authority remains unchanged
  -> resume/continue through normal installed path
  -> governed operation succeeds after switch
  -> durable before/after evidence
```

Only implement code if that installed proof exposes a proven defect in an existing owner.

After B, prove C, D, and E individually.

---

## 9. Documentation maintenance rule

After every meaningful C5/R7 proof attempt:

- append the observed command/path/result;
- record whether the failure was product, packaging, fixture, configuration, evidence, validation, recovery, or environment;
- record the earliest proven owner;
- record the fix only after it is implemented;
- record validation at the level actually executed;
- update the A-E matrix;
- preserve failed attempts that teach a durable anti-repeat lesson;
- do not preserve transient noise that does not change future decisions.

This record must be updated before declaring another C5 proof family complete.

---

## 10. C5 Proof C — installed checkpoint/resume after external change

Source revision adding the missing installed checkpoint adapter:

`88e87a0a8c301059f109fc5e2a34f2739c559438`

Controlled fixture:

```text
workspace: G:\Developments\lbe-p1-002-proof\c5-resume-project-v1
runtime DB: G:\Developments\lbe-p1-002-proof\c5-resume-runtime-v1\acceptance.sqlite3
session: c5-resume-session-v1
task: c5-resume-running-v1
```

The missing installed-path seam was a CLI adapter, not another R4 owner. The
new `lbe session checkpoint` command delegates to the existing
`SessionMemoryRuntimeBridge`: it records only named workspace-relative file
hashes, persists an existing compaction payload and active constraints, and
returns the persisted checkpoint identity.

Installed proof:

```text
normal installed audit request started task c5-resume-running-v1
  -> proof-only CLI process interrupted after task persisted RUNNING
  -> installed lbe session checkpoint recorded README.md fact + checkpoint
  -> README.md changed and committed externally
  -> installed lbe session continue rehydrated same session/task/workspace
  -> checkpoint head check = MISMATCH
  -> checkpoint reactivation_allowed = false
  -> prior verified_facts = []
  -> task remained RUNNING with no stale completion claim
```

The resumed packet carried the preserved active constraint and required live
Git/source revalidation. Current workspace Git head was authoritative over the
checkpoint. The external change left the controlled workspace clean after its
commit.

**Verdict: C5 Proof Family C — PROVEN.**

Durable lesson: R4’s storage/revalidation implementation is not enough for an
installed acceptance claim unless the control surface can create the same
file-backed checkpoint through the authoritative runtime bridge.

---

## 11. C5 Proof D — installed read-only audit

The same controlled fixture ran the installed audit path using explicit
external runtime config/governance files. These files remain outside the tracked
proof project and are not wheel package data.

```text
installed lbe audit
  -> persisted session c5-resume-session-v1
  -> mode=audit, runtime_policy=audit, permission=read_only
  -> mode capabilities excluded modify
  -> provider returned workspace evidence request and deterministic result
  -> task c5-resume-task-v1b persisted COMPLETED
  -> README.md SHA-256 and Git status were unchanged by the audit
```

The first attempt without explicit runtime config failed closed because the
wheel intentionally excludes machine-specific `config.json`; that was a
fixture configuration error, not a packaging defect. Supplying the existing
environment-configured external owner produced the installed read-only proof.

**Verdict: C5 Proof Family D — PROVEN.**

Durable lesson: runtime configuration is a user-controlled external resource.
Never package machine-specific config simply to make an installed proof pass.

---

## 12. C5 Proof E — installed escalation/denial

The first installed request correctly produced no forbidden proposal. A later
real-provider request did propose `workspace.replace_text`; it exposed one
remaining handoff defect: `LBERequestController` rejected the known bounded
tool as `UNKNOWN_TOOL` before existing R6E/R6C could decide authority.

Source revision:

`e905da130801483070da0288f4c7780ceb204aef`

The correction preserves rejection of unknown tool IDs, but allows a
schema-valid request for an existing governed tool to reach the R6E tool
registry. Tool visibility still remains audit read-only; R6C is now the first
owner that classifies an attempted known write outside authority.

Installed final proof:

```text
real provider proposal: workspace.replace_text README.md
  -> audit mode decision omitted modify
  -> R6E tool registry received the bounded request
  -> R6C authorization returned ESCALATED
  -> CLI returned Capability 'modify' is not enabled by audit mode policy
  -> task c5-escalation-task-v4 persisted BLOCKED / TOOL_ESCALATED
  -> README.md SHA-256 identical before and after
  -> Git status remained clean
```

The handler was not invoked. No generic tool, approval framework, second
authorization resolver, or audit write exposure was added.

Validation for the final correction:

- focused acceptance/owner tests: **105 passed**;
- full repository suite: **630 passed**;
- installed-wheel smoke: **1 passed**;
- `git diff --check`: passed.

**Verdict: C5 Proof Family E — PROVEN.**

Durable lesson: provider-visible tool lists are guidance, but a known governed
tool proposed by an untrusted provider must reach the existing authorization
boundary for an attributable denial receipt. Unknown tools still fail closed
before orchestration.

---

## 13. Current next actions

```text
B: externally blocked by Provider-B HTTP 429 credit_balance_exhausted; the
   explicit config exists but cannot satisfy the required health contract.
Overall C5/R7: NOT READY.
```
