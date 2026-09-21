# Project Intent Ledger

Status: **CANONICAL PRE-MUTATION INTENT LEDGER**

Every meaningful repository mutation must resolve to exactly one intent record before staging.
The machine gate binds the active slice to the `INTENT_ID`, and the affected structure must exist
in `PROJECT_INDEX.md`.

## Current reconciliation — 2026-09-05

The current implementation uses the originating project-planning concepts as a
bounded LBE startup projection. `lbe start` profiles the selected workspace and
returns the applicable guard catalog; it does not execute guards or transfer
authorization, execution, receipt, evidence, persistence, validation, or
completion authority to the planner, provider, or CLI.

The CEP plan is connected to the canonical `cep` rule pack. The callback
implementation is registered as `cep.callback_contract` through `rules/cep.py`,
and the pack loader no longer mistakes the imported implementation for a second
rule. The reference files remain provenance and schema inputs, not executable
configuration.

Current proof for this bounded integration is recorded as:

```text
focused adapter validation         = PASS — 15/15
live parent->child->parent proof   = PASS
live cancellation terminality      = PASS
canonical verifier proof           = PASS
ready for gate closure             = YES
```

This reconciliation does not advance or close
`PERSISTED_CHILD_RESULT_PARENT_CONTINUATION_AND_CORRELATION`.

## INTENT LBE-INTENT-PROJECT-PROFILE-GUARD-CATALOG-INTEGRATION-001

```text
INTENT_ID: LBE-INTENT-PROJECT-PROFILE-GUARD-CATALOG-INTEGRATION-001
STATUS: COMPLETED (bounded integration; active TUI gate unchanged)
REQUEST: Connect the repository's project-profile, rule-pack, and planner-output concepts to the canonical LBE start and audit paths without creating a second planner, guard executor, or authority owner.
WHY: The reference planning artifacts carry meaningful repository architecture and must inform the first profile/guard decision while remaining separate from live runtime configuration.
AFFECTED_STRUCTURE: lbe_guard_inspector/cli.py,lbe_guard_inspector/project_profiler.py,lbe_guard_inspector/guard_catalog.py,audit_controller.py,rules/cep.py,rules/cep_callback.py,examples/reference/,docs/acceptance/,docs/contracts/,docs/governance/,docs/CURRENT_STATUS.md
EXISTING_OWNER: ProjectProfiler; canonical guard catalog; deterministic rule-pack loader; LBE CLI/session owners; existing authorization, execution, receipt, evidence, persistence, validation, and completion owners.
DESIRED_RESULT: `lbe start` exposes read-only `project_profile` and `guard_catalog` projections; CEP profiles select the canonical `cep` rules; the callback contract resolves without duplicate rule discovery; reference planner/registry files remain provenance inputs.
NON_GOALS: No autonomous planner execution; no guard execution during startup; no provider or client authority; no reference-file loading as live configuration; no new test files; no TUI gate advancement or publication.
REUSE_DECISION: REUSE ProjectProfiler, select_guard_catalog, existing audit loader, canonical CEP rule implementation, and LBE runtime owners. ADAPT only the bounded startup projection and CEP pack registration.
AUTHORITY_IMPACT: None. LBE remains the sole authority for authorization, governed execution, receipts, evidence, persistence, validation, and completion.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,audit_controller.py,rules/,examples/reference/,docs/contracts/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md
REQUIRED_EVIDENCE: startup profile/catalog projection; canonical CEP rule resolution; target-profile audit scope; no duplicate callback rule discovery; focused integration regression; full Python regression; preserved active TUI gate.
MACHINE_SLICE: NONE — bounded implementation record; does not alter the machine-declared active slice.
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/CURRENT_STATUS.md and .agent/evidence/CURRENT_TASK.md
```

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
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,docs/DOCUMENT_INTENT_MANIFEST.md,.lbe/governance/
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
STATUS: COMPLETED
REQUEST: Complete the normal governed coding lifecycle by composing existing R5 bounded recovery, trusted completion-evidence producers, R6F deterministic completion, and validated memory promotion so provider completion remains provisional until LBE proof is ready.
WHY: The normal coding gateway already establishes an immutable completion contract and produces trusted source_change/focused_test/git_status evidence, but it stops before calling the existing completion gate. Recovery and completion are proven separately; the product still needs one owner-composed lifecycle that automatically finalizes deterministic proof and promotes only validated completion truth.
AFFECTED_STRUCTURE: lbe_guard_inspector/agent_integration.py, lbe_guard_inspector/runtime/completion_runtime.py, lbe_guard_inspector/runtime/completion_evidence_producers.py, lbe_guard_inspector/session_memory_runtime.py, lbe_guard_inspector/memory/, tests/, docs/acceptance/, docs/governance/, docs/CURRENT_STATUS.md, .lbe/governance/
EXISTING_OWNER: SessionMemoryRuntimeBridge.run_recoverable/load_recovery_state; lbe_guard_inspector/recovery.py; CodingCompletionRuntime and existing completion gate; CompletionEvidenceProducers; TaskCompletionEvidencePersistence; MemoryPromoter/WorkspaceMemoryStore; GovernedAgentGateway.
DESIRED_RESULT: Mutation-capable reasoning is executed once without automatic retry; trusted idempotent validation/evidence operations may use bounded persisted recovery; provider COMPLETED creates only provisional/unverified task-completion proof; the normal gateway calls the existing deterministic completion gate after trusted evidence exists; READY sets the task COMPLETED and promotes the same task-completion proof to VERIFIED; FAILED/INCOMPLETE never creates verified completion truth.
NON_GOALS: No retry of mutation-capable provider reasoning, no second recovery engine, no second completion evaluator, no provider-selected evidence, no direct promotion of provider prose, no new memory database, no publication, no lbe-core/lbe-tui mutation.
REUSE_DECISION: REUSE R5 recovery through SessionMemoryRuntimeBridge, existing R6F completion runtime/evaluator, C2 evidence producers, MemoryPromoter, task/session persistence and GovernedAgentGateway. ADD only the missing lifecycle composition and provisional-to-verified completion proof contract.
AUTHORITY_IMPACT: No new authority owner. LBE completion truth becomes automatic on the normal path while remaining evidence-gated.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,docs/DOCUMENT_INTENT_MANIFEST.md,.lbe/governance/
REQUIRED_EVIDENCE: provider completion provisional before gate, provisional task_complete memory unverified, mutation reasoning not retried, idempotent validation recovery only, recovery state persists across runtime reconstruction, trusted evidence loaded from existing persistence, existing completion gate invoked automatically, READY alone promotes task_complete VERIFIED, failed/incomplete cannot promote verified completion, terminal recovery state prevents duplicate validation operation execution, no duplicate authority owner, focused integration tests, full regression
MACHINE_SLICE: RECOVERY_COMPLETION_PROMOTION_INTEGRATION
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/RECOVERY_COMPLETION_PROMOTION_CHECKPOINT.md
```

## INTENT LBE-INTENT-INSTALLED-PACKAGE-END-TO-END-ACCEPTANCE-001

```text
INTENT_ID: LBE-INTENT-INSTALLED-PACKAGE-END-TO-END-ACCEPTANCE-001
STATUS: COMPLETED
REQUEST: Prove the complete LBE runtime from an isolated installed distribution, not from repository-source imports, exercising the normal product entry, persisted session/provider path, governed capability dispatch, evidence, recovery, and deterministic completion.
WHY: All complete-runtime source slices are proven; the remaining product requirement is proof that the packaged and installed artifact composes those owners correctly as the product.
AFFECTED_STRUCTURE: lbe_guard_inspector/,tests/,scripts/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
EXISTING_OWNER: product_entry and CLI entry point; SessionMemoryRuntimeBridge/WorkspaceMemoryStore; provider registry/config/health; GovernedAgentGateway; R6C authorization; R6E GovernedToolOrchestrator/ToolRegistry/ToolReceipt; CompletionEvidenceProducers; CodingCompletionRuntime; R5 recovery; MemoryPromoter; Textual LBE interface.
DESIRED_RESULT: A freshly built isolated installed LBE distribution can create/restore a session, use an explicitly configured provider, execute governed capabilities only through LBE, produce correlated evidence and receipts, deterministically validate completion, and survive runtime reconstruction without importing canonical runtime code from the source tree.
NON_GOALS: No TUI redesign, no session-lifecycle-unification patch, no Cline integration, no lbe-tui activation, no lbe-core mutation, no release/tag/publication, no version change unless an already-proven packaging defect blocks the installed proof.
REUSE_DECISION: ACCEPTANCE ONLY. Reuse all existing LBE runtime, provider, session, authorization, dispatch, receipt, evidence, recovery, completion, promotion, and Textual owners; add no authority.
AUTHORITY_IMPACT: NONE. Acceptance only; no new runtime/provider/session/execution/completion authority.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,docs/DOCUMENT_INTENT_MANIFEST.md,lbe_guard_inspector/,tests/,scripts/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: isolated build and wheel hash, installed entrypoint/import isolation, persisted session create/restore, provider/model identity, installed registry fail-closed behavior, governed capability receipt/evidence, deterministic completion and verified promotion, recovery reconstruction, installed interface smoke, focused installed tests, full regression.
MACHINE_SLICE: INSTALLED_PACKAGE_END_TO_END_ACCEPTANCE
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/INSTALLED_PACKAGE_END_TO_END_ACCEPTANCE_CHECKPOINT.md
```

## INTENT LBE-INTENT-SESSION-APPLICATION-CONTRACT-UNIFICATION-001

```text
INTENT_ID: LBE-INTENT-SESSION-APPLICATION-CONTRACT-UNIFICATION-001
STATUS: COMPLETED
REQUEST: Unify CLI and Textual session/provider lifecycle operations behind one shared LbeSessionService contract while preserving existing LBE persistence, provider, and turn-control owners.
WHY: The preserved lifecycle patch removes duplicate CLI/TUI lifecycle call sites, but it must be reconciled against current main and activated under its own architecture intent before it can be used.
AFFECTED_STRUCTURE: lbe_guard_inspector/session_lifecycle.py,lbe_guard_inspector/cli.py,lbe_guard_inspector/textual_tui.py,tests/test_session_lifecycle.py,tests/test_cli.py,tests/test_textual_tui.py,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
EXISTING_OWNER: SessionMemoryRuntimeBridge / WorkspaceMemoryStore; ProviderRegistry; PersistentTurnControl; existing CLI and Textual projection owners. No second session, provider, persistence, or turn-control authority may be created.
DESIRED_RESULT: CLI and Textual session creation, resume, and provider selection call one shared LbeSessionService while persisted identity, provider/model state, event projection, and turn control remain owned by existing runtime services.
NON_GOALS: No TUI redesign; no lbe-tui activation; no lbe-core mutation; no provider transport replacement; no new persistence or authorization system; no publication or release.
REUSE_DECISION: ADAPT the preserved lifecycle patch only after hash verification and reconcile it against current main; preserve SessionMemoryRuntimeBridge, WorkspaceMemoryStore, ProviderRegistry, PersistentTurnControl, and existing CLI/Textual owners.
AUTHORITY_IMPACT: One shared application-service contract; no new persistence, provider, execution, authorization, receipt, or completion authority.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,docs/DOCUMENT_INTENT_MANIFEST.md,lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: preserved patch hash match, shared lifecycle service used by CLI and Textual, persisted session identity across restart, provider/model identity persistence, no duplicate lifecycle authority, focused lifecycle/CLI/Textual/provider/session tests, full regression, fresh installed regression.
MACHINE_SLICE: SESSION_APPLICATION_CONTRACT_UNIFICATION
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/SESSION_APPLICATION_CONTRACT_UNIFICATION_CHECKPOINT.md
```

## INTENT LBE-INTENT-CLINE-AGENTRUNTIME-001

```text
INTENT_ID: LBE-INTENT-CLINE-AGENTRUNTIME-001
STATUS: COMPLETED
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
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,docs/acceptance/,docs/design/,docs/research/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: deny-before-execute, allow-exactly-once, receipt-backed continuation, event mapping,
native mutation disabled, canonical LBE session ownership
MACHINE_SLICE: LBE_AGENT_CONVERSATION_CONTINUATION
SUPERSEDES: none
RESULT: PASS
ACTIVE_SCOPE: LBE-owned conversation projection, continuation, streaming/runtime feedback, and event presentation using existing PersistentTurnControl, provider turn runtime, and terminal projection owners.
NON_GOALS_FOR_ACTIVE_SLICE: No independent Cline runtime, provider, session, execution, authorization, receipt, evidence, persistence, or completion authority; no lbe-tui activation; no branch/worktree creation; no publication.
COMPLETION_CHECKPOINT: docs/acceptance/LBE_AGENT_CONVERSATION_CONTINUATION_CHECKPOINT.md
```

## INTENT LBE-INTENT-LBE-INTERFACE-PRODUCT-SURFACE-001

```text
INTENT_ID: LBE-INTENT-LBE-INTERFACE-PRODUCT-SURFACE-001
STATUS: COMPLETED
REQUEST: Deliver the usable LBE interface on the existing canonical Textual owner, with the supplied visual direction and selectively adapted interaction mechanics behind LBE authority.
WHY: The product identity is LBE and the interface must expose the real persisted session, provider, capability, receipt, evidence, and control state in a usable terminal surface.
AFFECTED_STRUCTURE: lbe_guard_inspector/textual_tui.py,lbe_guard_inspector/terminal_projection.py,lbe_guard_inspector/tui_view_models.py,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
EXISTING_OWNER: Textual LBE interface; SessionMemoryRuntimeBridge; WorkspaceMemoryStore; ProviderRegistry; PersistentTurnControl; ToolRegistry; ToolReceipt; persisted evidence and completion owners.
DESIRED_RESULT: A runnable LBE interface provides a clear conversation surface, persisted session/provider state, capability visibility, streaming/runtime feedback, receipt/evidence detail, and keyboard controls without acquiring execution or authorization authority.
NON_GOALS: No lbe-tui activation; no independent provider transport; no independent session identity; no native shell execution; no second runtime, persistence, authorization, receipt, evidence, or completion owner; no publication; no branch or worktree creation.
REUSE_DECISION: ADAPT approved interaction, continuation, event, streaming, layout, and branding mechanics from reference inputs only; preserve LBE runtime and authority owners.
AUTHORITY_IMPACT: LBE interface remains a projection/control surface; no new authority.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: canonical Textual launch, persisted session projection, provider and capability projection, receipt/evidence detail, keyboard controls, focused UI tests, full regression, real local launch.
MACHINE_SLICE: LBE_INTERFACE_PRODUCT_SURFACE
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/LBE_INTERFACE_PRODUCT_SURFACE_CHECKPOINT.md
```

## INTENT LBE-INTENT-LIVE-PROVIDER-CONVERSATION-001

```text
INTENT_ID: LBE-INTENT-LIVE-PROVIDER-CONVERSATION-001
STATUS: COMPLETED
REQUEST: Deliver progressive provider conversation feedback in the LBE interface using the existing LBE provider adapter, persisted event history, background turn runtime, and Textual projection.
WHY: The LBE product must show live model feedback while preserving LBE ownership of provider selection, session identity, authorization, execution, receipts, evidence, persistence, and completion.
EXISTING_OWNER: OpenAI-compatible provider adapter; provider turn runtime; PersistentTurnControl; SessionOperationalHistory; Textual LBE interface.
DESIRED_RESULT: Provider message deltas are normalized and persisted as they arrive, the LBE interface projects them during a running turn, and terminal completion remains authoritative and deterministic.
NON_GOALS: No independent Cline runtime; no direct provider/session/execution authority from reference code; no lbe-tui activation; no new persistence or authorization system; no publication; no branch/worktree creation.
REUSE_DECISION: ADAPT approved streaming/event presentation mechanics behind existing LBE provider and history owners.
AUTHORITY_IMPACT: None.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: normalized progressive events, persisted live projection, cancellation truth, focused provider/runtime/Textual tests, full regression, canonical checkpoint.
MACHINE_SLICE: LBE_LIVE_PROVIDER_CONVERSATION
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/LBE_LIVE_PROVIDER_CONVERSATION_CHECKPOINT.md
```

## INTENT LBE-INTENT-PARENT-CONTINUATION-DEEP-CORRELATION-001

```text
INTENT_ID: LBE-INTENT-PARENT-CONTINUATION-DEEP-CORRELATION-001
STATUS: ACTIVE
REQUEST: Reconcile the parent-continuation and deep-correlation machine gate so the
         persisted child result is the authoritative parent input, with the live proof
         chain recorded as evidence-backed PASS rather than stale PENDING state.
