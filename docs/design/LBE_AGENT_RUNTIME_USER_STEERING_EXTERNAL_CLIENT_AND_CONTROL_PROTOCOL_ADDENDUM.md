# LBE Agent Runtime User Steering, External Client, and Control Protocol Addendum

Status: **AUTHORITATIVE COMPANION DESIGN GATE**
Updated: 2026-08-12

Companion to:

- `docs/design/LBE_AGENT_RUNTIME_CLI_TUI_AND_TOOL_ACCESS_SPEC.md`

This addendum closes four design gaps that must be resolved before implementation of the post-V1 agent interaction event model:

1. active user steering while an agent turn is running;
2. the difference between LBE-owned agent execution and external-agent attachment;
3. the difference between an agent-control protocol and MCP tool exposure;
4. provenance for user-, agent-, runtime-, validation-, and recovery-initiated actions.

The existing CLI/TUI/tool-access specification remains authoritative. This document extends it; it does not replace or reopen accepted C5/R7 runtime, governance, provider, package, or npm work.

---

## 1. Reference-derived interaction findings

This design is derived from working coding-agent interfaces and runtimes rather than generic terminal/dashboard assumptions.

Primary references:

- OpenAI Codex
  - repository: `https://github.com/openai/codex`
  - app-server exposes a bidirectional client/runtime protocol with Thread -> Turn -> Item primitives;
  - turns emit started/completed lifecycle notifications and item started/completed/delta events;
  - clients can start, resume, fork, steer, and interrupt turns;
  - rich interfaces are clients over the same runtime rather than separate agent engines.

- Google Gemini CLI
  - repository: `https://github.com/google-gemini/gemini-cli`
  - tool calls are stateful UI/runtime objects with validating, awaiting-approval, executing, success, cancelled, and error states;
  - history distinguishes user/model messages, thinking, tool groups, direct user shell operations, compression, subagents, MCP state, and other runtime items;
  - slash commands can be handled locally, schedule a tool, or intentionally submit model input;
  - MCP is a real capability integration surface.

- Cline
  - repository: `https://github.com/cline/cline`
  - user feedback can be routed into an already-running/streaming task;
  - active ask/approval/resume/compaction states route user responses back into the same task;
  - runtime commands such as compaction are intercepted by the client/runtime instead of being sent as literal text for the model to improvise;
  - MCP is available as an external capability surface.

- Google Antigravity CLI
  - repository: `https://github.com/google-antigravity/antigravity-cli`
  - CLI/TUI and GUI are described as two faces over one shared core agent engine;
  - persistent history, tool calling, permissions, multi-step reasoning, and multi-file editing belong to the shared engine rather than the renderer.

- Anthropic Claude Code
  - repository: `https://github.com/anthropics/claude-code`
  - public material confirms a terminal-first natural-language coding-agent interaction model and an extensible plugin surface;
  - the public repository does not expose enough of the proprietary renderer/runtime internals to use it as the primary code-level event-model reference.

Reference priority for implementation:

```text
Codex app-server / TUI
  -> primary control-protocol and terminal runtime reference

Gemini CLI
  -> primary tool-state, direct-user command, MCP, and history-item reference

Cline
  -> primary active-user-feedback, approval, resume, and runtime-command routing reference

Antigravity CLI
  -> shared-engine / multiple-client-surface architectural reference

Claude Code
  -> terminal-first user experience and extensibility reference
```

---

## 2. User participation is part of the runtime contract

A usable agent runtime is not only:

```text
user prompt
  -> agent
  -> tools
  -> final answer
```

It is a live three-way relationship:

```text
               USER
                <->
       steering / approval
       commands / feedback
                <->
               TURN
                <->
          AGENT + TOOLS
                <->
            LBE RUNTIME
```

The user remains an active participant while a turn is running.

### Required invariant

A running turn remains steerable unless:

- an atomic action cannot safely accept mid-action input;
- a modal approval/credential/human-only blocker temporarily requires resolution;
- policy explicitly marks the turn non-steerable;
- the turn has already reached a terminal state.

The input composer should therefore remain available during normal execution.

Example:

