# Complete LBE Agent Runtime Gate

Status: **OPEN — EXPLICIT USER AUTHORIZATION — PUBLICATION PAUSED**

## Machine-selected state

```text
phase: COMPLETE_LBE_AGENT_RUNTIME_IMPLEMENTATION
slice: DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE
status: OPEN
implementation_allowed: true (active complete-runtime slice only)
architecture_changes_allowed: true (explicit user authorization)
next_phase_locked: true
publication_controls: false (nested publication governance records)
```

## Scope

Deliver one local LBE agent runtime. Providers supply reasoning only; LBE owns
workspace identity, doctrine/mode, policy, authorization, governed dispatch,
receipts, evidence, persistence, recovery, and deterministic completion. The
terminal is the user-facing IDE projection/control client and must not become a
second runtime.

The current product loop is:

```text
open LBE -> resolve workspace/session/provider/profile/doctrine -> load bounded
LBE knowledge and project context -> agent reasons and requests a capability ->
existing LBE Core decides -> governed adapter returns receipt/evidence -> agent
continues -> LBE determines completion -> TUI presents result/evidence/diff/
uncertainty/next action
```

## Existing owners to reuse

- `SessionMemoryRuntimeBridge`, `SessionOperationalHistory`, and recovery
  owners for session/task/checkpoint persistence;
- R6C/R6E and `GovernedToolOrchestrator` / `ToolReceipt` for governed
  authorization and execution;
- provider registry and provider turn runtime for reasoning continuation;
- terminal projection and Textual client for terminal rendering and controls.

## Slice checkpoints

### VERSIONED_USER_STATE_AND_PROVIDER_PROFILE_LIFECYCLE — PASS

Completed 2026-08-22 with focused provider/profile contracts (`48 passed`),
an actual Windows Credential Manager synthetic write/read/delete round trip,
and a persisted user-state non-leakage assertion. The user-state record holds
only provider metadata and a credential ID. The explicit `lbe provider migrate`
path never discovers legacy files and never emits a source path or secret.

Current active slice: `DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE`.

### DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE — IN PROGRESS

Source and focused runtime proof now cover both provider paths. The governed
coding controller already injects `ENGINEERING`; the non-streaming Audit and
Investigation TUI path now resolves the persisted mode and injects bounded
`AUDIT` or `INVESTIGATION` guidance. Only safe doctrine/provenance metadata is
persisted in runtime events; project instructions remain provider-only.

Focused validation: `14 passed` for provider/runtime/guidance tests and
`34 passed` for CLI/TUI/provider-state tests. A live local
`qwen/qwen3-coder-30b` comparison used the same workspace and objective under
Coding and Audit and produced distinct doctrine-aligned responses. The full
installed TUI acceptance, governed tool-call behavior with live tools, and
completion of this gate remain pending; no cloud fallback was used.

## Core baseline and integration finding

The following is the existing **LBE Core baseline**, not a newly proposed LBE
runtime structure and not a replacement for the current session, policy,
receipt, evidence, recovery, or completion owners. Core established a
pre-action control boundary in addition to the post-change repository gate:

```text
agent tool proposal
  -> LBE permission decision (allow | deny | approval_required)
  -> approved governed adapter
  -> transaction / rollback staging where required
  -> execution receipt and validation evidence
  -> temporary-workspace proof and repository-promotion gate
  -> main
```

The existing local-executor lineage is Core evidence for the intended
permission, adapter, audit, validation, backup, rollback, and recovery design.
The complete runtime work must integrate with those owners and re-prove their
active seams; it must not duplicate, rewrite, or rebrand Core as a new
structure.

The current gap is enforceability: an external agent integration can remain
able to call a native filesystem, shell, Git, network, or hosted-service tool
directly. A later receipt or repository gate cannot make that mutation governed
retroactively. Each capable integration must therefore expose LBE as its
permission and execution tool while withholding direct mutation tools from the
agent-facing tool set.

Repository promotion remains a separate control. It verifies TEMP proof,
intent/scope, validation, and independent evidence before MAIN opens; it does
not replace pre-action permission.

## Required implementation sequence

1. Trace the Core executor/API and prove the current permission-decision,
   adapter, transaction, receipt, rollback, and recovery seams. Record any
   integration gap as a finding; do not replace a proven Core owner with a
   parallel owner or alter Core structure.
2. Make LBE dispatch mandatory for every integrated agent mutation capability:
   filesystem, shell, Git, MCP/plugin, subagent, network, and hosted-service
   operations. Deny the equivalent direct tool exposure.
3. Versioned user state and non-leaking credential references.
4. Provider setup/profile lifecycle and verified health without silent fallback.
5. First-run setup and live session entry over persisted owners.
6. Build bounded agent guidance from the active workspace, policy, registered
   tools, and evidence contract; attach provenance and never treat guidance as
   authority.
7. Capability registry expansion behind the existing governed dispatch.
8. Terminal controls and detailed evidence/diff/settings/session surfaces.
9. Recovery, deterministic completion, TEMP proof/promotion integration, and
   installed-package acceptance.

## Future capability areas — not active-gate requirements

Platform sandbox backends, outbound DLP, AST indexing, local semantic search,
worktree subagents, protocol expansion, and additional host isolation remain
future capability areas. They may be researched and proposed, but are not
automatically promoted into this runtime gate or used to block the doctrine,
provider, capability, TUI, and evidence loop above.

## Invariants

- Credentials exist only in the host credential store and outbound transport.
- Cloud provider failure is explicit; a different provider/model is never used.
- MCP, plugins, and subagents are registrations behind LBE dispatch and receive
  policy, receipts, evidence, and scoped parent identity.
- Ordinary policy-covered work is automatic. High-risk authority expansion has
  a separate explicit decision showing target, effect, verification, and
  receipt; there is no generic approval queue.
- Provider prose cannot decide completion.
- No integrated agent receives a direct mutation tool that can bypass LBE's
  pre-action decision and approved adapter.
- A decision token, operation identity, receipt, and any required rollback
  evidence remain correlated from proposal through completion.
- Pre-action control, action evidence, and post-action repository promotion
  are separate layers; a passing later layer never excuses bypass of an earlier
  one.

## PASS evidence

- focused tests for configuration, credential non-leakage, setup, provider
  lifecycle, capability dispatch, and terminal handlers;
- persisted receipts/events/evidence/recovery proof;
- local installed runtime launch plus one local and one cloud provider proof;
- bypass proof: a simulated agent direct mutation is unavailable or denied,
  while the equivalent LBE-governed request produces the expected decision and
  receipt;
- transaction/rollback and tamper/adversarial evidence appropriate to the
  selected assurance profile;
- package-output and state secret scan;
- `git diff --check`.

## Exclusions

- publication, tagging, GitHub release, or provider API-token fallback;
- a parallel session, authorization, executor, receipt, or completion system.
