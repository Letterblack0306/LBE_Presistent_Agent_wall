# LBE Runtime Vision: Doctrine-Driven Engineering

Status: **PROPOSED PRODUCT AND UX DIRECTION**. This document records product
intent. It does not change the active machine gate, LBE Core ownership, or any
current runtime behavior until an authorized implementation slice proves it.

## Definition

> **LBE provides the engineering environment. Models provide reasoning.**

LBE is a doctrine-driven engineering-agent runtime. It lets a reasoning agent
perform useful engineering work without making that model the authority over
workspace mutations, policy, evidence, or completion. The CLI/TUI is the
runtime's local IDE surface; it is not the product's authority or a separate
agent.

```text
user objective
  -> provider reasoning
  -> LBE doctrine, policy, and governed capabilities
  -> receipts and evidence
  -> deterministic LBE completion / recovery
```

LBE Core remains the pre-action permission and governed-execution baseline.
This vision describes how the complete runtime presents and applies that
baseline to a provider and a user.

```text
LBE knowledge       -> influences provider reasoning
active doctrine     -> changes objective and evidence behavior
LBE Core            -> controls execution consequences
registered tools    -> let the agent work within authority
CLI/TUI             -> exposes the environment to the user
```

## Invisible workflow, visible evidence

For ordinary engineering work, the user does not construct a workflow or pick
tools from a console. LBE carries workflow semantics inside the runtime:
capability scope, policy, retries, resumability, evidence, and completion
criteria. The agent works naturally through the objective and active doctrine.

Specialist work that requires a reproducible multi-step deliverable may expose
an explicit, reviewable workflow and structured output. This is an exception
for the deliverable, not the default LBE interaction model.

The UI makes outcomes legible: what the agent tried, changed, observed, could
not establish, and what to do next. It does not make the user operate the
underlying workflow machinery.

## Adaptive doctrine, not rule overload

Rules must not all behave as absolute blocks. A rule carries a declared
severity and response so LBE can preserve engineering judgment while retaining
accountability:

| Severity | Runtime response | Intended use |
|---|---|---|
| Advisory | Supply guidance and persist the observation. | Conventions, hints, and non-critical improvement opportunities. |
| Warning | Surface the concern, require the agent to account for it, and retain evidence. | Material ambiguity or a departure that may be legitimate. |
| Justification required | Pause the affected action until the agent supplies a scoped rationale; LBE records it. | Exceptions that need a human-reviewable paper trail. |
| Strict block | Deny the tool request before execution. | Security, workspace boundary, destructive, or governance-critical violations. |

Severity is selected by policy and risk classification, never by provider prose.
An escape hatch is a bounded, auditable justification or an explicit
high-risk authorization; it is not an ungoverned bypass.

## Runtime doctrines

Modes are not personalities and are not tool presets. They are typed runtime
doctrines that alter the objective, authority boundary, evidence standard, and
completion contract while preserving LBE Core's permission boundary.

| Mode | Primary objective | Agent behavior | Completion standard |
|---|---|---|---|
| Engineering | Build within authority. | Inspect, propose, make governed changes, validate, and report. | Required validations and receipt/evidence contract are satisfied. |
| Audit | Establish truth. | Read-only inspection; correlate current evidence; identify uncertainty; ask focused questions rather than invent conclusions. | Findings are evidence-backed and recorded; no mutation is performed. |
| Investigation | Resolve a bounded unknown. | Trace hypotheses, compare evidence, surface ambiguity, and request high-value clarification when it changes the conclusion. | The cause, remaining uncertainty, or explicit blocker is recorded with provenance. |

Mode selection is user-visible and LBE-resolved from the persisted session,
permission, and runtime policy. Provider intent is advisory. A provider switch
must preserve workspace identity, policy, permissions, guards, evidence
semantics, task lifecycle, and deterministic completion ownership.

## Agent behavior

The agent is not a rigid command executor. It should reason over the governed
capabilities available in the active doctrine, use receipts to revise its plan,
and pause for a user only when clarification changes the safe or correct next
action.

Examples of expected questions:

- “This module is not consumed by any known path and has no documented intent.
  Is it retained for an external integration, or should I investigate removal?”
- “The evidence supports two plausible causes. Which deployment target is in
  scope before I propose a change?”

The agent must not use a question to evade routine policy-covered work. It
acts automatically when authority, scope, and evidence requirements are clear;
it asks when intent is materially ambiguous, an exception needs justification,
or a high-risk authority expansion is required.

## User experience

