# Professional Agent Runtime Product Pillar

Status: **AUTHORITATIVE PRODUCT PILLAR — ACTIVE PRIORITY**
Updated: 2026-08-12

This document is the primary product-direction gate for all post-V1 LBE work involving providers, interactive agent execution, developer tools, CLI/TUI/GUI clients, external-agent integration, IDE integration, and professional coding workflows.

It promotes the findings in:

- `docs/research/POST_V1_PROFESSIONAL_AGENT_CLI_PROVIDER_RUNTIME_RESEARCH.md`
- `docs/design/LBE_AGENT_RUNTIME_CLI_TUI_AND_TOOL_ACCESS_SPEC.md`
- `docs/design/LBE_AGENT_RUNTIME_USER_STEERING_EXTERNAL_CLIENT_AND_CONTROL_PROTOCOL_ADDENDUM.md`

from supporting research/design into the main product pillar.

---

## 1. Product decision

The professional agent runtime is now the highest-priority post-V1 implementation track.

The accepted work completed before this pillar remains valuable foundation:

- persistent session/runtime ownership;
- workspace identity;
- mode/permission/governance composition;
- evidence and validation/completion contracts;
- governed coding execution;
- provider-neutral bounded reasoning;
- provider adapters for OpenAI, Anthropic, Gemini, and OpenAI-compatible endpoints;
- public npm bootstrap and managed Python runtime installation;
- global project-agnostic profiling.

However, these foundations are not the complete professional product by themselves.

They become useful to professional users only when composed into a real interactive agent runtime with truthful provider capability negotiation, live provider/tool event handling, professional developer capabilities, durable execution/session state, and a high-fidelity user-facing client.

Therefore:

> **Do not treat the existing CLI, current bounded provider adapters, package release, or static command surfaces as the product destination. They are foundations for the professional agent runtime.**

---

## 2. Primary product target

LBE is not intended to be only:

```text
API key
+ prompt
+ read/write/run-command tools
+ pretty terminal output
```

The target is:

> **A persistent, provider-neutral professional agent runtime whose CLI/TUI, IDE clients, automation clients, GUI clients, and external-agent integrations are high-fidelity surfaces over the same governed runtime state.**

The runtime must be suitable for professional software engineering work, including:

- large repositories and monorepos;
- multi-file changes;
- long-running tests/builds/dev servers;
- interactive terminal processes;
- local, routed, and hosted models;
- model/provider switching;
- Git and worktree workflows;
- code intelligence;
- persistent sessions, checkpoints, replay, fork/resume;
- explicit validation/evidence/completion;
- active user steering and interruption;
- external agent integration without governance overclaiming;
- IDE integration;
- machine-readable automation/control clients.

---

## 3. Main runtime architecture

The required product flow is:

```text
provider-native stream
        ↓
provider-specific adapter
        ↓
normalized LBE model-event stream
        ↓
LBE Session / Turn / Item runtime
        ↓
capability discovery + negotiation
        ↓
mode / permission / governance authorization
        ↓
governed professional tool dispatcher
        ↓
workspace / Git / terminal / validation / browser / IDE capabilities
        ↓
normalized runtime/tool event stream
        ↓
provider-specific continuation
        ↓
persistent evidence + validation + completion state
        ↓
agent-control protocol / MCP / IDE bridge
        ↓
CLI/TUI / GUI / IDE / automation / external agents
```

There remains one runtime owner.

Do not create a second CLI-owned, GUI-owned, IDE-owned, provider-owned, or external-agent-owned session/governance/completion system.

---

## 4. Provider support must become capability-aware

The current 0.2.1 provider adapters prove bounded transport/contract compatibility. They do not yet prove professional interactive-agent capability.

The professional provider layer must determine capability at:

```text
provider
+ endpoint
+ selected model
+ enabled/beta features where applicable
```

Do not infer professional capabilities from provider name alone.

The capability model must be able to represent, at minimum:

```text
protocol_family
streaming_text
streaming_reasoning_summary
reasoning_visibility
client_tool_calls
server_tool_calls
parallel_tool_calls
streamed_tool_arguments
strict_tool_schema
tool_choice_modes
structured_output
native_mcp
server_side_state
previous_response_or_interaction_state
context_window
max_output
image_input
file_input
cache_controls
usage_reporting
cancellation
provider_request_id
retryable_error_signals
```

Each capability must be able to report:

```text
supported
unsupported
unknown
conditional
```

Conditional support must carry a reason.

Provider capability is descriptive only. It never grants workspace authority.

---

## 5. Normalize semantics, not wire formats

OpenAI, Anthropic, Gemini, OpenRouter/local OpenAI-compatible endpoints, Ollama, LM Studio, and future providers do not expose one universal agent grammar.

LBE must preserve provider-specific behavior at the adapter boundary and normalize it into LBE-owned events.

