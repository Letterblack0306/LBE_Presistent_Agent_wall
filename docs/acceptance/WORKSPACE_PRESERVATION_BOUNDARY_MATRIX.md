# Workspace Preservation Boundary Matrix

```text
purpose: WORKSPACE_RECONCILIATION_PRESERVATION
status: ESTABLISHED (documentation only; no staging, branch, worktree, or delete mutation)

canonical authority:
  repository: Letterblack0306/LBE_Presistent_Agent_wall
  remote: origin
  branch: main
  worktree: primary (C:/Agents-Memory-Tool-v6-integration)
  head: 090a53f4847279e2515dc84677efdaa995b9c809

mutation_authorization: NOT_YET
branch_cleanup: BLOCKED
worktree_cleanup: BLOCKED
tui_architecture_decision: BLOCKED
release: BLOCKED
```

## Rule

Every later `git add` / commit / branch / worktree / delete action MUST be checked
mechanically against the exact membership and exclusion rules below. No file may be
staged or moved across boundaries. No boundary may be merged into another.

```text
B1 documentation/navigation/doctrine
B2 runtime/provider/user-state
B3 tui/projection
B4 historical transcript/doc relocation
B5 quarantine/review (.agent/evidence + Doc/cline/*)
```

## Membership

Paths are exact, captured from `git status --short --untracked-files=all` at the
canonical head in the status block above.

### B1 — Documentation / navigation / doctrine

Tracked-modified:

```text
.agent/PROJECT_CONTEXT.md
README.md
VALIDATION_CURRENT.md
docs/AUDIT_FINDING_REVIEW_REGISTER.md
docs/CURRENT_STATUS.md
docs/IMPLEMENTATION_PLAN.md
docs/README.md
docs/acceptance/CURRENT_IMPLEMENTATION_GATE.md
docs/acceptance/PUBLICATION_VERSION_2_0_3_PREPARATION_GATE.md
docs/design/AGENT_AGENCY_LBE_AUTHORITY_SEPARATION.md
docs/reference/CLI_AGENT_REFERENCE_REVIEW_2026-08-21.md
docs/reference/ui/lbe_architecture_registry.html
docs/reference/ui/lbe_docs_node_map.html
```

Untracked:

```text
acceptance/README.md
docs/ARCHITECTURE.md
docs/MODES.md
docs/RUNTIME_CONTRACT.md
docs/acceptance/COMPLETE_LBE_AGENT_RUNTIME_GATE.md
docs/acceptance/README.md
docs/acceptance/TERMINAL_WORKSPACE_FOUNDATION_GATE.md
docs/design/LBE_RUNTIME_VISION_DOCTRINE_DRIVEN_ENGINEERING.md
```

Root-level untracked instruction file (review before staging, not doctrine-internal):

```text
LBE Documentation-Only Correction Instruction.md
```

Exclusion rule — MUST NOT be staged in the B1 doc-only change:

```text
.lbe/governance/implementation-gates.json
```

Review-before-stage (mixed-content hunks, do not blindly `git add` the whole file):

```text
README.md
docs/reference/ui/lbe_architecture_registry.html
docs/reference/ui/lbe_docs_node_map.html
```

### B2 — Runtime / provider / user-state

Tracked-modified:

```text
lbe_guard_inspector/cli.py
lbe_guard_inspector/provider_registry.py
lbe_guard_inspector/provider_turn_runtime.py
lbe_guard_inspector/reasoning_config.py
lbe_guard_inspector/runtime/governed_coding.py
lbe_guard_inspector/runtime/tool_orchestration.py
```

Untracked new source:

```text
lbe_guard_inspector/credential_store.py
lbe_guard_inspector/runtime/agent_guidance.py
lbe_guard_inspector/user_state.py
```

Tests:

```text
tests/test_cli.py
tests/test_provider_registry.py
tests/test_provider_turn_runtime.py
tests/test_agent_guidance.py
tests/test_user_state.py
```

### B3 — TUI / projection

