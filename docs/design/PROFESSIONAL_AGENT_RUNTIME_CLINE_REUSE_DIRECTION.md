# Professional Agent Runtime — Cline Reuse Direction

Status: **AUTHORITATIVE IMPLEMENTATION DIRECTION ADDENDUM — ACTIVE**
Updated: 2026-08-13

This document updates the implementation direction for the professional LBE runtime without replacing the canonical dependency architecture in `PROFESSIONAL_AGENT_RUNTIME_CANONICAL_IMPLEMENTATION_PLAN.md`.

It must be read with:

- `docs/design/PROFESSIONAL_AGENT_RUNTIME_CANONICAL_IMPLEMENTATION_PLAN.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_P0_P1_IMPLEMENTATION_GATE.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_P0_P1_PROVIDER_MAPPING_AND_AUTHORIZATION_CORRECTIONS.md`
- `docs/design/LBE_AGENT_RUNTIME_CLI_TUI_AND_TOOL_ACCESS_SPEC.md`
- `docs/design/LBE_AGENT_RUNTIME_USER_STEERING_EXTERNAL_CLIENT_AND_CONTROL_PROTOCOL_ADDENDUM.md`
- GPT-Knowledge `ai-agents/cline-runtime-reuse-for-governed-agent-infrastructure.md`

Where this addendum conflicts with an older assumption that LBE must independently implement every provider streaming/agent-loop layer, this addendum controls the implementation strategy. Existing accepted P0/P1/P2 contracts and existing LBE authority owners remain unchanged.

---

## 1. Direction

Before implementing parallel provider-native streaming/tool-call plumbing from scratch, LBE must evaluate selective reuse of the current Cline SDK lower layers.

Preferred evaluation order:

```text
@cline/llms
    -> provider transport / streaming reuse

@cline/agents
    -> optional agent-loop / continuation reuse
       only if LBE remains the tool/governance authority

@cline/shared
    -> selective type/event/helper reuse where useful

@cline/core / @cline/sdk
    -> do not adopt wholesale as LBE runtime authority
```

The objective is to reuse mature provider and agent-engine mechanics while preserving LBE's existing deterministic governance architecture.

---

## 2. Ownership boundary remains unchanged

### LBE remains authoritative for

```text
workspace/project identity
canonical workspace root
session/task identity
mode and permission profile
runtime policy
ProviderModelCapabilities truth/projection
runtime capability availability
R6C authorization
registered governed tool dispatch
operation identity/idempotency
evidence provenance
validation truth
completion truth
checkpoint/recovery policy
Session / Turn / Item durable state
agent-control protocol semantics
TUI/IDE/MCP product projection
```

Existing owners remain authoritative, including:

```text
lbe_guard_inspector/runtime/authorization_resolver.py
lbe_guard_inspector/runtime/tool_orchestration.py
lbe_guard_inspector/session_memory_runtime.py
existing memory/evidence/completion owners
```

### Cline lower layers may own or assist with

```text
provider transport
provider-specific request serialization
provider-native incremental streaming
provider-specific tool-call syntax
partial tool argument handling where genuinely supported
provider continuation serialization
provider retry/error normalization
context/token management
usage events
```

A Cline package must not gain workspace mutation authority merely because it can execute tools in its standalone configuration.

---

## 3. Target architecture

```text
                        LBE TUI / IDE / client
                                 |
                        agent-control/event API
                                 |
                    LBE Session / Turn / Item
                                 |
             capabilities + deterministic authorization
                                 |
                    existing governed tools
                                 ^
                                 |
                    normalized P0 model events
                                 |
                     Cline integration adapter
                       /                    \
              @cline/llms            @cline/agents
                 |                     optional
                 +----------+-------------+
                            |
                    provider-native APIs
```

The Cline adapter is replaceable infrastructure, not a new authority layer.

---

## 4. P3 implementation direction

Canonical P3 remains **Provider-Native Streaming + Tool-Call Adapters**, but the implementation strategy changes.

### P3A — Cline lower-layer compatibility proof

Before building provider adapters independently:

1. Pin the exact Cline package versions under evaluation.
2. Inspect `@cline/llms` provider interfaces and stream event contract.
3. Map real Cline provider events to the frozen LBE P0 normalized event vocabulary.
4. Verify OpenAI, Anthropic, Gemini, and OpenAI-compatible paths do not require fabricated semantics.
5. Verify provider-native IDs, usage, cancellation, incomplete/error states, and continuation metadata can be retained.
6. Verify the accepted bounded Python 0.2.1 reasoning path remains untouched.

Expected result:

```text
Cline native/provider event
        -> LBE adapter
        -> normalized model.* event
```

No Cline-native event object becomes the durable LBE public event contract.

### P3B — provider transport reuse decision

If `@cline/llms` satisfies P0/P2 truth requirements cleanly, prefer using it rather than maintaining redundant first-party streaming transports.

If it cannot preserve a required provider semantic or imposes unsuitable runtime/dependency constraints, implement the affected provider path natively behind the same LBE adapter contract.

This decision may be per provider; one provider need not force the same backend choice for all providers.

---

## 5. P7 implementation direction

Canonical P7 remains **Governed Provider Continuation Loop**.

Evaluate `@cline/agents` only if the tool boundary can be intercepted before mutation.

Required flow:

