# Cline Core Reuse Boundary Audit Checkpoint

phase: CLINE_CORE_REUSE_BOUNDARY_AUDIT
slice: CLASSIFY_CLINE_PROFESSIONAL_RUNTIME_REUSE
status: OPEN

base_sha: 31df367edcb9fc709ab99b5ce73a00fb3c13ae5a
implementation_sha: DOCUMENTATION_ONLY_GITHUB_AUDIT_PENDING_LOCAL_VALIDATION

cline_repository: cline/cline
cline_revision: 8bbdde2a5c1f972864fe1b954f639c21fac61a40

requirements:
  - audit current Cline core/agents/llms/shared source at exact revision
  - classify required professional-runtime capability families
  - identify existing LBE owner for every REUSE/ADAPT decision
  - record authority/bypass impact
  - identify first genuinely missing dependency without guessing

non_goals:
  - product/runtime implementation
  - new dependency adoption
  - architecture ownership changes
  - streaming/tool/TUI/MCP implementation

existing_owner:
  - workspace/session/authorization/evidence/validation/completion: existing LBE runtime owners
  - provider turn/cancellation: existing provider and turn runtime owners
  - deterministic authorization/tool dispatch: existing R6C/governed dispatcher owners
  - local evidence/execution routing: BirdEye
  - remote canonical source/revision truth: GitHub

reuse_decision:
  decision: ADAPT
  evidence: docs/research/CLINE_CORE_REUSE_BOUNDARY_MATRIX.md
  summary: reuse Cline AgentRuntime continuation/event/tool mechanics behind an LBE-owned adapter; reject direct native Cline mutation/execution tools as canonical LBE execution paths

required_evidence_level: INTEGRATION_DESIGN_EVIDENCE

validation_evidence:
  source_revision_proof: PASS - cline/cline 8bbdde2a5c1f972864fe1b954f639c21fac61a40
  matrix_completeness: PASS - all required capability families classified
  required_unverified_rows: none at source-audit level
  architecture_owner_change: NONE
  product_runtime_source_changes: NONE in the GitHub audit commit by construction; local post-pull proof still required
  machine_gate: PENDING LOCAL POST-PULL VALIDATION
  git_diff_check: PENDING LOCAL POST-PULL VALIDATION
  local_clean_worktree: PENDING LOCAL POST-PULL VALIDATION

unverified:
  - local post-pull machine-gate validation for the documentation-only audit commit
  - local git diff/check cleanliness after pulling the audit result
  - runtime integration behavior reserved for the separately authorized next slice

document_conflicts:
  - none found in the active audit contract

project_user_ready: UNVERIFIED
release_ready: UNVERIFIED
next_phase_locked: true

## Source-audit findings

1. Cline AgentRuntime already owns a mature model -> tool -> result -> provider-continuation loop.
2. `beforeTool` hooks and tool policies execute before `tool.execute()`, providing a viable interception point.
3. Direct Cline filesystem/editor and shell/process mutation paths cannot be canonical under strict LBE governance and are classified REJECT for direct reuse.
4. Cline model capability metadata is useful but intentionally permits unspecified/fail-open cases, so it is ADAPT rather than LBE capability authority.
5. ClineCore session persistence/checkpoints/events/automation are mature but would duplicate LBE authority if adopted wholesale; they are adapter/reference candidates only.
6. No new architecture authority owner is justified by this audit.

## First genuinely missing dependency

```text
LBE-to-Cline AgentRuntime governance adapter
```

Required responsibility:

- register/expose only LBE-governed executable tools to the reused Cline AgentRuntime path;
- call existing LBE deterministic authorization before any governed mutation/external action;
- guarantee denied actions never reach the Cline/tool executor;
- guarantee allowed actions execute exactly once through existing LBE owners;
- return governed results as Cline tool-result messages so the existing continuation loop is reused;
- project Cline runtime/provider/tool events into the LBE canonical event/evidence contract;
- keep native overlapping Cline mutation/execution tools disabled or unreachable;
- introduce no second session, authorization, evidence, validation or completion authority.

classification: ADAPT

required evidence for a future implementation slice: INTEGRATION

## Current classification

The **source-audit work is complete**, but this checkpoint intentionally remains `OPEN` until the GitHub documentation commit is pulled into the canonical primary worktree and the required local checks pass:

```text
python scripts/check-implementation-gate.py
git diff --check
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

Only after those checks confirm the exact audit commit, clean worktree and gate PASS may this checkpoint be changed to `PASS`.

After PASS, stop. A separate explicitly activated implementation slice is required before any adapter code is written.