Required normalized model-event direction:

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
model.turn.completed
model.turn.incomplete
model.turn.refused
model.error
```

Do not fake streaming, reasoning visibility, tool-call structure, parallelism, or server-side state when a provider/model does not actually support it.

Preserve provider-native metadata for diagnostics without coupling the renderer to provider wire objects.

---

## 6. Professional capability system

The professional product cannot be built around only:

```text
read file
write file
run command
```

Those are baseline capabilities only.

The runtime must grow a truthful professional capability registry.

### Workspace/code

```text
workspace.read
workspace.search
workspace.glob
workspace.inspect
workspace.diff
workspace.replace_text
workspace.apply_patch
workspace.symbols
workspace.definition
workspace.references
workspace.diagnostics
```

Semantic capabilities are advertised only when a real backend exists, such as an LSP, IDE bridge, parser, build system, or language service.

### Terminal/process

```text
terminal.exec
terminal.session.start
terminal.session.write
terminal.session.resize
terminal.session.interrupt
terminal.session.terminate
terminal.background.start
terminal.background.status
terminal.background.output
terminal.background.stop
```

The terminal layer must support true live output deltas and understand execution environment/shell family rather than requiring the provider to guess.

### Git/repository

```text
git.status
git.diff
git.log
git.show
git.branch
git.remote
git.blame
git.worktree.list
```

Governed mutations may include:

```text
git.stage
git.commit
git.branch.create
git.worktree.create
git.worktree.remove
```

Push, PR creation, publishing, releases, and deployments remain separately classified external mutations.

### Validation/evidence

```text
validation.run
validation.status
evidence.inspect
completion.status
```

### Browser

Browser tools are advertised only when a real browser backend exists.

### Session/runtime

```text
session.create
session.resume
session.fork
session.archive
session.export
session.checkpoint
session.compact
```

---

## 7. Professional terminal behavior is a first-class product requirement

A command tool that returns one final string is insufficient for professional workflows.

Required execution events include:

```text
command.started
command.stdout.delta
command.stderr.delta
command.progress
command.completed
command.failed
command.cancelled
```

Interactive and background processes must remain addressable through durable command/process identifiers.

The runtime must understand:

```text
Windows PowerShell
Windows cmd
Git Bash
WSL
POSIX sh/bash/zsh
containers
remote execution environments
```

where actually supported.

Do not assume POSIX shell behavior on Windows or vice versa.

---

## 8. Workspace and repository identity are persistent runtime truth

Workspace identity must never be reconstructed from model memory.

Required facts include:

```text
workspace_id
canonical_root
repository_root
repository_remote
VCS kind
branch/ref
HEAD/revision
dirty state
worktree identity
environment identity
allowed roots
project profile
```

If workspace identity is uncertain, inspect the bound workspace. Do not search unrelated drives or remembered repositories.

Large/multi-root workspaces must be explicit; sibling repositories never become implicit current-workspace truth.

---

## 9. Sessions are operational state, not chat logs

A professional session must persist enough state to resume real work:

```text
workspace/repository identity
provider/model and negotiated capabilities
runtime mode and permission profile
turn and item history
active terminal/background processes where resumable
changed-file set
Git/worktree state
authorization state
validation/evidence/completion state
context/compaction state
checkpoints
```

The runtime must support branching/resume patterns without requiring the user to reconstruct prior work manually.

---

## 10. User interaction is part of the control plane

The user is an active participant throughout execution.

The runtime distinguishes:

```text
new task
follow-up
active-turn steering
interrupt
cancel
approval response
runtime command
direct user tool action
```

A running turn should remain steerable when safe.

Runtime commands such as these must bypass model interpretation:

```text
/provider
/model
/mode
/tools
/permissions
/diff
/git
/validation
/processes
/context
/evidence
/checkpoints
/mcp
/logs
/compact
/interrupt
/cancel
```

---

## 11. User-facing surface

The primary user-facing surface is the live agent session, not an operations dashboard.

It must render the runtime truth:

```text
user input
agent commentary
reasoning summary when provider/policy permits
tool invocation
live tool/terminal output
file edit/diff
failure
agent reaction
approval when genuinely required
validation
final response
```

Tool invocation cells are mutable while in flight and finalize into replayable immutable records.

Professional secondary views are available on demand for:

```text
diff / changed files
Git/worktree state
plan/goals
evidence
validation/tests
background processes
capabilities/tools
provider/model diagnostics
token/context/cost/latency
session history/checkpoints
MCP/extensions
runtime logs
```

These views supplement the agent transcript; they do not replace it.

---

## 12. Public client surfaces

The same LBE runtime should eventually expose three complementary client boundaries:

```text
                    LBE runtime
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
 Agent Control       MCP Server      IDE Bridge
 Protocol
