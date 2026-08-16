# R7 Installed End-to-End Acceptance Gate

Status: **OPEN — OBSERVABLE 4 ACTIVE — IMPLEMENTATION LOCKED — NEXT OBSERVABLE LOCKED**

```text
phase: R7_INSTALLED_END_TO_END_ACCEPTANCE
slice: OBSERVABLE_4_PROVIDER_MODEL_SWITCH_AUTHORITY_STABILITY
base_sha: 69c6ae764bc217cd5795ddf8a972658223a681a0
original_activation_sha: 401a4f184fcbeae5ff6e4d58be139515b9861ed2
resume_after_repair: true
status: OPEN
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INSTALLED_RUNTIME_FRESH_PROCESS
release_path_authorized: true
publish_allowed_now: false
```

## Acceptance question

Can a clean installed LBE normal path perform persistent coding/audit work across separate processes and restart boundaries, preserve LBE authority while provider/model changes, revalidate after external workspace change, keep audit read-only, fail closed outside authority, and reach completion only through accepted evidence-owned validation?

## Required observables

1. exact-head isolated install without source leakage — `PASS`;
2. persistent installed session identity — `PASS`;
3. governed installed coding execution/receipts — `PASS_AFTER_REPAIR`;
4. **ACTIVE:** provider/model switch preserves workspace, mode, permission, profile, evidence policy, and LBE authority identity;
5. fresh installed process resumes the same persistent session/task identity;
6. bounded external workspace change is observed/revalidated rather than stale checkpoint state;
7. audit/investigation cannot mutate workspace state;
8. out-of-workspace/forbidden/out-of-authority action fails closed without mutation;
9. receipt/provider continuation correlation remains intact;
10. provider completion remains provisional until deterministic persisted validation;
11. terminal `COMPLETED / VALIDATED_COMPLETION` persists across a fresh process;
12. no credential/secret leakage into repo/logs/receipts/artifacts;
13. focused installed/runtime regression with exact package/head/environment evidence;
14. source remains unchanged unless a real falsifier activates a separate repair slice;
15. clean worktree plus exact limitations/falsifiers.

## Repaired observable 3 evidence

Installed normal coding now reaches the existing authority chain:

```text
lbe code
 -> GovernedAgentGateway
 -> GovernedClineWorker
 -> R6C authorization
 -> R6E GovernedToolOrchestrator
 -> ToolReceipt
 -> tool.result continuation
 -> CodingCompletionRuntime provisional state
```

Decisive command hash: `F3FB75C252CB7B561C05A233D4F93FC981032A0DAF41F9B90E9952FB9677F882`.

Observed: mutation `ALLOW`, receipt `EXECUTED`, two provider requests, `read_only=false`, provider completion truth false, persisted `running / AWAITING_VALIDATION`, source worktree clean.

## Observable 4 predicate

Using the installed package and persisted session authority, switch provider/model identity through the normal installed control plane and prove that only provider/model fields change. These must remain invariant:

```text
session_id
project_workspace_id
canonical_workspace_root
mode
permission
runtime_policy
active_profile_id
permission_policy_id
evidence_policy_id
```

Then prove a fresh installed process reads the switched provider/model together with the unchanged invariant authority fields.

## Falsifier

Any unauthorized change to workspace/mode/permission/profile/policy/evidence authority, loss of persistent session identity, source-tree dependency, or provider switch bypassing the normal installed persistent control plane is a product falsifier.

## Stop rule

Observable 4 is the only active acceptance slice. Do not run observable 5 or change production code until observable 4 is classified. A product falsifier requires a separate repair activation.
