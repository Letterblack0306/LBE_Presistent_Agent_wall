# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-10-10
Status: **ACTIVE — LBE-OWNED TERMINAL PRODUCT / CURRENT INSTALLED ACCEPTANCE**

## Documentation consolidation and workspace hygiene — active plan (2026-10-10)

**Scope:** documentation ownership, routing, contradictions, and workspace hygiene only. This section does not change implementation authority, mutate runtime code, or certify product readiness.

**One-reader entry order:** `docs/README.md` is the existing documentation entry point; `docs/DOCUMENT_INTENT_MANIFEST.md` is the per-file classification registry; `docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md` owns dated human product intent. Then consult `docs/CURRENT_STATUS.md` for the bounded status snapshot, this plan for remaining work, `PROJECT_INDEX.md` for structural ownership, and the active machine gate + intent ledger for mutation authority. Current source, runtime effects and receipts outrank every document.

**Document types, one responsibility each:** The existing `docs/README.md` and `docs/DOCUMENT_INTENT_MANIFEST.md` own routing/classification; the following table is a summary, not a parallel registry.

| Role | Single canonical destination | Allowed claims |
|---|---|---|
| Live implementation/worktree state | Current runtime, Git HEAD, source, generated operational receipts | Exact observed state, bounded by revision/time |
| Product status | `docs/CURRENT_STATUS.md` | Dated evidence-led snapshot only; not a live assertion |
| Product direction and pending work | `docs/IMPLEMENTATION_PLAN.md` | Goals, ordered dependencies, explicit OPEN work and acceptance |
| Source ownership and structural registry | `PROJECT_INDEX.md` | Path → owner → supporting contract → mutation boundary |
| Active mutation scope | `.lbe/governance/implementation-gates.json` plus existing intent ledger | Gate and intent state; never inferred from plan text |
| Feature-specific design | Existing `docs/design/` files | Proposed design with references and source reconciliation; no readiness claim |
| Acceptance proof | `docs/acceptance/` | Named fixture/revision/harness/provider/terminal conditions; cannot promote unrelated acceptance |
| Earlier blueprints/UI/external studies | `docs/reference/` and `docs/research/` | Historical or illustrative only; no runtime authority |
| Cross-project reference | GPT-Knowledge | Routing and architectural doctrine; live LBE outranks it |

**Consolidation method:** (1) inventory and detect contradictory current-state language, (2) establish path/type/owner and date, (3) link the original contract rather than copy it, (4) annotate stale/historical claims visibly without rewriting their evidence, (5) only remove or move files after inspecting every caller/import/link and obtaining a distinct approved cleanup scope, (6) verify links, document scope and actual runtime evidence independently. Preserve history and user-created/untracked files.

**Workspace hygiene rules:** No automated delete/move of unknown files, receipts, proofs, caches, personal launchers, or dirty Git state. Inventory and classify as tracked authoritative / tracked historical / generated ignored / untracked user-owned / unknown. A suggestion to relocate a file is not permission to mutate it. Never use an old checkout, simulated UI, green test, fixture, process exit code, or stale screenshot as proof of the installed product. Record HEAD, relevant config, observed effect, receipt and falsifier before classifying a claim as PROVEN. Alternative outcomes: DISPROVEN, INCONCLUSIVE, BLOCKED_CONFIGURATION, STALE_TEST_OR_FIXTURE, TEST_HARNESS_FAILURE.

**Current reconciled position:** At `2e0c3fd`, `ProviderKey` and the lossless provider-list decoder were added in Rust, but the real picker still uses the fixed `ProviderId`; do not call arbitrary-provider selection implemented. Prior Windows ConPTY tests established keyboard/mouse/slash interactions only; a real provider→governed tool→observation→completion acceptance is still open. Check live HEAD before repeating these bounded facts. The July blueprint under `docs/reference/README.md` is historical, not the active product description.

**Next documentation-only hygiene passes:** review all 73 tracked acceptance documents by claim/revision (avoid blanket statuses), annotate any unqualified current/ready/passed language with scope, reconcile duplicated sections without deleting historical receipts, and validate path/link references. This is an ordered maintenance backlog, not a declaration that those reviews have been completed.

---
## 0. Read this first

