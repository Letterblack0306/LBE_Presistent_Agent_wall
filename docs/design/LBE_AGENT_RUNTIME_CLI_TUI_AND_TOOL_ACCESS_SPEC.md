# LBE Agent Runtime CLI/TUI and Tool-Access Specification

Status: **AUTHORITATIVE DESIGN GATE — IMPLEMENTATION MUST NOT START WITHOUT THIS CONTRACT**
Updated: 2026-08-12

This document defines how LBE should expose an agent-facing CLI/TUI and how
providers receive access to runtime tools. It exists to prevent the repeated
mistake of designing a generic status dashboard or terminal control panel
instead of the user-facing runtime surface of an agent.

The current public npm package `@letterblack/lbe` remains a thin bootstrap and
launcher. The Python LBE runtime remains the only owner of sessions, provider
configuration, workspace identity, mode, permissions, governance, tool
authorization, evidence, validation, and completion.

---

## 1. Reference-derived product rule

The CLI/TUI must be derived from working agent runtimes, not from generic
dashboard assumptions.

Primary references:

- OpenAI Codex TUI/app-server:
  - ordered thread/turn/item lifecycle;
  - streaming agent message and reasoning items;
  - mutable command execution items;
  - command output deltas;
  - file-change items;
  - dynamic tool calls;
  - inline approval requests;
  - final item completion as the authoritative result.
- VS Code chat/agent:
  - a tool invocation is a stateful UI object;
  - states include streaming, executing, waiting for confirmation, cancelled,
    and completed/error states;
  - partial input, invocation messages, progress, and tool-specific data are
    part of the visible runtime object.
- CloudCLI / ClaudeCodeUI:
  - the UI is an external face over native agent sessions;
  - sessions, tools, file explorer, Git, and terminal are exposed without
    pretending to become the model/runtime itself;
  - tools are disabled by default and enabled selectively.
- Antigravity CLI:
  - terminal and GUI are two surfaces over one shared agent engine;
  - TUI is optimized for keyboard-first, remote, low-overhead operation;
  - permissions, command execution, multi-file editing, and persistent history
    are agent-engine features, not separate UI features.

Therefore:

```text
LBE runtime
  -> event stream / persisted session items
  -> CLI/TUI renderer
  -> future GUI renderer
```

Not:

```text
LBE runtime
  -> CLI-specific workflow engine
  -> GUI-specific workflow engine
```

---

## 2. Non-negotiable UI invariant

The primary surface is the **agent runtime conversation**, not a telemetry
dashboard.

The user must be able to watch:

1. user input;
2. assistant/agent commentary;
3. planning/reasoning summaries when policy allows;
4. tool calls appearing as active runtime cells;
5. live tool output or progress appended into the same cell;
6. tool completion, failure, cancellation, denial, or escalation;
7. agent reaction to that result;
8. continued tool use;
9. final validated response.

Do not build this as the primary screen:

```text
Provider: Healthy
Runtime: Running
Step 1: Complete
Step 2: Working
Evidence: 12
Validation: Pending
```

Those fields can exist as secondary chrome or detail panes, but they must not
replace the active agent session.

Correct primary shape:

```text
USER
Fix the provider registration issue and validate it.

AGENT
I will inspect the provider registry and the runtime composition path first.

● Reading lbe_guard_inspector/provider_registry.py
✓ Read provider_registry.py

● Searching default_provider_registry
  6 matches

AGENT
The provider IDs are registered, but composition still constructs only the
OpenAI-compatible backend. I am fixing the composition owner now.

● Editing lbe_guard_inspector/provider_registry.py
✓ Updated provider_registry.py

● Running python -m pytest -q tests/test_provider_registry.py
  ....................................
✓ 36 passed

AGENT
The provider path is now wired through the existing runtime owner. No session,
permission, or completion authority moved into the provider layer.
```

---

## 3. Runtime item model

Before any richer TUI work, LBE must expose or persist a stable ordered item
model. The names do not have to match Codex exactly, but the semantics must.

Required model:

```text
Session
  id
  workspace_identity
  provider_identity
  mode
  permission_profile
  status
  turns[]

Turn
  id
  session_id
  user_input
  status: in_progress | completed | failed | cancelled | blocked
  items[]
  started_at
  completed_at?
  token_usage?
  final_outcome?

Item
  id
  turn_id
  type
  status
  started_at
  completed_at?
```

Required item types:

```text
user_message
agent_message
reasoning_summary
plan
tool_call
command_execution
file_change
evidence_package
validation_run
completion_result
approval_request
error
```

The item lifecycle is:

```text
item.started
  -> zero or more item-specific deltas/progress events
  -> item.completed | item.failed | item.cancelled | item.declined | item.escalated
```

The final completed item is authoritative. Deltas are renderable progress, not
truth by themselves.

---

## 4. Tool-call cell model

A tool call must be a visible mutable cell, not a hidden backend event.

Required fields:

```text
tool_call_item:
  item_id
  call_id
  tool_id
  display_name
  namespace?
  mode_capability_required
  read_only_hint
  args_redacted_for_display
  args_hash
  status
  started_at
  duration_ms?
  progress[]
  live_output_chunks[]
  result_summary?
  receipt_id?
  evidence_refs[]
  error?
```

The renderer must append progress and live output into the existing item until
the item finalizes.

Related read/list/search calls may be grouped as an exploration cell when they:

- are read-only;
- belong to the same turn;
- are contiguous or share a planning/exploration phase;
- do not mutate the workspace;
- do not require separate approval.

Mutation, validation, browser action, provider check, and failed/escalated tool
calls should remain distinct unless a future design proves safe grouping.

---

## 5. Provider-to-tool access model

The provider never receives raw tool access.

Correct path:

```text
provider response
  -> bounded reasoning/tool proposal contract
  -> LBE request controller
  -> mode/capability resolver
  -> deterministic authorization
  -> governed tool dispatcher
  -> tool receipt/evidence
  -> validation/completion gate
  -> session item stream
```

Forbidden path:

```text
provider/model
  -> arbitrary tools
  -> workspace
```

Tool availability is calculated by LBE from:

- session mode;
- workspace identity;
- permission profile;
- project profile and optional guard packs;
- runtime policy;
- explicit user authorization;
- installed tool capabilities;
- credential/config availability;
- safety blockers.

The model/provider only sees the tool schema subset that LBE has made available
for that turn.

---

## 6. Capability registry

LBE must maintain a runtime capability registry separate from the provider
registry.

Provider registry answers:

```text
which reasoning adapters exist?
which model is selected?
how is provider HTTP transport shaped?
```

Tool/capability registry answers:

```text
which operations can this session perform?
under which mode?
with which permission?
with which evidence and validation requirements?
through which deterministic owner?
```

Minimum capability groups:

```text
workspace.read
workspace.search
workspace.inspect
workspace.replace_text
workspace.diff
git.status
git.diff
validation.run
session.checkpoint
session.resume
provider.check
browser.open
browser.snapshot
browser.click
browser.type
browser.submit
browser.download_metadata
```

Browser capabilities are not implicit. If browser tools are unavailable, the
runtime must report the capability gap rather than letting the model invent
browser observations.

---

## 7. Browser tool contract

The browser tool must follow an observed-state operating loop:

```text
check browser availability
list tabs
select or create target tab
snapshot before interaction
act using snapshot-derived target
snapshot after meaningful change
classify rendered outcome
continue or report exact blocker
```

The model or agent must not claim navigation, login, click, download, or form
submission success from a tool call alone. The rendered consequence must be
observed.

Manual blockers:

- login;
- CAPTCHA;
- two-factor authentication;
- payment confirmation;
- permission prompts;
- irreversible submissions;
- missing browser capability.

Completion evidence must include the observed profile/tab, final URL, visible
page state, important actions, and unresolved blockers.

---

## 8. Modes as runtime contracts

Do not implement modes as personalities.

```text
same provider/model
  + different LBE runtime contract
  = different behavior
```

### Audit / investigation mode

Default: read-only.

Allowed:

- inspect files;
- search workspace;
- read Git status/diff;
- produce findings;
- produce evidence packages;
- run non-mutating validation;
- report insufficiency.

Forbidden:

- modifying files;
- applying fixes;
- running write-capable tools;
- claiming proof without evidence;
- using indexed or historical facts as current truth.

### Coding mode

Allowed only under resolved permissions:

- inspect files;
- propose bounded edits;
- execute governed workspace mutation tools;
- run allowed validation commands;
- record receipts;
- validate completion.

Required:

- source-change evidence tied to executed receipt;
- before/after hashes for file edits;
- focused validation;
- Git-state reconciliation;
- completion gate outcome.

### Debug mode

Debug is not “free coding.”

It may inspect, reproduce, classify, and propose patches. Mutation requires the
same coding-mode capability resolution.

### Review mode

Read-only by default. It can inspect diffs and produce review findings. It must
not silently alter the workspace.

---

## 9. Tool exposure by mode

Initial matrix:

| Capability | Audit | Investigate | Coding | Review |
| --- | --- | --- | --- | --- |
| workspace.read | yes | yes | yes | yes |
| workspace.search | yes | yes | yes | yes |
| workspace.inspect | yes | yes | yes | yes |
| git.status | yes | yes | yes | yes |
| git.diff | yes | yes | yes | yes |
| workspace.replace_text | no | no by default | gated | no |
| validation.run | read-only only | read-only only | gated | read-only only |
| browser.open/snapshot | yes if configured | yes if configured | yes if configured | yes if configured |
| browser.click/type/submit | gated | gated | gated | gated |
| provider.check | yes | yes | yes | yes |
| session.checkpoint/resume | yes | yes | yes | yes |

The provider cannot expand this matrix.

---

## 10. Approvals and continuation

Approval requests are active turn items. They must render inline with the item
that triggered them and resolve back into the same turn.

If a user already authorized a larger objective and the next step is
non-destructive verification, the agent must continue automatically.

