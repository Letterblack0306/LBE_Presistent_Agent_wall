# Current Implementation Gate

Status: **OPEN — NEXT PHASE LOCKED**

Current phase: `P15_CONTROLLED_PROVIDER_TURN`

Current slice: `TYPED_START_TO_NON_STREAMING_PROVIDER_PROJECTION`

This record owns the one active implementation slice under the progression-lock model.

## Active P15 slice contract

Existing owners inspected: P10 typed persisted turn dispatcher, P3 provider
adapter, and P14 provider-to-history projection. The Textual client remains a
transport-only caller of typed controls.

The active work connects a typed start request to one configured non-streaming
provider call through the control owner, then persists its normalized events.
It must not stream, execute provider-requested tools, create LBE tool identity,
continue after tools, bypass approval, or make the UI a provider/runtime owner.

Required evidence level: `INTEGRATION` plus configured local-provider UI flow.
Reuse decision: P10 control owner invokes P3/P14 only; no second transport,
event store, tool executor, or UI controller.

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Completed P15 checkpoint

```text
phase: P15_CONTROLLED_PROVIDER_TURN
slice: TYPED_START_TO_NON_STREAMING_PROVIDER_PROJECTION
base_sha: c23eb047db22d963aace96f41e99e4d2e9c2f2a3
implementation_sha: c2d7ebc12dd063766a52eb83fdd6aded594ca6fc
requirements: typed start executes one explicitly configured non-streaming provider call through runtime control; normalized output persists to the active turn; UI remains presentation-only
existing_owner: P10 PersistentTurnControl, P3 adapter, P14 projection, P11 Textual client
reuse_decision: compose existing owners only; no second provider transport, controller, transcript store, or UI runtime
required_evidence_level: INTEGRATION plus LIVE_RUNTIME UI flow
validation_evidence: typed control-provider integration tests PASS (24); live Textual composer -> control -> smollm3-3b -> persisted events PASS, with truthful failed terminal after provider emitted ungoverned tool identity error; full repository suite PASS (654); implementation gate PASS; git diff --check PASS
unverified: governed tool-call identity and approval continuation; real provider/process interrupt propagation; provider selection through typed control; asynchronous/streaming turns; full user-flow and release acceptance
document_conflicts: none in the active gate
status: PASS
```

## Completed P14 checkpoint

```text
phase: P14_PROVIDER_EVENT_HISTORY_PROJECTION
slice: NON_STREAMING_ADAPTER_TO_PERSISTED_TURN
base_sha: f7fadbeb8c789c2b2b2d4722136d10f8151336a9
implementation_sha: a0c1a49eb3cba597729ca320c33682dca3107a99
requirements: ordered normalized provider-event persistence; truthful terminal turn mapping; preserve provider identity/text/usage; allow provider usage after terminal error; no tool execution or continuation
existing_owner: P3 OpenAI-compatible adapter, P0 event contract, P4 SessionOperationalHistory, P5 sole receipt projection
reuse_decision: one P3-to-P4 projection only; no transport, event store, receipt, tool executor, or continuation owner
required_evidence_level: INTEGRATION plus LIVE_RUNTIME
validation_evidence: focused provider projection/adapter tests PASS (6); live smollm3-3b projection persisted model.turn.started, model.message.completed, model.error, and model.usage.updated then finalized failed; full repository suite PASS (653); implementation gate PASS; git diff --check PASS
unverified: governed provider tool identity/approval/continuation; provider/process interrupt propagation; direct TUI-to-provider execution; typed provider selection through control; full user-flow and release acceptance
document_conflicts: none in the active gate
status: PASS
```

## Completed P13 checkpoint

```text
phase: P13_INSTALLED_TUI_INTERACTION
slice: FRESH_SESSION_COMPOSER_AND_CANCEL_FLOW
base_sha: 3ec380e5b08f1e6c2b2dc414ce480190b6aa6abc
implementation_sha: 4e3034c20a392924edf9ca42856feae45b765370
requirements: fresh installed session creation; installed Textual composer start and cancel control routing; packaged SQLite schema availability
existing_owner: P4 SQLite history, P10 control dispatcher, P11 Textual client, setuptools package-data metadata
reuse_decision: existing installed runtime and UI only; package the required existing schema rather than introducing a second state path
required_evidence_level: INSTALLED plus headless interactive UI control
validation_evidence: fresh wheel contained lbe_guard_inspector/memory/memory_schema.sql; isolated [tui] install PASS; installed lbe session create PASS; installed Textual composer/cancel interaction PASS; focused release-package/UI tests PASS (3); full repository suite PASS (651); implementation gate PASS; git diff --check PASS
unverified: live provider output in TUI; provider/process interrupt propagation; approval continuation; provider selection through control; full user-flow and release acceptance
document_conflicts: none in the active gate
status: PASS
```

