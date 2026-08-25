# Project Intent Ledger

Status: **CANONICAL PRE-MUTATION INTENT LEDGER**

Every meaningful repository mutation must resolve to exactly one intent record before staging.
The machine gate binds the active slice to the `INTENT_ID`, and the affected structure must exist
in `PROJECT_INDEX.md`.

## INTENT LBE-INTENT-WORKSPACE-HYGIENE-001

```text
INTENT_ID: LBE-INTENT-WORKSPACE-HYGIENE-001
STATUS: COMPLETED
REQUEST: Govern workspace document hygiene and bounded disposable deletion.
WHY: Prevent unexplained, stale, duplicate, generated, or abandoned workspace material from being treated as current project authority.
AFFECTED_STRUCTURE: docs/, scripts/, .lbe/, .agent/, lbe_guard_inspector/, tests/, unused-in-repo/
EXISTING_OWNER: LBE governance, documentation, runtime orchestration, and validation owners.
DESIRED_RESULT: Every material document has an owner, intent, reachability classification, and safe disposition; disposable deletion is governed and receipt-backed.
NON_GOALS: No new execution system, no unrestricted deletion, no destruction of unknown user work, no publication, no provider/UI architecture change.
REUSE_DECISION: Reuse existing machine gate, tool orchestrator, receipt, evidence, and documentation owners.
AUTHORITY_IMPACT: Strengthens pre-mutation checks without creating a second authority owner.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,docs/,scripts/check-implementation-gate.py,.lbe/governance/,.agent/,lbe_guard_inspector/,tests/,unused-in-repo/
REQUIRED_EVIDENCE: index/ledger match, staged-scope match, focused tests, diff check, protected-work preservation
MACHINE_SLICE: WORKSPACE_HYGIENE_GOVERNED_DELETION
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/WORKSPACE_HYGIENE_GOVERNED_DELETION_CHECKPOINT.md
```

## INTENT LBE-INTENT-MANDATORY-GOVERNED-MUTATION-DISPATCH-001

```text
INTENT_ID: LBE-INTENT-MANDATORY-GOVERNED-MUTATION-DISPATCH-001
STATUS: COMPLETED
REQUEST: Make LBE governed dispatch mandatory for the existing agent coding mutation path, covering bounded workspace text mutation, registered process execution, and main-only Git mutation while keeping arbitrary native mutation tools unavailable.
WHY: The LBE product requires providers to reason and request capabilities while LBE alone owns authorization, execution, receipts, and evidence. Direct filesystem, shell, or Git mutation exposure would bypass the product wall.
AFFECTED_STRUCTURE: lbe_guard_inspector/, tests/, docs/acceptance/, docs/governance/, docs/CURRENT_STATUS.md, .lbe/governance/
EXISTING_OWNER: R6C authorization resolver; R6E GovernedToolOrchestrator, ToolRegistry, ToolRequest, and ToolReceipt; GovernedProviderReasoningController; existing workspace/session identity; provider continuation; validation/completion owners.
DESIRED_RESULT: Provider-facing coding turns receive only LBE-generated tool definitions; bounded workspace mutation and Git mutation execute through existing R6C/R6E owners with receipts; arbitrary shell/native mutation remains unavailable; registered process commands are explicit and bounded.
NON_GOALS: No second executor, no second authorization owner, no second receipt/session/completion owner, no unrestricted shell, no branch/worktree creation, no push/publication, no TUI redesign, no lbe-core mutation, no direct Cline authority.
REUSE_DECISION: REUSE GovernedProviderReasoningController, R6C authorization, R6E orchestration/receipts, agent guidance, workspace governance helpers, provider continuation, and current session identity. ADAPT only tool specifications/handlers and provider registration. REJECT native filesystem/shell/Git exposure.
AUTHORITY_IMPACT: LBE authority remains unchanged; the agent-facing capability surface becomes stricter and more useful.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: provider-only LBE tool schema, contained write proof, stale-write denial, arbitrary-shell denial, bounded registered-process proof, primary-main Git proof, governed-staging proof, authorization-before-execution, correlated receipts, read-only audit/investigation preservation, duplicate-authority scan
MACHINE_SLICE: MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH_CHECKPOINT.md
```