```

### Agent Control Protocol

For LBE-owned TUI/GUI/IDE/SDK/automation clients.

Controls sessions, turns, steering, interruption, cancellation, approvals, provider/model selection, permissions, capabilities, replay, and events.

### MCP Server

For external agents such as Codex, Gemini CLI, Cline, Claude Code, and compatible clients to discover/call LBE capabilities.

LBE only governs operations actually routed through LBE.

### IDE Bridge

For editor-native context and actions such as current selection, open files, reveal location, diagnostics, symbols, and diff presentation.

---

## 13. External-agent governance truthfulness

Two external-agent modes remain distinct.

### Cooperative attachment

The external agent retains native tools.

LBE governs only LBE-routed actions.

### Strict attachment

Overlapping native mutation/terminal/browser capabilities must be disabled, restricted, sandboxed, or routed through LBE before full LBE governance can be claimed.

Never claim:

```text
LBE MCP connected = whole external agent governed
```

---

## 14. Active implementation priority

This pillar starts now.

The next implementation work is not TUI styling and not another provider-name integration.

Required order:

```text
P0  provider event normalization contract
P1  professional runtime capability contract
P2  provider/model capability negotiation and probes
P3  provider-native streaming/tool-call adapters
P4  normalized Session / Turn / Item event persistence
P5  professional workspace/Git/terminal capability foundation
P6  live tool/process execution events
P7  provider continuation loop through governed tools
P8  bidirectional agent-control protocol
P9  durable replay/resume/fork proof
P10 MCP external-agent surface
P11 transcript projection/renderer
P12 professional interactive TUI
P13 IDE bridge / richer client integration
P14 browser capability integration
P15 cooperative and strict external-agent acceptance
P16 professional end-to-end acceptance
```

A phase may split into smaller vertical slices, but later phases must not be used to bypass missing earlier contracts.

---

## 15. Immediate deliverables

The first implementation track must produce, in order:

### Deliverable A — Provider Event Normalization Contract

Define:

- provider-native event mapping;
- normalized LBE model events;
- tool-call identity;
- argument streaming;
- reasoning-summary policy;
- completion/incomplete/refusal/error semantics;
- usage/request diagnostics;
- provider continuation contract.

### Deliverable B — Professional Runtime Capability Contract

Define:

- capability descriptor schema;
- availability/gated/unavailable/conditional states;
- backend provenance;
- mode/permission requirements;
- workspace binding;
- execution and mutation class;
- concurrency/parallelism properties;
- evidence/validation production;
- provider-visible tool projection.

No professional TUI implementation should begin before A and B are accepted and backed by focused tests/fixtures where code-level contracts exist.

---

## 16. What must not happen

Do not:

- build a decorative TUI first;
- add provider integrations that only change HTTP envelopes and call that professional agent support;
- assume every model behind one provider has identical tool/streaming capability;
- expose raw unrestricted shell/filesystem authority to providers;
- make the CLI own policy, session, validation, or completion truth;
- flatten provider-native event differences into lossy strings;
- fake capabilities not backed by installed/runtime evidence;
- reduce all developer operations to shell strings when structured capabilities provide stronger semantics/evidence;
- treat workspace identity as model memory;
- treat MCP attachment as proof that an external agent's native tools are governed;
- allow UI-specific state to become unreplayable runtime truth;
- report tool success as task completion without required validation/evidence.

---

## 17. Acceptance bar

The professional-agent pillar is not complete because a TUI renders successfully.

Acceptance requires evidence that:

1. at least the supported first-party provider families map their real stream/tool semantics into normalized LBE events without fabricated capabilities;
2. provider/model capability negotiation is truthful;
3. tools are projected according to LBE mode/permission/capability state;
4. terminal output streams live for long-running processes;
5. tool calls preserve durable identity, origin, authorization, result/error, and evidence;
6. the same session can be replayed through a non-interactive client and the TUI without semantic divergence;
7. user steering/interrupt/cancel behavior is deterministic;
8. workspace/repository identity survives provider changes and session resume;
9. Git/worktree and validation workflows are usable for real repositories;
10. external-agent integration truthfully distinguishes cooperative and strict governance;
11. a clean installed consumer can complete a representative professional coding task end-to-end;
12. completion is based on current evidence/validation, not provider self-report.

---

## 18. Priority rule for future agents

Before proposing or implementing any significant provider, CLI/TUI, tool, IDE, external-agent, terminal, Git, browser, or session feature, read this pillar first.

Then consult the companion research/design documents and current source/runtime evidence.

When another document suggests work that conflicts with this pillar, do not silently follow the older route. Reconcile the documentation first.

Historical accepted work remains accepted unless a real regression is proven. This pillar changes the forward product priority; it does not retroactively invalidate proven foundations.

---

## 19. Final product invariant

```text
Provider reasons using only capabilities LBE truthfully exposes.
LBE owns workspace identity, authority, tools, evidence, validation, completion, and persistence.
The user can observe and steer the real running agent.
Professional tools expose real execution state, not simulated capability.
Every client renders or controls the same authoritative runtime.
```

That is the main post-V1 LBE product pillar.