## Completed P12 checkpoint

```text
phase: P12_INSTALLED_TUI_PATH
slice: OPTIONAL_DEPENDENCY_AND_CLI_SMOKE
base_sha: 3964639c80337ffb1c689e6f4b5f9a35686f4916
implementation_sha: 3964639c80337ffb1c689e6f4b5f9a35686f4916
requirements: fresh wheel build; isolated wheel installation with tui extra; installed lbe tui CLI help
existing_owner: setuptools packaging and existing lbe console-script declaration
reuse_decision: existing packaging path only; no separate launcher or distribution
required_evidence_level: INSTALLED
validation_evidence: built lbe_guard_inspector-0.2.0-py3-none-any.whl; fresh isolated venv install with [tui] PASS; installed lbe tui --help PASS; no source-path invocation used
unverified: live interactive TUI session; provider turn execution; provider interrupt propagation; approval continuation; provider switch through control; end-to-end user-flow and release acceptance
document_conflicts: none in the active gate
status: PASS
```

## Completed P11 checkpoint

```text
phase: P11_TEXTUAL_TUI_CLIENT
slice: PERSISTED_TRANSCRIPT_AND_TYPED_COMPOSER
base_sha: 0ea375d2e8969db15d31a9f74fd62cec33b72239
implementation_sha: c17ba102a53863acf6da27370136fc602195e1b7
requirements: Textual optional dependency and CLI command; truthful session header; ordered persisted transcript; composer routes start or steer; priority interrupt/cancel keys route typed controls; no UI-owned authority
existing_owner: P4/P9 history and replay; P8 vocabulary; P10 persistent turn dispatcher; CLI session persistence
reuse_decision: one optional Textual projection over existing runtime owners; no UI runtime, transcript store, tool executor, or provider controller
required_evidence_level: INTEGRATION
validation_evidence: focused Textual/control/transcript/CLI tests PASS (21); full repository suite PASS (651); implementation gate PASS; git diff --check PASS
unverified: installed TUI invocation; live provider turn and interrupt propagation; approval continuation; typed provider selection; full user-flow and release acceptance
document_conflicts: none in the active gate
status: PASS
```

## Completed P10 checkpoint

```text
phase: P10_PERSISTED_TURN_CONTROL
slice: START_STEER_INTERRUPT_CANCEL_INTENT
base_sha: 7ce9ded9aee6f22a3b75c4be1ea266ba3e5d2a89
implementation_sha: 0442690c02f033cbb760e15d4eb4187c941c2acc
requirements: typed start/steer/interrupt/cancel requests; persisted authoritative control events; active-turn rejection; cancellation finalization; no provider/tool/approval authority
existing_owner: P4 SessionOperationalHistory, P8 control vocabulary, SessionMemoryRuntimeBridge session persistence
reuse_decision: one dispatcher extending persisted history; no second session controller, provider executor, or approval owner
required_evidence_level: INTEGRATION
validation_evidence: focused turn-control/history/protocol tests PASS (5); full repository suite PASS (650); implementation gate PASS; git diff --check PASS
unverified: propagation of interrupt/cancel to a live provider/process; approval response; provider selection via control protocol; Textual interaction and installed/user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

## Completed P9 checkpoint

```text
phase: P9_REPLAYABLE_TRANSCRIPT_PROJECTION
slice: AUTHORITATIVE_EVENT_REPLAY_ONLY
base_sha: 243645294a3d1e5da6de1bb0e32168ee52f936e8
implementation_sha: 90c781daa9cf538a192561a346da8d721a17b4b5
requirements: deterministic session-scoped persisted-event replay; preserved sequence and event identity; no fabricated transcript activity; reopen from the same SQLite database
existing_owner: P4 SessionOperationalHistory and P5 governed receipt projection
reuse_decision: extend the existing history reader and add one read-only transcript projection; no transcript store, event producer, or session controller
required_evidence_level: INTEGRATION
validation_evidence: focused transcript/history tests PASS (3); full repository suite PASS (649); implementation gate PASS; git diff --check PASS
unverified: runtime control handlers; live steering/interruption/cancel/approval/provider switch; TUI interaction and installed/user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

