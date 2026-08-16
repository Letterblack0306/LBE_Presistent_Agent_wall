# Current Implementation Gate

Status: **OPEN — R4 CHECKPOINT/RESUME ACCEPTANCE PROOF — NEXT PHASE LOCKED**

Current phase: `R4_CHECKPOINT_RESUME_ACCEPTANCE`

Current slice: `PROVE_CHECKPOINT_RESTART_REHYDRATION_AND_STALE_STATE_INVALIDATION`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_CHECKPOINT.md
kind: acceptance proof, not implementation
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

## Prior gate

R3 runtime-to-existing-reasoning acceptance is complete and remains PASS.

Validated local/project closure head:

```text
9523cf02f8a2e9248ad87d7f6f4cadef6d959f51
```

R3 is classified `PROVEN_COMPLETE` and must not be reopened merely because R4 is now active.

## Existing owners

```text
persistent runtime/session/task:
  SessionMemoryRuntimeBridge

checkpoint + rehydrate adapter:
  SessionMemoryAdapter.checkpoint_compaction()
  SessionMemoryAdapter.rehydrate()

live source/Git revalidation:
  invalidate_changed_sources()
  protected_checkpoint_eligibility()
  rehydrate_context()

persistent state:
  WorkspaceMemoryStore
```

## Reuse decision

```text
REUSE
```

R4 is not being reimplemented. Current source already contains checkpoint, restart, stale-source invalidation and protected reactivation logic.

## Acceptance question

Does the existing runtime satisfy the R4 roadmap contract when a verified source fact and active constraint are checkpointed, the source and Git HEAD change externally, and the same session/task is reconstructed and resumed?

## Required observable

The bounded proof must show:

1. stable session/task/workspace identity across restart;
2. original source-backed fact is initially verified;
3. checkpoint identity is persisted;
4. checkpoint constraint survives restart;
5. external source change creates a different current Git HEAD;
6. resumed packet exposes the new current HEAD rather than the checkpoint HEAD;
7. checkpoint revalidation reports `head=MISMATCH`, `status=INELIGIBLE`, `reactivation_allowed=false`;
8. old source-backed fact becomes `STALE`;
9. stale fact is absent from resumed `verified_facts`;
10. task lifecycle and persisted provider/session configuration survive reconstruction;
11. compaction/history material is not promoted as current workspace truth;
12. no new checkpoint/resume/session/memory owner is introduced.

## Falsifier

R4 cannot PASS if stale source evidence remains verified/current, changed Git state is hidden by checkpoint state, constraints disappear, identity changes, compaction/history becomes workspace truth, or the proof requires a new parallel owner.

## Allowed work

- source/test inspection;
- bounded deterministic temporary-repository integration proof;
- focused R4/session-memory regression;
- acceptance/checkpoint documentation;
- diff/worktree proof.

## Forbidden work

- runtime/test source implementation before a real defect is proven;
- R5/R6/R7 implementation;
- new checkpoint/resume/session/memory owner;
- provider architecture changes;
- CLI/TUI/MCP/release work;
- architecture changes.

## Current status

```text
source owner inspection: PASS
integration proof: NOT RUN
focused regression: NOT RUN
checkpoint: UNVERIFIED
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

Do not advance automatically. If the R4 proof exposes a real implementation defect, stop and activate a separate bounded repair slice before modifying runtime source.