```text
lbe_guard_inspector/terminal_projection.py
lbe_guard_inspector/textual_tui.py
tests/test_terminal_projection.py
tests/test_textual_tui.py
```

Exclusion / hold — DO NOT COMMIT YET. Keep intact until the
Cline-vs-Textual architecture decision. Cleanup must not erase this evidence.
Relates to the secondary worktree
`C:/Agents-Memory-Tool-v6-integration.worktrees/tui-redesign-incomplete-features`.

### B4 — Historical transcript / doc relocation

Relocation deletions (tracked):

```text
docs/PHASE12_END_TO_END_PROOF.md
docs/PHASE_13_CALLBACK_VERTICAL_SLICE.md
docs/PRIORITY_MODULE_REGISTRY.md
docs/VALIDATED_WORKSPACE_MEMORY.md

tests/test differfence/1785460319869_yl0hf/1785460319869_yl0hf.json
tests/test differfence/1785460319869_yl0hf/1785460319869_yl0hf.messages.json
tests/test differfence/1785461332072_pt9mp/1785461332072_pt9mp.json
tests/test differfence/1785461332072_pt9mp/1785461332072_pt9mp.messages.json
```

Untracked relocation targets:

```text
docs/history/PHASE12_END_TO_END_PROOF.md
docs/history/PHASE_13_CALLBACK_VERTICAL_SLICE.md
docs/history/README.md
docs/history/agent-evaluations/README.md
docs/history/agent-evaluations/test-differfence-transcripts/1785460319869_yl0hf/1785460319869_yl0hf.json
docs/history/agent-evaluations/test-differfence-transcripts/1785460319869_yl0hf/1785460319869_yl0hf.messages.json
docs/history/agent-evaluations/test-differfence-transcripts/1785461332072_pt9mp/1785461332072_pt9mp.json
docs/history/agent-evaluations/test-differfence-transcripts/1785461332072_pt9mp/1785461332072_pt9mp.messages.json
docs/contracts/PRIORITY_MODULE_REGISTRY.md
docs/contracts/README.md
docs/contracts/VALIDATED_WORKSPACE_MEMORY.md
```

Rules:

- Pure hash-matching relocations within this set may form ONE unit.
- Modified historical moves (content differs between the deleted source and the
  new target) MUST be reviewed individually before being treated as a move.
- Before any delete is accepted as a "move", prove the target content hash equals
  the source content hash; otherwise it is a modification, not a relocation.

### B5 — Quarantine / review (.agent/evidence + Doc/cline/*)

```text
.agent/evidence/CURRENT_TASK.md
Doc/cline/1787447735839_spg38.messages.json
Doc/cline/1787447735839_spg38_actions.md
Doc/cline/1787447735839_spg38_content.md
```

Rule: do NOT stage, delete, or mix into any canonical commit until ownership is
established.

## Unassigned — excluded from all five boundaries

```text
.lbe/governance/implementation-gates.json   (modified, tracked; governance state,
                                             staged only by its own governance change)
```

## Mechanical check procedure (pre-staging validator)

```text
1. git status --short --untracked-files=all
2. partition every dirty path into exactly one boundary
3. assert no path is present in more than one boundary
4. assert .lbe/governance/implementation-gates.json is in NO staging set
   unless that set is the governance-change set
5. assert B3 paths are not staged (DO NOT COMMIT YET)
   unless the Cline-vs-Textual decision has explicitly lifted the hold
6. assert B4 deletions and B4 additions are staged together as one move unit
   and only if content-hash matched
7. assert B5 paths are absent from stage and index at all times
8. only then proceed to git add / git commit / branch / worktree reconciliation
```

## Reconciliation order (locked)

```text
1. preserve B1..B4 as five separate change units (documentation / runtime / hold / history)
2. reconcile branches against preserved local main state
3. remove obsolete PR + secondary worktree dependencies only after preservation confirmed
4. only when local main == origin/main with no unexplained dirt
   -> resume TUI architecture work
```

As of this record: step 1 is in progress, steps 2-4 are NOT yet authorized.