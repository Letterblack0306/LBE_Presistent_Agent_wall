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

## Retired agent and Cline control surfaces

| Path | Class | Intent / disposition |
|---|---|---|
The former `.agent/` and `.cline/` routing files were retired as obsolete local aliases. Current authority is owned by `PROJECT_INDEX.md`, `docs/README.md`, the governance ledger, and `.lbe/governance/implementation-gates.json`. Historical acceptance records may mention those paths to describe their former state; those records are not rewritten.

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

| `docs/acceptance/WORKSPACE_HYGIENE_GOVERNED_DELETION_CHECKPOINT.md` | `ACCEPTANCE_AUTHORITY` | PASS checkpoint for bounded governed disposable deletion; preserved snapshots remain outside this slice. |
| `docs/acceptance/RECOVERY_COMPLETION_PROMOTION_CHECKPOINT.md` | `ACCEPTANCE_AUTHORITY` | PASS checkpoint for recovery, deterministic completion, and proof promotion; installed-package acceptance remains a separate next slice. |
| `docs/acceptance/INSTALLED_PACKAGE_END_TO_END_ACCEPTANCE_CHECKPOINT.md` | `ACCEPTANCE_AUTHORITY` | PASS checkpoint for isolated installed-package runtime proof; publication remains separately locked. |
| `docs/acceptance/SESSION_APPLICATION_CONTRACT_UNIFICATION_CHECKPOINT.md` | `ACCEPTANCE_AUTHORITY` | PASS checkpoint for shared CLI/Textual session/provider lifecycle ownership; no new runtime authority. |

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
| `docs/acceptance/RELEASE_SCOPE_SPLIT_DECISION.md` | `ACCEPTANCE_AUTHORITY` | Decision record separating backend/package release readiness from the deferred visible Rust terminal acceptance; declares canonical-client selection OUT OF SCOPE/UNDECIDED; documents HEAD drift (807 passed/5 failed). Kept because governance references it. |
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
| `docs/governance/TUI_END_TO_END_TRACEABILITY.md` | `GOVERNANCE` | End-to-end TUI traceability map covering input, runtime authority, projections, tests, packaging, and live-acceptance gaps; reporting only. |
| `docs/governance/LBE_COMPLETE_PRODUCT_DIRECTION.md` | `GOVERNANCE` | North-star product-direction contract for normal coding-agent interaction, optional audit, authority ownership, lifecycle, feature scope, and acceptance rules. |
| `docs/governance/TUI_SURFACE_AUDIT_2026-09-21.md` | `GOVERNANCE` | Area-by-area TUI audit distinguishing complete pages, panels, partial setup flows, live proof, and remaining implementation gaps. |
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


## Full-document reconciliation supplement (2026-10-10)

This supplement closes the **path-inventory gap** found by comparing all on-disk files under `docs/` with the existing per-file manifest entries. The preexisting entries remain unchanged. An automated reader opened each file as bytes and classified the 59 previously missing paths by collection/declared purpose; each row includes a short content fingerprint. JSON examples, UI HTML/SVG, and historical transcripts are included instead of being silently excluded because they are not Markdown.

**Coverage:** 172 docs-tree files at this checkout; 113 paths already registered above; 59 additional paths below; zero missing paths after this supplement is applied. **This proves manifest coverage, not that every document's factual claims are currently correct or that every cross-reference is live.** The latter require a source-to-contract review with actual owner and revision; no PASS is automatically working.

When two docs disagree, resolve their authority by `docs/README.md`, `docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md` (product intent), current machine gate, and current source/runtime evidence. Preserve historical records. Never reclassify an acceptance checkpoint as current merely because its title contains GATE, LIVE or PASS.