The primary UI is objective-driven, not tool-driven. The user assigns a role
through a visible mode selector and provides an objective. LBE and the agent
select appropriate governed capabilities in the background.

The main runtime surface shows:

- current objective and workspace/session identity;
- active mode and a short plain-language doctrine explanation;
- progress, current uncertainty, evidence, decision, and next action;
- high-risk authorization only when it is genuinely required.

Raw tool calls, command logs, receipts, diffs, and diagnostics remain available
as secondary evidence views. They are not the primary user workflow.

On a mode transition, the TUI may briefly present an LBE-centered doctrine
card, then return to the workspace. For Audit, the card communicates:

```text
AUDIT
Evidence First
Documentation Allowed
Code Modification Disabled
```

The active doctrine remains visible in the normal header so the agent's
behavior always has a human-readable reason. Confidence may be shown as a
statement of bounded certainty and needed clarification; it is not a substitute
for evidence or a pass/fail verdict.

## Agent-facing operational knowledge

At session bootstrap and before governed turns, LBE builds bounded,
provenance-tagged guidance from the active workspace, doctrine, policy,
registered capabilities, and evidence contract. It tells the provider how to
use LBE appropriately. It does not grant authority, replace policy, or become
editable model memory.

Project instructions, `AGENTS.md`, and registered skills are context inputs
with provenance. All tool requests still pass through LBE Core's pre-action
permission boundary and approved adapters.

### Instruction trust hierarchy

Instruction-bearing content is not equally authoritative:

1. LBE doctrine and active persisted policy are trusted runtime authority.
2. Explicitly registered project instructions and skills are bounded,
   provenance-tagged guidance.
3. Ordinary workspace content is evidence and may contain untrusted text; it
   does not alter doctrine, policy, or tool authority.
4. Web content, MCP/plugin output, and external references are untrusted input
   unless a separate trusted integration contract proves otherwise.

The provider may consider lower-trust content as evidence, but it must never
treat it as an instruction to bypass LBE, modify policy, disclose data, or use
an unavailable capability.

## Acceptance and continuity

Completion criteria are a first-class product contract. LBE translates the
task's required evidence and validation into a deterministic completion result;
a plausible provider response is never sufficient.

Continuity is an engineering property, not a context-window assumption. On
resume, LBE restores persisted session/task identity, receipts, evidence,
history, checkpoints, and current workspace state. The agent re-evaluates that
state instead of relying on a remembered narrative.

Every capability invocation declares whether it is idempotent. A retry must be
safe to repeat, or the capability must provide compensation/rollback evidence
or require an explicit justification before retrying. Durable run records make
the resulting path replayable and reviewable.

## Non-negotiable boundaries

- The provider reasons; LBE owns authorization, execution, receipts, evidence,
  persistence, recovery, and completion truth.
- Integrated agents must not receive direct mutation tools that bypass LBE
  permission and governed adapters.
- Rules and durable constraints change through proposal, validation, and the
  applicable authorization process; they never silently become policy.
- A later repository-promotion check cannot retroactively govern a direct
  mutation that bypassed pre-action control.
- User interaction remains one LBE runtime; subagents and specialists are
  internal, scoped participants with receipt-backed outcomes.

## Implementation and proof direction

Before this vision is represented as live product behavior, prove:

1. persisted severity/response policy and an auditable justification path;
2. mode-specific guidance and behavior contracts supplied to a real provider;
3. objective/mode/doctrine UI projection backed by persisted runtime state;
4. focused clarification behavior without blocking ordinary permitted work;
5. direct-tool bypass denial, governed execution receipts, and deterministic
   completion across Engineering, Audit, and Investigation.

Until then, the current gate and source remain the only truth for implemented
behavior.

Host sandboxing, DLP, AST retrieval, worktree subagents, and protocol expansion
are future capability areas. They are not prerequisites for implementing this
doctrine-driven CLI/TUI loop unless a later active gate explicitly adopts them.

## Product statement

> **LBE is a doctrine-driven engineering-agent runtime. The CLI/TUI is its IDE
> surface; the model supplies intelligence; LBE supplies operational knowledge,
> mode-specific doctrine, authority, governed capabilities, evidence standards,
> and durable engineering memory.**

Reference: [CLI Agents and Agentic Workflows: When Workflow Becomes
Invisible](https://medium.com/%40takafumi.endo/cli-agents-and-agentic-workflows-when-workflow-becomes-invisible-164a7484d3fc)
is product research only; Core and the active LBE gate remain authoritative.
