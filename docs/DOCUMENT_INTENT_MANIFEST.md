# LBE Document Intent Manifest

Status: **LIVE INVENTORY — CANONICAL REMOTE MARKDOWN SET**

This manifest explains the intended role of every tracked Markdown file in the canonical LBE
repository. It is a navigation and classification record; it does not replace machine governance,
the active acceptance gate, source code, or runtime evidence.

## Classification rules

| Class | Meaning | Disposition |
|---|---|---|
| `ROUTER` | Entry point or routing instructions | Keep and link from the appropriate boot surface |
| `LIVE_OWNER` | Sole current owner of a fact, contract, or operational state | Keep current; do not duplicate |
| `GOVERNANCE` | Rules that constrain implementation progression | Keep; machine governance outranks prose |
| `ACCEPTANCE_AUTHORITY` | Active machine-selected or publication authority | Keep in `docs/acceptance/` |
| `ACCEPTANCE_HISTORY` | Closed, superseded, or historical proof | Preserve under `docs/history/` |
| `CONTRACT` | Current technical contract or registry | Keep as a named contract |
| `DESIGN` | Architecture or product design intent | Keep; not proof of runtime behavior |
| `REFERENCE` | Research or external/product reference | Keep but exclude from authority |
| `HISTORY` | Closed evidence or prior implementation record | Preserve; do not treat as current |
| `TEMPLATE` | Reusable recording template | Keep for governed records |
| `UNUSED_BUT_PRESERVED` | Material proven not to participate in the live repository but retained for recovery/review | Preserve only under `unused-in-repo/`; never treat as live authority |

An entry being unreferenced does not make it invalid. It must be classified before relocation or
removal. Every entry below has an explicit role and disposition.

## Agent and Cline control surfaces

| Path | Class | Intent / disposition |
|---|---|---|
| `.agent/CLINE_REUSE_AUDIT_INSTRUCTIONS.md` | `GOVERNANCE` | Instructions for the Cline reuse-boundary audit; keep as agent audit procedure. |
| `.agent/IMPLEMENTATION_CHECKPOINT_TEMPLATE.md` | `TEMPLATE` | Template for recording implementation checkpoint state; keep and reuse. |
| `.agent/PROJECT_CONTEXT.md` | `ROUTER` | First-read project routing and authority precedence; keep as the agent entrypoint. |
| `.cline/README.md` | `ROUTER` | Cline-specific project-control entrypoint; keep at its tool-consumed path. |
| `.cline/rules/00-lbe-workspace-and-progression.md` | `GOVERNANCE` | Always-on workspace and progression rules for Cline; keep at its runtime path. |
| `.cline/rules/01-cline-runtime-reuse-boundary.md` | `GOVERNANCE` | Always-on rule preventing Cline from replacing LBE authority; keep at its runtime path. |
| `.cline/skills/lbe-phase-execution/SKILL.md` | `GOVERNANCE` | Procedure for executing one governed LBE slice; keep at its skill path. |

## Root operational documents

| Path | Class | Intent / disposition |
|---|---|---|
| `BASELINE_VALIDATION.md` | `HISTORY` | Historical Agent.py baseline and validation record; preserve, do not use as current proof. |
| `MIGRATION.md` | `REFERENCE` | Legacy-state migration and rollback instructions; keep for migration use. |
| `PROJECT_INDEX.md` | `GOVERNANCE` | Root structural authority index; every implementation area must have an owner and mutation boundary before change. |
| `README.md` | `ROUTER` | Product overview and installation/usage entrypoint; keep concise and non-authoritative for mutable state. |

## Preserved unused-material registry

| Path | Class | Intent / disposition |
|---|---|---|
| `unused-in-repo/README.md` | `ROUTER` | Explains the bounded preservation surface; not a live project authority. |
| `unused-in-repo/MANIFEST.md` | `UNUSED_BUT_PRESERVED` | Records proof, ownership, original location, restoration notes, and move evidence for each preserved item. |

## Live documentation owners