## Completed P8 checkpoint

```text
phase: P8_TYPED_CONTROL_PROTOCOL
slice: STEERING_INTERRUPT_CANCEL_APPROVAL_VOCABULARY
base_sha: 43d4856ed9b65df59d2f9fd18657a5dd961c2197
implementation_sha: e5de6707a0a0357ecaeb34c6f1d61bb90ac71160
requirements: typed versioned requests; explicit accepted/rejected outcomes; steering, interruption, cancellation, provider selection, approval, evidence, and validation vocabulary; invalid-state rejection
existing_owner: P4 session history; P5 receipts; P7 continuation; existing session and R6C/tool authority
reuse_decision: one protocol vocabulary only; no second session controller, tool executor, or persistence owner
required_evidence_level: UNIT
validation_evidence: focused control-protocol tests PASS (2); full repository suite PASS (648); implementation gate PASS; git diff --check PASS
unverified: runtime control handlers; persisted control outcomes; live steering/interruption/cancel/approval/provider-switch flows; replay/TUI/user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

## Completed P7 slice contract

Existing owners inspected:

- provider proposals: P0/P3 normalized events;
- governed invocation and result: `GovernedToolOrchestrator` and `ToolReceipt`;
- persistence/event projection: P4/P5 operational history;
- existing `ToolReceipt` has an operation ID but no durable receipt ID.

The active work establishes durable receipt identity and a continuation stop
boundary. A provider can receive a continuation result only after LBE has
produced a governed receipt. Escalation/approval stops the loop; neither the
provider nor the continuation layer can execute a tool or bypass R6C.

Required evidence level: `INTEGRATION` for identity correlation and approved
receipt continuation. Live provider continuation requires separate runtime
proof and remains unverified.

Reuse decision: extend existing `ToolReceipt` and orchestrator outputs; do not
introduce a second tool executor, provider authority, or receipt store.

## Completed P7 checkpoint

```text
phase: P7_RECEIPT_BACKED_PROVIDER_CONTINUATION
slice: DURABLE_RECEIPT_IDENTITY_AND_STOP_BOUNDARY
base_sha: b6fa1dc58a28dc1ba9b974b9f7c5742f0c322af2
implementation_sha: ab79b31dab71488accea09618f574ef42f38addd
requirements: durable receipt ID; correlated receipt-backed provider continuation; escalated receipt stop boundary; no continuation execution authority
existing_owner: ToolReceipt/GovernedToolOrchestrator and P5 operational history
reuse_decision: extend existing receipt identity and add a provider-only continuation boundary
required_evidence_level: INTEGRATION
validation_evidence: focused continuation tests PASS (3); full repository suite PASS (646); implementation gate PASS; git diff --check PASS
unverified: live provider continuation; approval response/resume; controls; replay/TUI/user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Completed P6 slice contract

Existing owners inspected:

- fixed registered validation-command policy and execution:
  `ValidationCommandPolicyCatalog` and `CompletionEvidenceProducers`;
- governed tool dispatch/receipts: `GovernedToolOrchestrator`;
- ordered history: P4/P5 `SessionOperationalHistory`.

The active work is a process-observation layer for commands already selected by
fixed LBE policy. It may produce started/stdout/stderr/progress/completed/
failed/cancelled observations only from a real process. It must not accept
provider-controlled argv, use a shell, become a general command executor, or
claim live output for synchronous execution.

Required evidence level: `INTEGRATION` plus a local real-process test.
Cancellation must stop a real launched process; a static handler result is not
process-stream proof.

Reuse decision: reuse the fixed validation command catalog and governed command
boundary. The canonical branch has no existing live process-event owner.

## Completed P6 checkpoint