The machine gate is authoritative:

```text
.lbe/governance/implementation-gates.json
active_plan  = docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md
phase        = INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE
slice        = LBE_OWNED_TERMINAL_PRODUCT_SURFACE
status       = OPEN
implementation_allowed = true
next_phase_locked       = true
publication             = LOCKED
selected_reasoning_agent = engine-neutral; Cline is a supported adapter
```

The explicit 2026-10-10 product-owner decision supersedes the earlier Rust/Ratatui final-surface choice. The normal visible product is the LBE-owned Python terminal client entered through `lbe`. Rust/Ratatui remains reference/integration material. No LBE authority moved into the client.

## 1. Product goal

Build one persistent, provider-neutral LBE coding-agent product:

```text
USER
  -> lbe
  -> LBE-owned Python terminal client
  -> canonical LBE product-entry/session boundary
  -> engine-neutral reasoning/provider/model mechanics (Cline supported adapter)
  -> LBE authorization and governed execution
  -> ToolReceipt / evidence
  -> provider continuation
  -> persistence / recovery
  -> deterministic validation / completion
  -> truthful terminal projection
```

The terminal client owns presentation and input only. The selected reasoning engine owns cognition, planning, provider/model interaction, tool proposals, continuation, and response composition. LBE owns all authority-bearing consequences and truth.

## 2. Product entrypoint, UI, and embedded mechanics

```text
product                   = LBE
entrypoint                = lbe
visible terminal client   = lbe_guard_inspector/terminal_ui.py
installed composition     = bin/lbe.cmd -> lbe-launch.ps1 -> Python terminal_ui/product_entry
visual contract/reference = existing LBE HTML/React work + canonical GPT-K UI contract
reasoning mechanics       = engine-neutral LBE binding; Cline supported adapter where selected
runtime authority         = LBE Agent Wall
Rust/Ratatui              = reference/integration only
```

The visible client must reuse existing `product_entry`, session, mode, provider, authorization, governed execution, receipt/evidence, persistence and completion owners. It must not create a parallel provider catalog, session store, executor, receipt system or completion authority.

## 3. Feature truth and self-check contract

Final installed acceptance is necessary but not sufficient for a truthful product experience. Every user-facing feature must carry independent status across implementation, automated testing, live behavior, and user-visible completion.
### Status vocabulary

```text
IMPLEMENTED = source capability exists at its declared owner
TESTED      = focused automated check passed
LIVE        = real runtime interaction was observed
WORKING     = the user-visible journey completed correctly
PROVEN      = required evidence is current, correlated, and authoritative
MOCK        = simulated or preview behavior only
UNVERIFIED  = required check has not been run or evidence is stale
FAILED      = a current check reproduced a defect
BLOCKED     = progress is prevented by a dependency, gate, or unavailable prerequisite
INCOMPLETE  = partial implementation does not satisfy the complete requirement
```

`PASS` in a historical record, source presence, a rendered panel, a unit test, or a mock response must never be promoted to `WORKING` or `PROVEN` without current runtime evidence.

### Historical R3–R7 baseline

R3, R4, R5, R6, and R7 acceptance records are preserved as an accepted historical baseline for their declared revisions and bounded observables. They remain valid historical evidence and are not retroactively invalidated by later source or product reconciliation. The current installed product must nevertheless re-prove the relevant invariants through the present packaged `lbe` path whenever source, provider/model composition, client ownership, or artifact provenance has changed.

```text
historical R3–R7 PASS             preserved / bounded historical acceptance
current installed acceptance      OPEN
current release/product status    BLOCKED until fresh installed proof
promotion of historical PASS      prohibited without current correlated evidence
```

The September 20, September 4, and August 26 Google Drive exports were reconciled with the current local plans and acceptance records on September 25, 2026. The reconciliation confirmed the architecture and the current OPEN gate. It did not close current acceptance, and it does not supersede the newer September 24 provider/model mismatch, receipt/evidence provenance questions, or the unverified exactly-once, continuation, restart/resume, and final Rust/TUI journeys.

### Feature verification matrix

