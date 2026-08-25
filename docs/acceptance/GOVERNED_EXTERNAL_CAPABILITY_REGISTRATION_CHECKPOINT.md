# Governed External Capability Registration Checkpoint

Status: **PASS**

Date: 2026-08-25

## Scope

Bounded complete-runtime slice `GOVERNED_EXTERNAL_CAPABILITY_REGISTRATION`.

This slice adds a registration contract for MCP, plugin, subagent, network, and hosted-service capabilities behind the existing LBE `ToolRegistry`, R6C authorization, R6E `GovernedToolOrchestrator`, `ToolReceipt`, provider continuation, session, and completion owners. It does not create a generic external executor or give the reasoning provider transport authority.

## Canonical implementation

```text
implementation HEAD = 02c761ab5ee969edd1c24fed65a6a2d343d20927
new runtime owner = lbe_guard_inspector/runtime/external_capabilities.py
focused tests = tests/test_external_capabilities.py + existing governed coding/orchestration/guidance tests
```

## Local LoopTool acceptance

```text
COMMAND HASH = E474AAD3D03DEC376BF69944FFA3F56251052D534D46369B27547A7E9F563859
MACHINE_BINDING = PASS
focused regression = 58 passed
full regression = 732 passed
HEAD = 02c761ab5ee969edd1c24fed65a6a2d343d20927
local exception = ?? lbe-tui/ (reference-only, untouched)
```

## Proven behavior

- all external capabilities are pre-registered by LBE before provider exposure;
- MCP, plugin, subagent, network, and hosted-service registrations are explicitly classified;
- provider-controlled raw endpoint, URL, transport, executable, argv, command, and shell selection is rejected;
- network and hosted-service registrations require explicit network metadata;
- external registrations become `ToolSpec` / `ToolHandler` entries in the existing `ToolRegistry`;
- R6C authorization occurs before adapter execution;
- executed and denied/failing requests return correlated `ToolReceipt` truth through existing orchestration;
- unregistered external tool requests fail closed;
- the provider still receives only LBE-generated tool definitions;
- no second executor, authorization, receipt, session, evidence, or completion owner was introduced.

## Existing transport boundary retained

Existing provider HTTP transport remains reasoning-provider transport. `LocalHttpTransport` remains localhost-only inspection/callback transport. Neither is promoted into arbitrary agent network authority.

## Preservation

`lbe-tui/` remained untracked/reference-only and untouched. No `lbe-core/`, runtime database/state, credential store, snapshot/backup, or protected local material was mutated by validation.

## Result

```text
GOVERNED_EXTERNAL_CAPABILITY_REGISTRATION = PASS
COMPLETE_LBE_AGENT_RUNTIME = OPEN
PUBLICATION = PAUSED
```

This checkpoint does not by itself activate the next product slice.
