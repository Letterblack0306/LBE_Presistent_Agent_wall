
LBE Cline Governed Node STDIO Architecture Gate

Status: OPEN - ARCHITECTURE DESIGN ONLY - PRODUCTION IMPLEMENTATION LOCKED

Active phase
phase: LBE_CLINE_GOVERNED_NODE_STDIO_ARCHITECTURE
slice: DEFINE_GOVERNED_NODE_SUBPROCESS_STDIO_BOUNDARY
base_sha: 726f6b776dfa82778c2a4b400a84adb9c91cb078
Authorization

The user explicitly authorized continuing with the existing Cline reuse study rather than rebuilding mechanics already proven reusable.

Authorized architecture candidate:

GOVERNED_NODE_SUBPROCESS_STDIO

No other architecture candidate is authorized by this slice.

Why this slice exists

The completed Cline source audit proved that Cline AgentRuntime already owns mature reusable mechanics for:

model -> tool -> result -> continuation;

tool-call parsing and continuation;

pre-tool interception through beforeTool;

provider-native streaming/event mechanics;

cancellation and queued/continued turn mechanics.

The subsequent interop checkpoint classified direct in-process reuse as:

NEW_ARCHITECTURE_REQUIRED

because canonical LBE is Python-owned while audited Cline AgentRuntime is TypeScript/Node and no existing canonical Python-to-Node runtime boundary exists.

This slice therefore defines the smallest new boundary required to consume those mechanics without creating a second authority.

Existing authority owners that must remain authoritative
authorization:
  lbe_guard_inspector/runtime/authorization_resolver.py::resolve_authorization


governed tool execution and receipts:
  lbe_guard_inspector/runtime/tool_orchestration.py::GovernedToolOrchestrator


provider-turn ownership:
  lbe_guard_inspector/provider_turn_runtime.py


canonical session/history/evidence:
  existing LBE session, operational-history, receipt, validation and completion owners


process lifecycle:
  LBE/Python parent process

The Node worker is never an authority owner.

Architecture contract
Python LBE runtime - authoritative parent
        |
        | strict typed stdin/stdout protocol
        v
bounded Node child worker
        |
        v
Cline AgentRuntime mechanics
        |
        | tool proposal only
        v
Python LBE resolve_authorization
        |
        v
GovernedToolOrchestrator
        |
        | ToolReceipt + governed result
        v
Node worker / Cline AgentRuntime
        |
        v
existing Cline continuation loop
Required invariants

Python LBE owns child-process start, stop, timeout, restart policy and termination.

Node may propose a tool call but may never execute LBE workspace/process mutations directly.

Every executable proposal crosses resolve_authorization() before any executor.

Every allowed execution crosses GovernedToolOrchestrator.

Every tool result returned to Cline is correlated to the canonical LBE operation_id and ToolReceipt.

Native Cline editor, apply-patch, filesystem mutation, shell, terminal, process and equivalent direct mutation/execution surfaces are disabled, omitted, or unreachable.

Cline session/runtime IDs are correlation IDs only; canonical session/turn/history identity remains LBE-owned.

Node stdout is protocol-only. Diagnostic output must not corrupt the protocol channel.

Malformed protocol, unknown message types, duplicate request IDs, child exit, timeout, or identity mismatch fail closed.

Node never decides LBE validation, evidence sufficiency, approval, completion or release readiness.

Protocol direction
Python -> Node

The design must define typed envelopes for at least:

runtime.start
turn.execute
tool.result
control.cancel
control.steer
runtime.shutdown
Node -> Python

The design must define typed envelopes for at least:

runtime.ready
provider.event
tool.proposed
turn.completed
turn.failed
runtime.error

Every envelope must have:

protocol_version
message_id
session_id
turn_id
message_type

Tool-related envelopes additionally require:

cline_tool_call_id
lbe_call_id
operation_id
receipt_id when produced
Fail-closed tool flow
Cline tool proposal
    -> Python receives typed proposal
    -> map proposal identity
    -> resolve_authorization()
    -> denied/escalated => no executor call
    -> allowed => GovernedToolOrchestrator.invoke() exactly once
    -> persist/project ToolReceipt through existing LBE owners
    -> return governed result to Cline
    -> Cline continuation resumes
Explicitly rejected designs in this slice
LONG_LIVED_NODE_SIDECAR_RPC
EMBEDDED_JS_RUNTIME
ClineCore wholesale runtime/session adoption
second authorization resolver
second tool dispatcher
second canonical session/history store
native Cline filesystem/editor/shell/process authority
Node-owned validation/completion truth
Required design proof

Before this slice may become PASS, repository evidence must establish:

existing LBE owner call paths for authorization, orchestration, receipt identity, provider continuation and session/history;

exact Cline AgentRuntime integration symbols reused from the audited revision;

a complete typed protocol and identity map;

a native-tool disablement strategy;

fail-closed process/protocol lifecycle rules;

package/runtime/license/security evidence required by the next implementation slice;

implementation test plan proving deny-before-execute, allow-exactly-once, receipt-backed continuation, event mapping, cancellation/error attribution and no duplicate authority;

implementation-gate validator PASS;

git diff --check PASS.

Required evidence level
ARCHITECTURE / SOURCE

No runtime integration claim is permitted from this slice.

PASS meaning

PASS means the governed subprocess/stdio architecture is sufficiently bounded that one later production implementation slice can be activated without inventing additional authority or protocol semantics during coding.

PASS does not authorize production implementation automatically.

After PASS, stop and activate a separate implementation slice.

Non-goals

This slice does not:

add Node or Cline packages;

create a Node worker;

change Python runtime code;

enable native Cline tools;

change provider selection;

change TUI behavior;

add MCP;

change canonical session persistence;

claim installed/live/user-flow/release readiness.
