# LBE Complete Product Direction

Status: active product-direction proposal

This is the north-star contract for the complete LBE coding-agent product. The
original Cline-like interaction grew into a larger product, but the user
experience must remain natural rather than exposing an internal state machine.

## 1. Product statement

LBE is a complete coding-agent product that feels like a normal conversational
coding agent while LBE internally owns policy, authorization, governed
execution, evidence, receipts, persistence, validation, and completion.

The product has two complementary layers:

1. **Normal agent experience** — prompt, context, reasoning, tools, progress,
   results, and follow-up conversation.
2. **Audit layer** — optional visibility into policy, authorization, tools,
   evidence, receipts, runtime events, findings, and completion truth.

Audit is an additional lens over the coding agent, not a replacement agent.

## 2. User promise

For an ordinary coding task the user should be able to:

1. Open LBE in a workspace.
2. Enter or pass an initial prompt.
3. Let the agent inspect the workspace and explain its plan.
4. Allow safe reads without unnecessary interruption.
5. Approve sensitive changes when policy requires it.
6. See progress, tool activity, output, errors, and next steps.
7. Continue, revise, cancel, or resume naturally.
8. Understand what changed and why the task is or is not complete.

The user should not need to understand session IDs, event reducers, provider
bindings, receipt schemas, or internal policy states to complete a task.

## 3. Product layers and ownership

```text
User -> normal conversation -> visible client
     -> LBE session/runtime boundary
     -> reasoning engine/provider adapters
     -> LBE authorization and governed tools
     -> persistence/evidence/receipts/validation/completion
     -> visible result and optional audit projection
```

| Layer | Owns | Must not do |
| --- | --- | --- |
| Visible client | Conversation, controls, progress, results, audit views | Execute or declare completion |
| Reasoning engine | Reasoning, planning, tool proposals, response composition | Grant permission or invent receipts |
| Provider adapter | Provider/model transport and normalized events | Bypass LBE or silently switch provider |
| LBE runtime | Session, policy, authorization, execution, persistence | Allow unauthorized operations |
| Evidence/receipt owner | Operation correlation and provenance | Accept UI-only claims as evidence |
| Completion owner | Requirement validation and completion truth | Treat model prose or display `PASS` as completion |
| Audit layer | Explain runtime truth | Create a second executor or authority |

## 4. Normal coding lifecycle

```text
launch -> attach/create session -> resolve workspace/provider/model
  -> accept initial prompt -> inspect and plan -> propose capability
  -> authorize -> execute bounded operation -> stream progress/output
  -> persist evidence/receipt -> validate completion -> explain result
  -> remain available for follow-up
```

Rules:

- Reads should be low-friction when policy allows them.
- Mutations must be bounded, attributable, and authorized.
- Approval screens explain action, scope, risk, and next choice.
- Denials explain how the user can change course.
- Cancellation terminalizes the governed operation truthfully.
- Restart/resume preserves session identity and history.
- Provider failures remain visible failures.
- Completion requires LBE validation and evidence, not only agent prose.

## 5. Initial prompt contract

Initial prompts are first-class product input:

- interactive launch may prefill the composer;
- explicit automatic-start mode may submit once session and model are
  authoritative;
- the prompt must not submit twice after reconnect or restart;
- prompt, turn ID, events, output, approvals, receipts, evidence, and
  completion must be traceable;
- automatic start never bypasses authorization.

The UI distinguishes `prefilled`, `submitted`, `running`, `awaiting approval`,
`completed`, `failed`, `cancelled`, and `incomplete`.

## 6. Audit mode contract

Audit mode is a mode/lens, not a second agent. It may show session/workspace
identity, provider/model/engine binding, permission and runtime policy,
capability proposals, authorization verdicts, activity, evidence, receipts,
diagnostics, findings, audit verdicts, and missing completion evidence.

Audit remains read-only unless a separate governed action is explicitly
requested and authorized. Switching into audit must not grant permission or
change persisted session policy.

## 7. Complete product feature map

| Area | Required behavior | Acceptance evidence |
| --- | --- | --- |
| Conversation | Natural prompt/response loop with streaming | Real provider turn |
| Workspace | Browse, read, search, inspect changes, bounded patches | Hashes, receipts, evidence, authorization |
| Sessions | Create, resume, continue, history, cancellation | Persisted identity across restart |
| Providers/models | Discover, select, validate, report failure | No silent fallback |
| Tools | Project capabilities and proposals | Registered authorized execution |
| Coding changes | Review and apply bounded changes | Approval plus before/after evidence |
| Audit | Inspect truth without becoming executor | Projection tests plus live proof |
| Memory/context | Show useful history and compaction state | No fabricated memory/completion |
| Processes | Explicit registered bounded commands | No unrestricted shell |
| Extensions/MCP | Show installed capability state | Display never executes |
| Browser | Show connection and governed results | Separate browser acceptance |
| Output | Progress, errors, result, receipt, evidence, next action | No pass-only reporting |
| Accessibility | Keyboard, compact layout, ASCII/no-color/reduced motion | Input/render tests |
| Mouse | Convenience layer over keyboard actions | Scroll/safe clicks implemented; hit map plus interaction tests remain |

## 8. Truth labels

Visible features/results distinguish:

`IMPLEMENTED`, `TESTED`, `LIVE`, `MOCK`, `UNAVAILABLE`, `BLOCKED`, `FAILED`,
`COMPLETED`, and `INCOMPLETE`.

`PASS` alone never communicates product completion.

## 9. Direction reconciliation

Historical plans may describe Cline CLI/SDK, Python/Textual, HTML/JavaScript,
or Rust/Ratatui. Each must be classified as current canonical surface,
supported adapter/mechanic, audit/reference material, or superseded history.

Only one visible client may be canonical at a time. The current repository
index declares `apps/lbe-terminal` as the Rust/Ratatui visible client. If the
product owner chooses another client, the index, ledger, machine gate,
acceptance plan, and implementation scope must be updated before code changes.

The interaction contract here is client-agnostic: whichever client is
canonical, it must feel like a normal coding agent with audit as an additional
layer.

## 10. Development process

Every feature records:

1. user problem and normal-agent behavior;
2. audit behavior, if applicable;
3. authority owner and reused owner;
4. input and output contract;
5. real, mock, unavailable, and blocked states;
6. persistence, evidence, and receipt requirements;
7. keyboard and mouse requirements;
8. focused tests;
9. live acceptance scenario;
10. installed-release implications.

Implementation order:

```text
intent -> owner audit -> contract -> runtime -> projection -> UI
  -> focused tests -> live acceptance -> installed rebuild -> final report
```

No feature is complete merely because its panel renders or its unit test
passes.

## 11. Current gaps

- provider/model/workspace mouse hit mapping;
- unified implemented/live/mock/unavailable/completed status reporting;
- installed-runtime acceptance after latest worktree changes;
- reconciliation of historical direction documents with the canonical client.

These gaps do not require discarding the existing authorization, execution,
evidence, receipt, persistence, or validation foundations.