WHY: The parent-continuation gate must reflect the proven local adapter validation,
     live parent->child->parent proof, cancellation terminality proof, and canonical
     verifier proof without creating a second authority or heuristic correlation path.
AFFECTED_STRUCTURE: PROJECT_INDEX.md,.lbe/governance/implementation-gates.json,docs/CURRENT_STATUS.md,
                    docs/IMPLEMENTATION_PLAN.md,docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md,
                    docs/acceptance/PARENT_CONTINUATION_AND_DEEP_CORRELATION_ACCEPTANCE_GATE.md,
                    docs/governance/PROJECT_INTENT_LEDGER.md
EXISTING_OWNER: Existing LBE session/provider/authorization/ToolRegistry/GovernedToolOrchestrator/
                receipt/evidence/persistence/validation/completion owners; existing provider-turn
                runtime and continuation owners; existing Cline mechanics as projection/reuse input.
DESIRED_RESULT: The canonical gate records the persisted-child-result continuation slice as the
                active machine gate, marks all ordered slices PASS, exposes READY_FOR_GATE_CLOSURE,
                and preserves the invariant that parent continuation consumes authoritative LBE
                child results only.
NON_GOALS: No new runtime authority, no heuristic correlation, no second session/provider/receipt/
           evidence/completion owner, no publication, no branch/worktree creation, no UI redesign.
REUSE_DECISION: REUSE existing LBE persistence, continuation, receipt, validation, and completion
                owners plus existing Cline continuation mechanics where compatible; ADAPT only the
                gate projection and active slice bookkeeping.
AUTHORITY_IMPACT: LBE remains sole authority. The projection is bookkeeping only.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,.lbe/governance/,docs/CURRENT_STATUS.md,docs/IMPLEMENTATION_PLAN.md,docs/acceptance/,docs/governance/
REQUIRED_EVIDENCE: parent consumes persisted authoritative LBE child terminal result; no transient
                   local/Cline result is authoritative; provider_tool_call_id ↔ lbe_call_id ↔
                   child_run_id ↔ runtime_operation_id ↔ tool_receipt_id are all correlated;
                   no heuristic correlation; focused adapter validation; live continuation proof;
                   cancellation terminality proof; canonical verifier proof.