| Feature | Implementation owner | Current status | Next required evidence |
|---|---|---|---|
| Bare launch / clean process exit | installer + `lbe-launch.ps1` + `terminal_ui.py` | PROVEN on installed `1e31d208`; current-head repackage required | exact-current package/install + real PTY/ConPTY restoration |
| Session create | existing LBE session/runtime owners | IMPLEMENTED / TESTED / LIVE | current packaged restart/resume |
| Provider/model binding | existing LBE provider/session owners | IMPLEMENTED / TESTED / LIVE source; installed real turn proven on `1e31d208` | exact-current installed selection + turn |
| Provider/model controls | `terminal_ui.py` over `provider.list/models/select` | IMPLEMENTED / TESTED / LIVE source | exact-current installed PTY interaction |
| Reasoning/continuation | engine-neutral binding; Cline supported adapter | PROVEN bounded installed turn | current-head package parity |
| Approval/governed execution | LBE authorization/tool owners | historical PASS; current read execution PROVEN | current DENY/ALLOW + one safe mutation |
| Receipt/evidence projection | LBE receipt/evidence owners | PROVEN bounded installed read | current mutation receipt/evidence correlation |
| Mode/policy | existing LBE policy/runtime owners | historical PASS / owner reused | exact-current interactive mode probe |
| Restart/resume | LBE persistence/session owners | UNVERIFIED on Python terminal | current packaged resume proof |
| Final completion | LBE validation/completion owners | OPEN | exact-current correlated completion evidence |
### Required user journeys and executable checks

```text
launch -> fresh-shell `lbe` resolves the canonical installed launcher
session -> create or restore one persisted session identity
provider/model -> catalog, selection, endpoint identity, and mismatch behavior are checked
reasoning -> real provider turn produces an engine-owned response/tool proposal
approval -> DENY executes zero; ALLOW executes exactly once where policy permits
tool execution -> governed dispatch produces correlated operation, receipt, and evidence
continuation -> provider continues from the observed governed result
persistence/resume -> restart restores the same session and authoritative state
validation -> completion is determined from required evidence, not presentation state
clean exit -> PTY/ConPTY exits and restores the terminal without orphaned process state
```

Each journey must record owner, self-check, automated test, live result, evidence path, status, limitation, and next action. A feature is `WORKING` only when its relevant journey completes on the current product/artifact.

## 4. Proven baseline — do not reopen without regression evidence

Keep all previously proven LBE runtime/session/authorization/execution/receipt/evidence/persistence/validation/completion owners. Keep engine-neutral provider continuation and governed Cline adapter evidence. Rust/Ratatui reference code may remain, but it is not the primary visible product.

## 5. Current defect / open acceptance boundary

Current main implements and tests the Python terminal surface and its provider/model controls. The preceding exact installed package proved normal launch, live Gemma continuation, governed read, receipt/evidence correlation and clean process exit. The source head is newer than that installed artifact, so final acceptance remains open.

```text
Python LBE terminal client                  IMPLEMENTED / TESTED / LIVE SOURCE
provider/model controls                     IMPLEMENTED / TESTED / LIVE SOURCE
installed candidate 1e31d208               BOUNDED CURRENT RUNTIME PROOF
exact-current package after provider UI     PENDING
real PTY/ConPTY lifecycle                   PENDING
current approval/mutation round trip        PENDING
Python-client restart/resume                PENDING
final product acceptance                    BLOCKED
```

## 6. Current single job

```text
LBE_OWNED_TERMINAL_PRODUCT_SURFACE
```

Required implementation sequence:

1. Build/package/install the exact current canonical head.
2. Prove `/providers`, `/models`, and `/model <id>` from that installed artifact using the existing provider/session owners.
3. Prove real PTY/ConPTY keyboard interaction, clean exit, and terminal restoration.
4. In a disposable governed validation workspace, prove approval DENY executes zero and ALLOW executes exactly one bounded mutation with correlated receipt/evidence.
5. Prove restart/resume on the Python terminal client using the same persisted session.
6. Prove provider continuation and deterministic completion from the observed governed result.
7. Only then close `FINAL_PRODUCT_ACCEPTANCE`.

## 7. Final real-terminal acceptance

Required proof chain:

