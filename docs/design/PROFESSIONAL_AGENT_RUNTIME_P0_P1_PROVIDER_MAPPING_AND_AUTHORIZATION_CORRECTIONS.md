# Professional Agent Runtime P0/P1 Provider Mapping and Authorization Corrections

Status: **AUTHORITATIVE COMPANION CORRECTION — ACTIVE**
Updated: 2026-08-13

This document is an authoritative companion to:

- `docs/design/PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_P0_P1_IMPLEMENTATION_GATE.md`

It records the final correction pass required before P0/P1 can be frozen and P2 implementation can begin.

Where this document conflicts with an earlier P0/P1 planning proposal, provider mapping table, or capability-resolution pseudocode, this document controls.

No runtime code implementation is authorized by this document. P0/P1 remain contract work until final review accepts these corrections.

---

## 1. Current acceptance state

The following P0/P1 architecture is accepted in principle:

- P0/P1 precede P2 and all Session/Turn/Item persistence work;
- `ProviderModelCapabilities`, `RuntimeCapabilities`, and `EffectiveSessionCapabilities` remain distinct;
- runtime capability availability and provider-visible projection remain distinct;
- JSONL is projection/export/transport, not a competing persistence authority;
- live stdout/stderr is not claimed until a real streaming process backend exists;
- durable LBE tool-call identity is independent from provider-native call identity;
- model/provider events remain separate from runtime/tool/process/control/validation event domains;
- Gemini Interactions and Gemini GenerateContent are separate protocol families;
- Gemini thought/continuation signatures are provider continuation state, not automatically user-visible reasoning;
- provider health affects provider projection, not whether LBE itself owns a runtime capability.

P0/P1 are **not yet accepted for P2** until the provider mappings and authorization semantics below are incorporated.

---

## 2. OpenAI Responses API corrections

Do not invent a native `response.output_tool_call` lifecycle.

The Responses API function-call mapping must preserve the actual output-item/function-argument lifecycle:

```text
response.output_item.added
  where item.type = function_call
    -> model.tool_call.started

response.function_call_arguments.delta
    -> model.tool_call.arguments.delta

response.function_call_arguments.done
    -> arguments finalized

response.output_item.done
  where item.type = function_call
    -> model.tool_call.completed
```

Preserve both provider-native item identity and provider-native function-call identity when present, while assigning a separate durable `lbe_call_id`.

Text streaming remains conceptually:

```text
response.output_text.delta
    -> model.message.delta

response.output_text.done
    -> model.message.completed
```

### Reasoning summary lifecycle

Do not map reasoning-summary part lifecycle directly to reasoning text deltas.

Preserve the distinction:

```text
response.reasoning_summary_part.added
    -> reasoning-summary part lifecycle/metadata

response.reasoning_summary_text.delta
    -> model.reasoning_summary.delta

response.reasoning_summary_text.done
    -> model.reasoning_summary.completed
```

Provider output items of type `reasoning` may be preserved as provider-native diagnostic/state metadata when applicable.

### Refusal, failure, incomplete

Do not treat `response.incomplete_details.reason` as an event by itself.

Use:

```text
response.incomplete
    -> inspect response.incomplete_details.reason
    -> model.turn.incomplete
```

Refusal streaming and terminal refusal semantics must preserve the provider-native lifecycle rather than inventing one generic `response.refusal` event.

Provider failure/error events must remain distinguishable from model refusal.

---

## 3. Gemini must retain two protocol families

P0 must represent at least:

```text
gemini_interactions
gemini_generate_content
```

Do not collapse them into one generic Gemini streaming grammar.

### 3.1 Gemini Interactions

Use the current Interactions lifecycle semantics, including interaction-level state and step-level streaming.

Conceptual mapping:

```text
interaction.created
interaction.in_progress
interaction.requires_action
interaction.completed

step.start
step.delta
step.stop
```

Step types may include provider-native concepts such as:

```text
thought
function_call
model_output
```

For function calls:

```text
step.start where step.type = function_call
    -> model.tool_call.started

step.delta with function-call argument delta
    -> model.tool_call.arguments.delta

step.stop
    -> finalize model.tool_call.completed

interaction.requires_action
    -> model.turn.requires_tool
```

Do not use an invented `agent_action=function_call` wrapper if the provider protocol does not expose that structure.

### 3.2 Gemini GenerateContent / streamGenerateContent

GenerateContent remains a separate protocol family.

