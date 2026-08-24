# Priority Knowledge — LBE Module Registry

## Status

This document is a priority architecture contract for the persistent agent and workspace runtime.

The module registry is the canonical inventory of every functional production module in a workspace. Agents must consult the registry before reconstructing the runtime from imports, filenames, or broad source inspection.

## Core invariant

Every functional module is registered.

Every loaded module emits a runtime receipt.

Every running module reports its current activity.

Every declared dependency references another registered module.

Registered modules that did not load remain visible.

Loaded modules that were not registered are blocking defects.

The registry exists primarily to expose:

- module inventory;
- load state;
- runtime activity;
- dependency relationships;
- instance conflicts;
- failures and runtime evidence.

## Purpose

The registry must answer directly:

- What modules exist?
- Where are they located?
- What does each module do?
- Was it loaded?
- Who loaded it?
- Is it currently running?
- What action is it performing?
- Did it fail?
- Which other modules does it use?

The workspace must not require agents to search imports, inspect unrelated files, or manually reconstruct the runtime merely to answer these questions.

## Registration contract

Every production module must declare itself with a compact descriptive record.

```js
moduleRegistry.register({
  id: 'browser.loop-controller',
  path: 'src/system/LoopController.js',
  type: 'controller',
  purpose: 'Reads completed provider turns and sends them to the local agent.',
  provides: [
    'browser.loop.start',
    'browser.loop.stop',
    'browser.turn.poll',
    'browser.result.deliver'
  ],
  dependsOn: [
    'browser.chat-bridge',
    'agent.service'
  ],
  loadedBy: 'app.launcher',
  expectedProfiles: ['production', 'test']
});
```

Registration describes the module. It must not contain a large policy document.

## Required declaration fields

```json
{
  "id": "browser.loop-controller",
  "path": "src/system/LoopController.js",
  "type": "controller",
  "purpose": "Polls completed browser turns and dispatches them to the local agent.",
  "provides": [],
  "dependsOn": [],
  "loadedBy": "app.launcher",
  "expectedProfiles": ["production"]
}
```

| Field | Meaning |
|---|---|
| `id` | Stable module identifier |
| `path` | Workspace-relative source path |
| `type` | Service, controller, provider, adapter, UI, registry, tool, or store |
| `purpose` | Plain description of what the module does |
| `provides` | Capabilities exposed by the module |
| `dependsOn` | Other registered modules it requires |
| `loadedBy` | Module responsible for loading it |
| `expectedProfiles` | Runtime profiles where it should load |

## Runtime lifecycle receipts

When instantiated:

```js
moduleRegistry.loaded('browser.loop-controller', {
  instanceId: 'loop-controller-1'
});
```

When starting work:

```js
moduleRegistry.started('browser.loop-controller');
```

When performing an action:

```js
moduleRegistry.activity('browser.loop-controller', {
  action: 'provider-turn.poll',
  detail: 'Waiting for a completed browser turn'
});
```

When stopping:

```js
moduleRegistry.stopped('browser.loop-controller', {
  reason: 'Stopped by user'
});
```

When failing:

```js
moduleRegistry.failed('browser.loop-controller', {
  code: 'PROVIDER_CONNECTION_LOST',
  error: 'Provider target disconnected'
});
```

## Live module record

```json
{
  "id": "browser.loop-controller",
  "path": "src/system/LoopController.js",
  "type": "controller",
  "purpose": "Polls browser turns and dispatches them to the local agent.",
  "registered": true,
  "loaded": true,
  "running": true,
  "healthy": true,
  "loadedBy": "app.launcher",
  "instanceCount": 1,
  "provides": [
    "browser.loop.start",
    "browser.loop.stop",
    "browser.turn.poll",
    "browser.result.deliver"
  ],
  "dependsOn": [
    "browser.chat-bridge",
    "agent.service"
  ],
  "currentActivity": {
    "action": "provider-turn.poll",
    "detail": "Waiting for a completed browser turn",
    "startedAt": "2026-07-28T00:10:00.000Z"
  },
  "lastError": null,
  "loadedAt": "2026-07-28T00:09:31.000Z",
  "updatedAt": "2026-07-28T00:10:00.000Z"
}
```

## Watcher contract

Two modules form the registry layer:

- `module.registry`
- `module.watcher`

The watcher reads registration and lifecycle events. It must not infer module behavior by guessing.

```js
moduleWatcher.watch({
  onRegistered(module) {},
  onLoaded(module) {},
  onStarted(module) {},
  onActivity(module, activity) {},
  onStopped(module) {},
  onFailed(module, error) {}
});
```