```text
provider/model stream
        -> normalized LBE tool proposal
        -> EffectiveSessionCapabilities / ProviderProjection
        -> R6C authorization
        -> lbe_guard_inspector.runtime.tool_orchestration
        -> truthful tool/runtime events + evidence
        -> Cline/provider continuation input
        -> next model stream
```

Unacceptable flow:

```text
provider
   -> Cline built-in shell/editor/write tool executes
   -> LBE is informed afterward
```

That path bypasses LBE's execution authority and cannot be used for strict governance claims.

If `@cline/agents` cannot use host-provided governed tool execution cleanly, LBE will reuse only `@cline/llms` and own P7 itself.

---

## 6. Why not adopt ClineCore wholesale

Current Cline SDK documentation describes `ClineCore` as owning or providing:

```text
sessions
SQLite persistence
built-in tools
workspace/config discovery
RPC/multi-process support
execution-host behavior
```

Those overlap existing or planned LBE owners.

Using both as authorities would create ambiguous state for:

```text
which session is canonical
which workspace root is authoritative
which permission decision controls a write
which tool receipt proves execution
which checkpoint is resumable
which runtime decides task completion
```

Therefore:

> Do not make `ClineCore` the LBE core runtime unless a future explicit migration replaces an LBE owner with proof and updates the architecture first.

No such migration is currently planned.

---

## 7. P4/P6/P8 lessons from Cline, without authority transfer

Cline remains useful implementation evidence beyond P3/P7.

### P4 — Session / Turn / Item

Use Cline's current session/event coordination as comparative evidence for:

- rejecting stale events from non-active sessions;
- preserving authoritative turn state separately from transcript-tail inference;
- resumption after interruption;
- handling straggler events after cancel.

Do not copy Cline persistence as a second LBE history store.

### P6 — live execution events

Use Cline's streaming/event behavior as proof that client surfaces should receive incremental, typed events rather than polling a status dashboard.

LBE runtime events remain LBE-owned.

### P8 — steering/cancel/control

Use Cline's current session-event handling as comparative evidence for separate states such as running, resumable, completed, awaiting follow-up, and error.

The exact LBE state machine remains governed by the LBE control protocol and persisted runtime semantics.

---

## 8. CLI/TUI direction does not change

Reusing Cline underneath does not make the visible product a Cline CLI.

The primary LBE TUI remains a high-fidelity transcript over LBE runtime events:

```text
user input
agent commentary / streamed answer
in-flight governed tool cell
live stdout/stderr/progress
completed / failed / denied / escalated / cancelled result
agent reaction
edit/diff
validation
final response
```

Compact secondary views remain LBE-owned, including concepts such as:

```text
/diff
/git
/validation
/processes
/tools
/provider
/context
/evidence
/checkpoints
/mcp
/logs
```

The TUI must consume normalized LBE events, not Cline UI messages or provider-native wire payloads.

---

## 9. Dependency and licensing requirements

The current `cline/cline` repository is Apache License 2.0.

If Cline packages become production dependencies:

- pin exact package versions;
- record package/version provenance in LBE build/release metadata;
- preserve required Apache-2.0 license and NOTICE obligations;
- keep the Cline adapter isolated behind LBE interfaces;
- add compatibility tests before dependency upgrades;
- do not use Cline trademarks as LBE product identity;
- verify the license and package contents again at the version actually adopted.

---

## 10. Revised forward execution sequence

The canonical P0-P16 dependency order remains valid. The immediate forward path becomes:

```text
P2 current capability negotiation
        -> finish acceptance/regression proof

P3A Cline lower-layer compatibility proof
        -> @cline/llms event/provider mapping
        -> authority-boundary proof

P3B choose per-provider backend
        -> reuse @cline/llms where clean
        -> native adapter only where required

P4 persistent Session / Turn / Item under existing LBE owner

P5 governed professional capabilities under existing dispatcher

P6 live runtime execution events

P7 evaluate @cline/agents continuation reuse
        -> reuse only if LBE tool execution stays authoritative
        -> otherwise LBE owns continuation loop

P8-P16 continue under canonical plan
```

This is not permission to skip P0/P1/P2/P4 contracts. It is a direction to avoid rebuilding mature separable infrastructure unnecessarily.

---

## 11. Acceptance gate for adopting Cline lower layers

Cline reuse is accepted only when tests/evidence prove all of the following:

- LBE P0 normalized semantics can represent the relevant Cline/provider stream without fabrication;
- selected model capability truth still comes from LBE P2 evidence, not Cline brand assumptions;
- tool calls are intercepted before any workspace/external mutation;
- all mutations still pass existing LBE authorization and tool orchestration;
- provider continuation can consume LBE-produced tool results;
- cancellation/error attribution remains truthful;
- LBE session/workspace persistence remains authoritative;
- provider/backend replacement remains possible behind the adapter;
- bounded 0.2.1 provider path remains regression-safe until explicitly retired by migration proof;
- LBE TUI/control clients remain independent of Cline-native UI/event serialization.

If any condition fails, fall back to a lower Cline layer or a native LBE implementation for that responsibility.

## Final rule

**Reuse Cline where it is mature infrastructure; do not import Cline as a competing runtime authority. LBE owns governance, workspace/session truth, tools, evidence, validation, completion, and product-facing events. Cline lower layers may supply provider and agent mechanics only through an explicit replaceable adapter boundary.**
