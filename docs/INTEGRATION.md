# Integration Guide

Use the same kit in each workspace. Change only the workspace-specific policy overlay and task scope.

## Brew

Set `workspace.name` to the Brew workspace identity. Keep memory/index databases, provider configuration, terminal execution, Git changes, and project-owned runtime files under the same scope model. A memory or index record is evidence/context; it must not become authorization merely by existing.

## Access Browser Agent

Govern browser-agent runtime source, provider configuration, workflow/runtime files, browser tooling, package entrypoints, shell/Git operations, and UI/runtime integration. Generated `PROJECT_INDEX.md`-style reports must remain observational only.

## LBE Wall / TUI

Govern Rust/TUI source, PTY/terminal integration, provider discovery/configuration, session state, Git operations, and packaging. TUI display state is not runtime proof; acceptance must observe the actual underlying effect.

## BirdEye

Default to read/index/hash/retrieval capability. Grant mutation only when a task explicitly requires BirdEye-owned state or schema changes. Retrieval metadata and historical context must not override current repository/runtime facts.

## Stronger enforcement

Git hooks are a commit/push boundary, not an exclusive host execution boundary. For stronger enforcement, mutation-capable filesystem, shell, Git, MCP, and adapter operations should call:

```text
node scripts/action-preflight.mjs <action> [target]
```

before execution, then record the actual effect and proof afterward.

For exclusive enforcement, disable all mutation routes that do not pass through the controller/LBE boundary.