A `functionCall` part may arrive complete in one streamed response chunk. Do not manufacture argument-delta events when the provider supplies only the complete call.

Conceptual mapping:

```text
text parts from streamed GenerateContentResponse
    -> model.message.delta / model.message.completed

complete functionCall part
    -> model.tool_call.started
    -> immediately model.tool_call.completed
```

`streamed_tool_arguments` therefore remains capability-sensitive, not universally supported for Gemini.

---

## 4. Gemini continuation state and thought signatures

Provider continuation state must be separate from user-facing reasoning summaries.

Required distinction:

```text
model.reasoning_summary.*
    = optional user-facing/provider-exposed reasoning summary

provider continuation state
    = signatures / encrypted state / interaction identifiers required to continue correctly
```

The adapter must preserve provider continuation metadata such as thought signatures where required by the selected Gemini protocol/model.

Do not render continuation signatures as ordinary reasoning text.

Do not discard signatures that are required for a later function-call continuation.

### Function results are continuation inputs

A Gemini `function_result` supplied after LBE executes a tool is not a model event emitted by the provider.

Correct boundary:

```text
provider function_call
    -> model.tool_call.completed

LBE authorization
    -> tool.started
    -> tool.completed / tool.failed

Gemini continuation adapter
    -> serialize function_result input
    -> preserve call identity / interaction continuation state
    -> begin next provider interaction
```

Do not map a client-supplied function result to `model.*`.

---

## 5. Anthropic mapping and `pause_turn`

Anthropic client tool use remains conceptually:

```text
content_block_start(type = tool_use)
    -> model.tool_call.started

content_block_delta(input_json_delta / partial JSON)
    -> model.tool_call.arguments.delta

content_block_stop(type = tool_use)
    -> model.tool_call.completed

message_delta(stop_reason = tool_use)
    -> model.turn.requires_tool
```

Tool results are returned by the client as `tool_result` content associated with the provider tool-use ID. They are not provider-emitted `model.tool_call.result` events.

P0 must also represent Anthropic provider-native continuation states such as `pause_turn` when server-side tool execution or provider continuation requires another model call without a client-owned tool execution.

Do not collapse these two meanings:

```text
tool_use
    = client/LBE tool execution required

pause_turn
    = provider/server-side continuation required
```

The normalized vocabulary should therefore accommodate a distinct semantic such as:

```text
model.turn.requires_tool
model.turn.requires_continuation
```

Exact naming may be finalized in P0, but the distinction is mandatory.

### Terminal-state attribution

For normalized terminal states such as incomplete/refused/cancelled/error, preserve attribution:

```text
provider_native
client_interrupt
http_or_transport_error
runtime_policy
```

Do not imply that every normalized terminal state has a native equivalent in every provider API.

---

## 6. Provider/model events and runtime/tool events remain separate

`model.tool_call.result` is not part of P0.

Required boundary:

```text
model.tool_call.completed
        ↓
LBE authorization
        ↓
tool.started
        ↓
tool.output.delta / tool.progress when truthfully supported
        ↓
tool.completed | tool.failed | tool.cancelled | tool.denied | tool.escalated
        ↓
provider continuation adapter
        ↓
next model events
```

Runtime tool execution must never be mislabeled as a provider/model event merely because the result is later serialized into the provider continuation request.

---

## 7. Capability support and effective availability are separate types

Do not use one enum for both technical support and current-session availability.

Use two conceptual types.

### CapabilitySupport

Describes whether a provider/model or runtime backend can technically support a feature:

```text
SUPPORTED
UNSUPPORTED
CONDITIONAL
UNKNOWN
```

`CONDITIONAL` requires a reason and, when applicable, the condition source.

### EffectiveAvailability

Describes whether a capability can be used in the active session:

```text
AVAILABLE
GATED
UNAVAILABLE
CONDITIONAL
UNKNOWN
```

These types answer different questions and must not be conflated.

---

## 8. Runtime availability and provider projection are distinct states

A professional capability should not rely only on one `state` plus an untyped or incidental boolean.

The contract should explicitly preserve both:

```text
runtime_availability
provider_projection
```

Conceptual provider projection states:

```text
EXPOSED
HIDDEN
CONDITIONAL
```

Example:

```text
workspace.read

runtime_availability = AVAILABLE
provider_projection = HIDDEN
reason = selected provider/model cannot emit client tool calls
```

