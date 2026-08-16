# R6D Context Assembly and Rule/Guard Injection Acceptance Gate

Status: **OPEN — ACCEPTANCE PROOF ONLY — NEXT PHASE LOCKED**

```text
phase: R6D_CONTEXT_ASSEMBLY_ACCEPTANCE
slice: PROVE_BOUNDED_AUTHORITY_PRESERVING_CONTEXT_ACROSS_PROVIDER_AND_LIVE_WORKSPACE_BOUNDARIES
base_sha: 3d7bf3fbdc64f7dc9b57a617494381013b4513da
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

## Selection rationale

R6C is closed PASS. R6D is the next dependency boundary because provider reasoning must receive bounded, reproducible context while LBE retains authority over workspace truth, guard selection and evidence classification. Current source already has a dedicated context assembly owner integrated into `LBERequestController`; this slice is acceptance-first and does not declare a defect.

## Acceptance question

Can the existing LBE context path assemble deterministic provider-facing context from caller/session context plus validated indexed reference evidence, keep guard/rule authority on separate typed LBE channels, preserve current-workspace truth over reference/history when they conflict, and produce equivalent authoritative context across provider changes without allowing model prose to become retrieval or governance authority?

## Existing owners

```text
context assembly:
  lbe_guard_inspector.runtime.context_assembly.assemble_reasoning_context

provider-facing contract:
  lbe_guard_inspector.reasoning_contracts.ReasoningRequest

controller/injection boundary:
  lbe_guard_inspector.request_controller.LBERequestController

current/reference evidence authority:
  EvidenceService
  GuardRunner
  validated evidence contracts

persistent caller/session context:
  SessionMemoryRuntimeBridge / LBERequest.reference_context
```

## Reuse decision

```text
REUSE
```

Do not introduce another context store, retrieval owner, guard selector, prompt-policy engine, or provider-specific context authority.

## Required observables

1. identical authoritative inputs produce identical assembled provider-facing context ordering/content;
2. caller/session context remains ahead of indexed reference evidence and input records are not mutated;
3. validated indexed reference evidence remains reference-class context and cannot become current workspace truth merely through model prose;
4. applicable guard IDs remain on `approved_guard_ids`, not duplicated or invented inside `reference_context`;
5. irrelevant/unapproved guard IDs are not exposed as executable authority;
6. current workspace/guard evidence remains the source of deterministic truth when reference/history conflicts with live evidence;
7. equivalent authoritative inputs presented through provider A and provider B produce equivalent LBE reasoning context/guard authority, aside from provider identity itself;
8. model-authored plan/explanation fields cannot inject authorization, policy, verdict, mutation, or retrieval authority;
9. no second context/retrieval/guard/policy owner is introduced;
10. focused context/controller/provider/evidence regression passes on the exact acceptance head.

## Falsifier

R6D cannot PASS if reference/history can override current workspace truth, provider identity changes LBE context authority, unapproved rules/guards become executable through context text, model prose can create retrieval/governance authority, identical authoritative inputs yield materially different LBE context, or a parallel context/retrieval/guard authority is required.

## Evidence ladder

```text
source owner inspection
-> repository-owned context/controller contract tests
-> deterministic assembly discriminator
-> conflicting reference vs live workspace authority discriminator
-> provider A/B equivalent-context discriminator
-> model-prose authority rejection proof
-> focused regression
-> diff/scope/worktree proof
-> checkpoint
```

## Allowed work

- GitHub inspection of current context/evidence/controller/provider owners and tests;
- LoopTool execution of repository-owned tests and bounded runtime diagnostics;
- R6D acceptance/checkpoint/status documentation through GitHub;
- diff/scope/worktree verification.

## Forbidden work

- runtime/test implementation before a real defect is proven;
- R6E/R6F implementation;
- new context store/retrieval engine/guard selector/prompt-policy authority;
- provider-specific authority forks;
- CLI/TUI/MCP/release work;
- architecture changes.

## Completion predicate

PASS only when bounded deterministic assembly, live-workspace authority precedence, provider-equivalent authoritative context, separate approved-guard authority and model-prose non-authority are proven through the existing owner path with no falsifier. PASS does not auto-activate R6E or another phase.