```text
> Fix the failed browser capability registration

AGENT
I am tracing the capability resolver first.

* Reading capability_registry.py
* Searching browser.snapshot

> Do not change browser policy; only fix registration

SYSTEM
Feedback accepted for the active turn.

AGENT
Understood. I will keep browser policy unchanged and constrain the repair to registration wiring.
```

The new user message is not automatically a new session or unrelated task. It is active-turn steering.

---

## 3. Turn steering contract

The control protocol must expose an explicit steering operation.

Minimum operation:

```text
turn.steer
```

Required fields:

```text
turn_id
session_id
input
source = user
received_at
steering_policy
```

The runtime must classify the steering input as one of:

```text
apply_now
queue_after_current_atomic_action
interrupt_then_apply
reject_terminal_turn
reject_policy
```

The model does not decide whether steering is safe to inject immediately. The runtime owner decides based on current tool/action state.

### Steering provenance

Steering must become a persisted runtime item/event so replay shows that the user changed or refined the objective during execution.

Recommended event:

```text
turn.steering.received
```

with final routing state:

```text
turn.steering.applied
turn.steering.queued
turn.steering.rejected
```

### Atomic action rule

Do not mutate the arguments of an already-authorized atomic tool invocation after execution begins.

If steering conflicts with an in-flight atomic mutation:

```text
user steering
  -> runtime records steering
  -> current atomic action completes or is safely interrupted
  -> runtime re-enters reasoning with updated user intent
```

---

## 4. Interrupt and cancel are different

The UI and control API must distinguish:

```text
interrupt
```

from:

```text
cancel
```

### Interrupt

Purpose:

- stop or pause the current reasoning/tool loop;
- preserve the session and turn history;
- allow user feedback or revised intent;
- permit continuation when safe.

### Cancel

Purpose:

- terminate the current turn;
- finalize it as cancelled;
- do not continue automatically.

Recommended operations:

```text
turn.interrupt
turn.cancel
```

A renderer must not collapse both into a single generic "stop" state.

---

## 5. Two external-agent integration modes

"Another agent uses LBE" is ambiguous and must be separated into two explicit integration profiles.

### 5.1 LBE-owned agent runtime

LBE owns the agent execution boundary:

```text
OpenAI / Anthropic / Gemini / OpenAI-compatible / local model
                         |
                         v
                        LBE
                         |
             capability + permission resolution
                         |
                 governed tool dispatcher
                         |
                      workspace
```

Guarantee:

- all model-visible tools are selected by LBE;
- all governed actions route through LBE;
- LBE can truthfully own session, tool authority, evidence, validation, and completion semantics.

This is the strongest and preferred LBE mode.

### 5.2 External agent attached to LBE

Examples include:

- Codex CLI;
- Gemini CLI;
- Cline;
- Claude Code;
- another MCP-capable agent;
- an IDE agent with its own native tools.

The integration may look like:

```text
external coding agent
       |
       +---- native filesystem / shell / browser / Git tools
       |
       +---- LBE MCP / external capability tools
                    |
                    v
                  LBE
```

LBE cannot govern actions that bypass LBE.

This requires two attachment profiles.

---

## 6. Cooperative attachment profile

In **cooperative attachment**, the external agent retains its native tools.

LBE supplies additional capabilities such as:

- guard inspection;
- workspace policy lookup;
- evidence retrieval;
- validation requests;
- LBE-governed mutations when explicitly selected;
- session/evidence queries where supported.

Guarantee:

> LBE governs only operations routed through LBE.

LBE must not claim that the entire external-agent session is governed.

Required status language:

```text
attachment_mode: cooperative
native_tool_bypass_possible: true
lbe_governance_scope: lbe_routed_operations_only
```

This mode is useful for adoption and integration but is not equivalent to strict governed operation.

---

## 7. Strict LBE attachment profile

In **strict attachment**, overlapping external mutation capabilities must be disabled, restricted, sandboxed, or routed through LBE.

Required invariant:

```text
external agent
      |
      v
LBE authorization / capability boundary
      |
      v
LBE governed tools
      |
      v
workspace
```

For strict-governance claims, overlapping native capabilities such as these must not provide an uncontrolled bypass:

