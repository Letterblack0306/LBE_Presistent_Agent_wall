# Complete LBE TUI Implementation Gate

Status: **OPEN — EXPLICIT USER AUTHORIZATION — PUBLICATION PAUSED**

phase: `COMPLETE_TUI_IMPLEMENTATION`

active slice: `TUI_PROVIDER_MODEL_CONFIGURATION_AND_HEALTH`

required evidence level: `SOURCE_PLUS_INSTALLED_INTERACTIVE_RUNTIME_PROOF`

## Authorization and precedence

The user explicitly authorized building the complete LBE TUI and required GitHub to be the implementation authority. LoopTool/local execution is evidence-only and must not patch source.

This gate pauses, but does not mark PASS or erase, the earlier `PUBLICATION_VERSION_PREPARATION` gate. Publication, tagging, release creation, and package publication remain forbidden during this gate.

## Product contract

The TUI is one keyboard-first control and projection client over the existing LBE runtime. It must not become a second owner of sessions, provider state, authorization, execution, receipts, evidence, recovery, or completion.

The complete installed workflow must support:

1. create, open, resume, navigate, and inspect persisted sessions;
2. inspect, select, configure, and health-check provider/model profiles through existing owners;
3. submit objectives and steer, interrupt, or cancel active turns;
4. render structured model, tool-call, authorization, ToolReceipt, evidence, validation, failure, and completion events;
5. render bounded diff and evidence detail views from persisted runtime truth;
6. inspect registered capabilities and integrations without executing them directly;
7. expose truthful unavailable, loading, empty, denied, failed, cancelled, and completed states;
8. preserve one execution path through existing governed runtime owners.

## Existing owners to reuse

- `SessionMemoryRuntimeBridge`, `SessionOperationalHistory`, and existing session/recovery stores;
- provider registry, user state, credential-reference, provider health, and provider-turn runtime;
- R6C authorization and R6E `GovernedToolOrchestrator` / `ToolReceipt`;
- persisted operational events and deterministic completion/validation owners;
- `terminal_projection.py` and `textual_tui.py` as projection/client owners.

## Required implementation sequence

1. Typed, persisted TUI view models for session, provider, capability, tool, authorization, receipt, evidence, diff, validation, failure, and completion states.
2. One objective/activity workspace with spatially stable focus and progressive disclosure.
3. Real command routing for status, provider, evidence, help, interrupt, and cancel; commands must not alias unrelated help output.
4. Session/history navigation and create/resume flow.
5. Provider/model selection, configuration, and health surfaces using existing provider owners.
6. Structured activity, receipt, authorization, evidence, validation, and diff detail views.
7. Capability/integration inspection and truthful unsupported-state handling.
8. Installed interactive acceptance with a local provider and governed tool turn.
9. Compatibility and regression acceptance.

## Interaction and visual requirements

- keyboard-first interaction with visible focus and discoverable commands;
- consistent layout at 80x24 and graceful resize behavior;
- progressive disclosure rather than raw JSON as the primary view;
- monochrome usable, 16-color readable, and truecolor enhanced;
- semantic colors with no color-only meaning;
- respect `NO_COLOR`;
- avoid unsupported Unicode glyphs and provide ASCII-safe borders/symbols;
- no flicker, blocking provider call on the UI thread, or uncontrolled log scrolling;
- help must expose universal navigation, view actions, and contextual actions.

## Active slice

### TUI_PROJECTION_CONTRACT_AND_VIEW_MODELS — PASS

Question:

> Can the existing persisted runtime events and owners be projected into typed TUI states without introducing a second runtime or inventing unavailable evidence?

Allowed implementation paths:

- `lbe_guard_inspector/terminal_projection.py`
- `lbe_guard_inspector/textual_tui.py`
- a bounded TUI view-model module under `lbe_guard_inspector/`
- focused terminal/TUI tests
- this gate and machine-gate evidence

Required proof:

- owner/event mapping documented in tests;
- typed projection for every state required by the first sequence item;
- unknown/missing payloads render truthfully;
- no execution, authorization, or completion decisions occur in projection code;
- focused tests pass;
- `git diff --check`.

Checkpoint evidence:

- GitHub revision: `72aa6834871cb17ee68ee74367749440c9c0e0cc`;
- focused projection tests: `9 passed`;
- `git diff --check`: PASS;
- installed interactive acceptance remains pending and is not claimed by this checkpoint.

