# CLI Agent Reference Review — 2026-08-21

Status: **REFERENCE-BASED PLANNING INPUT — NOT CURRENT LBE ACCEPTANCE EVIDENCE**

## Scope and authority

This review compares public CLI product patterns with the LBE product direction. It does not
adopt external code, alter LBE authority, activate a machine gate, or claim that an external
product's behavior is correct for LBE.

**Provider-neutrality rule:** Cline, Codex, and Antigravity are external references only. They
are not LBE provider identities, defaults, dependencies to copy, or names for LBE product
surfaces. The only use of an external product name below is source attribution or the exact name
of an already-existing technical dependency under investigation.

LBE remains the local authority for workspace/session identity, policy, authorization, governed
execution, operation identity, receipts, persistence, validation, and completion truth.

## Public references inspected

| Reference | Relevant verified pattern | LBE interpretation |
|---|---|---|
| [Cline CLI](https://github.com/cline/cline/tree/main/apps/cli) — reference only | One shared agent core supports interactive TUI, one-shot, and structured JSON projections; it exposes Plan/Act, session history, tool approvals, and health tooling. | LBE needs one runtime contract with multiple projections. This is a product-pattern comparison, not an adoption of Cline as a provider or implementation. |
| [OpenAI Codex](https://github.com/openai/codex) | A local terminal coding-agent product with separate installation, configuration, and non-interactive documentation surfaces. | LBE needs a reliable installed command and a documented interactive/non-interactive contract before its CLI can be treated as product-ready. |
| [Google Antigravity CLI](https://github.com/google-antigravity/antigravity-cli) | A terminal-first interface shares one agent engine and settings with other surfaces; its public changelog emphasizes resumable conversations, permissions, diffs, MCP management, cancellation, and one execution path. | LBE should retain one authoritative execution path and project the same persisted sessions/events into its CLI/TUI. |

## Reference-informed product workflow

```text
user objective
 -> LBE restores or creates the persisted session
 -> reasoning agent receives the currently available governed capabilities
 -> agent chooses reasoning and tool turns
 -> LBE authorizes each governed operation
 -> LBE executes through the registered capability and emits ToolReceipt/event evidence
 -> agent receives receipts and may replan
 -> LBE deterministic validation decides completion
 -> CLI/TUI renders the persisted transcript, approvals, receipts, and terminal result
```

The CLI/TUI is a control and projection surface. It may start/resume a session, submit an
objective, display events and diffs, request approval, interrupt/cancel, and render results. It
must not prescribe the reasoning procedure, directly execute tools, infer approval, or claim
completion.

## Confirmed LBE findings

| ID | Finding | Evidence | Status |
|---|---|---|---|
| CLI-001 | The former Node-worker dependency failure is historical. The direct provider-neutral governed coding loop replaced that worker in commit `67ba749`. | Clean staged wheel audit and isolated installed R7 provider/tool-receipt/completion probe on 2026-08-21. | RESOLVED for the repaired release path. Source-root packaging remains sensitive to ignored local build residue; use clean staging/fresh clone for release proof. |
| CLI-002 | The governed coding path currently exposes only bounded registered workspace capabilities, including read and create-only candidate text. | `lbe_guard_inspector/runtime/governed_coding.py` and CLI inspection on 2026-08-21. | CONFIRMED. This is a deliberately bounded capability slice, not a complete terminal-agent product. |
| CLI-003 | The committed Textual TUI is a session transcript/composer surface, not the required terminal workspace. It lacks structured tool/approval/diff/evidence cells and interactive provider/session controls. | `lbe_guard_inspector/textual_tui.py`, CLI arguments, and supplied reference artifacts inspected on 2026-08-21. | CONFIRMED product gap. |
| CLI-004 | Current uncommitted coding-TUI wiring routes coding turns through the governed gateway and projects persisted receipts, but has only focused unit/CLI coverage. | Focused suite: 24 passed on 2026-08-21. No live interactive provider/TUI receipt render was available. | PARTIALLY VERIFIED; do not claim interactive product acceptance. |

## Required follow-on work (not activated by this document)

1. Define typed persisted runtime-event view models for tool calls, authorization decisions,
   ToolReceipts, diffs, evidence, failures, and validated terminal results. Both `lbe code` and
   the TUI must project those same events.
2. Implement approval preview/actions as an LBE-controlled contract: proposal, explicit operator
   decision, R6C authorization, R6E execution, receipt, and validation. The terminal must never
   infer approval from a model response or execute a tool directly.
3. Turn the supplied `docs/reference/ui/` artifacts into a Textual design reference only: retain
   their LBE title/logo motion intent, dark hierarchy, activity stream, and tool-cell readability,
   without treating the HTML research prototype as product UI or copying an external CLI.
4. Add a single terminal launcher that can create or resume a persisted session, select/check the
   configured provider and exact model, and truthfully show its state. The present TUI requires a
   pre-existing `--session-id` and optional external `--provider-config`.
5. Add terminal-native objective entry, session/history navigation, file references, command/help
   affordances, interrupt behavior, and explicit unsupported-state reporting.
6. Prove one installed interactive flow with a local test provider: objective, governed tool turn,
   receipt/diff/evidence rendering, authorization decision, deterministic completion, and resumed
   session. Browser/HTML rendering is separate evidence and is currently unavailable.
7. Keep package/full-regression validation bounded, diagnosable, and reproducible before treating
   a version as ready.

## Acceptance question for a future authorized slice

> From an isolated installed package, can a reasoning agent independently choose among the
> LBE capabilities available for its session, perform multiple governed tool turns, revise its
> approach from ToolReceipts and evidence, and complete only after deterministic LBE validation,
> while the CLI/TUI truthfully projects the same persisted session and event stream?

This is a proposed future acceptance question. It is not a current machine gate.
