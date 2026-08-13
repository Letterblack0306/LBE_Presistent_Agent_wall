# Professional Agent Runtime P0/P1 Acceptance Record

Status: **ACCEPTED — P2 AUTHORIZED**
Accepted: 2026-08-13

This record freezes the P0 provider-event normalization contract and P1 professional runtime capability contract for the next implementation phase.

Authoritative inputs:

- `docs/design/PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_CANONICAL_IMPLEMENTATION_PLAN.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_P0_P1_IMPLEMENTATION_GATE.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_P0_P1_PROVIDER_MAPPING_AND_AUTHORIZATION_CORRECTIONS.md`
- `docs/design/PROFESSIONAL_AGENT_RUNTIME_P0_P1_FINAL_RECONCILIATION_PATCH.md`
- current feature-branch source owners, especially provider registry/transport, R6C authorization, governed tool orchestration, and session/workspace persistence.

## Accepted P0 contract

P0 is accepted with these invariants:

- provider/model events remain separate from runtime/tool/process/control/validation events;
- initial protocol families distinguish `openai_responses`, `anthropic_messages`, `gemini_interactions`, `gemini_generate_content`, and `openai_compatible_chat`;
- OpenAI function-call mapping uses output-item lifecycle plus function-call argument delta/done events;
- OpenAI reasoning-summary part lifecycle is distinct from reasoning-summary text delta/done events;
- Gemini Interactions and GenerateContent remain separate protocol families;
- Gemini thought/provider continuation state is not automatically user-visible reasoning;
- Anthropic `tool_use` means client/LBE tool execution, while `pause_turn` means provider/server continuation;
- client-supplied tool/function results are provider continuation input after LBE execution, not `model.*` runtime events;
- `model.turn.requires_tool` and `model.turn.requires_continuation` are distinct semantics;
- durable `lbe_call_id` remains distinct from provider request/item/tool-call IDs;
- no streaming/reasoning/tool-argument/parallelism capability may be fabricated when a selected provider/model/backend does not prove it.

## Accepted P1 contract

P1 is accepted with these invariants:

- `ProviderModelCapabilities`, `RuntimeCapabilities`, and `EffectiveSessionCapabilities` are distinct layers;
- technical support uses `SUPPORTED | UNSUPPORTED | CONDITIONAL | UNKNOWN`;
- effective runtime availability uses `AVAILABLE | GATED | UNAVAILABLE | CONDITIONAL | UNKNOWN`;
- runtime availability and provider projection are separate dimensions;
- provider projection may be `EXPOSED | HIDDEN | CONDITIONAL` and never represents provider authority;
- provider outage or lack of client tool-call support may hide projection but must not erase direct LBE runtime capabilities;
- existing `lbe_guard_inspector/runtime/authorization_resolver.py::resolve_authorization()` remains the authority owner;
- `ALLOW -> AVAILABLE`, `DENY -> UNAVAILABLE/denied`, `ESCALATE -> GATED`;
- no new rule such as `write_allowed -> always GATED` is introduced;
- backend provenance, workspace binding, mode requirements, mutation/external-effect classes, streaming/interactivity/background/cancellation support, schemas, evidence, validation, and provider projection must be representable by the professional capability model;
- JSONL remains projection/export/transport, not a second session-history authority;
- live stdout/stderr claims require a real streaming process backend.

## P2 authorization

P2 may now proceed as bounded implementation slices.

The first authorized slice is the conservative provider/model capability discovery substrate:

```text
configured provider + endpoint + selected model
        ↓
protocol-family evidence
        +
explicit typed capability evidence
        ↓
ProviderModelCapabilities snapshot
```

Rules for the first slice:

- unproven professional features remain `UNKNOWN`;
- do not infer model capability from provider brand alone;
- do not reinterpret the legacy bounded adapter flags `streaming=False/tool_calls=False` as universal model incapability;
- do not grant workspace authority;
- do not alter R6C authorization;
- do not alter runtime capability ownership;
- do not start provider-native streaming or tool continuation yet;
- retain the accepted bounded 0.2.1 provider path as a regression-compatible foundation.

## Acceptance evidence required for P2A

P2A passes only when local verification proves:

1. the new capability-discovery tests pass;
2. existing provider registry tests pass unchanged;
3. existing provider health tests pass unchanged;
4. an OpenAI-compatible endpoint is classified by protocol syntax without claiming tool or streaming support;
5. explicit typed capability evidence can set a claim without creating workspace permission/authorization fields;
6. conditional support requires an explicit reason;
7. unrecognized endpoints remain protocol `UNKNOWN`;
8. changing selected model changes snapshot identity without manufacturing capabilities;
9. the broader regression suite does not show a P2A-caused failure.

## Final rule

> **P0/P1 are frozen. P2 may implement capability truth, not authority. Unknown remains unknown until evidence proves otherwise, and every later provider projection remains subordinate to LBE runtime authority.**
