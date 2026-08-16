# Current Implementation Gate

Status: **OPEN — R6D CONTEXT ASSEMBLY ACCEPTANCE — NEXT PHASE LOCKED**

Current phase: `R6D_CONTEXT_ASSEMBLY_ACCEPTANCE`

Current slice: `PROVE_BOUNDED_AUTHORITY_PRESERVING_CONTEXT_ACROSS_PROVIDER_AND_LIVE_WORKSPACE_BOUNDARIES`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R6D_CONTEXT_ASSEMBLY_ACCEPTANCE_CHECKPOINT.md
kind: acceptance proof, not implementation
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
status: OPEN
```

## Accepted baseline

```text
R3: PROVEN_COMPLETE
R4: PROVEN_COMPLETE
R5: PROVEN_COMPLETE
R6A: PROVEN_COMPLETE
R6B: PROVEN_COMPLETE
R6C: PROVEN_COMPLETE
```

Final synchronized R6C closure baseline:

```text
HEAD: 3d7bf3fbdc64f7dc9b57a617494381013b4513da
origin/main: 3d7bf3fbdc64f7dc9b57a617494381013b4513da
R6C gate: PASS
next_phase_locked: true
LoopTool closure command hash: ECEEA88E421AA1DD89CF498E78DCC59DFB35493496581A84828DA421A72FEE62
```

## Why R6D is selected next

R6A-R6C established provider neutrality, typed modes and deterministic authorization. Provider reasoning still depends on the context assembled before planning, so R6D is the next dependency boundary: LBE must preserve live workspace/evidence authority while passing bounded reference/session context to any provider.

Current source/tests already prove pieces independently:

- `assemble_reasoning_context()` deterministically orders caller/session context before validated indexed reference evidence;
- assembly copies source mappings rather than mutating them;
- `LBERequestController` uses that owner when constructing provider-facing `ReasoningRequest`;
- approved guard IDs remain a separate typed field rather than being inserted into `reference_context`;
- deterministic guard/current-workspace inspection remains LBE-owned after provider planning;
- `ReasoningPlan` rejects authority-bearing model fields including verdict, authorization, policy and mutation.

The missing artifact is combined integration proof for current-workspace-over-reference authority, equivalent LBE context across provider changes, and model-prose non-authority.

## Existing owners

```text
assemble_reasoning_context
ReasoningRequest
LBERequestController
EvidenceService
GuardRunner
SessionMemoryRuntimeBridge / LBERequest.reference_context
```

## Reuse decision

```text
REUSE
```

R6D is not being reimplemented.

## Acceptance question

Can the existing LBE context path provide bounded deterministic provider-facing context while keeping live workspace facts, guard applicability and governance authority LBE-owned across conflicting reference/history and provider changes?

## Required observable

1. identical authoritative inputs produce identical context ordering/content;
2. caller/session context precedes indexed reference evidence without source mutation;
3. approved guards stay on the typed guard channel and irrelevant/unapproved guards do not gain authority through context text;
4. conflicting reference/history cannot override current workspace/deterministic evidence;
5. provider A/B receive equivalent authoritative LBE context for equivalent inputs;
6. model-authored output cannot inject retrieval/governance/authorization/verdict/mutation authority;
7. no second context/retrieval/guard/policy owner is introduced.

## Falsifier

R6D cannot PASS if reference/history overrides current workspace truth, provider identity changes LBE context authority, unapproved guards become executable from prose, model output can establish policy/retrieval authority, or a parallel context/retrieval owner is required.

## Allowed work

- GitHub inspection of current context/evidence/controller/provider owners and tests;
- LoopTool execution of repository-owned tests and bounded runtime diagnostics;
- R6D acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- runtime/test implementation before a real defect is proven;
- R6E/R6F implementation;
- new context store/retrieval/guard selector/prompt-policy authority;
- provider-specific authority forks;
- CLI/TUI/MCP/release work;
- architecture changes.

## Current status

```text
source_owner_inspection: PASS
repository context tests: PRESENT
controller context handoff: PRESENT
combined authority-preserving integration: NOT RUN
focused regression: NOT RUN
checkpoint: UNVERIFIED
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

Do not advance automatically. If R6D exposes a real implementation defect, stop and activate a separate repair slice before modifying runtime or tests.