```text
phase: P6_GOVERNED_PROCESS_EVENTS
slice: FIXED_POLICY_COMMAND_LIFECYCLE
base_sha: 6cd7f5e2059c3f373cc4dbde054e61b5853dab19
implementation_sha: 1b8593b6f360f5e2326e3f06c1760db0596c36d9
requirements: fixed-policy shell-free process observation; real stdout/stderr; terminal outcome; cancellation terminates launched process
existing_owner: ValidationCommandPolicyCatalog and CompletionEvidenceProducers
reuse_decision: isolated process observer only; no general shell or provider-controlled argv
required_evidence_level: INTEGRATION plus local real process
validation_evidence: P6 real-process tests PASS (2); full repository suite PASS (643); implementation gate PASS; git diff --check PASS
unverified: process observer to operational-history wiring; provider continuation; controls; replay/TUI/user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Completed P5 slice contract

Existing owners inspected:

- governed dispatch/authorization/receipts: `GovernedToolOrchestrator` and
  `ToolReceipt`;
- authoritative ordered persistence: `SessionOperationalHistory`;
- provider events remain proposals only and never execute tools directly.

The active work projects already-produced governed receipts into ordered history
as `tool.completed`, `tool.denied`, `tool.escalated`, or `tool.failed`. It must
preserve receipt, operation, provider, and LBE-call identifiers when supplied.
It must not invoke a tool, bypass approval, change authorization, or synthesize
output/progress.

Required evidence level: `INTEGRATION` for real orchestrator receipt outcomes
persisted in the same SQLite event order. Process streaming remains outside
this slice until a real streaming backend exists.

Reuse decision: reuse `GovernedToolOrchestrator` receipts and P4 history; no
parallel tool dispatcher or receipt store is permitted.

## Completed P5 checkpoint

```text
phase: P5_GOVERNED_TOOL_EVENT_PROJECTION
slice: RECEIPT_TO_ORDERED_HISTORY_PROJECTION
base_sha: deced778188ece3153c79edbf347b91c05c826f2
implementation_sha: 110db48e01b25eb39b03a29318fb883e1c725ceb
requirements: project existing governed receipt outcomes into ordered SQLite history without tool invocation or authority changes
existing_owner: GovernedToolOrchestrator/ToolReceipt and SessionOperationalHistory
reuse_decision: projection only; no new dispatcher, receipt ID, or persistence authority
required_evidence_level: INTEGRATION
validation_evidence: focused operational-history/tool-orchestration tests PASS; full repository suite PASS (641); implementation gate PASS; git diff --check PASS
unverified: real process event streaming; provider tool proposal to governed receipt correlation; approval continuation; replay/TUI/user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

P5 preserves an existing operation ID, provider tool-call ID, and LBE call ID
when the caller supplies them. The current receipt type has no receipt ID, so
none is fabricated.

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Completed P4 slice contract

Existing owners inspected:

- canonical `main` has session/workspace state through `WorkspaceMemoryStore`,
  but no session/turn/item operational-history owner;
- P0 normalized provider observations and P3 native adapter remain event
  producers only;
- governed tool receipts and R6C authorization remain existing execution and
  authority owners.

The active work is one SQLite-backed authoritative history owner for ordered
sessions, turns, items, and observed runtime events. It must preserve distinct
provider, LBE-call, runtime-operation, and tool-receipt identities. It must not
be a second provider transport, session controller, authorization resolver, or
tool executor. JSONL/transcript output remains a later projection, not storage
authority.

Required evidence level: `INTEGRATION` for ordered persistence, reopening,
identity correlation, and replay from persisted events. No live provider or
tool execution claim is implied by persistence tests.

Reuse decision: extend the existing SQLite workspace-state store through one
operational-history module. The canonical branch has no equivalent owner to
reuse; the secondary worktree remains read-only reference evidence only.

## Completed P4 checkpoint