MACHINE_SLICE: PERSISTED_CHILD_RESULT_PARENT_CONTINUATION_AND_CORRELATION
SUPERSEDES: none
RESULT: ACTIVE
COMPLETION_CHECKPOINT: docs/acceptance/PARENT_CONTINUATION_AND_DEEP_CORRELATION_ACCEPTANCE_CHECKPOINT.md
```

## INTENT LBE-INTENT-CLINE-SURFACE-DIRECTION-001 (AMENDED: HTML-BASED LBE TUI)

```text
INTENT_ID: LBE-INTENT-CLINE-SURFACE-DIRECTION-001
STATUS: ACCEPTED (explicit user product decision, recorded 2026-08-26)
REQUEST: Record the product owner's binding technology decision for the LBE interface surface:
         the Cline CLI/SDK (https://cline.bot/cli, https://docs.cline.bot/sdk/overview) is the
         approved implementation surface direction; the Python/Textual LBE interface is REJECTED
         as the final LBE product UI technology.
WHY: The product owner directed reuse of mature, already-served Cline CLI/SDK capabilities
     instead of re-implementing them. Continuation of the pre-existing Python/Textual interface
     was an agent interpretation, never an approved final technology decision.
AFFECTED_STRUCTURE: docs/governance/, docs/CURRENT_STATUS.md, docs/research/, future lbe_guard_inspector/ presentation surfaces
EXISTING_OWNER: Product owner decision authority; LBE runtime/control/event contracts (unchanged).
DESIRED_RESULT: Future interface/product work targets Cline CLI/SDK mechanics under LBE
                authority (REUSE runtime interaction/continuation mechanics; ADAPT provider and
                presentation mechanics); no further Python/Textual product-surface investment.
NON_GOALS: No retroactive rewriting or deletion of completed checkpoint records; no second
           execution/authorization/session/persistence/completion authority; no immediate code
           deletion in this record; migration scoping happens in a follow-up slice.
REUSE_DECISION: REUSE Cline AgentRuntime/CLI/SDK mature mechanics; ADAPT onto LBE-owned
                governance, authorization, receipts, evidence, persistence, and completion;
                REJECT continued Python/Textual development as the product UI platform.
AUTHORITY_IMPACT: Presentation-platform ownership changes direction. LBE remains sole runtime,
                  authorization, receipt, evidence, session, and completion authority.
AMENDS_INTERPRETATION_OF: LBE-INTENT-LBE-INTERFACE-PRODUCT-SURFACE-001,
                          LBE-INTENT-LIVE-PROVIDER-CONVERSATION-001
                          (their runtime/PASS results remain valid evidence; their implicit
                          conclusion that Textual is the permanent final UI technology is
                          hereby overridden by explicit product-owner decision).
SUPERSEDES: none (amends interpretation only)
RESULT: DIRECTION ACCEPTED
MIGRATION_NOTE: Cline is an interaction/reference input only. The supplied HTML visual contract
                is the basis for the LBE TUI; no copied Cline CLI/OpenTUI product surface or
                Textual -> Cline product transition is authorized.
```

## INTENT LBE-INTENT-CLINE-RUNTIME-WIRING-001

```text
INTENT_ID: LBE-INTENT-CLINE-RUNTIME-WIRING-001
STATUS: ACCEPTED (implements LBE-INTENT-CLINE-SURFACE-DIRECTION-001)
REQUEST: Provide an LBE-owned foreground provider turn runtime that executes turns through the
         governed Cline Node worker (pinned AgentRuntime mechanics) behind existing LBE owners.
WHY: The stdio bridge proved worker mechanics in isolation; product turns require one runtime
     owner persisting worker events through SessionOperationalHistory while completion,
     authorization, receipts, and evidence remain LBE-owned.
AFFECTED_STRUCTURE: lbe_guard_inspector/runtime/cline_provider_turn_runtime.py, tests/, docs/governance/
EXISTING_OWNER: GovernedClineWorker; GovernedToolOrchestrator/R6C/R6E; SessionOperationalHistory;
                PersistentTurnControl-compatible turn lifecycle; turn finalization owners.
DESIRED_RESULT: ClineWorkerTurnRuntime satisfies the same foreground runtime contract as the
                existing non-streaming owner (run/cancel/was_cancelled/supports_cancellation),
                persists model message/turn events, fails closed on worker errors, and records
                no completion truth for cancelled turns.
NON_GOALS: No UI work (owned by parallel UI-experience slice); no second execution,
           authorization, receipt, session, persistence, or completion authority; no CLI entry
           rewiring in this record; no publication.
REUSE_DECISION: REUSE GovernedClineWorker protocol/lifecycle, GovernedToolOrchestrator tool
                mediation, SessionOperationalHistory event/finalization owners.
AUTHORITY_IMPACT: None. Cline remains mechanics under LBE authority.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/runtime/,tests/,docs/governance/
REQUIRED_EVIDENCE: completed turn persists message + finalizes COMPLETED; failed turn persists
                   model.error + finalizes FAILED; cancelled turn records no completion truth;
                   worker exception fails closed; focused tests pass.
SUPERSEDES: none
RESULT: PASS (focused)
MACHINE_SLICE: CLINE_RUNTIME_WIRING
```

## INTENT LBE-INTENT-CLINE-NATIVE-SURFACE-INTEGRATION-001 — SUPERSEDED / REFERENCE ONLY

```text
INTENT_ID: LBE-INTENT-CLINE-NATIVE-SURFACE-INTEGRATION-001
STATUS: SUPERSEDED (product-owner HTML-based TUI direction; retained as reference history)
REQUEST: Historical proposal to integrate the native Cline CLI/OpenTUI source as the LBE terminal surface while
         replacing visible product identity with LetterBlack Execution Engine and routing
         all authority-bearing runtime callbacks through existing LBE owners.
WHY: Cline CLI/OpenTUI is the selected base implementation and interaction model. LBE must
     reuse its native terminal mechanics without exposing Cline as the visible product or
     inheriting Cline's independent permission, execution, persistence, receipt, evidence,
     or completion authority.
AFFECTED_STRUCTURE: vendor/cline-cli/, lbe_guard_inspector/, tests/, .github/workflows/,
                    docs/acceptance/, docs/governance/, PROJECT_INDEX.md
EXISTING_OWNER: Pinned Cline CLI/OpenTUI source for rendering and interaction mechanics;
                LBE session, provider, authorization, ToolRegistry, GovernedToolOrchestrator,
                ToolReceipt, evidence, persistence, cancellation, and completion owners.
DESIRED_RESULT: Historical reference only. The current canonical UI is the HTML-based LBE TUI
                under `.ui-preview/`; Cline mechanics remain reference inputs and any governed
                bridge must be implemented through existing LBE owners.
NON_GOALS: No native Cline CLI/OpenTUI product surface, no separate Python/Textual UI, no native Cline mutation
           authority, no second session/provider/persistence/authorization/receipt/evidence/
           completion owner, no branch, no worktree, no publication, no global installation
           mutation, and no unpinned dependency drift.
REUSE_DECISION: REUSE pinned Cline CLI/OpenTUI rendering, input, dialog, streaming, and
                session interaction mechanics; ADAPT the runtime callback bridge and visible
                terminology to LBE; REJECT native Cline authority-bearing tool execution.
AUTHORITY_IMPACT: LBE remains sole authority for permissions, governed execution, receipts,
                  evidence, persistence, cancellation, and completion truth.
REQUIRED_EVIDENCE: pinned upstream source identity; native OpenTUI local launch; exact visible
                   branding audit; LBE authority callback tests; denied/allowed tool receipt
                   tests; session restore; streaming; cancellation; package/build proof;
                   full Python regression; native CLI tests; main-only topology proof.
MACHINE_SLICE: CLINE_NATIVE_SURFACE_INTEGRATION
RESULT: SUPERSEDED / REFERENCE_ONLY
SUPERSEDED_BY: LBE-INTENT-CLINE-SURFACE-DIRECTION-001 and LBE-INTENT-LBE-HOME-PROVIDER-CONTRACT-VERIFICATION-001
```

## INTENT LBE-INTENT-TUI-P2P3-GOVERNED-INTEGRATION-001

```text
INTENT_ID: LBE-INTENT-TUI-P2P3-GOVERNED-INTEGRATION-001
STATUS: SUPERSEDED BY LBE-INTENT-CLINE-CLI-LBE-RUNTIME-INTEGRATION-001
REQUEST: Activate the bounded TUI P2/P3 governed-execution integration slice through the existing LBE R6C/R6E authorization, ToolRegistry, GovernedToolOrchestrator, ToolReceipt, evidence, validation, and completion owners.
WHY: P1 read-only attachment is complete. The TUI now requires an explicitly scoped integration slice to submit authority-bearing requests without creating a second executor, authorization owner, receipt owner, evidence owner, or completion owner.
AFFECTED_STRUCTURE: PROJECT_INDEX.md,config.json,docs/governance/PROJECT_INTENT_LEDGER.md,.lbe/governance/implementation-gates.json,lbe_guard_inspector/,tests/,docs/acceptance/
EXISTING_OWNER: Existing LBE R6C authorization resolver; R6E ToolRegistry, GovernedToolOrchestrator, ToolRequest, and ToolReceipt; existing workspace/session identity; evidence, validation, and completion owners; canonical TUI LbeWrapper adapter.
DESIRED_RESULT: The TUI integration may adapt request and projection contracts to the existing governed LBE execution path while all authorization, policy, execution, evidence, validation, receipt, and completion truth remains LBE-owned.
NON_GOALS: No second executor; no second authorization, receipt, evidence, validation, persistence, or completion owner; no unrestricted shell; no direct Cline authority; no provider generation; no branch/worktree creation; no publication; no UI redesign; no bypass of Agent Wall policy.
REUSE_DECISION: REUSE existing R6C/R6E authorization and orchestration owners, ToolRegistry, ToolReceipt, evidence/validation/completion services, session/workspace identity, and the canonical TUI LbeWrapper boundary. ADAPT only TUI request/event/snapshot wiring.
AUTHORITY_IMPACT: No new authority owner. This slice opens only the bounded adapter path to already-proven Agent Wall governed execution.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,config.json,docs/governance/,.lbe/governance/,lbe_guard_inspector/,tests/,docs/acceptance/
REQUIRED_EVIDENCE: active intent and matching machine slice; current PROJECT_INDEX revision binding; authorization-before-execution; provider receives only LBE-generated tool definitions; governed ToolReceipt correlation; mutation denial outside registered capabilities; read-only audit/investigation preservation; focused tests; full regression; no duplicate authority owner.
MACHINE_SLICE: TUI_P2_P3_GOVERNED_EXECUTION_INTEGRATION
SUPERSEDES: none
RESULT: SUPERSEDED
COMPLETION_CHECKPOINT: docs/acceptance/TUI_P2_P3_GOVERNED_EXECUTION_INTEGRATION_CHECKPOINT.md
```

## INTENT LBE-INTENT-CLINE-CLI-LBE-RUNTIME-INTEGRATION-001

```text
INTENT_ID: LBE-INTENT-CLINE-CLI-LBE-RUNTIME-INTEGRATION-001
STATUS: SUPERSEDED IN CLIENT/PRESENTATION SCOPE; HEADLESS CLINE MECHANICS RETAINED
REQUEST: Make the Cline CLI/TUI the selected LetterBlack product surface and replace native
         Cline SessionRuntime product authority with an LBE-backed session/runtime adapter.
WHY: Cline provides reusable reasoning, provider, tool-proposal, continuation, and presentation
     mechanics, while LBE remains the sole authority for session identity, policy, authorization,
     governed execution, receipts, evidence, persistence, recovery, validation, and completion.
AFFECTED_STRUCTURE: PROJECT_INDEX.md,docs/governance/PROJECT_INTENT_LEDGER.md,.lbe/governance/implementation-gates.json,
                    docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md,bin/lbe.js,run-lbe.bat,
                    lbe_guard_inspector/product_entry.py,lbe_guard_inspector/cli.py,
                    lbe_guard_inspector/session_lifecycle.py,lbe_guard_inspector/provider_turn_runtime.py,
                    lbe_guard_inspector/persistent_turn_control.py,lbe_guard_inspector/memory/,
                    lbe_guard_inspector/runtime/,lbe_guard_inspector/runtime/cline_worker/
EXISTING_OWNER: Existing LBE session lifecycle, provider-turn runtime, R6C authorization, ToolRegistry,
                GovernedToolOrchestrator, ToolReceipt, evidence, persistence/recovery,
                validation/completion owners; existing Cline AgentRuntime mechanics.
DESIRED_RESULT: A bounded LBE authority stdio/session transport and Cline-side adapter expose
                authoritative LBE session/provider/event state to the Cline CLI, route governed
                proposals through LBE, and prevent native Cline SessionRuntime/tool/persistence
                authority from becoming product truth.
NON_GOALS: No second LBE runtime; no Cline-owned session, provider, authorization, execution,
           MCP, receipt, evidence, persistence, validation, or completion authority; no direct
           native mutation bypass; no publication; no branch/worktree creation.
REUSE_DECISION: REUSE existing LBE owners and Cline AgentRuntime/provider/event mechanics. ADD only
                the bounded authority stdio/session transport and adapter seam required for composition.
AUTHORITY_IMPACT: LBE remains the sole runtime and governance authority. Cline remains selected for
                  headless reasoning/provider/model/continuation mechanics, but is no longer the selected visible client surface.
EXPECTED_PATH_PREFIXES: bin/lbe.js,run-lbe.bat,lbe_guard_inspector/product_entry.py,lbe_guard_inspector/cli.py,lbe_guard_inspector/session_lifecycle.py,lbe_guard_inspector/provider_turn_runtime.py,lbe_guard_inspector/persistent_turn_control.py,lbe_guard_inspector/memory/,lbe_guard_inspector/runtime/,docs/governance/
REQUIRED_EVIDENCE: transport framing and identity validation; authoritative session start/restore;
                   provider event streaming; native SessionRuntime not instantiated for product path;
                   deny-before-execute; allow-exactly-once; receipt/evidence correlation; continuation;
                   cancellation; persistence/resume; installed Cline CLI acceptance; no duplicate authority.
MACHINE_SLICE: TUI_P2_P3_GOVERNED_EXECUTION_INTEGRATION
SUPERSEDES: LBE-INTENT-TUI-P2P3-GOVERNED-INTEGRATION-001 for the selected product surface and adapter scope
SUPERSEDED_BY: LBE-INTENT-LBE-OWNED-RUST-TUI-PRODUCT-SURFACE-001 (client/presentation scope only)
RESULT: SUPERSEDED_IN_CLIENT_SURFACE_SCOPE
COMPLETION_CHECKPOINT: docs/acceptance/TUI_P2_P3_GOVERNED_EXECUTION_INTEGRATION_CHECKPOINT.md
```

## Historical product-owner correction — HTML-based TUI (superseded in scope)

The prior Cline surface-direction record is amended by the current product decision: the
supplied `docs/reference/ui/lbe_runtime_console.html` and
`docs/reference/ui/lbe_runtime_surface_preview.html` are the visual/layout basis for the LBE
TUI. Cline is reference material for interaction ideas only. A copied Cline CLI/OpenTUI tree is
not a product UI implementation and must remain quarantined as reference/archive material.
The HTML cockpit was recorded as the canonical UI target at that time, but that technology selection
is superseded by the current UI technology scope correction below. Existing LBE runtime/authority
owners remain canonical; the older Textual projection remains forbidden as product UI.

## INTENT LBE-INTENT-UI-TECHNOLOGY-SCOPE-CORRECTION-001

```text
INTENT_ID: LBE-INTENT-UI-TECHNOLOGY-SCOPE-CORRECTION-001
STATUS: ACCEPTED (explicit current user instruction, recorded 2026-09-02)
REQUEST: Narrow product UI governance to forbid Python/Textual product UI without selecting HTML,
         CSS, JavaScript, Rust/Ratatui, Tauri, WinUI/WPF, or another frontend as canonical.
WHY: The prior HTML-only lock encoded a stronger decision than the current user intent authorizes.
AFFECTED_STRUCTURE: PROJECT_INDEX.md,governance.json,.lbe/governance/implementation-gates.json,
                    docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md,docs/CURRENT_STATUS.md,
                    docs/IMPLEMENTATION_PLAN.md,docs/governance/PROJECT_INTENT_LEDGER.md,
                    scripts/check-implementation-gate.py,tests/test_ui_implementation_authority.py
EXISTING_OWNER: User product-decision authority; LBE runtime, authorization, execution, receipt,
                evidence, session, persistence, validation, and completion owners unchanged.
DESIRED_RESULT: Python/Textual product UI remains forbidden; frontend technology is OPEN until an
                explicit user decision records a deterministic gate transition.
NON_GOALS: No frontend selection; no runtime redesign; no deletion of historical records; no
           silent agent gate change; no branch, worktree, publication, or release action.
REUSE_DECISION: Preserve existing frontend candidates as candidates/reference surfaces only.
AUTHORITY_IMPACT: Governance becomes user-overridable through explicit transition records while
                  agents remain unable to silently change a gate to unblock themselves.
TRANSITION_RULE: A new explicit user decision may supersede prior UI intent only after recording
                 the new intent, updating the active gate, superseding the old interpretation,
                 reconciling owner/index docs, and passing deterministic validation.
SUPERSEDES: HTML-only interpretation in LBE-INTENT-CLINE-SURFACE-DIRECTION-001 and related current
             HTML-canonical projections; historical records are retained.
RESULT: ACCEPTED / APPLIED
```

## INTENT LBE-INTENT-CLINE-REASONING-AGENT-SELECTION-001

```text
INTENT_ID: LBE-INTENT-CLINE-REASONING-AGENT-SELECTION-001
STATUS: ACCEPTED (explicit current user instruction, recorded 2026-09-02)
REQUEST: Use the official Cline repository as the selected reasoning-agent source instead of the
         VS Code repository.
WHY: Cline is the safer selected agent-loop source for this product direction.
AFFECTED_STRUCTURE: .lbe/governance/implementation-gates.json,docs/acceptance/,
                    docs/governance/PROJECT_INTENT_LEDGER.md,docs/IMPLEMENTATION_PLAN.md
EXISTING_OWNER: Cline Agent/AgentRuntime and ClineCore mechanics under the LBE adapter; LBE
                identity, authorization, execution, receipts, evidence, persistence, validation,
                and completion owners remain authoritative.
DESIRED_RESULT: Cline reasoning/planning/tool-proposal/continuation mechanics are the selected
                agent source and all authority-bearing consequences remain LBE-governed.
NON_GOALS: No direct Cline mutation, shell, MCP, provider, session, receipt, evidence, persistence,
           or completion authority; no VS Code agent implementation; no publication or release.
REUSE_DECISION: ADAPT official Cline agent-loop mechanics behind the existing LBE boundary.
AUTHORITY_IMPACT: Selected reasoning-agent source changes to Cline; LBE authority is unchanged.
SOURCE: https://github.com/cline/cline
SUPERSEDES: Unselected VS Code agent direction; does not supersede LBE authority.
RESULT: ACCEPTED / APPLIED
```

## INTENT LBE-INTENT-LBE-HOME-PROVIDER-CONTRACT-VERIFICATION-001

```text
INTENT_ID: LBE-INTENT-LBE-HOME-PROVIDER-CONTRACT-VERIFICATION-001
STATUS: COMPLETED
REQUEST: Verify the contract and ownership boundary for the LBE Home/provider experience before
         implementing or staging the HTML product surface.
WHY: The supplied HTML establishes the intended LBE landing and provider/model setup experience,
     but its model discovery is currently a reference simulation and no runtime bridge has been
     proven. Existing LBE owners must be mapped before any UI or provider integration changes.
AFFECTED_STRUCTURE: .ui-preview/,docs/reference/ui/,docs/contracts/LBE_HOME_PROVIDER_SURFACE_CONTRACT.md,
                    lbe_guard_inspector/provider_registry.py,
                    lbe_guard_inspector/provider_capability_discovery.py,
                    lbe_guard_inspector/provider_health.py,lbe_guard_inspector/session_lifecycle.py,
                    lbe_guard_inspector/cli.py,tests/,docs/acceptance/,docs/governance/,PROJECT_INDEX.md,
                    .lbe/governance/
EXISTING_OWNER: LBE provider registry and descriptors; provider/model capability-discovery contract;
                provider health contract; LbeSessionService and persisted SessionMemoryRuntimeBridge/
                WorkspaceMemoryStore owners; existing HTML/CSS/JavaScript projection boundary; LBE
                authorization, execution, receipt, evidence, persistence, validation, and completion
                owners. Cline/OpenTUI and unused-in-repo material are reference-only.
DESIRED_RESULT: A read-only contract verification identifies the authoritative provider/model discovery,
                health, session, and projection seams; distinguishes static/reference behavior from
                live behavior; records every implementation gap; and proves that the future Home/
                provider surface remains a projection/control client under LBE authority.
NON_GOALS: No implementation; no staging or cleanup of existing dirty paths; no provider I/O or
           credential changes; no new provider registry, session, transport, authorization, execution,
           receipt, evidence, persistence, validation, or completion authority; no Textual product UI;
           no Cline/OpenTUI product surface; no branch/worktree/publication.
REUSE_DECISION: REUSE existing ProviderRegistry, ProviderModelCapabilitySnapshot,
                discover_provider_model_capabilities, provider health, LbeSessionService,
                SessionMemoryRuntimeBridge, persisted history, and LBE projection/control contracts;
                ADAPT only after the read-only contract gaps and bridge boundary are proven.
AUTHORITY_IMPACT: None. This is a read-only verification slice and does not authorize product or
                  runtime implementation.
EXPECTED_PATH_PREFIXES: .ui-preview/,docs/reference/ui/,docs/contracts/,lbe_guard_inspector/,tests/,docs/acceptance/,
                         docs/governance/,PROJECT_INDEX.md,.lbe/governance/
REQUIRED_EVIDENCE: dirty-path ownership matrix; HTML static/reference versus live-runtime classification;
                   provider/model discovery and health owner mapping; session/provider persistence owner
                   mapping; LBE authority-boundary proof; obsolete Textual and quarantined Cline disposition;
                   explicit implementation-gap list; no second authority owner; read-only verification
                   tests or contract evidence only after a follow-on implementation authorization.
MACHINE_SLICE: LBE_HOME_PROVIDER_CONTRACT_VERIFICATION
SUPERSEDES: LBE-INTENT-CLINE-NATIVE-SURFACE-INTEGRATION-001 (product-surface direction only; prior
            runtime evidence remains historical/reference evidence)
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/LBE_HOME_PROVIDER_CONTRACT_VERIFICATION_CHECKPOINT.md
```

## INTENT LBE-INTENT-LBE-HOME-PROVIDER-OWNER-NORMALIZATION-001

```text
INTENT_ID: LBE-INTENT-LBE-HOME-PROVIDER-OWNER-NORMALIZATION-001
STATUS: PROPOSED (non-authorizing until explicitly activated by the machine gate)
REQUEST: Add bounded provider-boundary normalization for model discovery, provider-specific
         authentication results, and typed provider health outcomes before implementing the HTML
         bridge or changing the HTML surface.
WHY: The frozen Home/provider contract has proven its existing owner mappings but live model
     enumeration, authentication state, and typed health failures still have no complete producers.
     These state producers must be bounded and evidence-bearing before bridge composition.
AFFECTED_STRUCTURE: lbe_guard_inspector/provider_registry.py,
                    lbe_guard_inspector/provider_capability_discovery.py,
                    lbe_guard_inspector/provider_health.py,lbe_guard_inspector/runtime/,
                    tests/,docs/contracts/,docs/acceptance/,docs/governance/,PROJECT_INDEX.md,
                    .lbe/governance/
EXISTING_OWNER: ProviderRegistry and provider-specific adapters; ProviderModelCapabilitySnapshot;
                existing provider health probe; LBE runtime/provider boundary; existing evidence,
                session, authorization, execution, persistence, validation, and completion owners.
                No standalone global authentication service is authorized by this intent.
DESIRED_RESULT: Existing provider-boundary adapters return deterministic model-discovery results,
                provider-specific authentication outcomes normalized to unknown/authenticated/
                authentication_required/unavailable, and typed health outcomes with reasons and
                optional evidence references. Registry identity, session selection, and LBE authority
                remain owned by their existing owners.
NON_GOALS: No HTML changes; no bridge implementation; no Textual cleanup; no session/runtime
           authority changes; no replacement ProviderRegistry; no standalone global authentication
           service; no provider fallback; no credential persistence changes; no provider I/O outside
           explicitly bounded provider adapters; no receipts for ordinary reads by default; no
           publication, branch, or worktree.
REUSE_DECISION: REUSE ProviderRegistry for registered provider identity, existing provider-specific
                adapter mechanics, ProviderModelCapabilitySnapshot for configuration-derived claims,
                check_provider_health as the health owner, and existing LBE evidence/persistence/
                authority owners. ADD only bounded provider-boundary discovery/auth probes and a
                normalization layer; ADAPT health output without replacing its owner.
AUTHORITY_IMPACT: No new session, authorization, execution, receipt, evidence, persistence,
                  validation, or completion authority. Provider adapters own provider-specific
                  mechanics; LBE normalization owns only the bounded surface result.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/provider_registry.py,lbe_guard_inspector/provider_capability_discovery.py,
                         lbe_guard_inspector/provider_health.py,lbe_guard_inspector/runtime/,tests/,
                         docs/contracts/,docs/acceptance/,docs/governance/,PROJECT_INDEX.md,.lbe/governance/
REQUIRED_EVIDENCE: provider model enumeration is bounded and distinct from registry identity;
                   discovery collection state and provenance are deterministic; provider-specific
                   authentication outcomes are explicit and not inferred from health/errors; health
                   results are typed with deterministic reasons; optional evidence references remain
                   optional; no credential leakage or persistence change; no second provider/session/
                   authority owner; focused owner-normalization tests; full regression; diff check.
MACHINE_SLICE: LBE_HOME_PROVIDER_OWNER_NORMALIZATION
SUPERSEDES: none
RESULT: NOT_STARTED
```

## INTENT LBE-INTENT-FINAL-PRODUCT-SOURCE-RECONCILIATION-001

```text
INTENT_ID: LBE-INTENT-FINAL-PRODUCT-SOURCE-RECONCILIATION-001
STATUS: ACTIVE
REQUEST: Reconcile the preserved local provider-runtime delta (cli.py, cline_reasoning_provider.py,
         provider_turn_runtime.py, tests/test_provider_turn_runtime.py, pyproject.toml) onto canonical
         origin/main 388ca647 under the FINAL_PRODUCT_SOURCE_RECONCILIATION gate, without duplicating
         the on_tool_receipt correlation owner or existing provider continuation owners.
WHY: Laptop-local uncommitted provider/continuation and model-validation work had to be preserved
     across the required fast-forward to 388ca647 and either land in canonical source or be explicitly
     superseded; losing it silently would drop genuine governed-runtime work.
AFFECTED_STRUCTURE: lbe_guard_inspector/cli.py, lbe_guard_inspector/cline_reasoning_provider.py,
                    lbe_guard_inspector/provider_turn_runtime.py, tests/test_provider_turn_runtime.py,
                    pyproject.toml, docs/governance/PROJECT_INTENT_LEDGER.md
EXISTING_OWNER: Existing governed provider-turn runtime owners; existing Cline stdio bridge
                on_tool_receipt correlation owner; ClineReasoningBackend provider adapter owner;
                product_entry single-command CLI surface; existing validation/completion owners.
DESIRED_RESULT: Canonical main carries the retained deltas (governed runtime doctrine delivery and
                guidance load, backend model resolution, provider adapter reads, model-validation
                hardening) with no duplicate owner and the canonical lbe entrypoint intact.
NON_GOALS: No Textual deletion; no gate merge or gate transition; no branch or worktree; no generated
           artifact commits; no on_tool_receipt duplication; no provider registry replacement.
REUSE_DECISION: REUSE GovernedProviderTurnRuntime, the stdio bridge correlation path, and registry
                adapter construction; ADD only the preserved local deltas adapted to current owners;
                ADAPT ClineReasoningBackend model resolution to keep upstream factories working.
AUTHORITY_IMPACT: No new session, authorization, execution, receipt, evidence, persistence,
                  validation, or completion authority; retained deltas strengthen existing owners only.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/,tests/,pyproject.toml,docs/governance/PROJECT_INTENT_LEDGER.md,PROJECT_INDEX.md
REQUIRED_EVIDENCE: focused provider-runtime tests; cline stdio bridge tests; CLI/package-relevant
                   tests; full pytest suite; git diff --check clean.
MACHINE_SLICE: FINAL_PRODUCT_SOURCE_RECONCILIATION
SUPERSEDES: none
RESULT: NOT_STARTED
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


## INTENT LBE-INTENT-DOCUMENT-SOURCE-OF-TRUTH-CONSOLIDATION-001

```text
INTENT_ID: LBE-INTENT-DOCUMENT-SOURCE-OF-TRUTH-CONSOLIDATION-001
STATUS: ACTIVE
REQUEST: Establish one canonical LBE product source-of-truth document and one narrowly-scoped agent document-write policy before any documentation cleanup.
WHY: Current product truth is distributed across roadmap, design, status, acceptance, and historical records. Agents must not infer that an omitted feature is obsolete, rewrite architecture merely to match current wiring, or generate new competing status/plan documents.
AFFECTED_STRUCTURE: docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md,docs/governance/AGENT_DOCUMENT_WRITE_POLICY.md,docs/governance/PROJECT_INTENT_LEDGER.md
EXISTING_OWNER: PROJECT_INDEX.md; docs/README.md; .lbe/governance/implementation-gates.json; PROJECT_INTENT_LEDGER.md; current runtime/source/acceptance owners.
DESIRED_RESULT: One product-truth document preserves current architecture, implemented/partial/planned feature inventory, evidence classifications, and feature-preservation rules. One governance policy defines that after the one-time consolidation, agents may not create or edit arbitrary documentation; ordinary agent documentation writes are limited to bounded intent lifecycle entries in PROJECT_INTENT_LEDGER.md.
NON_GOALS: No product-code mutation. No deletion or relocation in this intent. No feature removal. No architecture ownership change. No modification of completed historical intent records. No conversion of historical acceptance evidence into current truth. No publication.
REUSE_DECISION: REUSE existing machine governance, project index, intent ledger, Git history, current runtime/source evidence, and acceptance evidence. Consolidate current truth without discarding historical proof.
AUTHORITY_IMPACT: None. This intent changes documentation routing only and does not create a new runtime, reasoning, execution, validation, persistence, or completion authority.
EXPECTED_PATH_PREFIXES: docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md,docs/governance/AGENT_DOCUMENT_WRITE_POLICY.md,docs/governance/PROJECT_INTENT_LEDGER.md
REQUIRED_EVIDENCE: created source-of-truth document; created document-write policy; no product-code changes; no existing docs deleted; canonical GitHub commit(s) available for local pull.
MACHINE_SLICE: NONE — explicit user-authorized documentation-governance bootstrap; does not advance the closed product gate.
SUPERSEDES: none
RESULT: ACTIVE
```

## INTENT LBE-INTENT-LBE-OWNED-RUST-TUI-PRODUCT-SURFACE-001

```text
INTENT_ID: LBE-INTENT-LBE-OWNED-RUST-TUI-PRODUCT-SURFACE-001
STATUS: COMPLETED
REQUEST: Deliver the usable LBE product interface as the LBE-owned Rust/RatatuI client colocated at apps/lbe-terminal, projecting the real persisted session, provider, capability, receipt, evidence, and control state behind LBE authority.
WHY: The product identity is LBE and its canonical visible client surface is the LBE-owned Rust/RatatuI terminal projection that must expose the real persisted session, provider, capability, receipt, evidence, and control state.
AFFECTED_STRUCTURE: apps/lbe-terminal/,lbe_guard_inspector/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
EXISTING_OWNER: LBE runtime; SessionMemoryRuntimeBridge; WorkspaceMemoryStore; ProviderRegistry; PersistentTurnControl; ToolRegistry; ToolReceipt; persisted evidence and completion owners.
DESIRED_RESULT: A runnable LBE-owned Rust/RatatuI terminal client colocated at apps/lbe-terminal exposes a clear conversation surface, persisted session/provider state, capability visibility, streaming/runtime feedback, receipt/evidence detail, and keyboard controls without acquiring execution or authorization authority.
NON_GOALS: No lbe-tui activation; no independent provider transport; no independent session identity; no native shell execution; no second runtime, persistence, authorization, receipt, evidence, or completion owner; no publication; no branch or worktree creation.
REUSE_DECISION: REUSE approved interaction, continuation, event, streaming, layout, and branding mechanics from reference input; preserve LBE runtime and authority owners.
AUTHORITY_IMPACT: LBE interface remains a projection/control surface; no new authority.
EXPECTED_PATH_PREFIXES: PROJECT_INDEX.md,apps/lbe-terminal/,tests/,docs/acceptance/,docs/governance/,docs/CURRENT_STATUS.md,.lbe/governance/
REQUIRED_EVIDENCE: canonical Rust/RatatuI launch, persisted session projection, provider and capability projection, receipt/evidence detail, keyboard controls, focused UI tests, full regression, real local launch.
MACHINE_SLICE: LBE_OWNED_RUST_TUI_PRODUCT_SURFACE
SUPERSEDES: none
RESULT: PASS
COMPLETION_CHECKPOINT: docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md
```

## INTENT LBE-INTENT-REASONING-ENGINE-PROVIDER-BINDING-SEPARATION-001

```text
INTENT_ID: LBE-INTENT-REASONING-ENGINE-PROVIDER-BINDING-SEPARATION-001
STATUS: ACTIVE
REQUEST: Transition LBE's reasoning/runtime layer from Cline-as-required-owner to Cline-as-one-supported-engine-adapter, with engine-neutral authorized/default/selected/fallback model and provider-binding separation behind LBE-owned authority.
WHY: The current architecture encodes Cline privilege at the composition/import level (module-scope cline_reasoning_provider import -> cline_stdio_bridge) even though Cline is already optional at the runtime-path level. The audit identified this as the first code defect and the architecture change as coherent but not presently implementable under the current gate. This intent authorizes the governance/index/gate transition so the implementation can proceed lawfully.
GLOBAL_INVARIANTS: KEEP Cline working. DO NOT make Cline the definition of provider support. DO NOT require every provider to have a native LBE implementation immediately. ALLOW multiple engine implementations for the same provider. PREFER an existing native LBE backend when already proven. MIGRATE provider routes incrementally. LBE session/policy/authorization/execution/receipt/persistence/validation/completion remain unchanged regardless of engine. NO silent engine fallback. NO silent provider fallback. Cline absence must eventually degrade only Cline-backed capabilities, not LBE Core.
LBE_AUTHORITY_UNCHANGED: LBE remains the sole authority for session/workspace identity, provider policy truth, authorization, governed execution, receipts/evidence, persistence/recovery, validation, and completion. Reasoning engines own cognition/continuation/tool-proposal mechanics; LBE owns the authority boundary.
ENGINE_NEUTRAL_MODEL: selected_reasoning_agent becomes engine-neutral authorized/default/selected/fallback model. Cline is one supported engine, not the required engine. Native provider bindings are allowed behind the same LBE authority boundary.
REQUIRED_EVIDENCE_REPLACEMENT: Replace headless_cline_provider_turn with engine-neutral governed-turn proof, while retaining Cline regression proof to ensure no regression.
NON_GOALS: independent provider transport outside LBE-owned engine/provider bindings; silent engine/provider fallback; publication without separate authorization; branch/worktree creation; changes to the canonical client workspace (C:/Agents-Memory-Tool-v6-integration/apps/lbe-terminal); changes to existing working Cline-backed routes without regression proof.
FIRST_CODE_CHANGE: After governance opens the slice, make the module-scope cline_reasoning_provider import optional/feature-scoped as the first implementation change, proving Cline-absent LBE initialization before re-pointing any provider bindings.
AFFECTED_STRUCTURE: lbe_guard_inspector/provider_registry.py, lbe_guard_inspector/reasoning_runtime.py, lbe_guard_inspector/cline_reasoning_provider.py, lbe_guard_inspector/cli.py, lbe_guard_inspector/runtime/, tests/, PROJECT_INDEX.md, docs/governance/PROJECT_INTENT_LEDGER.md, docs/acceptance/, .lbe/governance/implementation-gates.json
EXISTING_OWNER: LBE runtime owners; existing Cline adapter mechanics under LBE authority; engine/provider binding owner (new structural responsibility per PROJECT_INDEX.md).
DESIRED_RESULT: LBE initializes and operates through an engine-neutral reasoning runtime. Cline is one supported adapter. Provider bindings are engine/provider-scoped behind LBE authority. No silent fallback. Cline regression proof retained.
REUSE_DECISION: REUSE existing LBE runtime, authorization, execution, receipt, evidence, persistence, validation, and completion owners. REUSE existing Cline adapter as one supported engine. ADAPT the provider registry and reasoning runtime to be engine-neutral with optional/supported Cline import.
AUTHORITY_IMPACT: LBE authority unchanged. Reasoning engine/provider bindings become a distinct structural responsibility owned by LBE runtime + engine/provider binding owner. Cline mechanics remain under LBE authority.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/provider_registry.py, lbe_guard_inspector/reasoning_runtime.py, lbe_guard_inspector/cline_reasoning_provider.py, lbe_guard_inspector/cli.py, lbe_guard_inspector/runtime/, tests/, PROJECT_INDEX.md, docs/governance/, docs/acceptance/, .lbe/governance/
REQUIRED_EVIDENCE: engine-neutral LBE initialization proof; Cline-absent LBE initialization proof; Cline regression proof; provider binding structure registered in PROJECT_INDEX.md; gate amendment record; focused tests for engine-neutral runtime; full regression.
MACHINE_SLICE: REASONING_ENGINE_PROVIDER_BINDING_SEPARATION
RESULT: IMPLEMENTED_STATIC_VALIDATION_PENDING
IMPLEMENTATION_COMMITS: 39dd7cf9a6194a4931d1c564f43af50d5d8d9f7f, 7685ecae0412a92f7b61f9b5b51011e3125a4f8d, e28c873d1bd4074cd157141d146487ca0bcff564, e807598361ca5abb41cd2fe94c52d3ae58996d31, aea2deb1a4e5f117f712c8d27ad5cb521756481a, 90f9d2bb49295b50db6570b5f9c861fdcc600c81, e652ec492c87dbb22fedafd79f8e618d89f5b4be, 9b48a9d3ce8106de048779708691a91e3cee22ff, 263382e386c40ab87620880bb6394fd47203c35f, fd501f40b9715bc6f2da073cb8891c7c7cabb25e, d113364613ca78e47bce6a0b9e13af53ef08b5b1, 944b4e65978f149b68ed36d26c404191bcedec74
REFERENCE_CHAIN: GPT-K ai-agents/studies/agent-feature-reference-map-2026-09-20.json -> Cline 9a2512bb9835869d74774da99708a7f9d80b0fe8 sdk/packages/README.md -> OpenCode ebb7b76eca82342642c78645109e865614533827 packages/opencode/src/tool/registry.ts
VALIDATION_BLOCKER: GitHub Actions validate attempt 1 continues to terminate all matrix jobs with zero executed workflow steps; rerun attempt 2 was requested after source convergence. Container network/DNS cannot clone GitHub. Until a runner executes test steps, focused/full regression and live runtime proof remain UNVERIFIED.
AUTHORIZATION: EXPLICIT_USER_AUTHORIZATION_2026_09_20
SCOPE_AMENDMENT_2026_09_21: Explicit user instruction `goahead build it in the repo` authorizes convergence of the existing canonical `lbe code` product-entry path onto the already-selected engine-neutral governed coding factory. This adds only `lbe_guard_inspector/cli.py` as an existing-owner path; it does not authorize TUI mutation, new runtime authority, branch/worktree creation, publication, or gate closure.
```\n

## INTENT LBE-INTENT-GOVERNED-TOOL-PERMISSION-REFERENCE-CONVERGENCE-001

```text
INTENT_ID: LBE-INTENT-GOVERNED-TOOL-PERMISSION-REFERENCE-CONVERGENCE-001
STATUS: PROPOSED (non-authorizing until current active slice completes and machine gate selects this slice)
REQUEST: Converge LBE tool/capability presentation and permission interaction onto the existing R6C/R6E owners, using exact upstream tool-registry and approval references without creating a second executor.
WHY: LBE already owns ToolRegistry, resolve_authorization(), GovernedToolOrchestrator and ToolReceipt. Upstreams provide mature tool catalog/visibility/approval patterns that should improve the existing surface rather than replace authority.
REFERENCE_CHAIN: Cline cline/cline@9a2512bb9835869d74774da99708a7f9d80b0fe8 docs/tools-reference/all-cline-tools.mdx + sdk/packages/core/src/extensions/tools/; OpenCode anomalyco/opencode@ebb7b76eca82342642c78645109e865614533827 packages/opencode/src/tool/registry.ts + packages/web/src/content/docs/permissions.mdx; Claude Code anthropics/claude-code@7974a70773fa229e4cc65aa1b356cc21f5c216c4 official tools/permissions docs; Antigravity google-antigravity/antigravity-cli@7bb195acaec9e7788df5210d0dc3e15f3cefc6b3 README.md + CHANGELOG.md + official permissions docs.
AFFECTED_STRUCTURE: lbe_guard_inspector/runtime/tool_orchestration.py,lbe_guard_inspector/runtime/authorization_resolver.py,lbe_guard_inspector/professional_capabilities.py,lbe_guard_inspector/runtime/external_capabilities.py,tests/,apps/lbe-terminal/,docs/governance/PROJECT_INTENT_LEDGER.md,PROJECT_INDEX.md,.lbe/governance/
EXISTING_OWNER: ToolRegistry; R6C authorization resolver; GovernedToolOrchestrator; ToolReceipt; runtime capability projection; Rust client approval/tool projection.
DESIRED_RESULT: Tool visibility, capability readiness, approval prompts and tool-result projection are exact and truthful while every mutation/external action still crosses R6C/R6E exactly once.
NON_GOALS: No native provider/external tool bypass; no second permission engine; no direct upstream executor; no silent auto-approval changes.
REUSE_DECISION: REUSE LBE owners. ADAPT upstream registry/approval UX and visibility mechanics only.
AUTHORITY_IMPACT: None; LBE remains sole authorization/execution/receipt owner.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/runtime/,lbe_guard_inspector/professional_capabilities.py,tests/,apps/lbe-terminal/,docs/governance/,PROJECT_INDEX.md,.lbe/governance/
REQUIRED_EVIDENCE: exact tool registry projection; allow/deny/escalate zero/once execution proof; capability truth proof; UI approval projection; focused tests; full regression; live acceptance.
MACHINE_SLICE: GOVERNED_TOOL_PERMISSION_REFERENCE_CONVERGENCE
RESULT: NOT_STARTED
```


## INTENT LBE-INTENT-SESSION-CHECKPOINT-SUBAGENT-REFERENCE-CONVERGENCE-001

```text
INTENT_ID: LBE-INTENT-SESSION-CHECKPOINT-SUBAGENT-REFERENCE-CONVERGENCE-001
STATUS: PROPOSED (non-authorizing until selected by machine gate)
REQUEST: Preserve and complete LBE session/history/checkpoint/rewind and child-agent/team lifecycle surfaces using exact Cline/OpenCode/Claude/Antigravity references while retaining LBE session and persistence authority.
WHY: LBE already has persisted sessions, checkpoints, child-agent operational history and Rust session/checkpoint controls. Remaining work should be gap-only and lifecycle-explicit.
REFERENCE_CHAIN: Cline cline/cline@9a2512bb9835869d74774da99708a7f9d80b0fe8 apps/cli/src/tui/views/history-view.tsx + apps/cli/src/tui/components/dialogs/checkpoint-picker.tsx + sdk/packages/core/src/session/team/ + sdk/packages/core/src/extensions/tools/team/; OpenCode anomalyco/opencode@ebb7b76eca82342642c78645109e865614533827 packages/tui/src/routes/session/index.tsx + subagent-footer.tsx + packages/opencode/src/tool/task.ts; Claude Code anthropics/claude-code@7974a70773fa229e4cc65aa1b356cc21f5c216c4 official subagents/agent-teams/interactive docs; Antigravity google-antigravity/antigravity-cli@7bb195acaec9e7788df5210d0dc3e15f3cefc6b3 CHANGELOG.md + statusline example + official CLI docs.
AFFECTED_STRUCTURE: lbe_guard_inspector/memory/,lbe_guard_inspector/product_entry.py,lbe_guard_inspector/runtime/,apps/lbe-terminal/,tests/,docs/governance/PROJECT_INTENT_LEDGER.md,PROJECT_INDEX.md,.lbe/governance/
EXISTING_OWNER: SessionMemoryRuntimeBridge; WorkspaceMemoryStore; checkpoint/recovery owners; ChildAgentRun operational history; canonical Rust client session/checkpoint projection.
DESIRED_RESULT: Resume/fork/compare/restore/child-run/background lifecycle state is explicit, parent-linked, cancellable and truthfully projected without creating a second session store.
NON_GOALS: No independent child authority; no hidden recursive session owner; no checkpoint-as-current-truth shortcut.
REUSE_DECISION: REUSE LBE persistence/session owners; ADAPT upstream navigation, child-session and rewind ergonomics.
AUTHORITY_IMPACT: None; child workers remain subordinate to LBE session/authorization/completion.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/memory/,lbe_guard_inspector/product_entry.py,lbe_guard_inspector/runtime/,apps/lbe-terminal/,tests/,docs/governance/,PROJECT_INDEX.md,.lbe/governance/
REQUIRED_EVIDENCE: parent/child identity proof; persisted resume proof; stale checkpoint invalidation; compare/restore proof; cancellation; focused tests; full regression; PTY live acceptance.
MACHINE_SLICE: SESSION_CHECKPOINT_SUBAGENT_REFERENCE_CONVERGENCE
RESULT: NOT_STARTED
```


## INTENT LBE-INTENT-EXTENSION-SURFACE-REFERENCE-CONVERGENCE-001

```text
INTENT_ID: LBE-INTENT-EXTENSION-SURFACE-REFERENCE-CONVERGENCE-001
STATUS: PROPOSED (non-authorizing until selected by machine gate)
REQUEST: Complete MCP, skills, plugins and hooks as registered LBE capabilities with one discovery/health/projection path and no provider-controlled execution transport.
WHY: MCP/external capability registration is already implemented, but skills/plugins/hooks and broader user-facing management are partial. Upstream CLIs provide mature management surfaces.
REFERENCE_CHAIN: Cline cline/cline@9a2512bb9835869d74774da99708a7f9d80b0fe8 apps/cli/src/commands/mcp.ts + plugin.ts + skill.ts + apps/cli/src/tui/commands/slash-command-registry.ts; OpenCode anomalyco/opencode@ebb7b76eca82342642c78645109e865614533827 packages/opencode/src/mcp/ + skill/ + plugin/ + tool/registry.ts; Claude Code anthropics/claude-code@7974a70773fa229e4cc65aa1b356cc21f5c216c4 plugins/ + official hooks/MCP/skills docs; Antigravity google-antigravity/antigravity-cli@7bb195acaec9e7788df5210d0dc3e15f3cefc6b3 CHANGELOG.md + official CLI features docs.
AFFECTED_STRUCTURE: lbe_guard_inspector/runtime/external_capabilities.py,lbe_guard_inspector/runtime/installed_capability_registry.py,lbe_guard_inspector/runtime/agent_guidance.py,lbe_guard_inspector/product_entry.py,apps/lbe-terminal/,tests/,docs/governance/PROJECT_INTENT_LEDGER.md,PROJECT_INDEX.md,.lbe/governance/
EXISTING_OWNER: Governed external capability registration; ToolRegistry/R6C/R6E; installed capability registry; MCP projection.
DESIRED_RESULT: MCP/skill/plugin/hook entries have explicit source, health, availability and authority class; user-facing management projects those facts and all executable effects remain governed.
NON_GOALS: No arbitrary provider-supplied command/URL/transport; no skill-as-authority; no plugin bypass.
REUSE_DECISION: REUSE existing external-capability owner; ADAPT management/discovery patterns.
AUTHORITY_IMPACT: None.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/runtime/,lbe_guard_inspector/product_entry.py,apps/lbe-terminal/,tests/,docs/governance/,PROJECT_INDEX.md,.lbe/governance/
REQUIRED_EVIDENCE: deterministic discovery; malformed entry isolation; health projection; governed execution proof; UI management projection; focused/full regression.
MACHINE_SLICE: EXTENSION_SURFACE_REFERENCE_CONVERGENCE
RESULT: NOT_STARTED
```


## INTENT LBE-INTENT-RUST-TUI-REFERENCE-CONVERGENCE-001

```text
INTENT_ID: LBE-INTENT-RUST-TUI-REFERENCE-CONVERGENCE-001
STATUS: PROPOSED (non-authorizing until selected by machine gate)
REQUEST: Gap-fill the existing LBE-owned Rust/Ratatui user surface using exact upstream TUI references for home/chat/status, command palette, slash commands, pickers, diff/review and attention state; preserve every existing working LBE surface.
WHY: The canonical client already implements transcript, command palette, provider/model/session pickers, MCP/tools/process/activity/evidence/receipts/changes/memory/doctor/help panels, checkpoint compare/restore and authoritative workspace browsing. Work must be gap-driven, not a rewrite.
REFERENCE_CHAIN: Cline cline/cline@9a2512bb9835869d74774da99708a7f9d80b0fe8 apps/cli/src/tui/views/home-view.tsx + chat-view.tsx + components/status-bar.tsx + components/dialogs/command-palette-items.ts + commands/slash-command-registry.ts + model-selector/ + provider-picker.tsx; OpenCode anomalyco/opencode@ebb7b76eca82342642c78645109e865614533827 packages/tui/src/routes/session/index.tsx + sidebar.tsx + footer.tsx + component/dialog-model.tsx + dialog-provider.tsx + feature-plugins/system/diff-viewer.tsx; Antigravity google-antigravity/antigravity-cli@7bb195acaec9e7788df5210d0dc3e15f3cefc6b3 examples/statusline/statusline.sh + examples/title/title.sh + CHANGELOG.md; Claude Code anthropics/claude-code@7974a70773fa229e4cc65aa1b356cc21f5c216c4 official interactive-mode docs + mods/diff/.
AFFECTED_STRUCTURE: apps/lbe-terminal/,tests/,docs/governance/PROJECT_INTENT_LEDGER.md,PROJECT_INDEX.md,.lbe/governance/
EXISTING_OWNER: LBE-owned Rust/Ratatui projection/controller; RealLbeWrapper; existing App state machine; backend authority owners.
DESIRED_RESULT: One keyboard-first LBE interface truthfully projects mode, engine/provider/model, context, workspace/Git state, approvals, tools, processes, MCP, evidence, receipts, child runs, changes and health; no fake connected state.
NON_GOALS: No Cline/OpenCode/Claude/Antigravity branding copy; no upstream runtime ownership; no second file/provider/session index; no Electron.
REUSE_DECISION: REUSE current Rust client; ADAPT only missing interaction/projection mechanics from exact references.
AUTHORITY_IMPACT: None; client remains projection/control only.
EXPECTED_PATH_PREFIXES: apps/lbe-terminal/,tests/,docs/governance/,PROJECT_INDEX.md,.lbe/governance/
REQUIRED_EVIDENCE: feature-by-feature UI tests; actual backend event projection; keyboard/PTY acceptance; narrow/wide layout; no mock/fake success in real mode; full regression.
MACHINE_SLICE: RUST_TUI_REFERENCE_CONVERGENCE
RESULT: NOT_STARTED
```


## INTENT LBE-INTENT-HEADLESS-REMOTE-SURFACE-CONVERGENCE-001

```text
INTENT_ID: LBE-INTENT-HEADLESS-REMOTE-SURFACE-CONVERGENCE-001
STATUS: PROPOSED (non-authorizing until selected by machine gate)
REQUEST: Add/normalize headless machine-readable and remote-attach control surfaces over the same LBE session/runtime owner, without creating another agent runtime.
WHY: LBE already has JSON product-entry operations and a canonical TUI. Upstream CLIs demonstrate headless streams, attach/server, hub/ACP and remote-control patterns that can be adapted behind LBE identity and authority.
REFERENCE_CHAIN: Cline cline/cline@9a2512bb9835869d74774da99708a7f9d80b0fe8 apps/cli/src/commands/program.ts + apps/cli/src/acp/ + apps/cli/README.md; OpenCode anomalyco/opencode@ebb7b76eca82342642c78645109e865614533827 packages/web/src/content/docs/cli.mdx + packages/opencode/src/cli/cmd/attach.ts + serve.ts + web.ts; Claude Code anthropics/claude-code@7974a70773fa229e4cc65aa1b356cc21f5c216c4 official CLI docs for -p/stream-json/remote-control; Antigravity google-antigravity/antigravity-cli@7bb195acaec9e7788df5210d0dc3e15f3cefc6b3 README.md + CHANGELOG.md + official headless/remote-control docs.
AFFECTED_STRUCTURE: lbe_guard_inspector/product_entry.py,lbe_guard_inspector/cli.py,lbe_guard_inspector/runtime/,apps/lbe-terminal/,tests/,docs/governance/PROJECT_INTENT_LEDGER.md,PROJECT_INDEX.md,.lbe/governance/
EXISTING_OWNER: product_entry machine-readable surface; canonical session/workspace/runtime owners; Rust TUI as local client.
DESIRED_RESULT: Headless JSON/stream and remote clients attach to the same session/turn/authority state, with cancellation, approvals, receipts/evidence and actual engine/provider/model identity preserved.
NON_GOALS: No unauthenticated remote mutation; no second session store; no remote bypass of R6C/R6E; no hidden fallback.
REUSE_DECISION: REUSE product_entry/session/control owners; ADAPT transport/client mechanics only.
AUTHORITY_IMPACT: None.
EXPECTED_PATH_PREFIXES: lbe_guard_inspector/product_entry.py,lbe_guard_inspector/cli.py,lbe_guard_inspector/runtime/,apps/lbe-terminal/,tests/,docs/governance/,PROJECT_INDEX.md,.lbe/governance/
REQUIRED_EVIDENCE: same-session local/headless/remote identity proof; cancellation/approval propagation; JSON event contract; disconnect/reconnect; fail-closed auth; focused/full regression; live multi-client acceptance.
MACHINE_SLICE: HEADLESS_REMOTE_SURFACE_CONVERGENCE
RESULT: NOT_STARTED
```