```text
fresh terminal
-> lbe
-> LBE-owned Python terminal client
-> canonical LBE session identity
-> provider/model catalog + selected binding
-> reasoning turn
-> governed tool proposal
-> authorization decision
-> exactly-once LBE execution
-> ToolReceipt/evidence correlation
-> provider continuation
-> persistence/resume
-> deterministic validation/completion
-> clean quit
-> terminal restoration
```

No source-only test, package verifier, historical Rust acceptance or provider prose may substitute for this exact-current installed interactive proof.
## 8. Timeline / information surface contract

The final UI timeline is the readable operational foreground, not a decorative feed.

Meaningful events should project typed runtime truth, including as applicable:

```text
session_id
turn_id
operation_id
provider_tool_call_id
lbe_call_id
child_run_id
tool_receipt_id
evidence_refs
state
summary
target
provider
tool
result
error_code
```

Useful event families:

```text
instruction.received
agent.response
tool.requested
tool.started
tool.completed
tool.failed
provider.requested
provider.event
provider.failed
governance.blocked
validation.started
validation.completed
memory.recalled
skill.selected
skill.loaded
session.created
session.resumed
session.recovered
completion.proposed
completion.verified
```

Aggregate renderer plumbing, heartbeats, terminal resize noise, and repetitive health reads. Never hide a real failure or synthesize a success.

## 8. Memory / skills / evidence semantics

```text
tool     = executable capability
skill    = procedure for using capabilities
memory   = durable historical/project context
evidence = proof of an observed result
```

Historical memory may explain prior intent but cannot override current workspace/runtime truth.
Skills may guide procedure but cannot become execution authority.
Evidence and receipts remain LBE-owned.

## 9. Stop conditions

Continue automatically through routine implementation and validation. Stop only when:

- user-only authorization is actually required;
- the requested operation is destructive/publication-sensitive;
- canonical sources conflict and current evidence cannot resolve them;
- required external credentials/service/runtime are unavailable;
- the machine gate denies the mutation.

Do not stop merely because a request is marked unsupported. Trace the owner, implement the missing safe seam when relevant, record genuine exclusions, and continue.

## 10. Historical evidence routing

Do not embed historical failures into the live plan. Use the canonical records instead:

- `docs/acceptance/` for active/bounded acceptance records;
- `docs/history/` for superseded failure/repair history;
- `docs/governance/PROJECT_INTENT_LEDGER.md` for intent history;
- `docs/DOCUMENT_INTENT_MANIFEST.md` for document roles.

Historical PASS records are evidence for the revision and bounded slice that produced them. They are not current installed-product proof. Current status must be derived from the active machine gate and fresh runtime/artifact evidence.

## 11. Completion predicate

The current slice can pass only when all are true:

```text
one canonical LBE runtime authority
one persisted workspace/session identity
accepted Cline CLI/TUI launches from the intended product path
structurally distinct LBE UI is visibly accepted
provider/model state is real
agent reasoning remains independent
all authority-bearing execution crosses LBE authorization/governed dispatch
DENY executes zero times
ALLOW executes exactly once
ToolReceipt/evidence correlation survives continuation
session/recovery state survives resume
validation establishes completion truth
clean PTY/ConPTY exit restores the terminal
no second authority exists
```

Until then:

```text
FINAL_PRODUCT_ACCEPTANCE = BLOCKED
PUBLICATION = LOCKED
```

## Historical final-product claim — superseded

```text
LBE_OWNED_RUST_TUI_PRODUCT_SURFACE = HISTORICAL / BOUNDED PASS
FINAL_PRODUCT_ACCEPTANCE           = SUPERSEDED / CURRENTLY BLOCKED
CANONICAL_INSTALLER_CONTRACT       = HISTORICAL PASS / CURRENT PROVENANCE RECHECK REQUIRED
INSTALLED_SINGLE_COMMAND_LAUNCH    = HISTORICAL PASS / CURRENT PROOF REQUIRED
```

Those records prove bounded historical runs only. They do not close the current machine gate because current-main provider/model continuation and current installed-source acceptance remain unresolved. The active machine gate and current runtime evidence outrank this historical record.

## 12. Parallel final-product completion program

This section divides the active completion work into non-overlapping workstreams. Agents may work in parallel only within their assigned ownership boundary and only after the shared preflight is complete. No workstream may create a second runtime, provider, session, authorization, receipt, evidence, completion, or UI authority.

