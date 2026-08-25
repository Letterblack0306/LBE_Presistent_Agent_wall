# Stage 1 — Document Authority Map

```text
stage: 1
purpose: DOCUMENT_AUTHORITY_MAP
result: PASS_LOCAL_AWAITING_PUSH
scope: B1 documentation analysis only
source_commit: 2abca625cd277733aabfff2e79dbc168fa62d254
branch: main
remote: origin/main
file_moves_performed: none
historical_text_rewritten: none
B2_B3_B4_B5_touched: false
governance_touched: false
runtime_touched: false
```

This checkpoint records document ownership and proposed Stage 2 actions. It does not
move, delete, restore, merge, rewrite, or stage any document other than this checkpoint
when Stage 1 is canonicalized.

## Authority precedence

```text
current validation / live workspace evidence
  > .lbe/governance/implementation-gates.json
  > active acceptance gate named by the machine gate
  > canonical live owner documents
  > contracts and design intent
  > verified history and acceptance evidence
  > external/reference material
  > model inference
```

The machine governance file is explicitly outside the B1 staging boundary. It remains
the owner of permitted work and active-slice authorization even when a human-readable
document projects the same state.

## Canonical live owners — one fact to one owner

| Fact | One live owner | Supporting records | Competing claims are not owners |
|---|---|---|---|
| Current state, active slice, current gaps | `docs/CURRENT_STATUS.md` | `docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md`, root `README.md` | historical validation, old gates, design proposals |
| Architecture / execution wall | `docs/ARCHITECTURE.md` | `docs/design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md` | `docs/reference/docs/02_ARCHITECTURE.md`, product vision |
| Runtime contract | `docs/RUNTIME_CONTRACT.md` | `docs/LBE_AGENT_LIFECYCLE.md`, contracts | reference pipeline and historical blueprints |
| Runtime modes | `docs/MODES.md` | architecture, lifecycle, reference mode material | old execution-mode blueprints |
| Operational lifecycle | `docs/LBE_AGENT_LIFECYCLE.md` | `docs/design/AGENT_LIFECYCLE_PHASES.md` | implementation-plan summaries |
| Governance / permitted work | `.lbe/governance/implementation-gates.json` | `docs/governance/`, acceptance projections | prose status and historical gates |
| Active acceptance | machine gate `active_plan` → `docs/acceptance/COMPLETE_LBE_AGENT_RUNTIME_GATE.md` | `CURRENT_IMPLEMENTATION_GATE.md`, acceptance README | paused, superseded, and closed gates |
| Ordered implementation plan | `docs/IMPLEMENTATION_PLAN.md` | active acceptance gate, current status | roadmap/reference copies |
| Audit findings and review state | `docs/AUDIT_FINDING_REVIEW_REGISTER.md` | reference research | implementation plan summaries |
| Technical registries/contracts | `docs/contracts/` by named contract | implementation and acceptance evidence | status documents |
| Historical evidence | `docs/history/` and its catalog | acceptance records and provenance | current owners |
| External/product research | `docs/reference/` | design and current owner documents | acceptance proof |
| Architecture/design intent | `docs/design/` by named design subject | canonical live owners and active gate | current status |

## Document classes

```text
CANONICAL_LIVE_OWNER  current operational fact owner; may be updated in place
SUPPORTING_REFERENCE  linked context; cannot establish current status by itself
ACCEPTANCE_GATE_RECORD authorization, checkpoint, or proof record
CONTRACT              named technical registry or schema contract
DESIGN                proposed or detailed architecture/product intent
HISTORY_ARCHIVE       closed evidence retained without current authority
DUPLICATE             same live subject claimed by more than one document
STALE_SUPERSEDED      explicitly historical, paused, or replaced record
QUARANTINE            excluded from Stage 1 and requiring separate ownership review
```

## Relocation matrix — canonical spine and B1 documents

The action column is a proposal for Stage 2 only. Every row below is a classification;
no action below has been performed.

