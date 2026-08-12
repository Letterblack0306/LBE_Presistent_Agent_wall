# Current Status Routing

`docs/CURRENT_STATUS.md` is a historical July-era snapshot and must not be used by itself for current product, CLI, C5/R7, package, npm-distribution, or post-V1 professional-agent decisions.

## Active product priority

The main post-V1 product pillar is now:

`docs/design/PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md`

Status: **AUTHORITATIVE PRODUCT PILLAR — ACTIVE PRIORITY**

This pillar starts now. It defines the forward implementation priority for provider-native events, capability negotiation, professional tools, persistent agent interaction, terminal/process execution, Git/worktrees, agent-control protocol, MCP, IDE integration, and the eventual professional CLI/TUI.

The existing persistent runtime, C5/R7 acceptance, provider adapters, package release, npm bootstrap, and global project profiling remain accepted foundations. They must not be mistaken for the complete professional product.

For current work, read in this order:

1. `docs/design/PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md` — primary post-V1 product direction and implementation priority.
2. `docs/research/POST_V1_PROFESSIONAL_AGENT_CLI_PROVIDER_RUNTIME_RESEARCH.md` — provider/runtime/CLI research evidence underlying the pillar.
3. `docs/design/LBE_AGENT_RUNTIME_CLI_TUI_AND_TOOL_ACCESS_SPEC.md` — agent interaction and governed tool-access design gate.
4. `docs/design/LBE_AGENT_RUNTIME_USER_STEERING_EXTERNAL_CLIENT_AND_CONTROL_PROTOCOL_ADDENDUM.md` — active user steering, external-agent boundary, MCP vs control protocol, provenance.
5. `README.md` — current CLI-first product identity and user-facing architecture.
6. `docs/IMPLEMENTATION_PLAN.md` — established persistent-runtime architecture and implementation history; reconcile it with the professional-agent pillar for new post-V1 work.
7. `docs/acceptance/C5_R7_ACCEPTANCE_RECORD.md` — accepted persistent-runtime V1 proof record.
8. `docs/acceptance/POST_V1_RELEASE_PACKAGE_READINESS.md` — Python package/install readiness.
9. `docs/acceptance/POST_V1_NPM_CONSUMER_DISTRIBUTION_READINESS.md` — npm bootstrap/public-consumer release evidence.
10. current Git/source/runtime/provider/registry evidence.

Current distribution routing remains:

```text
npm / npx
  -> @letterblack/lbe
  -> thin Node bootstrap / launcher
  -> managed Python LBE runtime
  -> `lbe` CLI
```

The distribution path is not the complete professional-agent architecture. The professional runtime direction is:

```text
provider-native stream
  -> provider adapter
  -> normalized LBE model events
  -> persistent Session / Turn / Item runtime
  -> capability negotiation + LBE authorization
  -> governed professional tools
  -> live runtime/tool events
  -> provider continuation
  -> evidence / validation / completion
  -> agent-control protocol / MCP / IDE bridge
  -> CLI/TUI / GUI / IDE / automation / external agents
```

The historical Guard Inspector service/read-only commands remain compatibility and implementation surfaces, but they are no longer the complete product identity or the primary user control surface.

Do not route new product work through old `lbe-core`/Core-package assumptions unless a specific historical component is actually in scope. Python LBE remains the sole runtime/governance authority.

## Immediate implementation order

The next work is **not** TUI styling and not another shallow provider-name adapter.

Required active sequence:

```text
P0 provider event normalization contract
P1 professional runtime capability contract
P2 provider/model capability negotiation and probes
P3 provider-native streaming/tool-call adapters
P4 normalized Session / Turn / Item persistence
P5 professional workspace/Git/terminal capability foundation
P6 live tool/process execution events
P7 governed provider continuation loop
P8 bidirectional agent-control protocol
P9 replay/resume/fork proof
P10 MCP external-agent surface
P11 transcript projection
P12 professional interactive TUI
```

Later IDE/browser/external-agent acceptance work follows the pillar roadmap.

Do not start CLI/TUI implementation from generic dashboard assumptions. The primary user-facing surface must be the reference-derived live agent runtime stream with mutable tool invocation cells, user steering, truthful capability gating, live process output, and replayable session events.

When repository documentation disagrees with live Git/runtime/provider evidence, current evidence wins and the relevant current-status/design document must be reconciled. Historical acceptance receipts should not be rewritten merely to modernize terminology.

When a proposed post-V1 feature conflicts with `PROFESSIONAL_AGENT_RUNTIME_PRODUCT_PILLAR.md`, reconcile the documentation before implementation. Do not silently create a competing roadmap.