### TUI_OBJECTIVE_ACTIVITY_WORKSPACE — PASS

Question:

> Can the typed persisted projections be presented in one stable keyboard-first objective/activity workspace without blocking the UI thread or inventing runtime state?

Required proof:

- stable header, objective, activity stream, composer, command/status, and detail regions;
- deterministic focus and progressive disclosure;
- truthful empty, idle, active, failed, cancelled, and completed rendering;
- 80x24 and resize coverage at the source/test level;
- ASCII-safe primary symbols and no color-only meaning;
- focused Textual and terminal projection tests pass;
- `git diff --check`.

Checkpoint evidence:

- GitHub revision: `15c41d9f781fd197ea8cc51779d285baf0068ded`;
- focused TUI/projection tests: `14 passed`;
- 80x24, alternate size, focus, progressive details, persisted states, and `NO_COLOR` source behavior covered;
- `git diff --check`: PASS;
- installed interactive acceptance remains pending.

### TUI_COMMAND_ROUTING — PASS

Question:

> Do `/status`, `/provider`, `/evidence`, `/help`, `/interrupt`, and `/cancel` route to distinct truthful behavior while preserving the existing runtime/control owners?

Required proof:

- status, provider, evidence, and help produce distinct bounded projections;
- interrupt and cancel route through `PersistentTurnControl` during an active turn;
- unknown commands fail truthfully without creating runtime events;
- no command handler becomes an execution, provider, session, or evidence authority;
- focused tests pass;
- `git diff --check`.

Checkpoint evidence:

- GitHub revision: `00265ab3d6590a5dad716905507e05077ee9af1d`;
- focused TUI/projection tests: `15 passed`;
- all six commands exercised through the Textual input surface;
- `git diff --check`: PASS;
- installed interactive command acceptance remains pending.

### TUI_SESSION_NAVIGATION_AND_RESUME — PASS

Finding:

The canonical `WorkspaceMemoryStore` can load one session but has no public bounded session-list operation. Session navigation must add that query to the existing store rather than query SQLite from the TUI or create a second session registry.

Required proof:

- bounded session listing through `WorkspaceMemoryStore`;
- create through `SessionMemoryRuntimeBridge` and resume through persisted `SessionState`;
- navigation changes only the client projection target;
- active-turn transitions fail closed;
- focused store/session/TUI tests pass;
- `git diff --check`.

Checkpoint evidence:

- GitHub revision: `7bf75acc6d50915bebf5564698dda22dedd9d0c7`;
- focused store/session/TUI/projection tests: `18 passed`;
- create, list, resume, projection switch, and active-turn boundary covered;
- `git diff --check`: PASS;
- installed interactive session acceptance remains pending.

### TUI_PROVIDER_MODEL_CONFIGURATION_AND_HEALTH — OPEN

Question:

> Can provider/model selection and health be controlled from the TUI through existing provider and session owners without persisting or rendering credential values?

Required proof:

- registered provider/model selection delegates to `SessionMemoryRuntimeBridge.configure_session`;
- health delegates to `check_provider_health` with explicit configuration;
- unconfigured health is truthful and non-mutating;
- provider config and credential values are never rendered or persisted by the TUI;
- focused provider/session/TUI tests pass;
- `git diff --check`.

## Final acceptance

- exact GitHub revision and clean installed artifact identified;
- real Windows Terminal launch and render captured;
- all six commands exercise distinct truthful behavior;
- session create/resume/navigation proven;
- provider select/check proven without credential leakage;
- one governed local-provider tool turn renders proposal, decision, receipt, evidence, diff where applicable, continuation, and deterministic completion;
- interrupt and cancel proven during an active turn;
- 80x24, resize, monochrome, 16-color, truecolor, and `NO_COLOR` behavior checked;
- no unexplained runtime errors or false completion;
- full focused and relevant regression suites pass.

## Forbidden

- patching source through LoopTool;
- creating a second runtime, event store, session owner, provider owner, dispatcher, authorization path, receipt type, or completion owner;
- TUI-direct filesystem, shell, Git, network, MCP, plugin, or provider mutations;
- treating static source, labels, screenshots, mocks, or unit tests alone as installed runtime proof;
- publication, tagging, release creation, or package publication;
- unrelated architecture or capability expansion.