No extra prompt is required between:

```text
authorized write
  -> observe result
  -> retry bounded public/read-only verification
  -> install/smoke test
  -> evidence record
  -> final report
```

The runtime should stop only at:

- new destructive external action not covered by prior authorization;
- missing credential or account action;
- irreversible submission;
- human-only challenge;
- unsupported capability;
- policy denial/escalation;
- terminal success/failure.

---

## 11. TUI layout rule

The TUI layout should be:

```text
top chrome:
  workspace | mode | provider/model | permission profile | session

main:
  agent conversation / mutable runtime item stream

right/secondary drawer or toggle:
  plan
  evidence
  validation
  changed files
  diagnostics
  provider/config status

bottom:
  input composer + slash commands + interrupt hint
```

The status chrome is small. The transcript is primary.

Design direction:

- terminal-precise;
- keyboard-first;
- readable in SSH/remote sessions;
- compact but not cryptic;
- no decorative dashboard cards as the main experience;
- no fake workflow stepper.

Before visual implementation, create a `design.md` using a contextual design
selection process rather than defaulting to generic “dark terminal” styling.

---

## 12. Slash commands

The interactive CLI/TUI should expose explicit commands backed by existing
runtime owners:

```text
/help
/status
/mode
/provider
/model
/tools
/permissions
/workspace
/evidence
/validation
/diff
/checkpoint
/resume
/cancel
/compact
/browser
```

Commands must not bypass the runtime controller.

Example:

```text
/tools
  -> reads capability registry for current session
  -> displays available/gated/unavailable capabilities
  -> does not mutate policy

/permissions
  -> shows current permission profile and pending approvals
  -> permission changes go through LBE policy owner
```

---

## 13. Event API for future GUI and external clients

The same event model must support:

- non-interactive CLI;
- interactive TUI;
- future GUI;
- external integrations;
- automation/agent bridges.

Do not create a TUI-only state model.

Minimal API operations:

```text
session.create
session.resume
turn.start
turn.steer
turn.cancel
session.status
session.events.list
session.events.stream
provider.list
provider.check
capabilities.list
approval.respond
evidence.get
validation.get
```

Event records must be persistable and replayable.

---

## 14. Implementation sequence

### A. Research freeze

No implementation until this document and the reference-derived interaction
model are accepted as the gate.

### B. Runtime item/event contracts

Add typed contracts for session/turn/item lifecycle and tool-call updates.
Do not build the TUI yet.

### C. Instrument existing runtime

Map existing session, provider, request controller, tool orchestration,
completion evidence, validation, and provider-health paths into the event
model.

### D. Capability registry

Separate provider registry from capability registry. List available, gated, and
unavailable tools for the current session.

### E. Non-interactive event output

Add a command such as:

```text
lbe session events --format jsonl
```

or a turn-run mode that emits JSONL lifecycle events. Prove replay first.

### F. Transcript renderer

Implement a basic terminal renderer for the event stream:

- agent message;
- reasoning summary;
- tool started;
- tool progress;
- live output;
- tool completed/failed;
- approval request;
- final response.

### G. Interactive TUI

Only after event replay is proven, implement the interactive TUI. It consumes
the event stream and commands the runtime; it does not become another runtime.

### H. Browser tool integration

Only register browser capabilities when an actual browser tool backend exists.
Follow the observed-state loop defined above.

### I. End-to-end proof

Prove:

- audit mode read-only transcript;
- coding mode bounded edit transcript;
- validation transcript;
- provider switch without tool authority drift;
- browser unavailable blocker;
- browser available observed navigation;
- resume/replay of event history;
- public npm bootstrap launching the same runtime.

---

## 15. Anti-repeat blockers

Do not:

- build a dashboard-first TUI;
- implement provider-specific tool authority;
- let the model call raw shell/browser/filesystem directly;
- show only step cards instead of tool invocation cells;
- hide command output and file changes behind generic status labels;
- create a second session/controller for TUI;
- make browser claims without rendered observation;
- treat old indexed content as current workspace truth;
- add a CLI-only feature that future GUI cannot replay from events.

---

## 16. Acceptance criteria

The first CLI/TUI runtime slice is accepted only when:

```text
typed event contracts exist
existing runtime emits ordered session/turn/item events
tool invocations are visible and mutable while running
command/file/tool results finalize into authoritative item states
capability registry exposes available/gated/unavailable tools
provider switching does not change tool authority
audit mode cannot receive write tools
coding mode receives only governed write tools
browser capability is explicit and observable
event history can be replayed
TUI consumes events instead of owning runtime state
focused tests pass
full suite passes
package/install smoke passes
documentation records the final event contract
```

Until these conditions are met, do not claim a usable LBE agent TUI.

---

## 17. Current release boundary

This document does not reopen the accepted npm bootstrap or Python 0.2.1
runtime release candidate.

Next implementation should be a separate post-0.2.1 track:

```text
POST-V1 AGENT INTERACTION EVENT MODEL
```

That track starts with contracts and runtime event emission, not terminal
styling.