## INTENT LBE-INTENT-GOVERNED-EXTERNAL-CAPABILITY-REGISTRATION-001

```text
INTENT_ID: LBE-INTENT-GOVERNED-EXTERNAL-CAPABILITY-REGISTRATION-001
STATUS: COMPLETED
REQUEST: Add one LBE-owned registration contract for MCP, plugin, subagent, network, and hosted-service capabilities so integrations can be exposed to providers only through existing ToolRegistry/R6C/R6E dispatch.
WHY: Current source has no runtime MCP/plugin/subagent owner and no generic agent-facing network/hosted-service owner. External integrations must become registered governed capabilities rather than direct provider tools or parallel executors.
AFFECTED_STRUCTURE: lbe_guard_inspector/runtime/, tests/, docs/acceptance/, docs/governance/, docs/CURRENT_STATUS.md, .lbe/governance/
EXISTING_OWNER: ToolRegistry; GovernedToolOrchestrator; R6C authorization resolver; ToolRequest/ToolReceipt; GovernedProviderReasoningController; provider continuation; canonical session/workspace/completion owners. Existing provider HTTP and local callback transports remain transport-specific and are not promoted into generic external authority.
DESIRED_RESULT: Preconfigured external adapters are classified by kind, registered as ToolSpec/ToolHandler pairs, projected to the provider only through LBE-generated tool definitions, authorized before execution, and returned as correlated ToolReceipt evidence. Agent-controlled endpoint/executable/shell transport selection is rejected.
NON_GOALS: No generic arbitrary HTTP client, no raw endpoint tool, no shell transport, no second executor, no second authorization/receipt/session/completion owner, no direct MCP/plugin/subagent authority, no publication, no TUI redesign.
REUSE_DECISION: REUSE ToolRegistry, ToolSpec, ToolExecutionContext, R6C, R6E, provider tool projection and receipt continuation. ADD only the missing external capability registration metadata/validation layer and optional controller injection seam.
AUTHORITY_IMPACT: No new execution authority; this constrains future external integrations to the existing LBE execution wall.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/runtime/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: five external kinds classified, pre-registration required, raw transport arguments denied, network metadata enforced, provider-only LBE projection, authorization-before-adapter execution, correlated receipts, unregistered fail-closed, no duplicate authority owner
MACHINE_SLICE: GOVERNED_EXTERNAL_CAPABILITY_REGISTRATION
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/GOVERNED_EXTERNAL_CAPABILITY_REGISTRATION_CHECKPOINT.md
```

## INTENT LBE-INTENT-FIRST-RUN-LIVE-SESSION-ENTRY-001

