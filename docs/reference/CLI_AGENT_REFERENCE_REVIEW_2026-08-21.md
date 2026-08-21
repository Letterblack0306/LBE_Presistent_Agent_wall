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
| CLI-001 | The installed coding worker failed before provider execution because the tested installed environment lacked the existing `@cline/agents` adapter dependency. The result was `ORCHESTRATION_ERROR`, zero provider requests, and zero receipts. | Isolated `scripts/r7_observable13_installed_probe.py` run on 2026-08-21; direct Node import from installed `site-packages` returned `ERR_MODULE_NOT_FOUND`. | CONFIRMED for that installed artifact; this is a packaging failure, not an LBE provider selection. Current-source wheel parity remains unverified. |
| CLI-002 | `lbe code` selects its current Node-worker coding adapter, but its concrete registry exposes only `workspace.read` and create-only `workspace.create_candidate_text`. | `lbe_guard_inspector/cli.py` and `runtime/governed_coding.py` inspection on 2026-08-21. | CONFIRMED. The internal adapter class name is not a product/provider identity. |
| CLI-003 | The resulting product path is a bounded governed coding slice, not yet the intended agent-directed multi-capability loop. | CLI-002 plus the current fixed `ReasoningPlan`/controller architecture. | CONFIRMED architecture gap. |
| CLI-004 | Full regression, packaging/bridge tests, and a fresh exact-wheel build did not finish within their configured audit time limits. | `python -m pytest -q` timed out at 300 seconds; packaging/bridge group timed out at 120 seconds; `pip wheel` timed out at 300 seconds without a wheel. | UNVERIFIED; do not treat the source package as release-ready. |

## Required follow-on work (not activated by this document)

1. Restore reproducible installed-worker dependency provisioning and add a fast preflight that
   fails clearly when the current worker adapter dependency is unavailable; do not make that
   dependency an LBE provider default or product identity.
2. Prove an exact-wheel install from the current source can complete a real provider-tool-receipt-
   validation cycle in an isolated environment.
3. Replace the fixed central reasoning workflow with a provider-directed multi-turn capability
   loop. Keep `LBERequestController` and `ReasoningPlan` as optional specialist capabilities.
4. Expand the registered capability contract only through existing R6C/R6E authorization,
   ToolReceipt, operation-id, persistence, and deterministic completion owners.
5. Define one CLI contract over persisted runtime events: interactive session start/resume,
   objective submission, approval preview, receipt/diff rendering, interrupt/cancel, history,
   and machine-readable non-interactive output.
6. Prove interactive and non-interactive projections use the same runtime events and cannot
   bypass LBE authority.
7. Make package and full-regression validation bounded, diagnosable, and reproducible before
   treating a version as ready.

## Acceptance question for a future authorized slice

> From an isolated installed package, can a reasoning agent independently choose among the
> LBE capabilities available for its session, perform multiple governed tool turns, revise its
> approach from ToolReceipts and evidence, and complete only after deterministic LBE validation,
> while the CLI/TUI truthfully projects the same persisted session and event stream?

This is a proposed future acceptance question. It is not a current machine gate.
