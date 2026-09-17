# LBE Persistent Agent — Canonical Implementation Plan

Updated: 2026-09-17
Status: **ACTIVE — FINAL PRODUCT SOURCE RECONCILIATION / STRUCTURAL LBE UI / REAL TERMINAL ACCEPTANCE**

## 0. Read this first

The machine gate is authoritative:

```text
.lbe/governance/implementation-gates.json
active_plan  = docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md
phase        = INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE
slice        = FINAL_PRODUCT_SOURCE_RECONCILIATION
status       = OPEN
implementation_allowed = true
next_phase_locked       = true
publication             = LOCKED
selected_reasoning_agent = Cline
```

`docs/CURRENT_STATUS.md` owns present-tense status. This file owns only the ordered work.
Historical R3-R7 failures/repairs are preserved in acceptance/history records and must not be read as the current job.

## 1. Product goal

Build one persistent, provider-neutral LBE coding-agent product:

```text
USER
  -> Cline CLI/TUI reasoning + interaction mechanics
  -> LBE workspace/session/turn identity
  -> mode/policy
  -> authorization
  -> governed execution
  -> ToolReceipt / evidence
  -> provider continuation
  -> persistence / recovery
  -> deterministic validation / completion
  -> LBE client projection
```

Cline owns reasoning, planning, tool proposals, continuation mechanics, response composition, and client interaction.

LBE owns workspace/session/turn identity, provider/model policy truth, authorization, governed execution, operation/receipt identity, evidence provenance, persistence/recovery, validation, and completion truth.

Do not create a second provider gateway, session store, authorization engine, tool executor, receipt/evidence authority, persistence owner, or completion authority.

## 2. Accepted user-facing product surface

```text
client source = C:\LBE-TUI-Lab\cline\apps\cli
launcher      = C:\LBE-TUI-Lab\run-cline-lbe.ps1
runtime       = LBE Agent Wall
validation runtime = C:\Agents-Memory-Tool-v6-validation
```

Rust/Ratatui is reference/integration only:

```text
C:\LBE-TUI-Lab\src
C:\LBE-TUI-Lab\run-lbe.bat
```

Python/Textual remains reference/runnable material but is not the accepted final product surface when it presents PREVIEW or synthetic execution/receipt/evidence behavior.

## 3. Proven baseline — do not reopen without regression evidence

```text
R3-R6F constituent runtime authorities      PROVEN_COMPLETE
R7 installed end-to-end bounded acceptance  PASS
parent/child/parent correlation              PROVEN
cancellation terminality                     PROVEN
canonical verifier                           PROVEN
LBE runtime availability                     PROVEN
session create/list/inspect/resume            PROVEN
session persistence                           PROVEN
provider catalog                              PROVEN — 11 providers
provider routing                              PROVEN in bounded live runtime evidence
Cline TUI launch in real Windows terminal    PROVEN by user-visible run
accepted Cline client path exists locally    PROVEN by current local execution
```

The old claim that the Cline client is missing is **STALE**.

## 4. Current defect / open acceptance boundary

The current real-terminal UI is **not visually accepted**.

Observed result: the surface still retains the recognizable Cline centered hero/composer composition. Logo, labels, accent colors, and a left rail are not sufficient structural differentiation.

Current classification:

```text
LBE branding                       IMPLEMENTED
color/theme differentiation        IMPLEMENTED
Cline mechanics reuse              IMPLEMENTED
structural LBE visual shell         FAIL_CURRENT_IMPLEMENTATION
interactive final acceptance       PENDING_AFTER_UI_REWORK
final product acceptance           BLOCKED
```

Required LBE shell:

```text
persistent LBE/workspace/model/mode/git/context header
conversation + execution in one timeline
active operation shows at most ~3 emitted runtime lines
single expand action reveals full emitted process history
completed operations collapse to one summary line
[I] composer identity with active-process motion
context-window usage projection
no permanent centered Cline hero / TrackedRobot-style landing composition
```

## 5. Current single job

```text
CLINE_LBE_STRUCTURAL_VISUAL_DIFFERENTIATION
```

Execute this without reopening settled runtime architecture:

1. Work in the accepted Cline CLI/TUI source under `C:\LBE-TUI-Lab\cline\apps\cli`.
2. Preserve Cline interaction/reasoning mechanics that are already useful.
3. Remove the centered hero/robot/home composition as the primary layout.
4. Implement the persistent LBE runtime header.
5. Render conversation and execution in one chronological timeline.
6. Render current process output as a bounded ~3-line live block; expand on demand.
7. Auto-collapse completed operations to one summary row.
8. Add `[I]` composer identity and active-process motion.
9. Add context-window usage projection.
10. Keep all runtime/tool/receipt/evidence state as LBE-owned projections; do not fabricate success or completion in UI code.
11. Build the accepted Cline CLI artifact.
12. Run it in a real Windows TTY/ConPTY terminal with the live validation runtime.

## 6. Final real-terminal acceptance after UI rework

Run:

```powershell
cd C:\LBE-TUI-Lab
.\run-cline-lbe.ps1 -AgentWallRoot 'C:\Agents-Memory-Tool-v6-validation' -Workspace 'C:\LBE-TUI-Lab'
```

Required proof chain:

```text
LBE visual shell renders
-> canonical LBE session identity
-> provider/model projection
-> successful conversational turn
-> governed tool proposal
-> authorization decision where applicable
-> exactly-once governed execution
-> ToolReceipt/evidence correlation
-> provider continuation
-> persisted session consequence / resume
-> deterministic validation/completion
-> clean quit
-> terminal restoration
```

No lower-layer test, screenshot, branding check, or focused runtime test may substitute for this installed interactive proof.

## 7. Timeline / information surface contract

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
