# LBE Cline Provider Continuation Checkpoint

```text
phase: LBE_CLINE_PROVIDER_CONTINUATION
slice: ENABLE_PROVIDER_BACKED_AGENTRUNTIME_CONTINUATION
status: UNVERIFIED

base_sha: fc5512ffd0c405a9028f08f5a6d80f51fbe1d46d
implementation_sha: 703cf96bb896aa34f80c8e4e53397968fd9196ab
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
  - map failed AgentRuntime results to turn.failed with the underlying provider/runtime error
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
  initial_worker_sha: c10acb96cd7cbdd25a6c2f42917def4b66529ce1
  bridge_sha: ae110c32880b51e8a49bc864a286761efdba749d
  initial_tests_sha: e548076541b837f651bae3a8fc9b7640782d9bcf
  human_gate_reconciliation_sha: 17a1c64024cd02733baa201344d9636d5ecbbb56
  provider_fixture_fix_sha: 506ffc81f744781ad48e59125fc47c91661eb8b3
  failed_result_mapping_fix_sha: 703cf96bb896aa34f80c8e4e53397968fd9196ab

validation_evidence:
  source_contract:
    result: PASS BY SOURCE INSPECTION
    evidence: pinned Cline AgentRuntime exposes run/continue/abort; AgentTool execute callback and AgentRunResult shapes were inspected at revision 8bbdde2a5c1f972864fe1b954f639c21fac61a40
  node_syntax_initial:
    result: PASS at aecda2d08f0c799cf131a6a01021f7445b127866
  canonical_install_initial:
    result: PASS — npm ci installed 213 packages from the canonical worker lock
  initial_focused_provider_continuation:
    command: python -m pytest tests/test_cline_stdio_bridge.py -q
    result: FAIL — 9 passed, 2 failed
  provider_wire_diagnostic:
    result: PROVEN — original provider_id=openai produced AgentRunResult status=failed before HTTP; REQUESTS=[]; exact error was Unknown or disabled provider "openai".
  installed_provider_registry_diagnostic:
    result: PROVEN — actual installed @cline/llms@0.0.75 registry has no provider id openai; it exposes openai-compatible with model gpt-4o.
  corrected_provider_direct_runtime_probe:
    result: PASS — providerId=openai-compatible, modelId=gpt-4o completed with output hello from cline; one POST reached /v1/chat/completions with stream=true and usage enabled.
  failed_result_terminal_mapping:
    original_result: DISPROVEN — worker emitted turn.completed even when AgentRuntime returned status=failed and omitted result.error
    correction: 703cf96bb896aa34f80c8e4e53397968fd9196ab maps failed results to turn.failed / CLINE_AGENTRUNTIME_FAILED and preserves the underlying error message
  corrected_focused_provider_continuation:
    result: NOT RUN
  governed_orchestrator_regression:
    result: NOT RUN after correction
  dependency_security:
    result: PRIOR PASS; must be rechecked for zero high/critical on the corrected head
  implementation_gate:
    result: NOT RUN on corrected head
  git_diff_check:
    result: NOT RUN on corrected head

failure_classification:
  provider_selection_defect:
    classification: PROVEN IMPLEMENTATION/TEST CONFIGURATION DEFECT
    evidence: installed runtime rejects provider id openai and accepts openai-compatible; corrected direct runtime probe reaches the deterministic stub and completes
  terminal_mapping_defect:
    classification: PROVEN IMPLEMENTATION DEFECT
    evidence: AgentRuntime status=failed was wrapped as turn.completed; corrected worker now emits turn.failed
  test_harness_failure:
    classification: DISPROVEN for the text completion fixture
    evidence: the same local SSE fixture completed successfully once the valid installed provider identity was used

unverified:
  - corrected full focused provider-continuation suite at the exact current GitHub head
  - real tool-call proposal/result continuation through GovernedToolOrchestrator after provider identity correction
  - cancellation runtime behavior
  - external live-provider proof; missing credentials/configuration must remain BLOCKED_CONFIGURATION rather than being fabricated
  - focused/orchestrator/security/gate/diff validation on the corrected head
  - broader release readiness

document_conflicts:
  - RESOLVED: CURRENT_IMPLEMENTATION_GATE.md and .lbe/governance/implementation-gates.json now both declare LBE_CLINE_PROVIDER_CONTINUATION / ENABLE_PROVIDER_BACKED_AGENTRUNTIME_CONTINUATION
  - docs/IMPLEMENTATION_PLAN.md and docs/CURRENT_STATUS.md contain older sequencing and require a later separate reconciliation; they do not override the live machine gate, active plan, current checkpoint, or accepted P0-P16 history

project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

## Current conclusion

The earlier two-test failure is now causally explained. The actual published `@cline/llms@0.0.75` provider registry does not register `openai`; it registers `openai-compatible`. Direct execution with `openai-compatible` / `gpt-4o` reached the deterministic `/v1/chat/completions` stub and completed successfully, disproving the text-response fixture as the cause of the first failure.

A second independent adapter defect was also proven: failed `AgentRuntime` results were emitted as `turn.completed`. The worker now maps those results to `turn.failed` with the underlying error.

The slice remains `UNVERIFIED` until the corrected GitHub head is pulled to the canonical workspace and passes the focused provider/tool continuation tests plus the required regressions and gate checks. Do not advance the next phase before that proof.