```text
INTENT_ID: LBE-INTENT-FIRST-RUN-LIVE-SESSION-ENTRY-001
STATUS: COMPLETED
REQUEST: Provide one product-level first-run/live-session entry path that creates or restores a persisted LBE session using the existing workspace, provider/profile, policy, session, provider-turn, and terminal owners.
WHY: The runtime pieces are proven individually, but users should enter the LBE product through one bounded start path instead of manually composing session creation/restoration and terminal entry.
AFFECTED_STRUCTURE: lbe_guard_inspector/cli.py, lbe_guard_inspector/session_memory_runtime.py, lbe_guard_inspector/textual_tui.py, tests/, docs/acceptance/, docs/governance/, docs/CURRENT_STATUS.md, .lbe/governance/
EXISTING_OWNER: CLI thin control plane; SessionMemoryRuntimeBridge and WorkspaceMemoryStore persisted session owners; provider registry/profile/config/health owners; BackgroundProviderTurnRuntime and GovernedAgentGateway; Textual LBE projection/control client.
DESIRED_RESULT: `lbe start` deterministically restores an existing session or creates one new persisted session from explicit workspace/mode/provider/model/profile inputs, validates provider identity/config where execution is requested, then enters the existing live TUI/runtime without introducing a second session or provider authority.
NON_GOALS: No new session database, no new credential store, no new provider registry, no provider fallback, no direct external execution bypass, no TUI redesign, no publication, no lbe-core/lbe-tui mutation.
REUSE_DECISION: REUSE `_session_create`, `_runtime_from_state`, WorkspaceMemoryStore, SessionMemoryRuntimeBridge, existing provider validation/configuration, `_tui`, provider turn runtimes, PersistentTurnControl, and Textual projection. ADD only a product-level start resolver/CLI surface and focused acceptance tests.
AUTHORITY_IMPACT: No authority expansion; this composes existing owners into one entry path.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: create-new persisted session, restore-existing persisted session, explicit provider/model consistency, provider-config mismatch denial, no silent provider fallback, stable session identity, existing TUI/runtime owner reuse, no duplicate session/provider authority, full regression
MACHINE_SLICE: FIRST_RUN_LIVE_SESSION_ENTRY
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/FIRST_RUN_LIVE_SESSION_ENTRY_CHECKPOINT.md
```

## INTENT LBE-INTENT-INSTALLED-CAPABILITY-REGISTRY-001

```text
INTENT_ID: LBE-INTENT-INSTALLED-CAPABILITY-REGISTRY-001
STATUS: COMPLETED
REQUEST: Add one persisted, LBE-owned installed capability registry that discovers and configures concrete MCP/plugin/service/subagent adapters, then converts only validated configured entries into the already-proven governed external-capability registration contract.
WHY: The generic external registration contract is proven, but the product still lacks a concrete installed/configured integration inventory. Users need LBE to know which integrations exist and which governed capabilities are actually available without exposing raw transport configuration to the reasoning provider.
AFFECTED_STRUCTURE: lbe_guard_inspector/runtime/, lbe_guard_inspector/cli.py, lbe_guard_inspector/textual_tui.py, tests/, docs/acceptance/, docs/governance/, docs/CURRENT_STATUS.md, .lbe/governance/
EXISTING_OWNER: ExternalCapabilityRegistration/register_external_capabilities; ToolRegistry/R6C/R6E; CLI thin control plane; persisted workspace/session owners; terminal capability projection. No separate integration executor or provider-owned transport authority may be created.
DESIRED_RESULT: LBE can list configured installed integrations, validate their kind/tool identity and configuration provenance, report unavailable/misconfigured entries, and materialize only safe preconfigured adapters into the existing governed registry. The provider sees capability schemas, never raw endpoint/executable/shell credentials or transport-selection authority.
NON_GOALS: No arbitrary MCP auto-execution from filesystem discovery, no generic HTTP client, no shell command registry supplied by the model, no credential plaintext persistence, no direct plugin/subagent authority, no publication, no lbe-core/lbe-tui mutation.
REUSE_DECISION: REUSE external_capabilities.py, ToolRegistry/R6C/R6E, existing configuration/persistence/terminal projection owners. ADD only installed-integration metadata, validation/discovery/config loading, bounded adapter factories, and product/CLI projection.
AUTHORITY_IMPACT: No new execution authority. This turns concrete installed integrations into governed registrations under existing LBE policy.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: persisted installed-registry schema, five-kind configuration classification, invalid/duplicate configuration denial, no plaintext credential persistence, unavailable integration projection, safe conversion to ExternalCapabilityRegistration, provider transport arguments remain hidden, existing R6C/R6E path reused, focused tests, full regression
MACHINE_SLICE: INSTALLED_CAPABILITY_REGISTRY_DISCOVERY
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/INSTALLED_CAPABILITY_REGISTRY_DISCOVERY_CHECKPOINT.md
```

