# Complete LBE Agent Runtime Gate

Status: **OPEN — EXPLICIT USER AUTHORIZATION — PUBLICATION PAUSED**

## Machine-selected state

```text
phase: COMPLETE_LBE_AGENT_RUNTIME_IMPLEMENTATION
slice: WORKSPACE_HYGIENE_GOVERNED_DELETION
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

### DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE — PASS

Canonical implementation is commit
`0098e9c86614643e8364dd941e4f23e0295994d7` (`runtime: bridge doctrine
context into provider turns`). Clean-projection acceptance on 2026-08-25 used
an exact `git archive` of that commit with archive SHA-256
`98C125984A2DEBD4B28C6752756EF8435CD99681F02CB7B4A8A6EAB139722A8C`.
Focused doctrine/provider/runtime tests passed `11 passed`; the canonical
CLI/TUI/provider regression set passed `41 passed`; canonical `diff-tree
--check` passed. LoopTool command hash:
`4F96CC80BA93C2D68F53D2375E3501FDAB5334A60D15E88A79F312F68C776766`.
See `docs/acceptance/DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE_CHECKPOINT.md`.

The complete runtime gate remains OPEN: installed runtime/TUI acceptance, live
governed mutation proof, non-bypassability, deterministic completion, and the
remaining capability/evidence loop are not implied by this slice PASS.

Current active slice: `WORKSPACE_HYGIENE_GOVERNED_DELETION`.

### WORKSPACE_HYGIENE_GOVERNED_DELETION — IN PROGRESS

Explicit user authorization permits a bounded workspace-hygiene capability
inside this complete-runtime gate. This slice must reuse the existing workspace
identity, R6C/R6E authorization, `GovernedToolOrchestrator`, `ToolReceipt`,
evidence, persistence, and completion owners rather than introduce a parallel
filesystem authority or unrestricted shell deletion path.

Required behavior:

```text
canonical workspace identity
  -> inventory / reachability classification
  -> deletion proposal
  -> workspace containment + protected-path validation
  -> existing LBE permission decision
  -> approved workspace-scoped deletion adapter
  -> receipt/evidence
  -> post-action validation
```

Required safety/acceptance proof:

- a disposable test path inside the active canonical workspace can be deleted;
- an outside-workspace path is denied;
- protected/current-authority material is denied;
- traversal, symlink, alternate-path, and equivalent escape attempts fail
  closed;
- authorization occurs before adapter execution;
- the direct adapter is not exposed as a bypass to the reasoning provider;
- success and failure both produce correlated receipt/evidence truth;
- cleanup does not absorb or destroy unresolved user-owned work.

Workspace hygiene classifications include at least `CANONICAL_LIVE`,
`ACTIVE_WORK`, `REQUIRED_RUNTIME`, `REQUIRED_BUILD`,
`GENERATED_REGENERABLE`, `CACHE`, `TEMPORARY`, `OS_METADATA`, `HISTORICAL`,
`REFERENCE_ONLY`, `SUPERSEDED`, `DUPLICATE`, `DEAD_CODE`,
`ABANDONED_AGENT_WORK`, `UNKNOWN`, and `PROTECTED_USER_WORK`.

`UNKNOWN` is not authority and must be investigated rather than silently
promoted into provider context. Proven disposable/cache/generated material may
be permanently removed without archive/quarantine copies once bounded deletion
authority is proven. Protected or genuinely unresolved user work must remain
preserved.

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