```text
phase: P4_AUTHORITATIVE_OPERATIONAL_HISTORY
slice: SESSION_TURN_ITEM_ORDERED_PERSISTENCE
base_sha: 68f9c52c709b72080f8198d99b3c60db62efcef6
implementation_sha: 3274bfe8896082cde3b4129b5ee62a6c90bb860e
requirements: one SQLite session/turn/item/event history; monotonic session and turn ordering; reopen from same database; provider identity preservation
existing_owner: WorkspaceMemoryStore owns SQLite connection/schema and session_state; P0/P3 remain producers only
reuse_decision: extend the existing database; no second persistence store or JSONL authority
required_evidence_level: INTEGRATION
validation_evidence: focused operational-history test PASS (1); full repository suite PASS (640); implementation gate PASS; git diff --check PASS
unverified: model/tool runtime integration; item finalization; event replay status; process/control event projection; installed-wheel and user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

The ignored runtime source was explicitly added in commit `3274bfe`; it is
tracked and delivered, not merely present in the local worktree.

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Completed P3 slice contract

Existing owners inspected:

- P0 normalized model-event contract: `NormalizedModelEvent`;
- P1/P2 capability truth: `CapabilityClaim`, `ProviderModelCapabilities`, and
  deterministic endpoint discovery;
- bounded OpenAI-compatible HTTP transport: `UrllibJsonTransport` and
  `OpenAICompatibleReasoningBackend`;
- session, authorization, and governed tool-execution owners remain unchanged.

The active work is a native OpenAI-compatible adapter that produces truthful
non-streaming normalized events from an actual provider response. It must reuse
the existing HTTP boundary where possible and preserve provider identifiers.
It must not claim deltas, reasoning summaries, tool arguments, parallel calls,
or continuation semantics unless the provider actually returns them. It must
not replace existing bounded reasoning, persist events, select providers, or
execute tools.

Required evidence level: `UNIT` plus `LIVE_RUNTIME` for one non-streaming
provider response. Streaming is explicitly outside this slice unless live
provider evidence proves it.

Reuse decision: P3 uses a native adapter. The evaluated `@cline/llms@0.0.73`
pin remains ineligible because its dependency/license gate failed. Existing
transport and authority owners stay unchanged.

Live prerequisite satisfied on 2026-08-15: `http://127.0.0.1:1234/v1/models`
was reachable, and the existing bounded provider health check completed with
`openai-compatible` / `smollm3-3b`. This proves one structured response only.

## Completed P3 checkpoint

```text
phase: P3_NATIVE_PROVIDER_EVENT_ADAPTER
slice: OPENAI_COMPATIBLE_NON_STREAMING_EVENT_FIDELITY
base_sha: 6e6f12a1077d82fdc3ad66e1d536ca48d072e280
implementation_sha: 3de2f94d86dc8dfd5d14b518ad7f1afeb5d612ef
requirements: native non-streaming OpenAI-compatible normalization; provider request identity; completed text/usage/terminal truth; no fabricated deltas or tool identity
existing_owner: P0 normalized events; existing urllib provider transport; P1/P2 capability truth; existing session/R6C/tool owners
reuse_decision: native adapter only; no Cline package, provider SDK, persistence, or authority owner added
required_evidence_level: UNIT plus LIVE_RUNTIME
validation_evidence: focused adapter/P0/P2 tests PASS (8); full repository suite PASS (639); implementation gate PASS; live smollm3-3b endpoint returned provider request ID, completed text, and usage
unverified: streamed events; governed durable tool-call identity; tool execution/approval/continuation; persistence; TUI and user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

The live provider emitted unsolicited tool calls after its text response. With
no governed durable call identity yet available, the adapter emitted the
truthful `LBE_CALL_ID_REQUIRED` error rather than fabricating identity or
executing a tool. This is a valid P3 boundary result, not tool continuation.

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Completed P2 slice contract

Existing owners inspected:

- P0 protocol-family vocabulary: `ProviderProtocolFamily`;
- P1 typed technical-claim owner: `CapabilityClaim` and
  `ProviderModelCapabilities`;
- legacy bounded provider metadata: `ProviderCapabilities` and
  `ProviderDescriptor` through `ProviderRegistry`;
- R6C authority: `resolve_authorization()` and governed execution owners.

The active work is deterministic discovery for one configured provider,
endpoint, and selected model. Endpoint syntax may prove a protocol family;
all professional feature claims remain `unknown` until explicit typed evidence
is supplied. This slice must not perform provider I/O, read secrets, modify the
legacy registry, select a provider, project tools, grant authority, or execute
tools.

Required evidence level: `UNIT` for endpoint classification, explicit-evidence
validation, and unknown-by-default behavior. Live endpoint/model evidence is
outside this slice and remains required before any live-provider claim.

Reuse decision: reuse P0 protocol vocabulary and P1 typed claims. Keep legacy
provider metadata unchanged; do not add a parallel transport or provider SDK.

The deterministic endpoint map is limited to `/responses`, `/v1/messages` or
`/messages`, Gemini `interactions`, Gemini `GenerateContent`/
`streamGenerateContent`, and `/chat/completions`; every other endpoint is
`unknown`. This identifies protocol syntax only. It is not a streaming, tool,
reasoning, context-window, or health claim.

## Completed P2 checkpoint

```text
phase: P2_PROVIDER_MODEL_CAPABILITY_DISCOVERY
slice: CONSERVATIVE_CONFIGURED_ENDPOINT_DISCOVERY
base_sha: 855e7ce027c0975a90a3bdf0e089998421acc7a5
implementation_sha: 062e716e0cd2246bd3cfdcf037190efb4783482a
requirements: endpoint-syntax protocol classification; explicit typed evidence only; unknown-by-default feature support; no provider I/O or authority
existing_owner: P0 ProviderProtocolFamily; P1 CapabilityClaim/ProviderModelCapabilities; legacy ProviderRegistry; R6C resolve_authorization()
reuse_decision: isolated deterministic discovery using P0/P1 contracts; no provider SDK, transport, registry rewrite, or authority owner added
required_evidence_level: UNIT
validation_evidence: py_compile PASS; focused discovery/P0/P1/registry tests PASS (28); full repository suite PASS (635); implementation gate PASS; git diff --check PASS
unverified: provider endpoint reachability; authenticated provider/model metadata; live streaming; provider selection; persisted projection; governed continuation; user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