## INTENT LBE-INTENT-INTERFACE-CONTROL-EVIDENCE-SURFACES-001

```text
INTENT_ID: LBE-INTENT-INTERFACE-CONTROL-EVIDENCE-SURFACES-001
STATUS: COMPLETED
REQUEST: Complete the remaining LBE-owned terminal projection and control surfaces by connecting installed integration/MCP state to the existing Textual client and proving settings, provider, session, evidence, receipt/diff detail, interrupt, and cancel surfaces remain backed by existing runtime owners.
WHY: The LBE interface already owns keyboard-first session/provider/evidence/control projection, but `/integrations` and `/mcp` remained hard-coded unavailable placeholders even though the installed capability registry is now proven. Product truth must be projected without creating new execution authority.
AFFECTED_STRUCTURE: lbe_guard_inspector/textual_tui.py, lbe_guard_inspector/tui_view_models.py, lbe_guard_inspector/terminal_projection.py, lbe_guard_inspector/product_entry.py, lbe_guard_inspector/cli.py, tests/, docs/acceptance/, docs/governance/, docs/CURRENT_STATUS.md, .lbe/governance/
EXISTING_OWNER: Textual LBE client; terminal projection; TUI view models; SessionOperationalHistory; PersistentTurnControl; persisted session/provider/settings owners; installed capability registry and existing ToolRegistry projection seam.
DESIRED_RESULT: The live LBE interface truthfully shows installed integration/MCP availability from LBE-owned registry data, keeps settings/provider/session/evidence/diff/control projections owner-backed, and never authorizes or executes integrations merely by displaying them.
NON_GOALS: No UI redesign, no new terminal framework, no new integration executor, no direct TUI filesystem/network/service execution, no second session/provider/authorization/receipt/completion owner, no publication, no lbe-core/lbe-tui mutation.
REUSE_DECISION: REUSE build_textual_tui/run_textual_tui, ToolRegistry projection seam, installed capability registry metadata, terminal event/detail projections, SessionOperationalHistory, PersistentTurnControl, provider and session owners. ADAPT only bounded projection inputs and truthful rendering/tests.
AUTHORITY_IMPACT: No authority expansion. The interface remains projection/control only.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: installed registry projects without execution, integrations command truthfully lists installed state, MCP command filters MCP state, settings/provider remain read-only or owner-delegated, session switching/new session reuse persistence owner, receipt/evidence/diff detail identity preserved, interrupt/cancel route through PersistentTurnControl, no duplicate authority owner, focused TUI regression, full regression
MACHINE_SLICE: LBE_INTERFACE_CONTROL_EVIDENCE_SURFACES
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/LBE_INTERFACE_CONTROL_EVIDENCE_SURFACES_CHECKPOINT.md
```

## INTENT LBE-INTENT-RECOVERY-COMPLETION-PROMOTION-001

