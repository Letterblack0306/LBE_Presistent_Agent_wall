# Workspace execution discipline

These rules are always active for this repository.

## Establish truth before acting
- At task start, inspect the actual repository root, current branch, HEAD, dirty state, and relevant active files before proposing edits.
- Treat source files, runtime evidence, tests, and current Git state as truth. Documentation, indexed knowledge, prior chats, and historical reports are guidance only until confirmed against the current workspace.
- Do not assume a file is active because its name matches the feature. Trace entry points, imports, registries, factories, routes, or runtime loaders to identify the active owner.
- Distinguish known, mapped, inspected, reachable, runtime-active, changed, and validated paths.

## Diagnose before editing
- Classify the problem first: structural, behavioral, runtime, integration, state, permission/authority, validation, performance, or recovery.
- Capture the exact failure or requirement, then identify the earliest proven incorrect state.
- Form only bounded hypotheses and run discriminating checks before editing.
- Prefer the smallest proven edit surface. Do not patch the final symptom when an earlier owner is proven.

## Preserve architecture and authority
- Reuse existing contracts, planners, services, guards, and governance boundaries before creating new abstractions.
- Search for duplicate or parallel implementations before adding a new module, route, provider, state owner, or execution path.
- Do not create a second authority for an operation already owned elsewhere.
- The reasoning model may interpret, select, request evidence, explain, and propose. Deterministic guards own verdict conditions; validation owns proof; governance owns authorization and mutation authority.
- Never synthesize PASS/FAIL from model opinion, documentation, or indexed reference knowledge.

## Workspace hygiene
- Work only in the current resolved repository unless the task explicitly requires another repository.
- Do not create extra repository copies, worktrees, backup trees, patch scripts, temporary source files, or generated artifacts unless they are required by the task and cleaned afterward.
- Do not modify generated `build/`, `dist/`, cache, state, or local-secret files unless the task explicitly targets them.
- Never stage secrets, local provider configuration, runtime databases, caches, or unrelated files.
- Stage exact intended paths; avoid broad staging when the workspace contains unrelated or untracked content.
- Keep one feature concern per branch/commit where practical.

## Evidence and validation
- Validate at the level required by the claim: source -> static/build -> unit/contract -> integration -> runtime -> user-visible proof.
- A successful command or passing unit test is not proof that the active runtime path uses the change.
- After a fix, perform a bounded regression/duplicate-authority scan around the affected path.
- Run focused tests first, then the repository-level validation required by the project before declaring completion.
- Run `git diff --check` and inspect `git status --short` before final completion.
- Do not claim completion when required validation was not executed, evidence is missing, or an in-scope blocker remains.

## Interaction behavior
- Use repository and terminal tools to inspect and validate directly instead of asking the user to manually copy/paste information that the available tools can obtain.
- Ask the user only when intent is materially ambiguous, required authority is missing, or a decision changes scope or persistent policy.
- Keep progress reports concise. Report the proven issue, the affected authority/path, what changed, validation evidence, and any remaining blocker.

## Project-specific reasoning boundary
- Follow `docs/design/LLM_REASONING_LAYER_ROADMAP.md`, `docs/CURRENT_STATUS.md`, and `docs/IMPLEMENTATION_PLAN.md` for the current architecture, but verify claims against live source before acting.
- Indexed/reference evidence guides discovery; current workspace evidence is required for project-specific conclusions.
- Workspace-rule proposals remain read-only until explicit approval and governance authorization.
