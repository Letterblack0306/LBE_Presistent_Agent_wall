# Professional Agent Runtime P0/P1 Final Reconciliation Patch

Status: **AUTHORITATIVE FINAL RECONCILIATION PATCH — P2 BLOCKED UNTIL PASS**
Updated: 2026-08-13

This document is a narrow authoritative patch under:

- `docs/design/PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_CANONICAL_IMPLEMENTATION_PLAN.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_P0_P1_IMPLEMENTATION_GATE.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_P0_P1_PROVIDER_MAPPING_AND_AUTHORIZATION_CORRECTIONS.md`

It exists because a later local-agent candidate declared P0/P1 "Finalized & Accepted" while still conflicting with the canonical architecture.

A local agent cannot self-accept P0/P1. P2 remains blocked until the conditions below pass review against current GitHub source and primary provider evidence.

---

## 1. Acceptance state

The following are already accepted conceptually:

- provider protocol families remain distinct;
- durable `lbe_call_id` is distinct from provider-native IDs;
- `CapabilitySupport` and `EffectiveAvailability` are separate domains;
- runtime availability and provider projection are separate dimensions;
- JSONL is not the session persistence authority;
- live output cannot be claimed without a streaming backend;
- provider/model events do not represent LBE tool execution;
- R6C remains the authorization owner.

The following remain blocking corrections.

---

## 2. OpenAI reasoning-summary lifecycle

Do not map:

```text
response.reasoning_summary_part.added
    -> model.reasoning_summary.delta
```

The summary-part lifecycle is metadata/lifecycle, not the text delta itself.

Required semantic distinction:

```text
response.reasoning_summary_part.added
    -> reasoning-summary part lifecycle / provider metadata

response.reasoning_summary_text.delta
    -> model.reasoning_summary.delta

response.reasoning_summary_text.done
    -> model.reasoning_summary.completed
```

Likewise, `response.incomplete_details.reason` is not an event.

Required direction:

```text
response.incomplete
    -> inspect response.incomplete_details.reason
    -> model.turn.incomplete
```

Refusal, provider failure/error, and incomplete must remain semantically distinct.

---

## 3. Gemini Interactions exact lifecycle

Do not use invented or unverified wrappers such as:

```text
interactions.step.started(type=function_call)
interactions.step.completed(type=function_call)
agent_action=function_call
```

The P0 contract must use the verified Interactions interaction/step lifecycle and provider-native step types.

Canonical conceptual family:

```text
interaction.created
interaction.in_progress
interaction.requires_action
interaction.completed

step.start
step.delta
step.stop

step types:
  thought
  function_call
  model_output
```

Function-call mapping:

```text
step.start where type=function_call
    -> model.tool_call.started

step.delta with argument delta when actually supplied
    -> model.tool_call.arguments.delta

step.stop
    -> model.tool_call.completed

interaction.requires_action
    -> model.turn.requires_tool
```

Gemini GenerateContent remains a separate protocol family. A complete `functionCall` part must not be converted into fabricated argument deltas.

Thought signatures / encrypted continuation state remain adapter/provider continuation state, not ordinary user-visible reasoning.

---

## 4. Anthropic continuation boundary

Anthropic `tool_result` is continuation input produced after LBE executes a client tool. It does not itself create the LBE runtime completion event.

Required direction:

```text
Anthropic tool_use
    -> model.tool_call.started/completed

LBE R6C authorization
    -> tool.started
    -> tool.completed | tool.failed | tool.denied | tool.escalated

Anthropic continuation adapter
    -> serialize tool_result using provider tool-use ID
    -> next provider request
```

`pause_turn` is not a generic standalone runtime event and is not equivalent to client tool use.

It must normalize to a provider continuation semantic distinct from `model.turn.requires_tool`, for example:

```text
model.turn.requires_continuation
```

Exact class naming remains P0-owned, but the semantic distinction is mandatory.

---

## 5. R6C authorization is mandatory in P1 resolution

The capability resolver must not recreate approval policy with custom branches such as:

```text
if tool is WRITE ...
if permission == write_allowed -> GATED
if mode != CODING -> invent availability
```

Current deterministic authority owner:

```text
lbe_guard_inspector/runtime/authorization_resolver.py
resolve_authorization()
```

Required resolution path:

```text
runtime technical support
        -> workspace/backend conditions
        -> mode capability eligibility
        -> AuthorizationRequest
        -> resolve_authorization()
        -> AuthorizationDecision
```

Required conceptual mapping:

```text
ALLOW
    -> EffectiveAvailability.AVAILABLE

DENY
    -> EffectiveAvailability.UNAVAILABLE / denied

ESCALATE
    -> EffectiveAvailability.GATED
```

Do not introduce a new unconditional `write_allowed -> GATED` rule.

Already-delegated ordinary workspace work must not gain repetitive approval prompts merely because P1 exists.

---

## 6. Runtime availability must never be overwritten by provider projection

This is invalid:

```text
if provider is unavailable:
    runtime capability state = UNAVAILABLE
```

Provider state controls projection only.

Required example:

```text
provider/model backend = unavailable
provider client tool calls = unavailable

workspace.read:
  runtime_availability = AVAILABLE
  provider_projection = HIDDEN
```

The capability remains usable by authorized direct-user commands, deterministic runtime logic, validation, control-protocol clients, or other LBE-owned paths.

Provider outage must not erase `workspace.read`, `git.diff`, `terminal.exec`, or any other proven runtime capability.

---

## 7. Do not mix CapabilitySupport and EffectiveAvailability

These are different typed domains.

Invalid:

```text
visible_state = runtime_support
```

where `runtime_support` is `CapabilitySupport` but `visible_state` is expected to be `EffectiveAvailability`.

Required distinction:

```text
CapabilitySupport:
  SUPPORTED
  UNSUPPORTED
  CONDITIONAL
  UNKNOWN

EffectiveAvailability:
  AVAILABLE
  GATED
  UNAVAILABLE
  CONDITIONAL
  UNKNOWN
```

Technical support is an input to availability resolution; it is not the same state object.

---

## 8. ProviderProjection semantics

Use a typed projection dimension such as:

```text
ProviderProjection:
  EXPOSED
  HIDDEN
  CONDITIONAL
```

Meaning:

```text
EXPOSED
  = the capability/tool schema may be exposed to the selected provider/model

HIDDEN
  = runtime capability exists or may exist, but this provider/model must not receive it

CONDITIONAL
  = projection depends on an explicit provider/model/endpoint/session condition
```

`EXPOSED` does **not** mean the provider owns identity, workspace authority, permission, policy, validation, or completion truth.

LBE remains the authority owner.

---

## 9. Do not assume future ToolSpec fields already exist

Current implementation fields must be verified from live source before use.

Do not write algorithms that assume fields such as:

```text
tool_spec.backend
```

unless the current source actually provides them.

Backend provenance remains a required future P1 capability metadata field, but implementation location and representation are deferred until the implementation slice inspects live source.

Use these labels during planning:

```text
confirmed current owner
likely future integration point
implementation decision deferred
```

---

## 10. Canonical tool lifecycle

The only accepted conceptual ordering is:

```text
model.tool_call.completed
        -> effective capability/projection check
        -> R6C authorization
        -> tool.started
        -> tool.output.delta / tool.progress when truthfully supported
        -> tool.completed | tool.failed | tool.denied | tool.escalated | tool.cancelled
        -> provider-specific continuation serialization
        -> next model events
```

Never emit `tool.completed` before `tool.started`.

Never authorize a tool result instead of the proposed operation.

Never represent LBE tool execution as `model.*`.

---

## 11. Required final correction output

Before P2, return only:

1. corrected OpenAI Responses mapping;
2. corrected Gemini Interactions mapping;
3. corrected Anthropic tool-use / tool-result / pause-turn continuation mapping;
4. corrected capability resolution pseudocode that explicitly calls `resolve_authorization()`;
5. one provider-down/runtime-available example;
6. focused tests proving these boundaries;
7. PASS/FAIL against every section of this reconciliation patch.

Do not repeat the entire P0-P16 roadmap.

Do not create P2 code.

Do not self-declare acceptance.

---

## 12. P2 release condition

P2 may begin only after review confirms all of the following:

- exact provider lifecycle mappings are no longer invented;
- OpenAI summary-part lifecycle and summary-text deltas are separate;
- Gemini Interactions uses verified interaction/step semantics;
- Anthropic `tool_result` is continuation input after LBE execution;
- `pause_turn` is distinct from client tool use;
- P1 uses R6C instead of recreating approval policy;
- runtime availability survives provider outage;
- `CapabilitySupport` never substitutes for `EffectiveAvailability`;
- provider projection never grants authority;
- future source fields are not assumed without live verification;
- canonical tool lifecycle ordering is preserved.

## Final rule

> **P0/P1 is frozen only when provider semantics are accurate and P1 derives availability from existing LBE authority. A provider can change what is projected to the model; it cannot redefine what LBE owns or what the active session is authorized to do.**