| Path | Class | Intent / disposition |
|---|---|---|
| `docs/AUDIT_FINDING_REVIEW_REGISTER.md` | `LIVE_OWNER` | Owner for finding review and disposition records; keep current. |
| `docs/CURRENT_STATUS.md` | `LIVE_OWNER` | Human-readable current-state projection; must mirror machine governance and live evidence. |
| `docs/IMPLEMENTATION_PLAN.md` | `LIVE_OWNER` | Ordered roadmap and implementation sequence; must not become a second active-state authority. |
| `docs/LBE_AGENT_LIFECYCLE.md` | `LIVE_OWNER` | Operational lifecycle owner for an LBE agent turn; keep current. |
| `docs/README.md` | `ROUTER` | Canonical documentation entrypoint, collection map, and document-hygiene policy. |
| `docs/DOCUMENT_INTENT_MANIFEST.md` | `ROUTER` | This per-file intent inventory; keep synchronized with the tracked Markdown set. |

## Acceptance and gate records

| Path | Class | Intent / disposition |
|---|---|---|
| `docs/acceptance/CLINE_CORE_REUSE_BOUNDARY_AUDIT_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed Cline source-reuse audit proof; preserve as historical evidence. |
| `docs/acceptance/CLINE_CORE_REUSE_BOUNDARY_AUDIT_GATE.md` | `ACCEPTANCE_HISTORY` | Closed Cline reuse-audit gate; preserve as historical evidence. |
| `docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed CLI normal-path proof; preserve as historical evidence. |
| `docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_GATE.md` | `ACCEPTANCE_HISTORY` | Closed CLI acceptance gate; preserve as historical evidence. |
| `docs/acceptance/COMPLETE_LBE_AGENT_RUNTIME_GATE.md` | `ACCEPTANCE_AUTHORITY` | Machine-declared complete-runtime active plan; keep in the active acceptance namespace. |
| `docs/acceptance/COMPLETE_LBE_TUI_IMPLEMENTATION_GATE.md` | `ACCEPTANCE_HISTORY` | Superseded TUI acceptance record; preserve outside live authority. |
| `docs/acceptance/CURRENT_AGENT_EXECUTION_GATE.md` | `ACCEPTANCE_HISTORY` | Superseded P16 execution record; preserve as history, not current authority. |
| `docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md` | `ACCEPTANCE_AUTHORITY` | Human projection of the machine gate; keep aligned with governance. |
| `docs/acceptance/DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Completed doctrine-bridge slice proof; preserve as closed evidence. |
| `docs/acceptance/LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed dependency-security resolution proof; preserve as history. |
| `docs/acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_ARCHITECTURE_GATE.md` | `ACCEPTANCE_HISTORY` | Bounded Cline Node architecture decision; preserve as historical design evidence. |
| `docs/acceptance/LBE_CLINE_PROVIDER_CONTINUATION_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed provider-continuation proof; preserve as historical evidence. |
| `docs/acceptance/LBE_RUNTIME_ROADMAP_RECONCILIATION_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed roadmap reconciliation proof; preserve as history. |
| `docs/acceptance/P16_CANCELLATION_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed cancellation checkpoint; preserve as historical proof. |
| `docs/acceptance/PUBLICATION_EXECUTION_AUTHORIZATION_GATE.md` | `ACCEPTANCE_AUTHORITY` | Publication authorization boundary; keep because governance references it. |
| `docs/acceptance/PUBLICATION_PRECHECK_GATE.md` | `ACCEPTANCE_HISTORY` | Completed publication precheck; preserve as release evidence. |
| `docs/acceptance/PUBLICATION_VERSION_2_0_3_PREPARATION_GATE.md` | `ACCEPTANCE_AUTHORITY` | Current version-preparation authority; keep because governance references it. |
| `docs/acceptance/R3_RUNTIME_REASONING_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R3 proof; preserve as historical evidence. |
| `docs/acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R4 proof; preserve as historical evidence. |
| `docs/acceptance/R5_BOUNDED_RECOVERY_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R5 proof; preserve as historical evidence. |
| `docs/acceptance/R6A_PROVIDER_ABSTRACTION_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R6A proof; preserve as historical evidence. |
| `docs/acceptance/R6A_PROVIDER_ABSTRACTION_ACCEPTANCE_GATE.md` | `ACCEPTANCE_HISTORY` | Closed R6A gate; preserve as historical evidence. |
| `docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R6B proof; preserve as historical evidence. |
| `docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_GATE.md` | `ACCEPTANCE_HISTORY` | Closed R6B gate; preserve as historical evidence. |
| `docs/acceptance/R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R6C proof; preserve as historical evidence. |
| `docs/acceptance/R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_GATE.md` | `ACCEPTANCE_HISTORY` | Closed R6C gate; preserve as historical evidence. |
| `docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R6D proof; preserve as historical evidence. |
| `docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_GATE.md` | `ACCEPTANCE_HISTORY` | Closed R6D gate; preserve as historical evidence. |
| `docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R6E proof; preserve as historical evidence. |
| `docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_GATE.md` | `ACCEPTANCE_HISTORY` | Closed R6E gate; preserve as historical evidence. |
| `docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R6F proof; preserve as historical evidence. |
| `docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_GATE.md` | `ACCEPTANCE_HISTORY` | Closed R6F gate; preserve as historical evidence. |
| `docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md` | `ACCEPTANCE_HISTORY` | Closed R7 installed acceptance proof; preserve as historical evidence. |
| `docs/acceptance/R7_OBSERVABLE13_DEPENDENCY_PROVISIONING_REPAIR_GATE.md` | `ACCEPTANCE_HISTORY` | Closed R7 dependency repair proof; preserve as historical evidence. |
| `docs/acceptance/R7_REPAIR_IMPLEMENTATION_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R7 repair implementation proof; preserve as historical evidence. |
| `docs/acceptance/R7_REPAIR_INVESTIGATION_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed R7 repair investigation proof; preserve as historical evidence. |
| `docs/acceptance/RELEASE_PACKAGE_CONTRACT_REPAIR_GATE.md` | `ACCEPTANCE_HISTORY` | Closed release-contract repair proof; preserve as historical evidence. |
| `docs/acceptance/RELEASE_PACKAGE_READINESS_AUDIT_GATE.md` | `ACCEPTANCE_HISTORY` | Closed package-readiness proof; preserve as historical evidence. |
| `docs/acceptance/STAGE_0_BASELINE_FREEZE.md` | `ACCEPTANCE_HISTORY` | Closed Stage 0 baseline record; preserve as historical evidence. |
| `docs/acceptance/STAGE_1_DOCUMENT_AUTHORITY_MAP.md` | `ACCEPTANCE_HISTORY` | Closed Stage 1 authority-map record; preserve as historical evidence. |
| `docs/acceptance/STAGE_2_FINAL_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed Stage 2 relocation record; preserve as historical evidence. |
| `docs/acceptance/STAGE_3_GOVERNANCE_ALIGNMENT_CHECKPOINT.md` | `ACCEPTANCE_HISTORY` | Closed Stage 3 governance record; preserve as historical evidence. |

## Contracts

| Path | Class | Intent / disposition |
|---|---|---|
| `docs/contracts/PRIORITY_MODULE_REGISTRY.md` | `CONTRACT` | Registry contract for prioritized LBE modules and ownership; keep current. |
| `docs/contracts/VALIDATED_WORKSPACE_MEMORY.md` | `CONTRACT` | Validated workspace-memory and adapter contract; keep as a technical contract. |

## Design and roadmap

| Path | Class | Intent / disposition |
|---|---|---|
| `docs/design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md` | `DESIGN` | Defines provider agency versus LBE authority ownership; keep as architecture boundary. |
| `docs/design/AGENT_LIFECYCLE_PHASES.md` | `DESIGN` | Live lifecycle map of phases, owners, surfaces, and Cline reuse boundaries. |
| `docs/design/AUTHORITY_OWNERSHIP_INSPECTOR_CONTRACT.md` | `DESIGN` | Contract for inspecting and proving authority ownership; keep as design contract. |
| `docs/design/C0_RUNTIME_POLICY_COMPOSITION_ROADMAP.md` | `DESIGN` | Documentation-first policy-composition roadmap; retain as planned design. |
| `docs/design/C1_TASK_COMPLETION_POLICY_ROADMAP.md` | `DESIGN` | Documentation-first completion-policy roadmap; retain as planned design. |
| `docs/design/CLI_CONTROL_PLANE_PROVIDER_BOUNDARY.md` | `DESIGN` | Accepted CLI, control-plane, and provider boundary; keep as architecture direction. |
| `docs/design/LLM_REASONING_LAYER_ROADMAP.md` | `DESIGN` | Reasoning-layer design proposal; keep but exclude from current authority. |
| `docs/design/WORKSPACE_MODULAR_STRUCTURE_PLAN.md` | `DESIGN` | Workspace modular-structure draft; keep as proposed design until approved or superseded. |

## Governance

| Path | Class | Intent / disposition |
|---|---|---|
| `docs/governance/AGENT_IMPLEMENTATION_EXECUTION_GUIDE.md` | `GOVERNANCE` | Canonical operating guide for implementation execution; keep current. |
| `docs/governance/PROJECT_INTENT_LEDGER.md` | `GOVERNANCE` | Canonical pre-mutation intent authority binding requested work to one active machine slice; keep current. |
| `docs/governance/WORKSPACE_AND_IMPLEMENTATION_PROGRESSION_LOCK.md` | `GOVERNANCE` | Active progression and one-slice lock; keep as governance reference. |

## Closed history

| Path | Class | Intent / disposition |
|---|---|---|
| `docs/history/PHASE12_END_TO_END_PROOF.md` | `HISTORY` | Closed Phase 12 proof record; preserve and exclude from current authority. |
| `docs/history/PHASE_13_CALLBACK_VERTICAL_SLICE.md` | `HISTORY` | Closed Phase 13 proof record; preserve and exclude from current authority. |
| `docs/history/VALIDATION_2026-07-25.md` | `HISTORY` | Dated historical validation report; preserve as evidence only. |
| `docs/history/legacy-acceptance/README.md` | `ROUTER` | Catalog for archived acceptance records; keep as history navigation. |
| `docs/history/legacy-acceptance/RELOCATION_RECEIPT_2026-08-25.md` | `HISTORY` | Receipt proving the prior acceptance relocation; preserve immutably. |

The following legacy acceptance files are historical records, not current gates:

| Path | Intent / disposition |
|---|---|
| `docs/history/legacy-acceptance/LBE_CLINE_AGENTRUNTIME_INTEROP_CHECKPOINT.md` | Preserve interop-boundary evidence. |
| `docs/history/legacy-acceptance/LBE_CLINE_AGENTRUNTIME_INTEROP_GATE.md` | Preserve superseded interop gate. |
| `docs/history/legacy-acceptance/LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION_GATE.md` | Preserve dependency-security gate. |
| `docs/history/legacy-acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_IMPLEMENTATION_CHECKPOINT.md` | Preserve unverified implementation checkpoint. |
| `docs/history/legacy-acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_IMPLEMENTATION_GATE.md` | Preserve superseded Node foundation gate. |
| `docs/history/legacy-acceptance/LBE_CLINE_PROVIDER_CONTINUATION_GATE.md` | Preserve provider-continuation gate. |
| `docs/history/legacy-acceptance/LBE_RUNTIME_ROADMAP_RECONCILIATION_GATE.md` | Preserve roadmap reconciliation gate. |
| `docs/history/legacy-acceptance/R3_RUNTIME_REASONING_ACCEPTANCE_GATE.md` | Preserve R3 acceptance gate. |
| `docs/history/legacy-acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_GATE.md` | Preserve R4 acceptance gate. |
| `docs/history/legacy-acceptance/R5_BOUNDED_RECOVERY_ACCEPTANCE_GATE.md` | Preserve R5 acceptance gate. |
| `docs/history/legacy-acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md` | Preserve R7 observable checkpoint. |
| `docs/history/legacy-acceptance/R7_REPAIR_IMPLEMENTATION_GATE.md` | Preserve R7 repair gate. |
| `docs/history/legacy-acceptance/R7_REPAIR_INVESTIGATION_GATE.md` | Preserve R7 investigation gate. |

The numbered reference set is retained as an immutable legacy blueprint:

| Path range | Intent / disposition |
|---|---|
| `docs/history/reference-legacy/docs/01_VISION.md` | Historical vision blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/02_ARCHITECTURE.md` | Historical architecture blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/03_RUNTIME_PIPELINE.md` | Historical runtime-pipeline blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/04_PROJECT_DETECTOR.md` | Historical project/workspace detector blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/05_TOOL_REGISTRY.md` | Historical tool-registry blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/06_GUARD_SELECTOR.md` | Historical guard-selector blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/07_RULES_AND_GUARDS.md` | Historical rules-and-guards blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/08_LBE_GALLERY.md` | Historical LBE gallery/knowledge blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/09_RETRIEVAL_AND_INSPECTION.md` | Historical retrieval/inspection blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/10_WORKSPACE_INSPECTION.md` | Historical workspace-inspection blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/11_VALIDATION_AND_VERDICTS.md` | Historical validation/verdict blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/12_GOVERNANCE.md` | Historical governance blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/13_REASONING_LAYER.md` | Historical reasoning-layer blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/14_MEMORY_AND_CHECKPOINTS.md` | Historical memory/checkpoint blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/15_EXECUTION_MODES.md` | Historical execution-mode blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/16_ROADMAP.md` | Historical roadmap blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/17_ACCEPTANCE_CRITERIA.md` | Historical acceptance-criteria blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/18_WORKED_EXAMPLES.md` | Historical worked examples; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/19_IMPLEMENTATION_VERTICAL_SLICE.md` | Historical implementation-slice blueprint; preserve outside current ownership. |
| `docs/history/reference-legacy/docs/20_MIGRATION_FROM_OLD_BLUEPRINT.md` | Historical migration blueprint; preserve outside current ownership. |

## Reference and research

| Path | Class | Intent / disposition |
|---|---|---|
| `docs/reference/AGENT_REASONING_TRANSPORT_BOUNDARY.md` | `REFERENCE` | Reasoning/provider transport boundary reference; keep as non-authoritative evidence. |
| `docs/reference/CLI_AGENT_REFERENCE_REVIEW_2026-08-21.md` | `REFERENCE` | CLI product-surface review; use as planning input, not acceptance authority. |
| `docs/reference/COMPLETION_CONTRACT_RESEARCH_EVIDENCE.md` | `REFERENCE` | Completion-contract research evidence; keep outside current-state ownership. |
| `docs/reference/MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md` | `REFERENCE` | Mode-policy wiring evidence; keep as reference, not live governance. |
| `docs/reference/README.md` | `ROUTER` | Reference collection entrypoint; keep and route readers to evidence boundaries. |
| `docs/research/CLINE_CORE_REUSE_BOUNDARY_MATRIX.md` | `REFERENCE` | Cline reuse/adaptation/rejection matrix; preserve the LBE-owned adapter decision. |
| `examples/reference/README.md` | `REFERENCE` | Reference examples catalog; keep outside product authority. |
| `schemas/reference/lbe_agent_blueprint/README.md` | `REFERENCE` | Historical/reference schema blueprint; preserve outside runtime authority. |

## Maintenance invariant

This manifest must be updated whenever a tracked Markdown file is added, removed, moved, or
reclassified. A clean index is not sufficient completion evidence: the manifest, inbound links,
machine governance paths, and the local workspace inventory must agree.