P2 is complete at its required `UNIT` evidence level. It does not prove that a
configured endpoint is reachable or that any provider/model feature is live.
The next phase remains locked until a new exact P3 slice is registered.

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Completed P1 slice contract

Existing owners inspected:

- legacy bounded provider metadata: `ProviderCapabilities` and
  `ProviderDescriptor` through `ProviderRegistry`;
- bounded provider transport: `OpenAICompatibleReasoningBackend` through
  `ProviderRegistry`;
- session/workspace authority: `SessionMemoryRuntimeBridge` and
  `WorkspaceMemoryStore`;
- governed execution and authorization: `GovernedAgentGateway`,
  `ToolExecutionContext`, `GovernedToolOrchestrator`, and R6C
  `resolve_authorization()`.

The active work is the frozen typed professional capability contract required
before P2 capability discovery and provider projection. It must separate
provider/model technical support, LBE runtime availability, and effective
session capability projection. It must not alter the existing bounded provider
registry, add provider I/O, grant tool authority, execute tools, or infer
unknown capability support.

Required evidence level: `UNIT` for deterministic state separation,
unknown-by-default behavior, and invalid-state rejection. R6C remains the
authority owner: later projection may describe a capability but cannot grant it.

Reuse decision: reuse the existing provider registry and R6C authority as
unchanged owners. Add one isolated typed professional contract only; do not
replace or widen the legacy boolean `ProviderCapabilities` metadata before an
accepted migration slice exists.

Frozen P1 state vocabulary:

```text
technical support: supported | unsupported | conditional | unknown
runtime availability: available | gated | unavailable | conditional | unknown
provider projection: exposed | hidden | conditional
```

`ProviderModelCapabilities` contains only evidence-backed provider/model
technical claims. `RuntimeCapabilities` contains only LBE-owned capability
descriptors, including backend provenance, workspace/mode/permission
requirements, mutation and external-effect class, interactivity/streaming/
background/cancellation/parallelism support, schemas, evidence, and validation
types. `EffectiveSessionCapabilities` combines those layers deterministically
while keeping runtime availability and provider projection separate.

The only accepted R6C mapping is `ALLOW -> available`, `DENY -> unavailable`,
and `ESCALATE -> gated`. Unknown provider support hides provider projection; it
does not erase a direct LBE runtime capability or create authority.

## Completed P1 checkpoint

```text
phase: P1_PROFESSIONAL_CAPABILITY_CONTRACT
slice: FROZEN_TYPED_CAPABILITY_SEPARATION
base_sha: 09f719901e5459c6d70c2cc2a74552946ce56a4c
implementation_sha: fca8a2b746461ace80c41223c7610f509f234c45
requirements: separate typed provider technical support, runtime availability, and provider projection; preserve unknown; preserve R6C authority ownership
existing_owner: ProviderRegistry legacy metadata; R6C resolve_authorization(); existing governed execution and session owners
reuse_decision: isolated professional capability contract; no rewrite of legacy ProviderCapabilities and no new provider/tool authority
required_evidence_level: UNIT
validation_evidence: py_compile PASS; focused contract/registry/R6C tests PASS (34); full repository suite PASS (626); implementation gate PASS; git diff --check PASS
unverified: endpoint/model discovery; live provider support; provider selection; persisted projection; governed approval continuation; user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

P1 is complete at its required `UNIT` evidence level. This does not prove any
provider endpoint, feature advertisement, live tool-call projection, or user
flow. The next phase remains locked until a new exact P2 slice is registered.

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Completed P0 slice contract

Existing owners inspected:

- bounded provider transport: `OpenAICompatibleReasoningBackend` through
  `ProviderRegistry`;
- session/workspace authority: `SessionMemoryRuntimeBridge` and
  `WorkspaceMemoryStore`;
- governed execution: `GovernedAgentGateway`, `ToolExecutionContext`, and
  `GovernedToolOrchestrator`.

The active work is the frozen normalized provider-event contract required before
P1 capability projection, P2 negotiation, P3 provider streaming, persistence,
or continuation implementation. It must not add a provider transport, Cline
session, persistence, authorization, or tool-execution owner.

Required evidence level: `UNIT` for event identity and invalid-state rejection.
The contract must preserve distinct provider request/item/tool-call identities
and LBE call identity; runtime-operation and tool-receipt identities remain
absent until governed execution.

Frozen P0 vocabulary:

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
model.turn.requires_continuation
model.turn.completed
model.turn.incomplete
model.turn.refused
model.cancelled
model.error
```