| Path | Classification | Disposition and evidence fingerprint |
|---|---|---|
| `docs/acceptance/AUDIT_MODE_ENFORCEMENT_FINDING.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 4357 bytes; SHA256 `b56a1bff9c3b` |
| `docs/acceptance/FIRST_RUN_LIVE_SESSION_ENTRY_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1946 bytes; SHA256 `3b5905121274` |
| `docs/acceptance/GOVERNED_EXTERNAL_CAPABILITY_REGISTRATION_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 2724 bytes; SHA256 `4a30cc811cfb` |
| `docs/acceptance/INSTALLED_CAPABILITY_REGISTRY_DISCOVERY_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 2316 bytes; SHA256 `04ca0b72d357` |
| `docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1964 bytes; SHA256 `c729ff0709bf` |
| `docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 8955 bytes; SHA256 `4ab8bb329159` |
| `docs/acceptance/LBE_AGENT_CONVERSATION_CONTINUATION_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1296 bytes; SHA256 `2ec1cc6a5ff4` |
| `docs/acceptance/LBE_CLINE_WRAPPED_PRODUCT_GOVERNED_BIRDEYE_GATE.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 9829 bytes; SHA256 `79bf5a178a2c` |
| `docs/acceptance/LBE_INTERFACE_CONTROL_EVIDENCE_SURFACES_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 2503 bytes; SHA256 `caab97981145` |
| `docs/acceptance/LBE_INTERFACE_PRODUCT_SURFACE_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1340 bytes; SHA256 `2c47977e5280` |
| `docs/acceptance/LBE_LIVE_PROVIDER_CONVERSATION_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1048 bytes; SHA256 `b3d58b0edad9` |
| `docs/acceptance/LBE_PRODUCT_INTEGRATION_MACHINE_CHECK.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 4866 bytes; SHA256 `52bdd04ab4c4` |
| `docs/acceptance/MACHINE_FEATURE_TEST_REPORT_2026-09-21.json` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 3875 bytes; SHA256 `c8874fb25db0` |
| `docs/acceptance/MACHINE_FEATURE_TEST_REPORT_2026-09-21.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1369 bytes; SHA256 `514c1b24840b` |
| `docs/acceptance/MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 2767 bytes; SHA256 `ddd8bbf9c522` |
| `docs/acceptance/PARENT_CONTINUATION_AND_DEEP_CORRELATION_ACCEPTANCE_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1299 bytes; SHA256 `f894965c5fcc` |
| `docs/acceptance/PARENT_CONTINUATION_AND_DEEP_CORRELATION_ACCEPTANCE_GATE.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1274 bytes; SHA256 `65176780b9fd` |
| `docs/acceptance/PROVIDER_CONFIG_MODEL_FIELD_INCONSISTENCY.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 3668 bytes; SHA256 `86e974105f1b` |
| `docs/acceptance/PROVIDER_CREDENTIAL_PERSISTENCE_HAZARD.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 2631 bytes; SHA256 `5247a202f123` |
| `docs/acceptance/README.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 2082 bytes; SHA256 `ba5425d3bb8e` |
| `docs/acceptance/REASONING_ENGINE_PROVIDER_BINDING_SEPARATION_CHECKPOINT.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 4411 bytes; SHA256 `6460352ac0d3` |
| `docs/acceptance/TERMINAL_WORKSPACE_FOUNDATION_GATE.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1809 bytes; SHA256 `21d636c4159f` |
| `docs/acceptance/TEXTUAL_RETAINED_MODULE_FINDING.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 3947 bytes; SHA256 `d1b6c2c76ccd` |
| `docs/acceptance/TUI_INTERACTIVE_ACCEPTANCE_CHECKLIST.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 24127 bytes; SHA256 `c820c628be50` |
| `docs/acceptance/VISUAL_MACHINE_ACCEPTANCE_POLICY.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 1720 bytes; SHA256 `e5fb62f83c15` |
| `docs/acceptance/WORKSPACE_PRESERVATION_BOUNDARY_MATRIX.md` | ACCEPTANCE_HISTORY | Bounded checkpoint/gate; live activation must be checked separately; 7172 bytes; SHA256 `11571b518cc8` |
| `docs/BLOCKER_GUIDE.md` | REFERENCE | Support document; use canonical owners for current claims; 1622 bytes; SHA256 `ec726a0449b2` |
| `docs/contracts/README.md` | CONTRACT | Contract description; validate against current runtime; 416 bytes; SHA256 `48128c63a741` |
| `docs/design/lbe_product_surface_spec.json` | DESIGN | Design intent; not installed acceptance; 6976 bytes; SHA256 `099e16124ff9` |
| `docs/design/LBE_RUNTIME_VISION_DOCTRINE_DRIVEN_ENGINEERING.md` | DESIGN | Design intent; not installed acceptance; 10902 bytes; SHA256 `99a37ca09188` |
| `docs/design/PROVIDER_EXTENSIBILITY_REFERENCE_PLAN.md` | DESIGN | Design intent; not installed acceptance; 7462 bytes; SHA256 `1b6193877646` |
| `docs/governance/AGENT_DOCUMENT_WRITE_POLICY.md` | GOVERNANCE | Supporting governance; machine gate outranks prose; 5305 bytes; SHA256 `74d826fc000d` |
| `docs/GOVERNANCE_RULES.md` | GOVERNANCE | Guidance; consult machine gate; 5942 bytes; SHA256 `2251756d21bf` |
| `docs/history/agent-evaluations/README.md` | HISTORY | Retained record; no current-state authority; 1248 bytes; SHA256 `f8aab6ab9991` |
| `docs/history/agent-evaluations/test-differfence-transcripts/1785460319869_yl0hf/1785460319869_yl0hf.json` | HISTORY | Retained record; no current-state authority; 9038 bytes; SHA256 `4d06ad8d78ae` |
| `docs/history/agent-evaluations/test-differfence-transcripts/1785460319869_yl0hf/1785460319869_yl0hf.messages.json` | HISTORY | Retained record; no current-state authority; 36635 bytes; SHA256 `475a71d6fb52` |
| `docs/history/agent-evaluations/test-differfence-transcripts/1785461332072_pt9mp/1785461332072_pt9mp.json` | HISTORY | Retained record; no current-state authority; 6905 bytes; SHA256 `308c315119f3` |
| `docs/history/agent-evaluations/test-differfence-transcripts/1785461332072_pt9mp/1785461332072_pt9mp.messages.json` | HISTORY | Retained record; no current-state authority; 532681 bytes; SHA256 `97da3704c640` |
| `docs/history/legacy-acceptance/post_fix_acceptance_plan.json` | HISTORY | Retained record; no current-state authority; 1950 bytes; SHA256 `a1d1c399b9fb` |
| `docs/history/pasted-inputs/20260913-lbe-recovery-handoff.md` | HISTORY | Retained record; no current-state authority; 46134 bytes; SHA256 `d04c90e9bb41` |
| `docs/history/README.md` | HISTORY | Retained record; no current-state authority; 530 bytes; SHA256 `a9d0b366354b` |
| `docs/INTEGRATION.md` | REFERENCE | Support document; use canonical owners for current claims; 1655 bytes; SHA256 `feeb02838e98` |
| `docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md` | LIVE_OWNER | Human product-intent owner; dated claims require live verification; 14248 bytes; SHA256 `3d0578529869` |
| `docs/reference/examples/evidence_package.example.json` | REFERENCE | Historical design/fixture; not runtime truth; 1005 bytes; SHA256 `5ebfc674f5cf` |
| `docs/reference/examples/guard_request.example.json` | REFERENCE | Historical design/fixture; not runtime truth; 361 bytes; SHA256 `567431e99775` |
| `docs/reference/examples/guard_result.example.json` | REFERENCE | Historical design/fixture; not runtime truth; 637 bytes; SHA256 `f126c518fec6` |
| `docs/reference/MANIFEST.json` | REFERENCE | Historical design/fixture; not runtime truth; 1200 bytes; SHA256 `508fa9281684` |
| `docs/reference/schemas/evidence_package.schema.json` | REFERENCE | Historical design/fixture; not runtime truth; 2292 bytes; SHA256 `c58a9cb56e3c` |
| `docs/reference/schemas/guard_request.schema.json` | REFERENCE | Historical design/fixture; not runtime truth; 769 bytes; SHA256 `7e75e0e0451c` |
| `docs/reference/schemas/guard_result.schema.json` | REFERENCE | Historical design/fixture; not runtime truth; 1276 bytes; SHA256 `68e82cee3585` |
| `docs/reference/schemas/rule_proposal.schema.json` | REFERENCE | Historical design/fixture; not runtime truth; 1443 bytes; SHA256 `50811de69453` |
| `docs/reference/schemas/task_record.schema.json` | REFERENCE | Historical design/fixture; not runtime truth; 844 bytes; SHA256 `594d033940b5` |
| `docs/reference/TERMINAL_UI_CONTRACT_MAPPING.md` | REFERENCE | Historical design/fixture; not runtime truth; 7576 bytes; SHA256 `29d52b5a6200` |
| `docs/reference/ui/lbe-logo.svg` | REFERENCE | Historical design/fixture; not runtime truth; 913 bytes; SHA256 `afe90729aed5` |
| `docs/reference/ui/lbe_architecture_registry.html` | REFERENCE | Historical design/fixture; not runtime truth; 23481 bytes; SHA256 `46becd7571fa` |
| `docs/reference/ui/lbe_docs_node_map.html` | REFERENCE | Compatibility redirect to root LBE_DOCS_EXPLORER.html; historical references preserved; not runtime truth |
| `docs/reference/ui/lbe_landing_animated.html` | REFERENCE | Historical design/fixture; not runtime truth; 11398 bytes; SHA256 `070a0536773f` |
| `docs/reference/ui/lbe_product_surface.html` | REFERENCE | Historical design/fixture; not runtime truth; 9012 bytes; SHA256 `b9b45dd58ede` |
| `docs/reference/ui/lbe_tui_research_preview.html` | REFERENCE | Historical design/fixture; not runtime truth; 12742 bytes; SHA256 `e688eae84a4f` |

