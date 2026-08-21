# Agent Agency / LBE Authority Separation

Status: **PROPOSED FOLLOW-ON ARCHITECTURE REVIEW** (documentation only — no runtime source
change). This is a future architecture acceptance requirement / proposed review, **not** an
active machine gate.

## Central invariant

> **LBE governs an agent's capabilities and consequences; it does not prescribe the agent's
> reasoning procedure.**

## Ownership boundary

```text
Agent / provider owns:
- reasoning
- investigation strategy
- hypothesis formation
- capability / tool selection
- replanning after results
- interpretation
- communication

LBE owns:
- workspace / session identity
- mode / policy
- authorization
- capability boundaries
- governed execution
- operation identity
- ToolReceipt
- evidence provenance
- persistence
- deterministic validation / completion truth
```

## The architectural mistake

> **Reasoning controller became the agent.**

`LBERequestController` and the fixed `ReasoningPlan` workflow evolved from a bounded,
read-only inspection mechanism into the central cognitive path:

```text
provider = constrained planner / explainer
LBE     = reasoning workflow engine
```

The intended architecture is:

```text
reasoning agent
    ↓ uses
LBE governed capabilities
```

## What was built / what was intended / what must change

| Item | WAS BUILT (current) | WAS INTENDED | MUST CHANGE |
|------|---------------------|--------------|-------------|
| Mandatory `ReasoningPlan` | provider must emit a fixed plan structure every reasoning turn | optional structured output for a planning/inspection capability | make optional; main agent may operate without emitting it |
| Reasoning contract | `_APPROVED_TOOLS = {"workspace.read"}` read-only contract; controller builds evidence, asks plan, selects/runs guard, asks explanation | provider freely chooses among registered LBE capabilities | expose capabilities the agent may invoke; do not encode the sequence |
| Guard selection | driven by LBE workflow in the controller | guard inspection is one available capability | demote `LBERequestController` / `GuardInvestigationCapability` to a bounded/specialist investigation capability an agent may call (`guard.inspect`) |
| Deterministic Guard Inspector | correct deterministic mechanism | same | REPOSITION, not discarded; stays deterministic, exposed as a capability |
| R6C authorization | correct deterministic authorization | same | NOT a mistake; remains the authoritative execution boundary |
| R6E governed tool orchestration | correct deterministic execution/orchestration | same | NOT a mistake; remains the authoritative execution boundary |
| ToolReceipt | correct execution-evidence boundary | same | NOT a mistake; remains the execution evidence boundary |
| Provider continuation | correct receipt-backed continuation | same | NOT a mistake; remains receipt-backed |
| Persistent session/task state | correct LBE-owned persistence | same | NOT a mistake; remains LBE-owned |
| Completion validation | correct LBE-owned deterministic completion truth | same | NOT a mistake; remains LBE-owned |

Deterministic guards, authorization, receipts, persistence, and completion evidence are
**not** mistakes. The mistake is their placement around the reasoning agent — the controller
became the agent instead of the agent using governed capabilities.

## Reposition, do not discard

```text
LBERequestController       -> bounded/specialist investigation capability
ReasoningPlan              -> optional structured contract for specific planning/inspection capabilities
Guard Inspector            -> deterministic capability available to an agent
R6C / R6E / ToolReceipt    -> remain the authoritative governed-execution boundary
memory / context           -> resources supplied to reasoning, not replacements for reasoning
```

## Future architecture acceptance question

> Can a reasoning agent independently choose among registered LBE capabilities, perform
> multiple reasoning/tool turns, revise its approach from receipts/evidence, and complete
> work without LBE prescribing a fixed cognitive workflow, while all mutation, authorization,
> identity, persistence, receipts, and completion authority remain governed by LBE?

This is recorded as a **future architecture acceptance requirement / proposed follow-on
review**. It is not an activated machine gate and does not change current gate state.

## Reference-informed CLI requirements

Public CLI references reinforce the intended boundary: a terminal client is a projection over a
shared agent runtime, not a separate agent or execution owner. Those projects are comparative
references only and do not define an LBE provider, dependency, product identity, or code source.
LBE therefore needs one persisted runtime/event contract that can support interactive, one-shot,
and machine-readable CLI projections while retaining explicit approval, receipt, cancellation,
history/resume, and deterministic completion boundaries.

The current verified product gaps and the required follow-on proof sequence are recorded in
`docs/reference/CLI_AGENT_REFERENCE_REVIEW_2026-08-21.md`. Those findings are planning input
only; they do not activate a gate or authorize an architecture change.

## Proposed Unified Interactive CLI / TUI Launcher (Single-Command Entry)

Currently, `lbe` exposes multiple subcommands (`lbe session create`, `lbe session continue`, `lbe tui --session-id <id>`).

As a proposed future UX enhancement (post-R7 acceptance), the CLI projection layer will support a single-entry launcher (`lbe` or `lbe start`) that:
- **Auto-initializes / resumes** workspace sessions seamlessly without requiring explicit UUID parameters.
  - **Provides an interactive full-screen terminal experience** with a clear LBE-specific interaction model featuring:
  - Header banner with workspace path, active mode (`Plan` / `Act`), model provider, token metrics, and auto-approve toggles (`Shift+Tab`).
  - Interactive transcript panel with motion/streaming reasoning output, tool calls, and execution receipts.
  - Interactive input composer supporting `@` file mentions, `/` slash commands, and hotkeys (`Ctrl+P`).

> **Note:** The CLI/TUI layer remains strictly a user-facing projection layer; all underlying session management, authorization, receipts, and completion authority remain strictly governed by LBE runtime services.

## Cross-references

- `docs/IMPLEMENTATION_PLAN.md` — section 15 (doc reconciliation & this proposed review).
- `docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md` — current machine-gate state.
- `.agent/PROJECT_CONTEXT.md` — canonical agent entry point (links here).
- `docs/design/LLM_REASONING_LAYER_ROADMAP.md` — prior reasoning-layer design record.
- `docs/reference/CLI_AGENT_REFERENCE_REVIEW_2026-08-21.md` — public CLI reference review and
  current LBE product-gap findings.