```text
filesystem write
shell / terminal mutation
Git mutation
browser mutation
external publish/deploy mutation
```

Acceptable mechanisms depend on the external client and may include:

- disabling the native tool;
- configuring read-only mode;
- sandboxing native execution outside the governed workspace;
- removing tool permission;
- exposing only LBE wrappers for overlapping operations;
- using an external client's permission/plugin policy when that policy is independently verifiable.

Required status language:

```text
attachment_mode: strict
native_tool_bypass_possible: false | unresolved
lbe_governance_scope: governed_workspace_operations
```

If bypass status is unresolved, the runtime must not advertise the session as fully LBE-governed.

---

## 8. External-agent governance truth rule

Never infer global governance from the presence of the LBE plugin/MCP server.

Forbidden claim:

```text
LBE MCP server connected
therefore this Codex/Cline/Gemini/Claude session is governed by LBE
```

Correct interpretation:

```text
LBE MCP server connected
  -> LBE capabilities are available
  -> only LBE-routed operations are definitely governed
  -> native external-agent capabilities remain outside LBE unless independently restricted
```

This is an acceptance-critical boundary.

---

## 9. MCP and the LBE agent-control protocol are different products

MCP is an external capability integration surface.

It is appropriate for:

```text
agent discovers LBE tools
agent invokes LBE tool
agent receives structured result
```

MCP alone is not sufficient as the complete control protocol for LBE's own interactive clients.

LBE's own TUI, future GUI, IDE extension, automation client, and SDK require control over:

- session creation;
- session resume;
- turn start;
- active user steering;
- interruption;
- cancellation;
- event streaming;
- approvals;
- replay/history;
- provider changes;
- mode/permission changes;
- capability-state changes.

Therefore the runtime has two distinct external surfaces:

```text
                     LBE Python Runtime
                            |
              +-------------+-------------+
              |                           |
              v                           v
      Agent Control Protocol          MCP Server
              |                           |
     LBE-owned clients              external agents
```

Do not merge these responsibilities into one ambiguous interface.

---

## 10. Agent-control protocol

LBE must expose a bidirectional, typed, versioned control protocol before a rich TUI is implemented.

Preferred first transport:

```text
stdio
```

Preferred message framing:

```text
newline-delimited JSON / JSONL
```

Protocol semantics should be JSON-RPC-like or equivalently typed and bidirectional.

The exact wire standard may be chosen during implementation, but it must support requests, responses, and asynchronous notifications.

Recommended process surface:

```text
lbe agent-server --stdio
```

Name is provisional; architecture is not.

### Initialization

Every client connection must initialize before controlling runtime state.

Recommended request:

```text
initialize
```

Client metadata should include:

```text
client_name
client_version
client_kind
supported_protocol_version
supported_event_capabilities
```

The runtime returns effective protocol/runtime metadata and rejects incompatible protocol versions explicitly.

---

## 11. Minimum control operations

The first control-protocol contract should cover:

```text
initialize

session.create
session.resume
session.read
session.status
session.events.list
session.events.subscribe

turn.start
turn.steer
turn.interrupt
turn.cancel

provider.list
provider.check
provider.select

capabilities.list
permissions.get
approval.respond

evidence.get
validation.get
```

Later operations must extend this contract rather than create a second client-specific controller.

---

## 12. Minimum asynchronous notifications

Recommended notification model:

```text
session.started
session.updated

turn.started
turn.steering.received
turn.steering.applied
turn.steering.queued
turn.interrupted
turn.completed

item.started
item.delta
item.progress
item.completed
item.failed
item.cancelled
item.declined
item.escalated

approval.requested
capabilities.changed
permissions.changed
provider.changed
```

All terminal state notifications must be persistable/replayable where the underlying state is durable.

---

## 13. JSONL event output is a proof surface, not the final control API

The existing design correctly proposes non-interactive JSONL event output before TUI implementation.

Keep that proof requirement.

However:

```text
lbe session events --format jsonl
```

is observational only unless paired with a request/control channel.

Therefore the sequence is:

```text
runtime event contracts
  -> durable event emission
  -> JSONL replay/observation proof
  -> bidirectional control protocol proof
  -> transcript renderer
  -> interactive TUI
```