| Current path | Target class / target path | Stage 2 action | Classification / conflict note |
|---|---|---|---|
| `README.md` | canonical live owner / `README.md` | KEEP | package and top-level routing entry |
| `docs/README.md` | canonical live owner / `docs/README.md` | KEEP | documentation-library entry and routing owner |
| `docs/CURRENT_STATUS.md` | canonical live owner / same path | KEEP | sole prose owner of current state |
| `docs/ARCHITECTURE.md` | canonical live owner / same path | KEEP | sole execution-wall owner |
| `docs/RUNTIME_CONTRACT.md` | canonical live owner / same path | KEEP | sole runtime-contract owner |
| `docs/MODES.md` | canonical live owner / same path | KEEP | sole current mode-matrix owner |
| `docs/LBE_AGENT_LIFECYCLE.md` | canonical live owner / same path | KEEP | sole operational lifecycle owner |
| `docs/IMPLEMENTATION_PLAN.md` | canonical live owner / same path | KEEP | ordered plan owner; current state must link, not duplicate |
| `docs/AUDIT_FINDING_REVIEW_REGISTER.md` | canonical live owner / same path | KEEP | finding/review owner |
| `.agent/PROJECT_CONTEXT.md` | supporting instruction / `.agent/PROJECT_CONTEXT.md` | KEEP; link to owners | agent-routing context, not a competing status owner |
| `VALIDATION_CURRENT.md` | history/archive / `docs/history/VALIDATION_2026-07-25.md` | ARCHIVE_IN_STAGE_2 | file declares itself historical and not current |
| `LBE Documentation-Only Correction Instruction.md` | history/archive or controlled instruction catalog | MERGE_REVIEW_REQUIRED | root instruction artifact; ownership and target require review |
| `docs/acceptance/STAGE_0_BASELINE_FREEZE.md` | acceptance checkpoint / same path | KEEP | canonicalized Stage 0 checkpoint |
| `docs/acceptance/STAGE_1_DOCUMENT_AUTHORITY_MAP.md` | acceptance checkpoint / same path | KEEP | this Stage 1 checkpoint |
| `docs/acceptance/WORKSPACE_PRESERVATION_BOUNDARY_MATRIX.md` | acceptance/preservation record / same path | KEEP | boundary record; not authority for active implementation |
| `acceptance/post_fix_acceptance_plan.json` | history/archive / `docs/history/legacy-acceptance/post_fix_acceptance_plan.json` | ARCHIVE_IN_STAGE_2 | legacy acceptance fixture outside the canonical acceptance collection |
| `acceptance/README.md` | history/archive / `docs/history/legacy-acceptance/README.md` | ARCHIVE_IN_STAGE_2 | explicitly calls itself legacy acceptance fixtures |

## Relocation matrix — acceptance and gate records

All existing `docs/acceptance/*.md` files are acceptance/gate records. The active
human plan is determined only by the machine gate. Closed, paused, superseded, and
historical records remain evidence and are not current authorization.