## Module states

Each module has one clear state:

- `REGISTERED`
- `NOT_LOADED`
- `LOADED`
- `RUNNING`
- `IDLE`
- `BLOCKED`
- `FAILED`
- `STOPPED`
- `DISABLED`

Example:

```text
browser.chat-bridge       RUNNING
browser.loop-controller   IDLE
agent.service             RUNNING
llm.provider-registry     RUNNING
llm.lm-studio-adapter     BLOCKED
renderer.main             RUNNING
watcher.controller        STOPPED
```

## Registry view

The UI should expose a direct table:

| Module | Purpose | State | Current activity | Loaded by |
|---|---|---|---|---|
| `app.launcher` | Starts the runtime | Running | Serving runtime | Process entrypoint |
| `browser.chat-bridge` | Connects to provider chat | Running | Connected to ChatGPT tab | `app.launcher` |
| `browser.loop-controller` | Watches provider turns | Idle | Waiting for completed turn | `app.launcher` |
| `agent.service` | Runs local agent sessions | Running | Waiting for instruction | `app.launcher` |
| `llm.provider-registry` | Selects reasoning provider | Running | LM Studio selected | `agent.service` |
| `llm.lm-studio-adapter` | Sends requests to LM Studio | Blocked | Provider timeout | Provider registry |

A module detail view should show:

- source path;
- purpose;
- capabilities;
- dependencies;
- loader;
- instances;
- current activity;
- recent activity;
- last error;
- runtime evidence.

## Required registry defects

### `MODULE_UNREGISTERED`

Raised when a production-loaded module has no declaration.

### `REGISTERED_NOT_LOADED`

A declared module was not loaded. This remains visible but is not automatically a failure.

### `EXPECTED_MODULE_NOT_LOADED`

Raised when a module expected for the active runtime profile did not load.

### `MODULE_DEPENDENCY_UNREGISTERED`

Raised when a module declares or uses a dependency absent from the registry.

### `MODULE_INSTANCE_CONFLICT`

Raised when a singleton module has multiple active instances.

Different modules may cover related functionality if they have separate IDs and purposes. For example:

- `browser.chrome-launcher`
- `browser.chrome-health-check`
- `browser.chrome-status-projection`

The registry makes their distinctions visible instead of assuming that repeated Chrome-related functionality is a duplicate defect.

## Declaration versus runtime receipt

The registry compares two evidence sources.

### Declared module

What the workspace says should exist:

```json
{
  "id": "browser.loop-controller",
  "path": "src/system/LoopController.js",
  "expectedProfiles": ["production"]
}
```

### Runtime receipt

What actually loaded:

```json
{
  "id": "browser.loop-controller",
  "instanceId": "loop-controller-1",
  "loaded": true,
  "loadedBy": "app.launcher"
}
```

Expected comparisons:

| Declaration | Runtime | Result |
|---|---|---|
| Registered | Loaded | Healthy |
| Registered | Not loaded | Visible missing module |
| Not registered | Loaded | Blocking defect |
| Disabled | Loaded | Blocking defect |
| Registered singleton | Two instances | Conflict |

## Start Loop evidence example

After clicking **Start Loop**, the registry should immediately expose the runtime chain:

```text
renderer.main
  activity: command browser.loop.start requested

agent.http-server
  activity: POST /api/agent/start

browser.loop-controller
  state: RUNNING
  activity: Connecting to browser bridge

browser.chat-bridge
  state: RUNNING
  activity: Validating provider tab

browser.loop-controller
  activity: Recording startup baseline

browser.loop-controller
  activity: Waiting for completed browser turn
```

If the route also resumes an agent session, that must appear separately:

```text
agent.session-runtime
  activity: Resuming persistent session
```

This exposes hidden coupling without requiring source-code investigation.

## Agent priority rule

For questions about runtime inventory, load state, active behavior, dependencies, module failures, or duplicate instances, the agent must:

1. read the module registry;
2. read watcher and lifecycle receipts;
3. compare declarations with runtime state;
4. report registry defects and missing evidence;
5. inspect source only when the registry is absent, contradictory, incomplete, or when exact implementation evidence is explicitly required.

The agent must not treat import search or broad file inspection as the primary way to discover module existence or runtime behavior once the registry is available.

## Scope boundary

The registry is a visibility and runtime-evidence layer. Authority ownership may be added later as a separate field, but must not complicate the base registry contract.
