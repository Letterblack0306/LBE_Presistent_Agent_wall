# Post-V1 Professional Agent CLI and Provider Runtime Research

Status: **RESEARCH GATE — DO NOT IMPLEMENT THE INTERACTIVE AGENT LAYER FROM PROVIDER/CLI ASSUMPTIONS**
Updated: 2026-08-12

Companion design gates:

- `docs/design/LBE_AGENT_RUNTIME_CLI_TUI_AND_TOOL_ACCESS_SPEC.md`
- `docs/design/LBE_AGENT_RUNTIME_USER_STEERING_EXTERNAL_CLIENT_AND_CONTROL_PROTOCOL_ADDENDUM.md`

This document records the research required before LBE turns its existing bounded reasoning/provider runtime into a professional interactive coding-agent runtime.

The objective is not to imitate one CLI. The objective is to understand the common execution model underneath mature coding agents, preserve provider-specific semantics where they matter, normalize them into one LBE-owned runtime model, and expose that runtime through a professional terminal/client surface.

LBE is intended for professional software work as well as smaller projects. Therefore its interaction, terminal, Git, validation, session, tool, extension, and provider contracts must be strong enough for large repositories, long-running tasks, multi-file changes, real test/build processes, remote/local models, external tooling, and controlled automation.

---

## 1. Research conclusion

The current LBE provider milestone and the future interactive agent runtime are different layers.

Current provider support proves:

```text
provider configuration
  -> provider-specific HTTP envelope
  -> bounded LBE reasoning/plan JSON
  -> LBE validates the contract
```

That is appropriate for the accepted 0.2.1 reasoning boundary.

A professional coding-agent runtime requires an additional layer:

```text
provider-native stream
  -> provider adapter
  -> normalized LBE model-event stream
  -> LBE capability resolver
  -> governed tool execution
  -> normalized tool/runtime event stream
  -> provider-native continuation
  -> persistent Session / Turn / Item state
  -> CLI/TUI/GUI/client rendering
```

Do not replace the proven bounded planning path until the interactive provider contract is separately designed and accepted.

---

## 2. Current LBE provider gap

At the current post-V1 feature branch, `ProviderCapabilities` contains only:

```text
streaming
tool_calls
structured_output
context_limit
```

and the built-in provider factories currently advertise:

```text
streaming = false
tool_calls = false
structured_output = true
```

for OpenAI, Anthropic, Gemini, and OpenAI-compatible providers.

The Anthropic adapter currently sends a Messages API request and extracts exactly one text block which must decode to the existing LBE JSON contract.

The Gemini adapter currently sends `generateContent`, requests JSON output, and extracts exactly one text part which must decode to the same LBE contract.

This is not a defect in the accepted provider slice. It is evidence that the next agent-runtime work must not assume the current provider abstraction already represents interactive tool use.

Required conclusion:

> Provider transport compatibility is not agent-runtime capability compatibility.

---

## 3. Provider APIs do not expose one universal agent grammar

### 3.1 OpenAI

The current Responses API exposes typed output items and streaming events. Relevant semantics include:

- response lifecycle events;
- output item lifecycle;
- message text deltas;
- function/custom tool calls with call identifiers;
- streamed tool/custom-tool input;
- parallel tool calls;
- built-in/server tools;
- MCP tool listing/calls/approval items;
- explicit incomplete/error states;
- response/conversation state identifiers.

OpenAI therefore already has an item-oriented stream that resembles an agent runtime, but LBE must still own workspace authority and tool execution for LBE-governed local tools.

### 3.2 Anthropic

Anthropic Messages uses content blocks rather than the OpenAI Responses item grammar.

Important differences:

- client tools return `tool_use` blocks;
- the application executes those tools and sends `tool_result` blocks;
- the normal client-tool loop is driven by `stop_reason = tool_use`;
- one response may contain multiple tool-use blocks;
- Anthropic also provides server-executed tools;
- Anthropic-schema client tools include trained schemas for common operations such as shell/editor/computer interactions;
- streaming is `message_start` / content block start+delta+stop / message delta / message stop;
- fine-grained tool input streaming can emit partial or temporarily invalid JSON and therefore requires accumulation and guarded parsing.

LBE must not pretend this is identical to OpenAI function-call streaming.

### 3.3 Gemini

The Gemini API has both generation-oriented APIs and the newer Interactions API intended for agentic workflows.

Important semantics include:

- function calls as typed steps;
- streaming `step.start` / `step.delta` style events for function-call arguments;
- partial argument accumulation before execution;
- server-side Google tools and client-side function calls can coexist;
- stateful interaction APIs can own more conversational state than a simple stateless generation call.

Gemini CLI itself adds a separate client/runtime layer around model streaming, tool scheduling, approvals, background processes, Git state, command processing, and history rendering. Provider API behavior and Gemini CLI behavior therefore must not be conflated.

### 3.4 OpenAI-compatible / routed / local providers

`openai-compatible` must remain a compatibility family, not a promise that every endpoint/model supports the same agent features.

Examples:

- OpenRouter normalizes tool-call request/response shapes across many model/provider combinations, supports parallel-tool-call controls, and may route tool requests only to endpoints supporting required parameters. Provider routing/fallback can change the physical backend while the logical model is unchanged.
- LM Studio exposes OpenAI-compatible Chat Completions and Responses endpoints, but tool reliability depends on the loaded model and parser/template support. It may parse model-emitted text into OpenAI-compatible tool-call structures.
- Ollama streams `thinking`, `content`, and `tool_calls` fields and requires the caller to accumulate them and feed tool results back.

Therefore LBE must negotiate **model-instance capabilities**, not infer capabilities from a provider name alone.

---

## 4. Required provider capability model

Replace the future assumption:

```text
provider supports tools: yes/no
```

with capability negotiation at provider + endpoint + model level.

Recommended capability dimensions:

```text
ProviderModelCapabilities
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

Capabilities may be:

```text
supported
unsupported
unknown
conditional
```

`conditional` must include a reason, such as:

```text
model_support_required
endpoint_support_required
beta_header_required
server_feature_toggle_required
tool_schema_restriction
```

The capability result is descriptive. It does not grant LBE workspace authority.

---

## 5. Normalize semantics, not provider wire formats

LBE should not expose OpenAI/Anthropic/Gemini wire objects directly to the TUI.

Provider adapters should emit a normalized provider-event vocabulary such as:

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

Each normalized event preserves provider-native metadata in an opaque diagnostic envelope:

```text
provider_id
model_id
provider_request_id?
provider_event_type?
provider_stop_reason?
raw_diagnostic_ref?
```

The renderer consumes normalized LBE events. Provider-specific diagnostics remain inspectable without making the UI provider-specific.

---

## 6. Tool-call identity and continuation

Every model-proposed tool call requires a durable LBE call identity.

Recommended mapping:

```text
provider_call_id?  -> LBE call_id -> tool receipt -> provider continuation
```

Do not rely on provider call IDs as the only execution identity.

The LBE call record must survive:

- provider switch after a completed turn;
- session replay;
- UI reconnect;
- process restart where supported;
- tool output streaming;
- approval wait;
- cancellation/failure;
- evidence packaging.

Parallel provider tool calls may be represented independently and executed in parallel only when dependency/policy/tool metadata allows it.

Model parallelism is permission to propose concurrently; it is not permission to execute mutations concurrently.

---

## 7. Professional terminal capability is more than `run command`

The uploaded Cline runtime trace proves a minimal cycle of command proposal -> execution -> stdout/stderr/result -> model recovery. It also shows independent tool calls and a real shell-compatibility failure (`head` under PowerShell) followed by recovery.

A professional LBE terminal layer requires a stronger contract.

### 7.1 Terminal execution classes

At minimum distinguish:

```text
terminal.exec
  bounded non-interactive process

