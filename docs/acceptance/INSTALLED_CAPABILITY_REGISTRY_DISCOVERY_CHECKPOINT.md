# Installed Capability Registry Discovery Checkpoint

Status: **PASS**

Validated implementation head:

`151136089b63fd9470d3a581a6ad6419cf567595`

## Scope proven

The LBE product now has one persisted installed-capability inventory for MCP, plugin, subagent, network, and hosted-service integrations. Registry discovery/configuration is metadata-only and does not create a second executor or bypass governed dispatch.

Proven properties:

- schema-versioned installed capability registry;
- five supported integration kinds are classified;
- duplicate and malformed configuration is denied;
- plaintext credential fields are rejected from persisted configuration;
- unavailable/disabled integrations project without executing adapters;
- configured entries convert only into the existing `ExternalCapabilityRegistration` contract;
- provider-controlled endpoint, executable, shell, command, argv, URL, and transport selection remains unavailable;
- concrete execution still requires the existing ToolRegistry / R6C authorization / R6E orchestration path;
- product commands expose bounded registry inspection/validation only;
- no second session, authorization, execution, receipt, evidence, or completion owner was introduced.

## LoopTool validation

```text
COMMAND HASH = F76DA642DAA71A9CCE6385710D4122AD30699A9B7B4B711578B2461B21D62E90
MACHINE_BINDING = PASS
focused registry regression = 71 passed in 1.40s
full regression = 760 passed in 207.36s
INSTALLED_CAPABILITY_REGISTRY_DISCOVERY = PASS
HEAD = 151136089b63fd9470d3a581a6ad6419cf567595
branch = main...origin/main
local exception = ?? lbe-tui/ (reference-only, untouched)
```

An earlier V1 acceptance command failed before tests because its Python ledger assertion used a backtick delimiter that was altered by the PowerShell/command envelope. That result is not an implementation failure. V2 removed the ambiguous delimiter and produced the decisive PASS above.

## Boundary preserved

```text
installed registry / product projection
        -> ExternalCapabilityRegistration
        -> ToolRegistry
        -> R6C authorization
        -> R6E approved adapter
        -> ToolReceipt / evidence
```

Discovery and projection do not authorize or execute integrations.

Publication remains paused.
