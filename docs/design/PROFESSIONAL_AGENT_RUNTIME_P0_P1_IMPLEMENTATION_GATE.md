# Professional Agent Runtime P0/P1 Implementation Gate

Status: **AUTHORITATIVE IMPLEMENTATION GATE — ACTIVE**
Updated: 2026-08-12

This document is the immediate implementation gate under `PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md`.

It exists to prevent a premature jump from the older CLI/TUI Step A–I design directly into a generic `RuntimeEvent` / `EventRecorder` implementation before provider-event semantics and professional runtime capability semantics are defined.

The older design documents remain valid supporting architecture, but this gate controls the next implementation work.

## 1. Immediate correction

Do **not** begin by implementing a flat generic event model such as:

```text
SESSION_STARTED
USER_MESSAGE
TOOL_CALL_STARTED
COMMAND_STARTED
EVIDENCE_COLLECTED
VALIDATION_RUN
APPROVAL_REQUESTED
```

in one undifferentiated enum.

That collapses multiple protocols and risks freezing the wrong abstraction before provider-native behavior and capability negotiation are understood.

The active sequence is:

```text
P0  provider event normalization contract
P1  professional runtime capability contract
P2  provider/model capability negotiation and probes
P3  provider-native streaming/tool-call adapters
P4  normalized Session / Turn / Item persistence
P5  professional workspace/Git/terminal capability foundation
P6  live tool/process execution events
P7  governed provider continuation loop
P8  bidirectional agent-control protocol
P9  replay/resume/fork proof
P10 MCP external-agent surface
P11 transcript projection
P12 professional interactive TUI
```

No later phase may be used to bypass missing P0/P1 contracts.

---

## 2. Event domains must remain conceptually distinct

At minimum, distinguish these domains before defining any shared persistence envelope.

### Provider/model events

```text
model.turn.started
model.message.delta
model.message.completed
model.reasoning_summary.delta
model.reasoning_summary.completed
model.tool_call.started
model.tool_call.arguments.delta
model.tool_call.completed
model.usage.updated
model.turn.requires_tool
model.turn.completed
model.turn.incomplete
model.turn.refused
model.error
```

### Runtime/session events

```text
session.started
session.resumed
turn.started
turn.completed
item.started
item.completed
item.failed
item.cancelled
```

### Tool execution events

```text
tool.started
tool.output.delta
tool.progress
tool.completed
tool.failed
tool.cancelled
tool.denied
tool.escalated
```

### Process/terminal events

```text
command.started
command.stdout.delta
command.stderr.delta
command.progress
command.completed
command.failed
command.cancelled
```

### Control events

```text
steering.received
steering.applied
approval.requested
approval.responded
turn.interrupted
turn.cancelled
```

### Validation/completion events

```text
validation.started
validation.completed
completion.evaluated
completion.blocked
```

A future renderer may project these into `Session -> Turn -> Item`, but the provider and capability contracts come first.

---

## 3. P0 — Provider Event Normalization Contract

P0 must define the provider-facing semantic contract before implementation of the generic runtime event layer.

For each supported provider family, document and test the mapping for:

- native request lifecycle;
- native streaming lifecycle;
- text/message delta semantics;
- reasoning/thinking visibility and summaries;
- client-side tool-call initiation;
- server-side tool behavior where applicable;
- partial/streamed tool arguments;
- parallel tool calls;
- tool-result continuation;
- completed/incomplete/refused/error states;
- cancellation;
- request/response identity;
- usage/accounting;
- server-side conversation/interaction state where applicable;
- provider-native diagnostics.

Supported initial families must include:

```text
OpenAI
Anthropic
Gemini
OpenAI-compatible/local/routed providers
```

`OpenAI-compatible` is a transport/protocol family, not proof that every selected model supports the same interactive-agent features.

### Required normalized provider event shape

Do not settle the final wire object prematurely, but P0 must define the required semantics for an adapter event such as:

```text
ProviderAdapterEvent
  provider_id
  model_id
  provider_request_id
  provider_event_type
  normalized_event_type
  message_id?
  provider_tool_call_id?
  lbe_tool_call_id?
  sequence?
  normalized_payload
  stop_reason?
  usage?
  continuation_ref?
  provider_metadata_ref?
```

The LBE durable tool-call identity must be distinct from provider-native call IDs so replay, retry, approval waits, reconnects, and evidence can refer to one operation independent of provider representation.

### Raw provider data

Do not use `provider_raw: dict[str, Any]` as the architecture.

Raw provider payloads may be preserved as diagnostic references, but clients and runtime logic must depend on normalized typed semantics rather than provider-private wire objects.

### Truthfulness rule

Do not manufacture:

- streaming when only final output exists;
- reasoning visibility the provider does not expose;
- partial tool arguments when only complete arguments are returned;
- parallel tool-call support when the selected model does not support it;
- server-side state when the provider is stateless.

---

## 4. P1 — Professional Runtime Capability Contract

P1 must define runtime capabilities separately from provider/model capabilities.

Do not reduce capability state to:

```text
available: bool
```

The runtime must represent at minimum:

```text
available
gated
unavailable
conditional
unknown
```

with an explicit reason for any non-simple state.

### Capability descriptor requirements

A professional capability descriptor must be able to represent:

```text
capability_id
family
backend_id
backend_version
availability
availability_reason
workspace_binding
mode_requirements
permission_requirements
mutation_class
external_effect_class
supports_streaming
supports_interactive
supports_background
supports_cancellation
supports_parallelism
input_schema
output_schema
evidence_types
validation_types
provider_projection
```

Additional fields may be introduced when proven necessary, but the contract must remain typed and evidence-backed.

### Required capability families

Initial design must accommodate at least:

```text
workspace/code
terminal/process
Git/repository
validation/evidence
session/runtime
browser when a real backend exists
IDE-native capabilities when a real bridge exists
```

A semantic capability such as `workspace.references` must be advertised only when a real backend such as LSP/IDE/parser/project tooling exists.

---

## 5. Three capability layers must remain separate

The architecture must explicitly distinguish:

```text
ProviderModelCapabilities
RuntimeCapabilities
EffectiveSessionCapabilities
```

### ProviderModelCapabilities

Answers what the selected provider + endpoint + model can express reliably, for example:

```text
streaming_text
client_tool_calls
parallel_tool_calls
streamed_tool_arguments
reasoning_visibility
structured_output
cancellation
```

### RuntimeCapabilities

Answers what the current LBE installation/session can actually execute, for example:

```text
workspace.read
git.diff
terminal.exec
terminal.session.start
browser.snapshot
```

### EffectiveSessionCapabilities

Derived from:

```text
ProviderModelCapabilities
        ×
RuntimeCapabilities
        ×
Mode
        ×
Permissions
        ×
Workspace binding
        ×
Backend health/configuration
        ↓
EffectiveSessionCapabilities
        ↓
provider-visible tool projection
```

Example:

```text
selected model supports tool calls
+
browser backend not installed
=
browser.snapshot unavailable to the provider
```

Conversely:

```text
runtime terminal PTY available
+
selected model cannot reliably emit tool calls
=
PTY exists for direct-user/runtime clients but is not projected as a provider tool
```

---

## 6. Live output must be backed by real runtime behavior

Do not add `TOOL_CALL_PROGRESS` or `command.stdout.delta` merely because the event model can represent them.

A synchronous backend such as:

```text
subprocess.run(...)
```

cannot produce truthful live deltas by itself.

Live terminal/process events are only valid once the execution backend actually supports incremental stdout/stderr, PTY/ConPTY, background-process observation, or an equivalent streaming primitive.

Event type existence is not capability proof.

---

## 7. Persistence ownership must remain singular

Do not create an `EventRecorder` that becomes a second session history or persistence authority alongside the existing persistent runtime/session owner.

Required direction:

```text
authoritative session/event persistence
        ↓
append normalized immutable event records
        ↓
projections/subscribers
  JSONL
  non-interactive CLI
  TUI
  future GUI
  IDE/SDK clients
```

JSONL is an export, transport, replay, or inspection representation of authoritative runtime events.

It is **not** a competing history database.

---

## 8. Relationship to the older Session / Turn / Item plan

The previous design work remains useful.

These concepts are still expected later:

- `Session -> Turn -> Item`;
- durable operation/tool-call IDs;
- replay;
- mutable in-flight tool cells;
- normalized user-facing events;
- JSONL projection;
- transcript renderer;
- TUI.

But they now belong mainly to P4–P12, after P0 and P1 establish the provider and capability semantics that those runtime items must carry.

Do not implement `event_model.py` simply because the older Step B listed it first.

---

## 9. Immediate planning deliverables

Before P2 or runtime event implementation, produce and review:

1. revised architecture dependency graph;
2. P0 provider event normalization contract;
3. provider-by-provider native-to-normalized mapping table;
4. P1 professional runtime capability contract;
5. effective-capability resolution algorithm;
6. exact existing source owners P0/P1 will later integrate with;
7. focused acceptance tests/fixtures required before P2;
8. expected later source-file changes;
9. conflicts between the older Step A–I documentation and the active professional-runtime pillar.

Do not ask to implement code until P0 and P1 are reviewed and accepted.

---

## 10. Acceptance gate before P2

P0/P1 are ready only when all of the following are true:

- provider-native differences are explicitly mapped instead of hidden in an untyped payload;
- provider/model capabilities are separate from runtime capabilities;
- effective capability projection is deterministic and testable;
- unsupported/unknown/conditional states remain truthful;
- tool-call identity survives provider differences;
- live-output semantics are not claimed without a streaming backend;
- persistence ownership remains singular;
- existing C5/R7 and 0.2.1 accepted foundations are not unnecessarily rewritten;
- the next implementation slice can be written without immediately redesigning the event/capability contracts.

## Final rule

> **Do not freeze the user-facing event model before defining what providers actually emit and what the runtime can truthfully expose. P0 and P1 are the immediate implementation gate. Session/Turn/Item, replay, JSONL, transcript rendering, and TUI follow after those contracts, not before them.**