This means the capability can still be used by direct user commands, deterministic runtime logic, validation, control-protocol clients, or other authorized runtime paths even though it is not projected to the provider.

Provider backend health affects provider projection. It does not erase LBE-owned runtime capability support.

---

## 9. Existing R6C authorization remains the authority owner

P1 must not invent a new rule such as:

```text
write_allowed -> always GATED / approval required
```

The existing deterministic authorization resolver remains authoritative.

Current owner:

```text
lbe_guard_inspector/runtime/authorization_resolver.py
resolve_authorization()
```

Its semantic contract remains:

```text
ALLOW
    active typed mode already delegates the capability for the requested scope

DENY
    operation is explicitly forbidden

ESCALATE
    operation would expand/conflict with current delegated authority,
    exceed workspace scope,
    require undelegated destructive authority,
    require undelegated persistent-policy authority,
    or otherwise require escalation
```

P1 must consume this owner rather than recreate approval policy.

Conceptual availability mapping:

```text
AuthorizationVerdict.ALLOW
    -> EffectiveAvailability.AVAILABLE

AuthorizationVerdict.DENY
    -> EffectiveAvailability.UNAVAILABLE / denied

AuthorizationVerdict.ESCALATE
    -> EffectiveAvailability.GATED
```

Whether an escalated capability remains visible to the provider for proposal/approval is a separate provider-projection rule and must be specified explicitly.

Already-authorized ordinary workspace work must not acquire new repetitive approval prompts merely because P1 introduces a capability registry.

---

## 10. Correct effective-capability resolution order

The capability resolution contract must preserve separate technical support, runtime availability, deterministic authorization, and provider projection.

Conceptual direction:

```text
Runtime backend support
        ↓
workspace binding / backend health
        ↓
mode capability eligibility
        ↓
AuthorizationRequest
        ↓
existing resolve_authorization()
        ↓
runtime EffectiveAvailability

ProviderModelCapabilities
        +
provider endpoint/model health
        +
runtime EffectiveAvailability
        +
projection policy
        ↓
ProviderProjection
```

Do not let provider inability to call tools change the runtime capability from AVAILABLE to UNAVAILABLE.

Do not let provider backend outage erase direct-user/runtime capabilities.

If the provider/model cannot emit client tool calls:

```text
runtime availability may remain AVAILABLE/GATED
provider projection = HIDDEN
```

for all provider-callable runtime tools, read or write.

---

## 11. Implementation-location claims remain provisional until implementation phase

P0/P1 planning may identify:

```text
confirmed current owner
likely future integration point
implementation decision deferred
```

Do not prematurely state that P0/P1 "will replace" a specific synchronous method, "will add" a particular database table, or "will create" a particular module unless that change is required by the accepted contract and verified against the implementation slice when work begins.

Contract acceptance determines semantics first. P2+ determines the smallest implementation change against live source.

---

## 12. Final P0/P1 review gate

Before P2 is authorized, verify that the final P0/P1 contract includes all of the following:

- exact OpenAI Responses function-call lifecycle mapping;
- correct OpenAI reasoning-summary text delta lifecycle;
- refusal/failure/incomplete kept semantically distinct;
- Gemini Interactions and GenerateContent separated;
- current Gemini Interactions interaction/step grammar used rather than invented wrappers;
- GenerateContent complete function calls do not fabricate argument deltas;
- Gemini thought signatures/continuation state retained separately from user reasoning;
- Gemini function results treated as continuation input after LBE tool execution;
- Anthropic client `tool_use` distinguished from provider-native `pause_turn` continuation;
- provider-native versus runtime/client terminal-state attribution preserved;
- no runtime tool result emitted as `model.*`;
- `CapabilitySupport` and `EffectiveAvailability` separated;
- runtime availability and provider projection separately represented;
- provider health affects projection rather than deleting runtime capabilities;
- lack of provider tool calling hides all provider tool projections but does not erase runtime tools;
- R6C `resolve_authorization()` remains the authority owner for ALLOW/DENY/ESCALATE;
- no new unconditional write-approval rule is introduced;
- future implementation locations remain provisional until the corresponding implementation phase.

Only after this review passes may P0/P1 be marked accepted and P2 begin.

## Final rule

> **Normalize each provider from its real native lifecycle, preserve provider continuation state, keep runtime execution in runtime domains, and derive session availability through existing LBE authorization. Provider projection is a view over runtime authority; it is never the authority itself.**
