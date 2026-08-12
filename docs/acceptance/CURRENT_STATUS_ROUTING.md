# Current Status Routing

`docs/CURRENT_STATUS.md` is a historical July-era snapshot and must not be used by itself for current product, CLI, C5/R7, package, or npm-distribution decisions.

For current work, read in this order:

1. `README.md` — current CLI-first product identity and user-facing architecture.
2. `docs/IMPLEMENTATION_PLAN.md` — canonical runtime architecture and implementation sequence.
3. `docs/acceptance/C5_R7_ACCEPTANCE_RECORD.md` — accepted persistent-runtime V1 proof record.
4. `docs/acceptance/POST_V1_RELEASE_PACKAGE_READINESS.md` — Python package/install readiness.
5. `docs/acceptance/POST_V1_NPM_CONSUMER_DISTRIBUTION_READINESS.md` — npm bootstrap/public-consumer release evidence.
6. Before any CLI/TUI/operator-console implementation, read `docs/design/LBE_AGENT_RUNTIME_CLI_TUI_AND_TOOL_ACCESS_SPEC.md`.
7. current Git/source/runtime/registry evidence.

Current product routing is:

```text
npm / npx
  -> @letterblack/lbe
  -> thin Node bootstrap / launcher
  -> managed Python LBE runtime
  -> `lbe` CLI
```

The historical Guard Inspector service/read-only commands remain compatibility and implementation surfaces, but they are no longer the complete product identity or the primary user control surface.

Do not route new product work through old `lbe-core`/Core-package assumptions unless a specific historical component is actually in scope. The current persistent-agent control surface is the `lbe` CLI, while Python LBE remains the sole runtime/governance authority.

Do not start CLI/TUI implementation from generic dashboard assumptions. The primary user-facing surface must be a reference-derived agent runtime item stream with mutable tool invocation cells, runtime capability gating, and replayable session events.

When repository documentation disagrees with live Git/runtime/registry evidence, current evidence wins and the relevant current-status/acceptance document must be reconciled. Historical acceptance receipts should not be rewritten merely to modernize terminology.
