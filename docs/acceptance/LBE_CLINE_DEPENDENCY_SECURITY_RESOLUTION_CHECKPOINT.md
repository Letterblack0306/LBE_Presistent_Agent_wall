# LBE Cline Dependency Security Resolution Checkpoint

```text
phase: LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION
slice: RESOLVE_REACHABLE_DIFY_UNDICI_SECURITY_BLOCKER
status: UNVERIFIED

base_sha: 999a5b623530229e3135780afa89c984ef227aac
implementation_sha: 2288ccc38a68e71a6319ed877c670402ccf3bc3e
checkpoint_sha: populated by GitHub commit containing this file

requirements:
  - resolve the reachable vulnerable undici branch used through @cline/llms -> dify-ai-provider
  - keep @cline/agents pinned to 0.0.75
  - use the narrow candidate mitigation aligned with Cline upstream draft PR #13223
  - generate and validate a deterministic worker package-lock.json
  - prove no resolved undici <= 6.27.0 remains on the worker graph
  - prove npm audit has zero high/critical findings
  - prove direct @cline/agents import still succeeds
  - prove GovernedClineWorker and existing GovernedToolOrchestrator regression remain green
  - prove npm ci reproduces the dependency graph
  - prove the Python wheel contains worker.mjs, package.json, and the canonical package-lock.json

non_goals:
  - no provider-backed continuation implementation
  - no provider selection expansion
  - no ClineCore adoption
  - no LBE authorization/tool-orchestration changes
  - no MCP work
  - no TUI/CLI UI work
  - no preview.html implementation
  - no release-ready claim

existing_owner:
  - worker dependency contract -> lbe_guard_inspector/runtime/cline_worker/package.json
  - worker lifecycle -> lbe_guard_inspector/runtime/cline_stdio_bridge.py::GovernedClineWorker
  - authorization -> lbe_guard_inspector/runtime/authorization_resolver.py::resolve_authorization
  - governed execution/receipt -> lbe_guard_inspector/runtime/tool_orchestration.py::GovernedToolOrchestrator.invoke

reuse_decision:
  decision: ADAPT
  evidence: LBE adopts only the narrow dependency mitigation direction proposed by Cline draft PR #13223; no Cline runtime/provider logic is forked or duplicated.

architecture_change:
  introduced: no
  user_authorized: yes
  canonical_docs_updated_first: yes

files_changed:
  - .lbe/governance/implementation-gates.json
  - docs/acceptance/LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION_GATE.md
  - lbe_guard_inspector/runtime/cline_worker/package.json
  - docs/acceptance/LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION_CHECKPOINT.md

required_evidence_level: INTEGRATION

validation_evidence:
  dependency_resolution:
    command: npm install / npm ls on worker package after adding override undici@<6.0.0 -> >=7.29.0 <8
    result: PASS — Dify remains 1.1.1, provider-utils remains 3.0.32, its undici resolves to 7.29.0; other observed undici instances resolve to 6.28.0 or 7.29.0
  audit:
    command: npm audit --prefix lbe_guard_inspector/runtime/cline_worker --package-lock-only --json
    result: PASS FOR THIS GATE — 0 critical, 0 high, 0 moderate, 1 low
    residual: @ai-sdk/provider-utils@3.0.32 low severity uncontrolled resource consumption advisory, transitive/non-direct; gate requires zero high/critical rather than zero findings
  direct_import:
    command: import('@cline/agents') from worker directory
    result: PASS — AgentRuntime and createAgentRuntime remain functions
  focused_regression:
    command: python -m pytest tests/test_cline_stdio_bridge.py tests/test_tool_orchestration.py -q
    result: PASS — 20 passed at 2288ccc38a68e71a6319ed877c670402ccf3bc3e
  clean_install:
    command: npm ci --prefix lbe_guard_inspector/runtime/cline_worker --ignore-scripts --no-audit --no-fund
    result: PASS — generated lock reproduces successfully
  package_build:
    command: python -m build --wheel --outdir .lbe-tmp-dist
    result: PASS locally — generated wheel contained worker.mjs, package.json, and the locally generated package-lock.json
  implementation_gate:
    result: PASS — phase=LBE_CLINE_DEPENDENCY_SECURITY_RESOLUTION slice=RESOLVE_REACHABLE_DIFY_UNDICI_SECURITY_BLOCKER next_phase_locked=true
  git_diff_check:
    result: PASS on tracked state

security_evidence:
  - original Dify path was import-time reachable and resolved undici 5.29.0
  - current candidate override resolves the Dify undici dependency to 7.29.0
  - no observed worker-graph undici remains in the gate's affected range <=6.27.0
  - npm audit high finding is eliminated
  - one low @ai-sdk/provider-utils advisory remains and is recorded explicitly
  - Cline upstream PR #13223 remains draft/open and unmerged; it is supporting evidence only, not upstream approval

lock_transfer_evidence:
  - validated local package-lock.json size: 104917 bytes
  - validated local package-lock.json SHA-256: 19E594A4143A9241BF9FCE199969DF74574FC20B37B6BA404B786A9AA5AA811C
  - lock content was transported in eight bounded gzip/base64 chunks and reconstructed exactly; reconstructed size and SHA-256 matched the validated local artifact
  - a temporary GitHub Actions lock-generation workflow was attempted only after the active gate explicitly authorized it; the GitHub run failed before executing any job steps, consistent with the repository's existing Actions startup-failure condition
  - the temporary workflow was removed after that failed attempt
  - one GitHub contents transfer produced a partial lock payload; it was detected before acceptance and immediately deleted. That commit is not canonical evidence and no incomplete lock remains on main

unverified:
  - despite exact reconstruction, the current GitHub connector does not provide a file-upload/write primitive that can atomically transfer the full 104917-byte verified lock from the reconstructed artifact without reserializing it through a bounded text argument
  - therefore package-lock.json is still not canonical in GitHub
  - therefore the wheel proof does not yet prove packaging from a canonical GitHub lock
  - broader project/release readiness

document_conflicts:
  - docs/CURRENT_STATUS.md remains stale relative to current main; separate reconciliation remains required

workspace_proof:
  repository: Letterblack0306/LBE_Presistent_Agent_wall
  branch: main
  tested_head: 2288ccc38a68e71a6319ed877c670402ccf3bc3e
  origin_match: PASS

project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

## Current conclusion

The dependency-security mitigation itself is validated at integration level. The reachable Dify `undici@5.29.0` path is replaced by `undici@7.29.0`, the prior high-severity audit finding is eliminated, direct Cline import still works, `npm ci` succeeds, and the focused bridge/orchestrator regression remains 20/20.

The validated lock artifact itself is also now byte-for-byte identified and independently reconstructed: `104917` bytes with SHA-256 `19E594A4143A9241BF9FCE199969DF74574FC20B37B6BA404B786A9AA5AA811C`.

This checkpoint remains `UNVERIFIED`, not `PASS`, for one concrete integration reason: the verified lock still cannot be made canonical through the currently available GitHub connector without risking a partial or reserialized transfer, and GitHub Actions cannot currently execute the temporary generation workflow because the repository's Actions startup failure occurs before job steps run.

Do not unlock provider continuation, MCP, UI/TUI, or release work from this checkpoint.
