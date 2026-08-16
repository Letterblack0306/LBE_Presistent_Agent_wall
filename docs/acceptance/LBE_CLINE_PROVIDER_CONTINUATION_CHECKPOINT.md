# LBE Cline Provider Continuation Checkpoint

```text
phase: LBE_CLINE_PROVIDER_CONTINUATION
slice: ENABLE_PROVIDER_BACKED_AGENTRUNTIME_CONTINUATION
status: UNVERIFIED

base_sha: fc5512ffd0c405a9028f08f5a6d80f51fbe1d46d
implementation_sha: e548076541b837f651bae3a8fc9b7640782d9bcf
checkpoint_sha: populated by GitHub commit containing this file

requirements:
  - instantiate pinned @cline/agents AgentRuntime from ephemeral provider configuration
  - do not persist or echo provider credentials
  - expose only explicit LBE allowed_tools as Cline AgentTool proxies
  - emit tool.proposed with deterministic identity chain
  - mediate every executable proposal through existing GovernedToolOrchestrator.invoke
  - feed ToolReceipt back as tool.result to the same Cline continuation loop
  - map cancellation to AgentRuntime.abort
  - fail closed on tool-result identity mismatch
  - preserve LBE evidence/validation/completion/session authority

existing_owner:
  - Cline continuation -> @cline/agents@0.0.75 AgentRuntime.run/continue
  - worker lifecycle/protocol -> GovernedClineWorker
  - authorization -> resolve_authorization
  - registered tool execution/receipt/idempotency -> GovernedToolOrchestrator.invoke
  - canonical human implementation history -> docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md

reuse_decision:
  decision: ADAPT
  evidence: the pinned Cline AgentRuntime already owns provider streaming, tool-call parsing, tool execution callbacks, and continuation; LBE supplies proxy tools whose execute callbacks cross the existing governed Python boundary rather than duplicating the Cline loop.

required_evidence_level: INTEGRATION

implementation:
  gate_activation_sha: 23cdd43c6b0f2445f9a6d69afc83987bf244f1f1
  worker_sha: c10acb96cd7cbdd25a6c2f42917def4b66529ce1
  bridge_sha: ae110c32880b51e8a49bc864a286761efdba749d
  tests_sha: e548076541b837f651bae3a8fc9b7640782d9bcf

validation_evidence:
  source_contract:
    result: PASS BY SOURCE INSPECTION
    evidence: pinned Cline AgentRuntime exposes run/continue/abort; AgentTool execute callback and AgentRunResult shapes were inspected at revision 8bbdde2a5c1f972864fe1b954f639c21fac61a40
  node_syntax:
    result: PASS at aecda2d08f0c799cf131a6a01021f7445b127866
  canonical_install:
    result: PASS — npm ci installed 213 packages from the canonical worker lock
  focused_provider_continuation:
    command: python -m pytest tests/test_cline_stdio_bridge.py -q
    result: FAIL — 9 passed, 2 failed
    failures:
      - test_local_provider_turn_completes_through_real_cline_runtime: AgentRuntime result status was failed rather than completed
      - test_cline_tool_call_routes_through_governed_orchestrator_and_continues: terminal output_text was empty rather than tool complete
  governed_orchestrator_regression:
    result: NOT RUN because the focused provider-continuation command failed first
  dependency_security:
    result: NOT RE-RUN because focused proof failed first; prior dependency-security slice remains PASS
  implementation_gate:
    result: NOT RUN in the failed command because execution stopped at focused proof
  git_diff_check:
    result: NOT RUN in the failed command because execution stopped at focused proof

failure_classification:
  observed: provider-backed Cline execution reaches the new integration tests but fails to produce the expected successful terminal result
  current_classification: UNKNOWN
  hypotheses_not_yet_proven:
    - TEST_HARNESS_FAILURE / stale OpenAI-compatible fixture
    - PROVIDER_PROTOCOL_MISMATCH between the pinned Cline provider adapter and the local SSE stub
    - IMPLEMENTATION_DEFECT in worker provider configuration or result mapping
  required_next_diagnostic: capture the actual HTTP request path/body, exact turn result payload, and worker stderr before any implementation patch

unverified:
  - exact provider wire protocol selected by @cline/llms@0.0.75 for providerId=openai with the configured baseUrl
  - whether the deterministic local provider fixture matches that selected protocol
  - real tool-call proposal/result continuation through GovernedToolOrchestrator
  - cancellation runtime behavior
  - external live-provider proof; missing credentials/configuration must remain BLOCKED_CONFIGURATION rather than being fabricated
  - full focused/orchestrator/security/gate/diff validation after the provider failure is resolved
  - broader release readiness

document_conflicts:
  - BLOCKING: docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md still declares P16_BACKGROUND_PROVIDER_EXECUTION / NON_BLOCKING_TURN_LIFECYCLE_AND_CONTROL_HANDOFF as the current active slice, while .lbe/governance/implementation-gates.json declares LBE_CLINE_PROVIDER_CONTINUATION / ENABLE_PROVIDER_BACKED_AGENTRUNTIME_CONTINUATION
  - docs/IMPLEMENTATION_PLAN.md and docs/CURRENT_STATUS.md also contain older sequencing; live accepted P0-P16 history outranks those older sections, but they still require later reconciliation
  - per .agent/PROJECT_CONTEXT.md and docs/governance/AGENT_IMPLEMENTATION_EXECUTION_GUIDE.md, the CURRENT_IMPLEMENTATION_GATE conflict must be reconciled before another implementation patch

project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

## Current conclusion

The provider-continuation implementation is present on GitHub, but it is not accepted. Runtime evidence at `aecda2d08f0c799cf131a6a01021f7445b127866` proves the focused suite currently has `9 passed / 2 failed`; the root cause is not yet proven.

A separate governance defect is also now explicit: the machine gate and `CURRENT_IMPLEMENTATION_GATE.md` disagree about the active slice. That is a blocking `DOCUMENT_CONFLICT` under the repository's own progression rules.

Do not patch the worker from the current hypotheses. First reconcile the human/machine active-slice record, then run one discriminating read/debug probe that captures the actual provider request path/body, exact AgentRuntime result payload, and worker stderr. Only after that evidence identifies the failing layer may a bounded correction be made.