The initial protocol families are `openai_responses`, `anthropic_messages`,
`gemini_interactions`, `gemini_generate_content`, `openai_compatible_chat`,
and `unknown`. `unknown` means the protocol family has not been proven; it
does not infer provider or model capability. Reasoning-summary events remain
distinct from message events, and `requires_tool` remains distinct from
`requires_continuation`. This P0 contract creates no provider transport,
capability projection, persistence, authorization, or tool execution owner.

## Frozen P0 semantic mapping

- OpenAI Responses maps function-call output-item lifecycle to tool-call start
  and completion, and maps function-call argument deltas only when emitted.
  Reasoning-summary text deltas/completion map to the distinct reasoning-summary
  events; reasoning item/part lifecycle stays provider metadata rather than
  fabricated user-facing text. Incomplete, refusal, and provider failure remain
  distinct terminal semantics.
- Gemini Interactions maps its interaction and typed step lifecycle without an
  invented wrapper. Function-call steps may produce tool-call start, argument
  delta, completion, and `requires_tool` semantics.
- Gemini GenerateContent remains separate. A complete `functionCall` maps to
  start then completion; it must not generate an arguments-delta event that the
  provider did not emit. Thought signatures and other continuation state remain
  provider metadata, never ordinary reasoning text.
- Anthropic `tool_use` maps to LBE client-tool work and `requires_tool`;
  `pause_turn` maps to the distinct `requires_continuation` semantic. Client
  `tool_result` content is continuation input after governed execution, never a
  provider-emitted `model.*` event.
- Provider-native, client-interrupt, transport-error, and runtime-policy
  terminal attribution must remain distinguishable in typed metadata. The P0
  contract does not claim every provider exposes every terminal state.

Tool results, runtime-operation IDs, tool receipts, session events, process
events, control events, persistence, and transcript projections remain outside
P0. P0 does not manufacture streaming, visible reasoning, partial arguments,
parallel calls, or server-side state when a provider did not emit/prove them.

## Completed P0 checkpoint

```text
phase: P0_PROVIDER_EVENT_NORMALIZATION
slice: FROZEN_NORMALIZED_EVENT_CONTRACT
base_sha: 004674f2a6fba19d3d18fe6f77f046ccae89e167
implementation_sha: 0c2d6e01925118fe11c0dae8c880e4099d5fd9ac
requirements: frozen event/protocol vocabulary; separate provider and LBE identities; invalid-state rejection; no premature runtime receipt identity
existing_owner: OpenAICompatibleReasoningBackend/ProviderRegistry transport; SessionMemoryRuntimeBridge/WorkspaceMemoryStore session authority; GovernedAgentGateway/ToolExecutionContext/GovernedToolOrchestrator execution authority
reuse_decision: native typed vocabulary only; no Cline or provider transport dependency added; deferred P3 Cline decision remains NATIVE at the evaluated pin
required_evidence_level: UNIT
validation_evidence: py_compile PASS; focused provider tests PASS (39); full repository suite PASS (621); implementation gate PASS; git diff --check PASS
unverified: provider-native live-wire mappings; provider streaming; persistence; continuation; runtime tool execution; user-flow acceptance
document_conflicts: none in the active gate
status: PASS
```

P0 is complete at its required `UNIT` evidence level. This is not proof of
provider I/O, live streaming, governed execution, persistence, TUI behavior,
or user readiness. The next phase remains locked until a new exact slice is
registered in both the governance state and this record.