### Shared preflight — required by every agent

Before changing source, each agent must read and record:

```text
current HEAD and branch
working-tree status
.lbe/governance/implementation-gates.json
PROJECT_INDEX.md
docs/governance/PROJECT_INTENT_LEDGER.md
the owner document for the assigned area
```

Each agent must bind work to the existing active intent:

```text
LBE-INTENT-MAIN-HEAD-CONSOLIDATION-TRUTHFUL-ACCEPTANCE-001
MACHINE_SLICE = MAIN_HEAD_CONSOLIDATION_AND_TRUTHFUL_ACCEPTANCE
```

No agent may silently change the active slice, create a branch/worktree, publish, push, or edit unrelated documentation.

### Workstream A — source truth and integration coordination

```text
OWNER:        Coordinator / integration agent
PATHS:        .lbe/governance/, PROJECT_INDEX.md, docs/IMPLEMENTATION_PLAN.md,
              docs/governance/PROJECT_INTENT_LEDGER.md, docs/CURRENT_STATUS.md
DEPENDENCIES: Shared preflight only
NON_GOALS:    No runtime implementation; no gate transition; no publication
```

Responsibilities:

1. Maintain this plan's shared completion matrix.
2. Reconcile current Git/source/runtime evidence against claims from other workstreams.
3. Prevent overlapping ownership and duplicate implementations.
4. Record each workstream's evidence and status in this document.
5. Keep `FINAL_PRODUCT_ACCEPTANCE = BLOCKED` until every required row is proven on the current installed composition.

Exit evidence:

```text
one current source-of-truth plan
one active intent
no conflicting ownership assignments
all workstream results recorded with commands/evidence
```

### Workstream B — canonical launcher and installed composition

```text
OWNER:        Product-entry / packaging agent
PATHS:        launch-lbe.ps1, tools/lbe_product_integration.ps1,
              lbe_guard_inspector/product_entry.py, apps/lbe-terminal launch files
DEPENDENCIES: A; current provider configuration discovery from D
NON_GOALS:    No new runtime authority; no UI redesign; no provider replacement
```

Responsibilities:

1. Identify exactly one normal `lbe` launch path.
2. Ensure source build, package, installed binary, launcher, and runtime configuration refer to the same composition.
3. Keep compatibility shims forwarding only to the canonical entrypoint.
4. Prove fresh-shell command resolution and installed source provenance.

Exit evidence:

```text
fresh shell resolves the intended lbe
installed artifact hash matches the canonical build
launcher creates/resumes the authoritative LBE session
no alternate launcher owns runtime behavior
```

### Workstream C — Rust/Ratatui product surface and runtime projection

```text
OWNER:        Rust client agent
PATHS:        apps/lbe-terminal/src/, apps/lbe-terminal/tty-acceptance-test.ps1
DEPENDENCIES: B for the installed artifact; D for live provider/model; E for event/receipt contracts
NON_GOALS:    No backend authority duplication; no Textual rewrite; no Cline branding
```

Responsibilities:

1. Keep Rust/Ratatui as the canonical visible LBE client.
2. Project real session, provider, mode, policy, turn, receipt, evidence, approval, validation, and completion state.
3. Repair only adapter/projection gaps proven by current runtime evidence.
4. Verify PLAN/ACT/AUDIT presentation maps to backend mode/policy/permission owners.
5. Exercise keyboard, mouse, approval, interrupt, quit, terminal restoration, and no-orphan behavior through real PTY/ConPTY.

Exit evidence:

```text
Rust build/check/test pass
visible state is sourced from real runtime events
no synthetic success/receipt/evidence state in the canonical path
real PTY/ConPTY interaction evidence retained
```

### Workstream D — provider/model discovery and reasoning binding

```text
OWNER:        Provider/reasoning agent
PATHS:        lbe_guard_inspector/reasoning_*.py,
              lbe_guard_inspector/provider_*.py,
              lbe_guard_inspector/provider_turn_runtime.py,
              tests/provider and reasoning tests
DEPENDENCIES: A for current intent; B for installed launch; E for turn evidence
NON_GOALS:    No hardcoded model; no credential copying; no Cline-only authority
```