terminal.session.start
terminal.session.write
terminal.session.resize
terminal.session.interrupt
terminal.session.terminate
  PTY/conpty-backed interactive process

terminal.background.start
terminal.background.status
terminal.background.output
terminal.background.stop
  durable long-running/background process
```

Do not overload every operation into one untyped shell string.

### 7.2 Required execution metadata

```text
command_id
argv or shell_command
shell_kind
cwd
workspace_binding
environment_selection
env_delta_redacted
stdin_mode
pty
started_at
pid?
exit_code?
signal?
timeout?
stdout_chunks
stderr_chunks
output_truncated
background_state
origin
authorization_receipt
```

### 7.3 Streaming

Long-running developer commands require true output deltas:

```text
command.started
command.stdout.delta
command.stderr.delta
command.progress
command.completed | command.failed | command.cancelled
```

A professional TUI cannot wait for an entire build/test/server process to finish before showing output.

### 7.4 Shell portability

The runtime must know the execution environment and shell family.

Examples:

```text
Windows PowerShell
Windows cmd
Git Bash
WSL
POSIX sh/bash/zsh
remote/container shell
```

The provider should not be expected to infer shell semantics from path strings alone.

---

## 8. Professional workspace and repository identity

Workspace identity is runtime state, not model memory.

Required workspace facts should include:

```text
workspace_id
canonical_root
repository_root?
repository_remote?
VCS kind
branch/ref
HEAD/revision
dirty state
worktree identity
environment identity
allowed roots
project profile
```

The task-drift incident that caused an agent to search unrelated projects is a regression pattern:

```text
task bound to workspace A
-> context uncertainty
-> MUST inspect bound workspace identity
-> MUST NOT search drives for remembered project B
```

Professional use also requires large monorepo/multi-root awareness without allowing sibling roots to become implicit truth.

---

## 9. Git is a first-class tool family, not just shell text

Shell access may still execute Git, but LBE should have structured Git capabilities for common high-value operations and evidence.

Recommended read capabilities:

```text
git.status
git.diff
git.log
git.show
git.branch
git.remote
git.worktree.list
git.blame
```

Governed mutation capabilities may later include:

```text
git.stage
git.commit
git.branch.create
git.worktree.create
git.worktree.remove
```

Push/PR/publish actions remain separately classified external mutations.

Professional parallel work should support Git worktree isolation rather than allowing two agent sessions to race on the same files.

Claude Code's current worktree model is useful evidence: parallel sessions use isolated worktrees/branches, and worktree isolation can also be applied to subagents. This is a stronger professional pattern than merely starting multiple terminal processes in one checkout.

---

## 10. Session model must support real professional workflows

A session should not be only a chat history.

Required session properties include:

```text
workspace identity
provider/model state
runtime mode
permission profile
active environment
turn history
item/event history
active terminal/background processes
changed-file set
authorization state
validation state
completion contract
context/compaction state
checkpoints
```

Professional lifecycle operations should eventually include:

```text
session.create
session.resume
session.fork
session.archive
session.export
session.checkpoint
session.rewind or restore where policy allows
```

Codex app-server exposes start/resume/fork plus persisted thread/turn/item history. Claude Code supports resume/fork and snapshots affected files before changes. These are evidence that professional users need reversible and branchable sessions, not one linear disposable prompt stream.

---

## 11. User interaction is control-plane input

The user is not just the first message producer.

The runtime must support:

```text
new task
follow-up after completion
active-turn steering
interrupt
cancel
approval response
runtime slash command
direct user tool action
```

These are different event types with different semantics.

The composer remains usable during a steerable turn.

Runtime/operator commands must bypass model interpretation when they target deterministic runtime owners.

Examples:

```text
/provider
/model
/mode
/tools
/permissions
/diff
/validation
/checkpoint
/resume
/compact
/interrupt
/cancel
```

---

## 12. Professional CLI/TUI surface

The primary UI remains the live session transcript/item stream, but professional use needs inspectable depth without turning the product into a dashboard.

### Primary surface

```text
user input
agent commentary
reasoning summary where available/allowed
active tool invocations
streaming terminal/tool output
file edits/diffs
approvals
agent reaction
validation
final result
```

### Secondary professional views

Available by toggle/command, not inserted as noise into the conversation:

```text
changed files / diff
Git state
plan/goals
evidence
validation/test runs
background processes
capabilities/tools
provider/model diagnostics
token/context/cost/latency
session history/checkpoints
MCP/extensions
runtime logs
```

### Error detail levels

Professional users need both concise and full diagnostic modes.

Normal transcript:

```text
command failed: exit 1
meaningful stderr excerpt
```

Expanded diagnostics:

```text
full argv/cwd
full stdout/stderr or artifact reference
provider/tool IDs
receipt/evidence IDs
retry classification
timestamps
```

---

## 13. IDE and external client integration

The TUI must not be the only serious client.

Codex demonstrates a dedicated app-server powering richer interfaces using bidirectional JSON-RPC-like communication over stdio/other local transports with Thread/Turn/Item semantics.

Claude Code's VS Code integration demonstrates another useful split: an IDE-local MCP/RPC server provides editor-native functions such as diff viewing and selected/open-file context, while only an intentionally filtered subset of tools is model-visible.

LBE should therefore separate:

```text
Agent Control Protocol
  -> trusted LBE clients
  -> session/turn/event/control plane