Do not build a rich TUI directly on ad hoc subprocess parsing.

---

## 14. Runtime commands and model input must remain separate

Commands such as these are runtime/operator commands:

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

They must be intercepted by the CLI/TUI command router and sent directly to the correct runtime owner.

Forbidden path:

```text
user types /compact
  -> literal '/compact' sent to model
  -> model improvises a summary
```

Correct path:

```text
user types /compact
  -> CLI command router
  -> LBE compaction/session owner
  -> real runtime operation
  -> runtime item/event result
```

A slash command may intentionally submit model input only when its command contract explicitly defines that behavior.

---

## 15. Direct user actions are first-class runtime actions

The runtime must distinguish an action initiated by the model from an action initiated directly by the user or by runtime policy.

Required origin values:

```text
user
agent
runtime
validation
recovery
```

Every actionable item/receipt should preserve origin.

Example:

```text
tool: git.diff
origin: user

command: pytest -q
origin: validation

mutation: workspace.replace_text
origin: agent

checkpoint: session.checkpoint
origin: runtime
```

This provenance must survive event replay and evidence packaging.

---

## 16. Tool-call item provenance additions

Extend the tool-call item contract with:

```text
origin
origin_item_id?
origin_user_message_id?
origin_policy_id?
external_client_id?
attachment_mode?
```

For externally attached agents, receipts should identify whether the action was:

```text
lbe_routed
external_native_observed
external_native_unobserved
```

LBE must never fabricate receipts for external actions it did not execute or independently observe.

---

## 17. Approval remains inline with the active turn

Approval is not a separate dashboard/workflow subsystem.

Example:

```text
* Running npm publish --access public

  This publishes an immutable public package.

  [Allow once] [Allow for this objective] [Deny]
```

The lifecycle remains attached to the same action item:

```text
tool_call
  -> waiting_for_approval
  -> approval.respond
  -> executing
  -> completed | failed | declined
  -> agent continues
```

If the user already authorized the broader objective and the remaining steps are non-destructive observation/verification, the runtime continues without another approval boundary.

---

## 18. User-facing terminal interaction invariant

The primary terminal surface remains the live agent session.

Reference shape:

```text
project-x   CODING   Gemini/gemini-model   governed

> Fix the browser capability registration

* I will trace the capability resolver first.

* Explored
  - Read runtime/tools.py
  - Read capability_registry.py
  - Search browser.snapshot (4 matches)

* The browser implementation exists, but the session capability resolver never exposes it.

* Edited capability_registry.py
  +12 -2

* Running pytest -q tests/test_capabilities.py
  ......................
  22 passed

* I am checking that audit mode still cannot receive browser mutation capabilities.

> Do not change browser policy; only fix registration_

Ctrl+C interrupt   /tools   /mode   /diff
```

Required behavior:

- the composer remains usable while the turn runs when steering is allowed;
- running tool items mutate in place;
- approvals render inline;
- runtime/operator commands bypass the model;
- user steering remains part of the same turn/session history;
- status chrome remains secondary;
- the UI does not manufacture an independent workflow narrative.

---

## 19. External CLI interoperability matrix

The implementation should explicitly test common integration shapes.

| Client class | Preferred LBE integration | Governance claim |
| --- | --- | --- |
| LBE TUI / future GUI | Agent Control Protocol | Full LBE runtime semantics |
| LBE non-interactive CLI | Agent Control Protocol / direct runtime API | Full LBE runtime semantics |
| Codex CLI | MCP for capabilities; optional future dedicated adapter | LBE-routed operations only unless native tools are restricted |
| Gemini CLI | MCP for capabilities; optional future dedicated adapter | LBE-routed operations only unless native tools are restricted |
| Cline | MCP for capabilities; optional future dedicated adapter | LBE-routed operations only unless native tools are restricted |
| Claude Code | MCP/plugin-compatible surface where supported | LBE-routed operations only unless native tools are restricted |
| automation/client SDK | Agent Control Protocol | Depends on selected permission/attachment profile |

Do not hard-code behavior to one external agent product.

---

## 20. Capability negotiation for external clients

An external client should be able to discover:

```text
available
gated
unavailable
```

LBE capabilities without assuming every client can render every interaction type.

Client capability negotiation should cover at least:

- streaming item updates;
- inline approval rendering;
- user steering support;
- browser result rendering;
- file-diff rendering;
- rich tool result rendering;
- event replay support.

If the client cannot support a required interactive flow, LBE must downgrade explicitly or report the capability gap.

---

## 21. Security and authority implications

The control protocol must not become a bypass around governance.

Every mutating control request must still pass through existing LBE authority owners.

Forbidden:

```text
TUI client
  -> direct filesystem writer
```

```text
MCP client
  -> bypass permission resolver
```

```text
external agent attachment
  -> claim full LBE governance while native mutation tools remain unrestricted
```

Correct:

```text
client request / provider proposal
  -> existing LBE controller
  -> mode + permission + capability resolution
  -> governed execution
  -> evidence / validation / completion
  -> event stream
```

---

## 22. Implementation order amendment

The companion CLI/TUI specification's implementation sequence remains valid, with one required refinement.

Use this order:

```text
A. freeze reference-derived interaction contracts
B. typed Session / Turn / Item contracts
C. active-turn steering + interrupt/cancel contracts
D. instrument current LBE runtime into item/events
E. capability registry
F. durable JSONL event/replay proof
G. bidirectional agent-control protocol over stdio
H. MCP capability server for external agents
I. basic transcript renderer
J. interactive LBE TUI
K. browser capability integration
L. external-agent cooperative attachment proof
M. external-agent strict attachment proof where supported
N. end-to-end acceptance
```

Do not implement MCP first and mistake it for the LBE client-control protocol.

Do not implement TUI first and invent protocol/state afterward.

---

## 23. Required acceptance additions

Before claiming the LBE agent interaction layer usable, prove all of the following in addition to the companion specification's existing criteria:

```text
active user feedback can steer a running turn
steering provenance is persisted/replayed
interrupt and cancel have distinct semantics
runtime slash commands bypass model interpretation
user-initiated and agent-initiated actions are distinguishable
control protocol supports requests + async notifications
JSONL event replay matches the same persisted runtime items
MCP capability exposure does not imply full external-session governance
cooperative attachment reports native-tool bypass truthfully
strict attachment cannot claim success while native mutation bypass remains unresolved
external clients cannot expand LBE capability/permission state
provider switching does not change control-protocol or tool authority semantics
```

---

## 24. Anti-repeat blockers added by this addendum

Do not:

- disable user input for the entire duration of an otherwise steerable turn;
- force normal steering into a new session;
- treat interrupt and cancel as the same operation;
- send runtime slash commands to the model as ordinary prompt text;
- treat MCP connectivity as proof of whole-session governance;
- claim an external agent is strictly governed while it retains unrestricted native mutation tools;
- make MCP the only protocol for LBE-owned rich clients;
- build a TUI by parsing human-formatted stdout instead of typed runtime events;
- lose action origin/provenance when rendering or replaying a session;
- let an external client choose tools that the LBE capability resolver did not expose;
- duplicate session/turn/tool state inside the renderer.

---

## 25. Final invariant

The final architecture is:

```text
                         USER
                          ^
                          |
                 steering / approval
                          |
                          v
                 LBE SESSION / TURN
                          |
              +-----------+-----------+
              |                       |
              v                       v
      reasoning provider       runtime/operator commands
              |                       |
              +-----------+-----------+
                          |
                          v
                capability + policy
                          |
                          v
                 governed tool owner
                          |
                          v
                      workspace
```

External agents attach beside, not inside, that ownership claim:

```text
Codex / Gemini / Cline / Claude / other agent
              |
              +-- MCP -> LBE-routed governed capabilities
              |
              +-- native client tools
                    |
                    +-- outside LBE governance unless independently restricted
```

The product rule is therefore:

> LBE may claim authority only over actions whose execution path it actually owns or independently verifies. A connected external agent is not automatically a governed external agent.

And the user-experience rule is:

> The user watches and steers one live persistent agent session. Tools, approvals, runtime commands, feedback, validation, and completion all resolve back into that same authoritative session rather than into a second UI-owned workflow.