Responsibilities:

1. Discover live provider configuration, endpoint, advertised models, selected model, and session binding.
2. Preserve the engine-neutral boundary; Cline remains an adapter, not mandatory authority.
3. Ensure selected/configured/reachable/healthy/succeeded remain distinct states.
4. Route every interactive turn through one canonical provider-turn application boundary.
5. Prove a real current selected-model turn and continuation.

Exit evidence:

```text
live config discovered from the current machine
advertised model selected without hardcoding
health/turn/continuation evidence uses the same provider identity
provider mismatch fails closed and is visible
```

### Workstream E — governed execution, receipts, evidence, and completion correlation

```text
OWNER:        Runtime-governance integration agent
PATHS:        lbe_guard_inspector/runtime/, evidence_service.py,
              session/history owners, relevant tests
DEPENDENCIES: D for a real turn; C for UI projection; B for installed proof
NON_GOALS:    No second executor, receipt store, evidence store, session owner, or completion gate
```

Responsibilities:

1. Verify provider proposals enter the existing ToolRegistry and authorization path.
2. Prove approval-to-mutation exactly-once behavior and replay protection.
3. Verify persisted ToolReceipt and Evidence records contain the IDs displayed by the UI.
4. Verify provider continuation consumes the real result and preserves correlation.
5. Verify deterministic validation/completion remains LBE-owned.

Exit evidence:

```text
DENY executes zero times
ALLOW executes exactly once
receipt is persisted
evidence is persisted
UI identifiers equal persisted identifiers
completion is derived from validation, not provider prose
```

### Workstream F — installed end-to-end acceptance and restart/resume

```text
OWNER:        Acceptance/ConPTY agent
PATHS:        apps/lbe-terminal/tty-acceptance-test.ps1,
              scripts/ and tests/ acceptance surfaces,
              acceptance evidence under the active gate
DEPENDENCIES: B, C, D, and E must provide candidate proofs
NON_GOALS:    No source repair hidden inside acceptance; no PASS from unit tests alone
```

Responsibilities:

1. Use a fresh temporary installation and isolated database.
2. Run the complete installed chain: launch, session, provider, prompt, governed read, approval, governed write, receipt, evidence, validation, completion, exit, restart, resume, continuation.
3. Record exact artifact hashes, process/terminal behavior, persisted IDs, and failure edges.
4. Mark each matrix row `PROVEN`, `FAIL`, `UNVERIFIED`, or `BLOCKED` based on current evidence.

Exit evidence:

```text
fresh install and fresh shell
real terminal interaction
real persisted database
real provider/model turn
real receipt/evidence correlation
clean exit and terminal restoration
same session resumed after restart
```

### Workstream G — legacy/synthetic path reachability audit

```text
OWNER:        Legacy-path audit agent
PATHS:        lbe_guard_inspector/textual_tui.py,
              legacy launchers, package manifests, import/reachability references
DEPENDENCIES: B and C for canonical-path comparison
NON_GOALS:    No deletion without explicit cleanup authorization and non-use proof
```

Responsibilities:

1. Determine whether Textual or any preview/fake path is reachable from normal `lbe` launch or installed packaging.
2. Classify synthetic receipt/evidence/provider/session values as test-only, demo-only, dead, or production-reachable.
3. If unreachable, document the classification and leave it unchanged unless separately authorized for cleanup.
4. If reachable, report the exact call edge to Workstream B/C; do not independently redesign it.

Exit evidence:

```text
normal launch reachability result
installed-package reachability result
synthetic-state inventory
explicit keep/deprecate/remove recommendation with evidence
```

## 13. Shared completion status matrix

This matrix is the single progress/status surface for the parallel program. Agents update only their assigned rows with date, status, evidence command or artifact, and blocker. `PASS` means current claim-matched proof, not source presence or historical evidence.