MCP Server
  -> external model/agent capability exposure

IDE Bridge
  -> editor-native operations and context
  -> only explicitly exposed capabilities become model-visible
```

Do not force editor/UI operations through model-visible MCP tools when they are control-plane functions.

---

## 14. Extension model

Professional adoption requires extensibility without surrendering runtime ownership.

Extension categories should be explicit:

```text
MCP capability servers
skills/instruction packs
project policy/profile packs
validators
tool providers
IDE bridges
lifecycle hooks
provider adapters
```

Hooks require deterministic precedence and must not silently bypass deny policy.

A useful reference is Claude Code's hook model, where lifecycle hooks can deny/ask/inspect operations but permission rules retain their own precedence.

LBE should preserve the stronger invariant:

> Extension code may participate in evaluation or provide capabilities, but it does not become the owner of LBE session authority, completion truth, or workspace boundary.

---

## 15. Code intelligence should not be reduced to file grep forever

A professional coding agent needs progressive code intelligence.

Initial deterministic tools:

```text
workspace.read
workspace.search
workspace.glob
workspace.symbol_search where available
workspace.references where available
workspace.diagnostics where available
```

Potential backends:

- repository-native search;
- language-server protocol adapters;
- IDE bridges;
- parser/tree-sitter indexes;
- project-specific build-system metadata.

The capability registry must report what is actually available in the selected environment.

Do not claim semantic references/diagnostics when only text search is available.

---

## 16. Validation is a first-class runtime tool family

Professional completion is not equivalent to `command exited 0`.

Validation needs structured identity:

```text
validation.discover
validation.run
validation.result
validation.compare
```

The runtime should capture:

```text
validator identity
source of validator selection
command/tool execution receipt
scope
exit state
structured test/build/lint data when available
artifact references
workspace revision/hash binding
```

Provider narration cannot convert a failed/partial validator into success.

---

## 17. Browser/computer capability remains optional and explicit

Browser capability should be a registered runtime backend, not presumed model knowledge.

Professional browser use may include:

```text
browser.tabs
browser.open
browser.snapshot
browser.click
browser.type
browser.submit
browser.download_metadata
browser.console
browser.network where supported
```

The observed-state loop remains mandatory.

Computer/desktop-control capability, if ever added, is a separate high-risk capability family and must not be silently treated as browser equivalence.

---

## 18. Background tasks and parallelism

Professional workflows require concurrency, but concurrency must be explicit.

Distinguish:

```text
parallel read-only tool calls
parallel background processes
parallel isolated sessions/worktrees
subagents/delegated contexts
```

Do not collapse these into one `parallel=true` flag.

Background processes need process identity, output subscription, lifecycle controls, and session/workspace ownership.

Subagents, if added later, should be a runtime-owned delegation facility with explicit tool/permission/context boundaries. They are not required for the first professional CLI slice.

The first priority is a strong single-agent runtime; parallel agents must not compensate for weak tool/session semantics.

---

## 19. Context and compaction

Long professional sessions need deterministic context management.

Runtime must distinguish:

```text
persisted session history
provider-visible context window
workspace evidence
summaries/compaction
memory
```

Compaction must be an actual runtime operation, not a prompt asking the provider to "summarize itself" without durable bookkeeping.

Provider context limits and cache behavior differ, so the context assembler must use negotiated model capabilities rather than one static token policy.

---

## 20. Resource and performance observability

Professional users need operational visibility without turning the main transcript into telemetry.

Secondary diagnostics should expose when available:

```text
provider/model
request IDs
latency / time-to-first-token
tokens in/out/cache
context utilization
tool duration
terminal duration
retry/fallback state
provider routing identity when known
background process resource status where available
```

Provider routing services may change physical providers/fallbacks. LBE should preserve logical provider/model identity and record routing metadata separately when observable.

---

## 21. Non-interactive and automation mode

A serious CLI must support both humans and automation from the same runtime.

Human TUI:

```text
interactive transcript
steering
inline approvals
rich terminal output
```

Automation/client:

```text
machine-readable requests
machine-readable events
explicit exit status
no ANSI dependency
no parsing human transcript
non-interactive approval policy
stable schemas
```

The same Session/Turn/Item state is used by both.

Do not make scripting consume TUI text.

---

## 22. Professional-grade capability groups

The capability registry should eventually cover these groups, subject to installed backend and policy:

```text
workspace.*
  read/search/glob/inspect/symbols/references/diagnostics/edit/diff

