# R6D Context Assembly Acceptance Checkpoint

```text
phase: R6D_CONTEXT_ASSEMBLY_ACCEPTANCE
slice: PROVE_BOUNDED_AUTHORITY_PRESERVING_CONTEXT_ACROSS_PROVIDER_AND_LIVE_WORKSPACE_BOUNDARIES
status: UNVERIFIED

base_sha: 3d7bf3fbdc64f7dc9b57a617494381013b4513da
implementation_sha: NOT_APPLICABLE_ACCEPTANCE_ONLY
required_evidence_level: INTEGRATION
next_phase_locked: true
```

## Requirements

- prove deterministic bounded context ordering/content for identical authoritative inputs;
- prove caller/session context precedes indexed reference evidence without input mutation;
- prove guard/rule authority remains on typed LBE channels and unapproved guards cannot be created by context text;
- prove live workspace/deterministic evidence outranks conflicting reference/history;
- prove equivalent authoritative context across provider changes;
- prove model prose cannot inject verdict/authorization/policy/mutation/retrieval authority;
- run focused context/controller/provider/evidence regression on the exact acceptance head;
- record exact evidence, limitations, falsifiers, diff and clean-worktree proof.

## Existing owner

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
decision: REUSE
evidence: deterministic assembly and controller handoff already exist independently; combined provider/live-workspace authority acceptance is missing.
```

## Architecture change

```text
introduced: no
user_authorized: no new architecture requested
canonical_docs_updated_first: yes
```

## Validation evidence

```text
source_owner_inspection: PASS
repository_context_tests: PRESENT_NOT_YET_RUN_ON_GATE_HEAD
controller_context_handoff: SOURCE_PRESENT_NOT_YET_ACCEPTED
deterministic_assembly: NOT RUN
live_workspace_over_reference_conflict: NOT RUN
provider_equivalent_context: NOT RUN
approved_guard_channel_separation: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
model_prose_non_authority: SOURCE_PRESENT_NOT_YET_ACCEPTED
focused_regression: NOT RUN
git_diff_check: NOT RUN
worktree_clean: NOT RUN
```

## Falsifier state

```text
observed_falsifier: NONE YET
```

## Unverified

- combined live-workspace/reference conflict behavior;
- provider A/B equivalence at the actual controller boundary;
- absence of model-prose authority contamination in the same integrated path;
- focused regression and final scope/worktree proof.

## Document conflicts

```text
none known at activation
```

## Readiness

```text
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```