| Current paths | Target class / target path | Stage 2 action | Classification |
|---|---|---|---|
| `docs/acceptance/README.md` | acceptance catalog / same path | KEEP | collection routing owner |
| `docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md` | acceptance projection / same path | KEEP | human projection of machine state; not machine authority |
| `docs/acceptance/COMPLETE_LBE_AGENT_RUNTIME_GATE.md` | active acceptance gate / same path | KEEP | active plan named by machine gate |
| `docs/acceptance/PUBLICATION_EXECUTION_AUTHORIZATION_GATE.md` | acceptance gate record / same path | KEEP | release authorization evidence, not current publish permission |
| `docs/acceptance/PUBLICATION_PRECHECK_GATE.md` | acceptance gate record / same path | KEEP | publication evidence |
| `docs/acceptance/PUBLICATION_VERSION_2_0_3_PREPARATION_GATE.md` | paused acceptance gate / same path | KEEP | target preparation record; publication remains machine-blocked |
| `docs/acceptance/TERMINAL_WORKSPACE_FOUNDATION_GATE.md` | superseded acceptance record / same path | KEEP; mark/link as superseded | not active authorization |
| `docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | checkpoint evidence |
| `docs/acceptance/CLI_NORMAL_PATH_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | gate evidence |
| `docs/acceptance/CLINE_CORE_REUSE_BOUNDARY_AUDIT_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | audit evidence |
| `docs/acceptance/CLINE_CORE_REUSE_BOUNDARY_AUDIT_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | gate evidence |
| `docs/acceptance/COMPLETE_LBE_TUI_IMPLEMENTATION_GATE.md` | superseded acceptance record / same path | KEEP; catalog as superseded | not active authorization |
| `docs/acceptance/CURRENT_AGENT_EXECUTION_GATE.md` | historical/superseded acceptance record / same path | KEEP; catalog as superseded | filename must not imply current authority |
| `docs/history/legacy-acceptance/LBE_CLINE_AGENTRUNTIME_INTEROP_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | checkpoint evidence |
| `docs/history/legacy-acceptance/LBE_CLINE_AGENTRUNTIME_INTEROP_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | gate evidence |
| `docs/acceptance/LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | checkpoint evidence |
| `docs/history/legacy-acceptance/LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | gate evidence |
| `docs/acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_ARCHITECTURE_GATE.md` | historical/design acceptance record / same path | KEEP; catalog as historical | not active architecture authority |
| `docs/history/legacy-acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_IMPLEMENTATION_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | checkpoint evidence |
| `docs/history/legacy-acceptance/LBE_CLINE_GOVERNED_NODE_STDIO_IMPLEMENTATION_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | gate evidence |
| `docs/acceptance/LBE_CLINE_PROVIDER_CONTINUATION_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | checkpoint evidence |
| `docs/history/legacy-acceptance/LBE_CLINE_PROVIDER_CONTINUATION_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | gate evidence |
| `docs/acceptance/LBE_RUNTIME_ROADMAP_RECONCILIATION_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | checkpoint evidence |
| `docs/history/legacy-acceptance/LBE_RUNTIME_ROADMAP_RECONCILIATION_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | gate evidence |
| `docs/acceptance/P16_CANCELLATION_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | checkpoint evidence |
| `docs/acceptance/R3_RUNTIME_REASONING_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/history/legacy-acceptance/R3_RUNTIME_REASONING_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/history/legacy-acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R5_BOUNDED_RECOVERY_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/history/legacy-acceptance/R5_BOUNDED_RECOVERY_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6A_PROVIDER_ABSTRACTION_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6A_PROVIDER_ABSTRACTION_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6B_TYPED_MODE_POLICY_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6E_GOVERNED_TOOL_ORCHESTRATION_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R6F_COMPLETION_VALIDATION_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/history/legacy-acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R7_INSTALLED_END_TO_END_ACCEPTANCE_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | accepted baseline evidence |
| `docs/acceptance/R7_OBSERVABLE13_DEPENDENCY_PROVISIONING_REPAIR_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | repair evidence |
| `docs/acceptance/R7_REPAIR_IMPLEMENTATION_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | repair evidence |
| `docs/history/legacy-acceptance/R7_REPAIR_IMPLEMENTATION_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | repair evidence |
| `docs/acceptance/R7_REPAIR_INVESTIGATION_CHECKPOINT.md` | historical acceptance record / same path | KEEP; catalog as closed | repair evidence |
| `docs/history/legacy-acceptance/R7_REPAIR_INVESTIGATION_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | repair evidence |
| `docs/acceptance/RELEASE_PACKAGE_CONTRACT_REPAIR_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | package evidence |
| `docs/acceptance/RELEASE_PACKAGE_READINESS_AUDIT_GATE.md` | historical acceptance record / same path | KEEP; catalog as closed | package evidence |

## Relocation matrix — contracts and design

| Current paths | Target class / target path | Stage 2 action | Classification |
|---|---|---|---|
| `docs/contracts/README.md` | contract catalog / same path | KEEP | current contract routing owner |
| `docs/contracts/PRIORITY_MODULE_REGISTRY.md` | contract / same path | KEEP | current module ownership registry |
| `docs/contracts/VALIDATED_WORKSPACE_MEMORY.md` | contract / same path | KEEP; review hash before move | current technical contract; B4 source/target is non-pure |
| `docs/design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md` | accepted design / same path | KEEP | accepted authority-separation design |
| `docs/design/AGENT_LIFECYCLE_PHASES.md` | design / same path | KEEP | product lifecycle design detail |
| `docs/design/AUTHORITY_OWNERSHIP_INSPECTOR_CONTRACT.md` | design/contract detail / same path | KEEP | ownership detail; link to runtime contract |
| `docs/design/C0_RUNTIME_POLICY_COMPOSITION_ROADMAP.md` | design roadmap / same path | KEEP; mark non-active | roadmap, not current authorization |
| `docs/design/C1_TASK_COMPLETION_POLICY_ROADMAP.md` | design roadmap / same path | KEEP; mark non-active | roadmap, not completion truth owner |
| `docs/design/CLI_CONTROL_PLANE_PROVIDER_BOUNDARY.md` | design / same path | KEEP | provider boundary detail |
| `docs/design/lbe_product_surface_spec.json` | design contract / same path | KEEP | machine-readable product-surface design |
| `docs/design/LBE_RUNTIME_VISION_DOCTRINE_DRIVEN_ENGINEERING.md` | design vision / same path | KEEP; mark proposed | product direction, not implementation authority |
| `docs/design/LLM_REASONING_LAYER_ROADMAP.md` | design roadmap / same path | KEEP; mark non-active | roadmap, not runtime authority |
| `docs/design/WORKSPACE_MODULAR_STRUCTURE_PLAN.md` | design plan / same path | KEEP; mark non-active | structure proposal, not current owner |
| `docs/research/CLINE_CORE_REUSE_BOUNDARY_MATRIX.md` | supporting research / same path | KEEP; mark reference | research input, not acceptance proof |

## Relocation matrix — governance, history, and reference

| Current paths | Target class / target path | Stage 2 action | Classification |
|---|---|---|---|
| `docs/governance/AGENT_IMPLEMENTATION_EXECUTION_GUIDE.md` | governance reference / same path | KEEP; link to machine gate | policy guidance, not machine state |
| `docs/governance/WORKSPACE_AND_IMPLEMENTATION_PROGRESSION_LOCK.md` | governance reference / same path | KEEP; link to machine gate | active governance prose; machine file remains authority |
| `docs/history/README.md` | history catalog / same path | KEEP | history routing owner |
| `docs/history/PHASE12_END_TO_END_PROOF.md` | history archive / same path | KEEP; review non-pure relocation | closed evidence; do not rewrite silently |
| `docs/history/PHASE_13_CALLBACK_VERTICAL_SLICE.md` | history archive / same path | KEEP; review non-pure relocation | closed evidence; do not rewrite silently |
| `docs/history/agent-evaluations/README.md` | history catalog / same path | KEEP | transcript-history routing |
| `docs/history/agent-evaluations/test-differfence-transcripts/*` | history archive / same subtree | KEEP; verify source/target hashes in Stage 2 | historical transcripts; not acceptance proof |
| `docs/reference/README.md` | supporting reference catalog / same path | KEEP | reference collection owner |
| `docs/reference/AGENT_REASONING_TRANSPORT_BOUNDARY.md` | supporting reference / same path | KEEP | reference evidence |
| `docs/reference/CLI_AGENT_REFERENCE_REVIEW_2026-08-21.md` | supporting reference / same path | KEEP; link current gap to status | future-slice reference, not authorization |
| `docs/reference/COMPLETION_CONTRACT_RESEARCH_EVIDENCE.md` | supporting reference / same path | KEEP | research evidence, not completion truth |
| `docs/reference/MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md` | supporting reference / same path | KEEP | evidence, not mode owner |
| `docs/reference/MANIFEST.json` | reference/package manifest / same path | KEEP | reference/package metadata |
| `docs/reference/schemas/*` | contract examples/reference / same subtree | KEEP | schemas and examples, not status |
| `docs/reference/examples/*` | reference examples / same subtree | KEEP | examples, not acceptance evidence |
| `docs/reference/ui/*` | reference UI/navigation artifacts / same subtree | KEEP; label visual reference | not browser/runtime proof |
| `docs/reference/docs/01_VISION.md` | history/reference archive / `docs/history/reference-legacy/docs/01_VISION.md` | MOVE_IN_STAGE_2 | explicitly historical Guard Inspector blueprint |
| `docs/reference/docs/02_ARCHITECTURE.md` | history/reference archive / `docs/history/reference-legacy/docs/02_ARCHITECTURE.md` | MOVE_IN_STAGE_2 | historical capability architecture; conflicts with canonical platform architecture |
| `docs/reference/docs/03_RUNTIME_PIPELINE.md` | history/reference archive / `docs/history/reference-legacy/docs/03_RUNTIME_PIPELINE.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/04_PROJECT_DETECTOR.md` | history/reference archive / `docs/history/reference-legacy/docs/04_PROJECT_DETECTOR.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/05_TOOL_REGISTRY.md` | history/reference archive / `docs/history/reference-legacy/docs/05_TOOL_REGISTRY.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/06_GUARD_SELECTOR.md` | history/reference archive / `docs/history/reference-legacy/docs/06_GUARD_SELECTOR.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/07_RULES_AND_GUARDS.md` | history/reference archive / `docs/history/reference-legacy/docs/07_RULES_AND_GUARDS.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/08_LBE_GALLERY.md` | history/reference archive / `docs/history/reference-legacy/docs/08_LBE_GALLERY.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/09_RETRIEVAL_AND_INSPECTION.md` | history/reference archive / `docs/history/reference-legacy/docs/09_RETRIEVAL_AND_INSPECTION.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/10_WORKSPACE_INSPECTION.md` | history/reference archive / `docs/history/reference-legacy/docs/10_WORKSPACE_INSPECTION.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/11_VALIDATION_AND_VERDICTS.md` | history/reference archive / `docs/history/reference-legacy/docs/11_VALIDATION_AND_VERDICTS.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/12_GOVERNANCE.md` | history/reference archive / `docs/history/reference-legacy/docs/12_GOVERNANCE.md` | MOVE_IN_STAGE_2 | legacy governance blueprint; machine gate supersedes |
| `docs/reference/docs/13_REASONING_LAYER.md` | history/reference archive / `docs/history/reference-legacy/docs/13_REASONING_LAYER.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/14_MEMORY_AND_CHECKPOINTS.md` | history/reference archive / `docs/history/reference-legacy/docs/14_MEMORY_AND_CHECKPOINTS.md` | MOVE_IN_STAGE_2 | legacy blueprint |
| `docs/reference/docs/15_EXECUTION_MODES.md` | history/reference archive / `docs/history/reference-legacy/docs/15_EXECUTION_MODES.md` | MOVE_IN_STAGE_2 | legacy mode material; canonical modes owner supersedes |
| `docs/reference/docs/16_ROADMAP.md` | history/reference archive / `docs/history/reference-legacy/docs/16_ROADMAP.md` | MOVE_IN_STAGE_2 | legacy roadmap; implementation plan supersedes |
| `docs/reference/docs/17_ACCEPTANCE_CRITERIA.md` | history/reference archive / `docs/history/reference-legacy/docs/17_ACCEPTANCE_CRITERIA.md` | MOVE_IN_STAGE_2 | legacy acceptance criteria |
| `docs/reference/docs/18_WORKED_EXAMPLES.md` | history/reference archive / `docs/history/reference-legacy/docs/18_WORKED_EXAMPLES.md` | MOVE_IN_STAGE_2 | legacy examples |
| `docs/reference/docs/19_IMPLEMENTATION_VERTICAL_SLICE.md` | history/reference archive / `docs/history/reference-legacy/docs/19_IMPLEMENTATION_VERTICAL_SLICE.md` | MOVE_IN_STAGE_2 | legacy implementation record |
| `docs/reference/docs/20_MIGRATION_FROM_OLD_BLUEPRINT.md` | history/reference archive / `docs/history/reference-legacy/docs/20_MIGRATION_FROM_OLD_BLUEPRINT.md` | MOVE_IN_STAGE_2 | migration/history record |

## Duplicate and conflict register — record only, do not resolve in Stage 1

| Subject | Conflicting or overlapping records | Stage 1 disposition |
|---|---|---|
| Current state | `docs/CURRENT_STATUS.md`, `docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md`, `.lbe/governance/implementation-gates.json`, `docs/IMPLEMENTATION_PLAN.md` | `CURRENT_STATUS.md` owns prose; machine gate owns permission; projections link only |
| Architecture | `docs/ARCHITECTURE.md`, `docs/design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md`, `docs/reference/docs/02_ARCHITECTURE.md`, vision/design files | canonical architecture wins; design supports; legacy reference is historical |
| Runtime contract | `docs/RUNTIME_CONTRACT.md`, `docs/reference/docs/03_RUNTIME_PIPELINE.md`, contract/detail documents | runtime contract wins; legacy pipeline is reference/history |
| Modes | `docs/MODES.md`, `docs/reference/docs/15_EXECUTION_MODES.md`, acceptance mode records | current mode matrix wins; old mode text is historical/reference |
| Governance | `.lbe/governance/implementation-gates.json`, `docs/governance/*.md`, `docs/reference/docs/12_GOVERNANCE.md` | machine gate wins; prose is policy/reference; legacy governance is historical |
| Acceptance | active complete-runtime gate versus many named current/execution/publication/TUI gates | machine `active_plan` selects one; all others are evidence unless explicitly selected |
| Implementation plan | `docs/IMPLEMENTATION_PLAN.md`, `docs/reference/docs/16_ROADMAP.md`, design roadmaps | implementation plan owns ordered work; old roadmaps remain reference/history |
| History | deleted roots and untracked `docs/history`/`docs/contracts` targets | Stage 2 must hash-match pure moves and separately review non-pure pairs |
| Package identity | root README, reference README, legacy blueprint | root README owns package surface; reference README owns historical capability blueprint |
| UI authority | copied `docs/reference/ui/*.html`, CLI reference, terminal gate, source | UI files are reference/navigation only; source and acceptance evidence decide runtime truth |

## Explicit exclusions from Stage 1

The following are not analyzed or changed by this checkpoint:

```text
B2 runtime/provider/user-state paths
B3 TUI/projection paths
B4 deleted sources and relocation targets
B5 .agent/evidence and Doc/cline quarantine paths
.lbe/governance/implementation-gates.json
```

Their preservation and ownership boundaries remain those recorded by
`docs/acceptance/WORKSPACE_PRESERVATION_BOUNDARY_MATRIX.md` and Stage 0. Any B4 move,
hash proof, or historical rewrite is deferred to Stage 2.

## Stage 1 consistency checks

| Check | Result |
|---|---|
| B1 source set read | PASS |
| Existing `docs` / `acceptance` structure enumerated | PASS — 127 files before this checkpoint; 128 live including this checkpoint |
| Canonical owners defined for current state, architecture, runtime contract, modes, governance, acceptance, plan, history | PASS |
| One fact → one live owner rule recorded | PASS |
| B1 relocation matrix complete | PASS |
| Duplicate/stale/conflicting claims recorded without resolution | PASS |
| Stage 1 moved/deleted/restored documents | PASS — none |
| B2/B3/B4/B5 touched | PASS — no |
| Governance file altered | PASS — no |
| Runtime implementation started | PASS — no |
| Historical evidence silently rewritten | PASS — no |
| Stage 1 checkpoint itself | PASS_LOCAL_AWAITING_PUSH |

## Stage boundary

Only this checkpoint may be staged for Stage 1 canonicalization. Stage 2 remains
locked until this file is committed, pushed, and verified on `origin/main`. Stage 2
must then execute one approved classification group at a time, hash-check pure moves,
review modified relocations separately, repair links/navigation, and validate the
canonical boot path.