## Status-claim reconciliation queue (machine-identified, not fact-verified)

The following 99 Markdown documents contain a dated/status declaration and at least one strong readiness/status token. **This is a broad lexical review queue**, not proof each document is incorrect, and it is not a semantic per-claim acceptance review. Their original evidence remains intact. Prioritize current-source owners and active-gate-dependent records before historical checkpoints; do not turn the presence of the word PASS into acceptance.

| Document | First stated status/date | Required disposition |
|---|---|---|
| `docs/CURRENT_STATUS.md` | 2026-09-25 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/DOCUMENT_INTENT_MANIFEST.md` | **LIVE INVENTORY — CANONICAL REMOTE MARKDOWN SET** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/IMPLEMENTATION_PLAN.md` | 2026-09-25 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/LBE_AGENT_LIFECYCLE.md` | **Live operational document** - the complete end-to-end flow of an LBE agent | Require exact-version source or runtime check before any current-readiness claim |
| `docs/LBE_PRODUCT_SOURCE_OF_TRUTH.md` | **CANONICAL PRODUCT TRUTH** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/CLINE_CORE_REUSE_BOUNDARY_AUDIT_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/CLINE_CORE_REUSE_BOUNDARY_AUDIT_GATE.md` | **AUDIT PASS — NEXT IMPLEMENTATION PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_GATE.md` | **PASS — PROVEN_COMPLETE — RELEASE PATH ACTIVE — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/COMPLETE_LBE_AGENT_RUNTIME_GATE.md` | **CLOSED — COMPLETE RUNTIME AND SESSION CONTRACT PROVEN — PUBLICATION PAUSED | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/COMPLETE_LBE_TUI_IMPLEMENTATION_GATE.md` | **SUPERSEDED — RETAINED HISTORICAL TUI ACCEPTANCE RECORD** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/CURRENT_AGENT_EXECUTION_GATE.md` | **SUPERSEDED AS CURRENT AUTHORITY — HISTORICAL P16 PASS PRESERVED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md` | **OPEN — LBE-OWNED RUST TUI / INSTALLED PTY-CONPTY FINAL ACCEPTANCE** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/DOCTRINE_TO_PROVIDER_CONTEXT_BRIDGE_CHECKPOINT.md` | **PASS** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/FIRST_RUN_LIVE_SESSION_ENTRY_CHECKPOINT.md` | **PASS** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/GOVERNED_EXTERNAL_CAPABILITY_REGISTRATION_CHECKPOINT.md` | **PASS** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/INSTALLED_CAPABILITY_REGISTRY_DISCOVERY_CHECKPOINT.md` | **PASS** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_CHECKPOINT.md` | **REOPENED — SOURCE CONTRADICTION / FINAL PRODUCT NOT PROVEN** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_GATE.md` | **HISTORICAL PASS — NOT CURRENT ACCEPTANCE** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_AGENT_CONVERSATION_CONTINUATION_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_ARCHITECTURE_GATE.md` | PASS - ARCHITECTURE BOUNDED - PRODUCTION IMPLEMENTATION REQUIRES SEPARATE SL | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_CLINE_PROVIDER_CONTINUATION_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_CLINE_WRAPPED_PRODUCT_GOVERNED_BIRDEYE_GATE.md` | PASS - ARCHITECTURE BOUNDED - PRODUCTION IMPLEMENTATION REQUIRES SEPARATE SL | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_INTERFACE_CONTROL_EVIDENCE_SURFACES_CHECKPOINT.md` | **PASS** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_INTERFACE_PRODUCT_SURFACE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_LIVE_PROVIDER_CONVERSATION_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/LBE_RUNTIME_ROADMAP_RECONCILIATION_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/MANDATORY_GOVERNED_AGENT_MUTATION_DISPATCH_CHECKPOINT.md` | **PASS** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/P16_CANCELLATION_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/PARENT_CONTINUATION_AND_DEEP_CORRELATION_ACCEPTANCE_CHECKPOINT.md` | **PASS — LOCAL PROOF COMPLETE / GATE READY FOR CLOSURE** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/PARENT_CONTINUATION_AND_DEEP_CORRELATION_ACCEPTANCE_GATE.md` | **OPEN — READY FOR GATE CLOSURE** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/PROVIDER_CONFIG_MODEL_FIELD_INCONSISTENCY.md` | RECORDED, NOT RESOLVED | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/PROVIDER_CREDENTIAL_PERSISTENCE_HAZARD.md` | REMEDIATED at this revision | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/PUBLICATION_EXECUTION_AUTHORIZATION_GATE.md` | **AUTHORIZED FOR 2.0.3 — PUBLISH LOCKED PENDING VERSION VALIDATION** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/PUBLICATION_PRECHECK_GATE.md` | **PASS — REPOSITORY/SERVICE PRECHECK COMPLETE — PYPI TRUST BINDING ONLY PROV | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/PUBLICATION_VERSION_2_0_3_PREPARATION_GATE.md` | **OPEN — VERSION PREPARATION AUTHORIZED — PUBLISH LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R3_RUNTIME_REASONING_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R5_BOUNDED_RECOVERY_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6A_PROVIDER_ABSTRACTION_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6A_PROVIDER_ABSTRACTION_ACCEPTANCE_GATE.md` | **PASS — ACCEPTANCE COMPLETE — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_GATE.md` | **PASS — ACCEPTANCE PROOF COMPLETE — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_GATE.md` | **PASS — ACCEPTANCE PROOF COMPLETE — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_GATE.md` | **PASS — ACCEPTANCE PROOF COMPLETE — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_GATE.md` | **PASS — ACCEPTANCE PROOF COMPLETE — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_GATE.md` | **PASS — PROVEN COMPLETE — RELEASE PATH ACTIVE — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md` | **PASS — R7 INSTALLED END-TO-END ACCEPTANCE COMPLETE — RELEASE/PUBLISH STILL | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R7_OBSERVABLE13_DEPENDENCY_PROVISIONING_REPAIR_GATE.md` | **PASS — REPAIR CLOSED — IMPLEMENTATION LOCKED — NEXT OBSERVABLE MAY PROCEED | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R7_REPAIR_IMPLEMENTATION_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/R7_REPAIR_INVESTIGATION_CHECKPOINT.md` | PASS | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/REASONING_ENGINE_PROVIDER_BINDING_SEPARATION_CHECKPOINT.md` | IMPLEMENTED / STATIC VALIDATION ADDED / LIVE ACCEPTANCE PENDING | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/RELEASE_PACKAGE_CONTRACT_REPAIR_GATE.md` | **PASS — REPAIR CLOSED — PUBLISH LOCKED — ARCHITECTURE CHANGES FORBIDDEN** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/RELEASE_PACKAGE_READINESS_AUDIT_GATE.md` | **PASS — RELEASE/PACKAGE READINESS PROVEN — PUBLICATION STILL LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/RELEASE_SCOPE_SPLIT_DECISION.md` | **DECISION — RELEASE READINESS SCOPE SEPARATION** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/STAGE_2_FINAL_CHECKPOINT.md` | `PASS_LOCAL` | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/STAGE_3_GOVERNANCE_ALIGNMENT_CHECKPOINT.md` | `PASS_LOCAL` | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/TERMINAL_WORKSPACE_FOUNDATION_GATE.md` | **SUPERSEDED — RETAINED HISTORICAL ACCEPTANCE RECORD** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/TEXTUAL_RETAINED_MODULE_FINDING.md` | RECORDED | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/TUI_INTERACTIVE_ACCEPTANCE_CHECKLIST.md` | machine PTY input rows verified on 2026-10-08; full provider-connected accep | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/VISUAL_MACHINE_ACCEPTANCE_POLICY.md` | **ACTIVE — REQUIRED FOR VISIBLE PRODUCT ACCEPTANCE** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/acceptance/WORKSPACE_HYGIENE_GOVERNED_DELETION_CHECKPOINT.md` | `PASS` | Require exact-version source or runtime check before any current-readiness claim |
| `docs/design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md` | **PROPOSED FOLLOW-ON ARCHITECTURE REVIEW** (documentation only — no runtime  | Require exact-version source or runtime check before any current-readiness claim |
| `docs/design/AGENT_LIFECYCLE_PHASES.md` | **Live design artifact** — the single product lifecycle that everything hang | Require exact-version source or runtime check before any current-readiness claim |
| `docs/design/C0_RUNTIME_POLICY_COMPOSITION_ROADMAP.md` | 2026-08-10 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/design/C1_TASK_COMPLETION_POLICY_ROADMAP.md` | 2026-08-10 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/design/LBE_RUNTIME_VISION_DOCTRINE_DRIVEN_ENGINEERING.md` | **PROPOSED PRODUCT AND UX DIRECTION**. This document records product | Require exact-version source or runtime check before any current-readiness claim |
| `docs/design/PROVIDER_EXTENSIBILITY_REFERENCE_PLAN.md` | PLANNED / NOT IMPLEMENTED. Observed baseline: 2026-10-09, LBE `main` at `425 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/governance/AGENT_DOCUMENT_WRITE_POLICY.md` | **CANONICAL DOCUMENT-GOVERNANCE POLICY** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/governance/AGENT_IMPLEMENTATION_EXECUTION_GUIDE.md` | **CANONICAL OPERATING GUIDE** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/governance/LBE_COMPLETE_PRODUCT_DIRECTION.md` | active product-direction proposal | Require exact-version source or runtime check before any current-readiness claim |
| `docs/governance/PROJECT_INTENT_LEDGER.md` | **CANONICAL PRE-MUTATION INTENT LEDGER** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/governance/WORKSPACE_AND_IMPLEMENTATION_PROGRESSION_LOCK.md` | **AUTHORITATIVE GOVERNANCE GATE — ACTIVE ON `main`** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/PHASE_13_CALLBACK_VERTICAL_SLICE.md` | 2026-07-28 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/LBE_CLINE_AGENTRUNTIME_INTEROP_CHECKPOINT.md` | OPEN | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/LBE_CLINE_AGENTRUNTIME_INTEROP_GATE.md` | **OPEN — BOUNDARY PROOF ONLY — NEXT IMPLEMENTATION PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION_GATE.md` | OPEN — DEPENDENCY SECURITY ONLY — NEXT PHASE LOCKED | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_IMPLEMENTATION_CHECKPOINT.md` | UNVERIFIED | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_IMPLEMENTATION_GATE.md` | OPEN — FOUNDATION IMPLEMENTATION ONLY — NEXT SLICE LOCKED | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/LBE_CLINE_PROVIDER_CONTINUATION_GATE.md` | OPEN | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/LBE_RUNTIME_ROADMAP_RECONCILIATION_GATE.md` | OPEN | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/R3_RUNTIME_REASONING_ACCEPTANCE_GATE.md` | **OPEN — ACCEPTANCE PROOF ONLY — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_GATE.md` | **OPEN — ACCEPTANCE PROOF ONLY — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/R5_BOUNDED_RECOVERY_ACCEPTANCE_GATE.md` | **OPEN — ACCEPTANCE PROOF ONLY — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md` | OPEN | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/R7_REPAIR_IMPLEMENTATION_GATE.md` | OPEN | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/R7_REPAIR_INVESTIGATION_GATE.md` | **OPEN — INVESTIGATION ONLY — IMPLEMENTATION LOCKED — NEXT PHASE LOCKED** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/legacy-acceptance/RELOCATION_RECEIPT_2026-08-25.md` | HISTORICAL RELOCATION COMPLETE | Require exact-version source or runtime check before any current-readiness claim |
| `docs/history/pasted-inputs/20260913-lbe-recovery-handoff.md` | OPEN | Require exact-version source or runtime check before any current-readiness claim |
| `docs/reference/AGENT_REASONING_TRANSPORT_BOUNDARY.md` | 2026-08-11 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/reference/CLI_AGENT_REFERENCE_REVIEW_2026-08-21.md` | **REFERENCE-BASED PLANNING INPUT — NOT CURRENT LBE ACCEPTANCE EVIDENCE** | Require exact-version source or runtime check before any current-readiness claim |
| `docs/reference/COMPLETION_CONTRACT_RESEARCH_EVIDENCE.md` | 2026-08-10 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/reference/MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md` | 2026-08-10 | Require exact-version source or runtime check before any current-readiness claim |
| `docs/research/CLINE_CORE_REUSE_BOUNDARY_MATRIX.md` | **SOURCE AUDIT COMPLETE — LOCAL VALIDATION PENDING** | Require exact-version source or runtime check before any current-readiness claim |

## Root visual documentation entry (2026-10-10)

| Path | Class | Intent / disposition |
|---|---|---|
| `LBE_DOCS_EXPLORER.html` | ROUTER | Primary visual doc navigator; graph nodes include historical references, while the manifest owns the full inventory. Generated/runtime facts cannot be asserted from this static HTML. Serve from repository root over HTTP. |