| ID | Completion requirement | Owner | Status | Required evidence / blocker |
|---|---|---|---|---|
| A1 | Current HEAD, gate, intent, and ownership reconciled | A | IMPLEMENTED | Current Git and governance records; worktree remains dirty |
| B1 | One canonical normal `lbe` launch path | B | IMPLEMENTED / REVALIDATION REQUIRED | `install.ps1` now delegates to `tools/lbe_product_integration.ps1 -Mode package`; fresh-shell command resolution remains unproven |
| B2 | Installed artifact/source provenance matches canonical build | B | UNVERIFIED | Build/install/hash evidence still required |
| C1 | Rust/Ratatui is the visible LBE product surface | C | ACCEPTED / IMPLEMENTED | Current plan and source registration |
| C2 | Runtime/session/provider/mode state is real projection | C | IMPLEMENTED / REVALIDATION REQUIRED | Current PTY evidence |
| C3 | Keyboard/mouse/approval/quit/terminal restoration pass | C | UNVERIFIED | Fresh ConPTY run |
| D1 | Live provider configuration and model discovered | D | IMPLEMENTED / REVALIDATION REQUIRED | Provider binding import and focused contract tests added; live provider discovery/turn remains unproven |
| D2 | Current selected-model turn and continuation pass | D | UNVERIFIED | Real provider turn using same identity |
| E1 | Governed tool proposal and authorization path pass | E | IMPLEMENTED / REVALIDATION REQUIRED | Current installed turn evidence |
| E2 | DENY zero / ALLOW exactly once mutation pass | E | UNVERIFIED | Approval and replay evidence |
| E3 | UI receipt/evidence equals persisted records | E | IMPLEMENTED / REVALIDATION REQUIRED | DB rows correlated to visible IDs |
| F1 | Fresh installed end-to-end chain passes | F | BLOCKED | Depends on B–E |
| F2 | Restart/resume same session passes on installed command | F | UNVERIFIED | Fresh-shell restart/resume evidence |
| G1 | Textual/preview path reachability classified | G | IMPLEMENTED / REACHABILITY CHECK REQUIRED | Canonical `lbe` does not route to Textual; verifier now probes actual `lbe_guard_inspector.textual_tui` path |
| Z1 | No parallel authority owner remains | A/E/G | UNVERIFIED | Duplicate-owner scan |
| Z2 | Final product acceptance | A/F | BLOCKED | All required rows must be PASS/PROVEN |

Status vocabulary:

```text
PROVEN       current claim-matched runtime/installed evidence exists
IMPLEMENTED  source exists but current runtime proof is still required
ACCEPTED     product direction/ownership decision is settled
UNVERIFIED   evidence is missing or stale
FAIL         current proof reproduced a defect
BLOCKED      dependency or gate prevents completion
STALE        historical evidence no longer represents current acceptance
```

## 14. Parallel-agent reporting contract

After each workstream slice, the agent must update its assigned row in this document and report:

```text
WORKSTREAM:
SLICE:
SOURCE TRUTH:
FILES READ:
FILES CHANGED:
REUSED OWNERS:
DUPLICATE OWNERS INTRODUCED: NONE | list
TESTS: command and result
RUNTIME / INSTALLED PROOF:
STATUS: PROVEN | IMPLEMENTED | ACCEPTED | UNVERIFIED | FAIL | BLOCKED
BLOCKER:
NEXT DEPENDENCY:
```

Agents may not mark another workstream complete. The coordinator records cross-workstream closure only when the cited evidence is available and current.

## 15. Completion and closure rule

The plan is complete only when every required matrix row is `PROVEN` or `ACCEPTED` as applicable, with no `FAIL`, `UNVERIFIED`, `BLOCKED`, or stale evidence in the final installed chain.

The final closure sequence is:

```text
all workstream evidence collected
-> current source and machine gate reconciled
-> fresh installed E2E run passes
-> restart/resume passes
-> no synthetic/parallel authority remains in the normal path
-> active intent RESULT updated with exact evidence
-> active gate may be advanced only by explicit governed transition
```

Until that sequence passes:

```text
FINAL_PRODUCT_ACCEPTANCE = BLOCKED
PUBLICATION = LOCKED
```


## Current provider-extensibility design (2026-10-09)

See [provider-extensibility reference plan](design/PROVIDER_EXTENSIBILITY_REFERENCE_PLAN.md). This plan is OPEN; a limited identity-decoder slice was implemented at `2e0c3fd`, but dynamic picker and installed provider acceptance remain unproven.