git.*
  status/diff/log/show/branch/remote/blame/worktree

terminal.*
  exec/session/background/process-control

validation.*
  discover/run/result

provider.*
  list/check/select/capabilities/diagnostics

session.*
  create/read/resume/fork/checkpoint/export

browser.*
  tabs/open/snapshot/interact/console/network metadata

mcp.*
  list/status/connect/disconnect where permitted

ide.*
  selection/open-file/diff/reveal/diagnostics where a bridge exists
```

No provider receives a capability merely because the schema exists globally. The session capability resolver exposes only the allowed subset.

---

## 23. Capability UX

The user should be able to ask the runtime what is truly available.

Example:

```text
/tools

Workspace
  read              available
  search            available
  edit              gated: coding mode
  diagnostics       unavailable: no semantic backend

Terminal
  exec              available
  interactive PTY   unavailable
  background        available

Browser
  snapshot          unavailable: browser backend not installed

Provider
  streamed text     available
  tool calls        conditional: selected model capability unverified
```

This is more useful than a generic "provider healthy" indicator.

---

## 24. Provider differences the UI must not leak directly

Examples of provider-native details that adapters normalize:

```text
OpenAI function/custom tool call
Anthropic tool_use block
Gemini function_call step
OpenRouter OpenAI-compatible tool_calls
Ollama streamed tool_calls
LM Studio parsed tool-call output
```

All may become:

```text
model.tool_call.started
model.tool_call.arguments.delta*
model.tool_call.completed
```

But the normalized event must preserve uncertainty:

- buffered provider arguments must not be rendered as if they streamed;
- parsed local tool calls must not be advertised as native structured generation when that is not true;
- unsupported parallelism must not be simulated as provider parallel generation;
- reasoning visibility must follow provider capability/policy;
- server-side tool execution must not be falsely recorded as an LBE-executed local tool.

---

## 25. Acceptance matrix before interactive implementation

Before the first professional interaction runtime is claimed ready, research/contract tests must cover at least:

### Provider normalization

```text
OpenAI streamed text
OpenAI one tool call
OpenAI parallel tool calls
OpenAI tool-argument deltas
Anthropic text/content blocks
Anthropic tool_use + tool_result loop
Anthropic parallel tool calls
Anthropic fine-grained tool input fragments including invalid partial JSON
Gemini streamed text
Gemini streamed function-call arguments
Gemini function result continuation
OpenAI-compatible model with valid tool calls
OpenAI-compatible model with no tool support
OpenAI-compatible malformed/parsed tool-call failure
provider cancellation/error/incomplete stop
```

### Runtime tools

```text
workspace read/search/edit
structured Git read path
terminal success/failure
stdout/stderr streaming
long-running command
background process
interrupt/cancel
validation
capability unavailable
```

### User interaction

```text
steer while model streaming
steer while read-only tool running
steer while atomic mutation is in flight
inline approval
direct slash command
interrupt vs cancel
resume/replay
```

### Professional workspace

```text
large repo
monorepo root vs selected project root
dirty workspace
branch change
external file change
worktree isolation
Windows and POSIX shell behavior
```

### Client surfaces

```text
JSONL replay
bidirectional stdio control client
TUI projection
non-interactive automation client
external MCP client
```

---

## 26. Implementation boundary after this research

Do not start with TUI widgets or terminal styling.

Do not start by replacing the 0.2.1 provider adapters.

The next architecture work should define two explicit contracts:

```text
A. Provider Event Normalization Contract
B. Professional Runtime Capability Contract
```

Then:

```text
provider capability probes/adapters
-> normalized model events
-> Session/Turn/Item persistence
-> terminal/workspace/Git capability registry
-> tool execution event streaming
-> provider continuation loop
-> agent-control protocol
-> transcript projection
-> professional TUI
```

---

## 27. Product bar

LBE should not compete by putting more boxes into a terminal.

The professional differentiator should be:

```text
provider-neutral reasoning
+ truthful per-model capability negotiation
+ persistent workspace-bound sessions
+ strong governed tool ownership
+ live tool/process observability
+ deterministic evidence and validation
+ user steering
+ reliable resume/replay
+ professional Git/worktree/session workflows
+ one runtime usable by TUI, IDE, automation, and external agents
```

The target is not "a CLI that can call an LLM."

The target is:

> **A persistent professional agent runtime whose CLI is one high-fidelity user surface over real provider events, governed developer tools, repository state, execution state, validation, and durable session history.**

---

## 28. Research sources

Primary implementation/code references:

- OpenAI Codex: `https://github.com/openai/codex`
  - app-server protocol;
  - Thread/Turn/Item model;
  - TUI execution/tool rendering;
  - approvals, steering, interruption, persistent threads.
- Google Gemini CLI: `https://github.com/google-gemini/gemini-cli`
  - stream hook;
  - tool scheduler/statuses;
  - approval state;
  - background process metadata;
  - Git service;
  - command/history routing.
- Cline: `https://github.com/cline/cline`
  - user feedback while streaming;
  - tool/approval ask routing;
  - MCP integration;
  - real runtime log supplied for this research.

Primary provider/runtime documentation:

- OpenAI Responses API streaming/tool events.
- Anthropic Claude Platform tool-use and streaming documentation.
- Google Gemini API function-calling and streaming documentation.
- OpenRouter tool calling and provider-routing documentation.
- LM Studio OpenAI-compatible Responses/tool-use documentation.
- Ollama tool-calling and streaming documentation.

Professional workflow references:

- Claude Code sessions, worktrees, permissions/hooks, IDE integration, and subagent documentation.

Reference use rule:

> These sources supply proven interaction and protocol patterns. LBE must derive its own provider-neutral contracts and must not copy any one product's internal ownership model blindly.