```text
INTENT_ID: LBE-INTENT-RECOVERY-COMPLETION-PROMOTION-001
STATUS: ACTIVE
REQUEST: Complete the normal governed coding lifecycle by composing existing R5 bounded recovery, trusted completion-evidence producers, R6F deterministic completion, and validated memory promotion so provider completion remains provisional until LBE proof is ready.
WHY: The normal coding gateway already establishes an immutable completion contract and produces trusted source_change/focused_test/git_status evidence, but it stops before calling the existing completion gate. Recovery and completion are proven separately; the product still needs one owner-composed lifecycle that automatically finalizes deterministic proof and promotes only validated completion truth.
AFFECTED_STRUCTURE: lbe_guard_inspector/agent_integration.py, lbe_guard_inspector/runtime/completion_runtime.py, lbe_guard_inspector/runtime/completion_evidence_producers.py, lbe_guard_inspector/session_memory_runtime.py, lbe_guard_inspector/memory/, tests/, docs/acceptance/, docs/governance/, docs/CURRENT_STATUS.md, .lbe/governance/
EXISTING_OWNER: SessionMemoryRuntimeBridge.run_recoverable/load_recovery_state; lbe_guard_inspector/recovery.py; CodingCompletionRuntime and existing completion gate; CompletionEvidenceProducers; TaskCompletionEvidencePersistence; MemoryPromoter/WorkspaceMemoryStore; GovernedAgentGateway.
DESIRED_RESULT: Mutation-capable reasoning is executed once without automatic retry; trusted idempotent validation/evidence operations may use bounded persisted recovery; provider COMPLETED creates only provisional/unverified task-completion proof; the normal gateway calls the existing deterministic completion gate after trusted evidence exists; READY sets the task COMPLETED and promotes the same task-completion proof to VERIFIED; FAILED/INCOMPLETE never creates verified completion truth.
NON_GOALS: No retry of mutation-capable provider reasoning, no second recovery engine, no second completion evaluator, no provider-selected evidence, no direct promotion of provider prose, no new memory database, no publication, no lbe-core/lbe-tui mutation.
REUSE_DECISION: REUSE R5 recovery through SessionMemoryRuntimeBridge, existing R6F completion runtime/evaluator, C2 evidence producers, MemoryPromoter, task/session persistence and GovernedAgentGateway. ADD only the missing lifecycle composition and provisional-to-verified completion proof contract.
AUTHORITY_IMPACT: No new authority owner. LBE completion truth becomes automatic on the normal path while remaining evidence-gated.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: provider completion provisional before gate, provisional task_complete memory unverified, mutation reasoning not retried, idempotent validation recovery only, recovery state persists across runtime reconstruction, trusted evidence loaded from existing persistence, existing completion gate invoked automatically, READY alone promotes task_complete VERIFIED, failed/incomplete cannot promote verified completion, terminal recovery state prevents duplicate validation operation execution, no duplicate authority owner, focused integration tests, full regression
MACHINE_SLICE: RECOVERY_COMPLETION_PROMOTION_INTEGRATION
SUPERSEDES: none
RESULT: IN_PROGRESS
```

## INTENT LBE-INTENT-CLINE-AGENTRUNTIME-001

```text
INTENT_ID: LBE-INTENT-CLINE-AGENTRUNTIME-001
STATUS: ACCEPTED_PRODUCT_DIRECTION
REQUEST: Use Cline AgentRuntime interaction and continuation mechanics behind an LBE-owned governance adapter.
WHY: Reuse the mature agent loop without creating a second LBE authority/runtime.
AFFECTED_STRUCTURE: lbe_guard_inspector/, docs/design/, docs/research/, .cline/
EXISTING_OWNER: LBE workspace/session identity, authorization, dispatch, receipts, evidence,
persistence, validation, and completion owners.
DESIRED_RESULT: Cline mechanics are adapted behind LBE authority; native Cline mutation/execution is
not canonical.
NON_GOALS: No direct Cline mutation authority, no second session authority, no React runtime before
the adapter boundary is proven.
REUSE_DECISION: REUSE continuation/event/tool mechanics; ADAPT provider and presentation mechanics;
REJECT native overlapping mutation/execution.
AUTHORITY_IMPACT: LBE authority remains unchanged.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,docs/design/,docs/research/,.cline/
REQUIRED_EVIDENCE: deny-before-execute, allow-exactly-once, receipt-backed continuation, event mapping,
native mutation disabled, canonical LBE session ownership
MACHINE_SLICE: FUTURE_SLICE_NOT_ACTIVE
SUPERSEDES: none
RESULT: NOT_ACTIVE
```

## Ledger law

```text
NO INTENT -> NO CHANGE
NO OWNER -> NO CHANGE
NO INDEX ENTRY -> NO CHANGE
NO MACHINE-GATE MATCH -> NO CHANGE
```

Completed intents must update `RESULT` and retain the evidence/commit reference. Proposed intents
remain non-authorizing until explicitly bound to the machine gate.