Explicit user authorization is recorded for this implementation. Architecture
changes remain disabled until the decision checkpoint is `PASS`.

## Deferred P3 decision evidence

Exact evaluated dependency: `@cline/llms@0.0.73` in an isolated temporary
installation. The installed package identity matched the pin and exposed
`./dist/index.js`; its package metadata did not declare a license value.

Dependency audit result: `FAIL` for production adoption at this pin. The
resolved tree reports one high and one moderate vulnerability, including the
transitive `undici` dependency. No package lockfile or sidecar dependency was
added to canonical LBE.

Decision: `NATIVE`. The Cline lower layer remains useful comparison evidence,
but this exact package must not become the production P3/P7 dependency while
the dependency/license gate fails. Existing LBE provider and governed-execution
owners remain unchanged.

The Cline evaluation remains evidence for the later P3 decision. No provider
transport implementation is active until P0, P1, and P2 are accepted and a
new exact P3 slice is registered with an existing-owner audit and required
runtime evidence.

## Completed governance-lock baseline

- canonical repository: `Letterblack0306/LBE_Presistent_Agent_wall`
- canonical branch: `main`
- base commit before this gate: `2ae2fd09676e9647410a0e6805e37fa312faec63`

## Required behavior

- implementation/delivery only from the primary worktree on `main`;
- pushes only to `origin/main`;
- no implementation commits from secondary worktrees;
- no new branches/worktrees for implementation;
- one active implementation slice at a time;
- existing owner inspection before implementation;
- reuse/adaptation evaluation before new parallel implementation;
- architecture changes blocked without explicit user authorization and prior documentation update;
- next phase remains locked until the current slice has a checkpoint classified `PASS` at the required evidence level.

## Evidence level for this slice

Required: `INSTALLED_LOCAL_GIT_GUARD`

Repository-side evidence included by this change:

- `.lbe/governance/workspace-lock.json`;
- `.lbe/governance/implementation-gates.json`;
- `.githooks/pre-commit`;
- `.githooks/pre-push`;
- `scripts/check-implementation-gate.py`;
- `scripts/enable-workspace-lock.ps1`;
- `docs/governance/WORKSPACE_AND_IMPLEMENTATION_PROGRESSION_LOCK.md`.

The local installer was run from the canonical primary worktree:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/enable-workspace-lock.ps1
```

The hook path resolves to the canonical primary `.githooks` directory even
when evaluated from an older secondary worktree. The real primary-main commit
and `origin/main` push passed their hooks. Direct execution of the resolved
secondary-worktree pre-commit and pre-push hooks rejected the non-main branch.

GitHub remote enforcement is active as repository ruleset
`20882121` (`LBE main-only remote ref lock`): all refs except existing `main`
are subject to creation and update restrictions with no bypass actor. A direct
GitHub API attempt to create `refs/heads/__lbe_workspace_lock_probe__` was
rejected with HTTP 422; a read-back returned HTTP 404, proving no probe ref was
created.

## Completed checkpoint

```text
phase: GOVERNANCE_LOCK_BASELINE
slice: MAIN_ONLY_AND_CHECKPOINT_ENFORCEMENT
base_sha: 2ae2fd09676e9647410a0e6805e37fa312faec63
implementation_sha: 3abafd9277e3de9cb3cb27a2da950699c47e441f
requirements: primary main only; origin/main only; local hooks; remote non-main ref lock
existing_owner: Git worktree/ref enforcement plus GitHub repository rulesets
reuse_decision: reuse Git hooks and GitHub branch rulesets; no parallel enforcement owner
required_evidence_level: INSTALLED_LOCAL_GIT_GUARD plus remote API enforcement
validation_evidence: installer PASS; primary pre-commit PASS; primary pre-push PASS; secondary hook rejection; GitHub API HTTP 422/404 probe
unverified: none for this baseline
document_conflicts: none
status: PASS
```

## Current classification

- repository implementation: `PASS`
- local hook installation: `PASS`
- non-main/secondary-worktree local rejection: `PASS`
- remote GitHub ruleset preventing non-main API ref creation/update: `PASS`
- next phase: `LOCKED PENDING EXPLICIT ACTIVATION`

No next phase is active until its exact plan/slice, existing-owner audit, reuse
decision, and evidence level are recorded in the governance state.
