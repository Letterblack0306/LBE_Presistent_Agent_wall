# Letterblack Governed Workspace

Before any mutation, read:

1. `docs/GOVERNANCE_RULES.md`
2. `.governance/workspace-policy.json`
3. `.governance/task-scope.json`
4. `docs/BLOCKER_GUIDE.md`

## Before any work starts: find prior results

Do this before planning or testing. It is a lookup, not an execution authority.

1. Read `.lbe/governance/implementation-gates.json` and `docs/LBE_CAPABILITY_INVENTORY.md`: they are the index of what is proven, partial and open. Add recent agent actions and receipts (BirdEye `workspace_command_history`, `state/executions`) and `memory_recall` for why something was decided.
2. State in your first message what is proven, what is open, and where the last agent stopped.
3. Plan only from that. Do not redo proven work unless the files that own it changed since the proof: `git diff <proof commit>..HEAD -- <owner files>` is empty and `git status` shows them clean means reuse the result and cite it.
4. Before any test, cite its prior result or say none exists. If you re-run it, compare the new result with the old one.

"Not evergreen, reverify at HEAD" in status documents means this comparison, not a blind re-run.

## Mandatory behavior

- Do not treat documentation as authorization.
- Mutations require an active locked task scope whose file/action boundaries cover the operation.
- No external signature, operator key, detached signature, or signing ceremony is required.
- If the gate blocks, follow `docs/BLOCKER_GUIDE.md`.
- Before direct filesystem/shell/Git mutations, use the governed controller or `node scripts/action-preflight.mjs <action> [target]` where integrated.
- Do not claim enforcement for any mutation route that bypasses governance.

## Blocked state

If no active locked scope exists, report the exact missing scope/action. Once the authorized scope and required validation pass, normal commit/push may proceed when those actions are allowed.

## Standing development authorization

Follow the standing authorization section of docs/GOVERNANCE_RULES.md: the active scope permits normal enhancements, bug fixes and removal of unwanted code; a blocked acceptance slice or one unavailable provider does not halt unrelated authorized work. Keep genuine workspace/effect boundaries and test real effects.

## Evaluation discovery before completion claims

For audit, repair, and code changes, inspect requirements and existing tests; query `lbe_guard_inspector.runtime.evaluation_discovery.discover_evaluations(changed_paths=..., task_kind=...)` for applicable checks. This read-only selector returns candidates, not execution authority or completion evidence. Execute tests through the authorized project path and distinguish unit, bridge, installed interaction, and visual proof. A passing unit test cannot prove the installed TUI works; absent live evidence is UNVERIFIED or BLOCKED, never PROVEN. The existing persisted task completion contract, producer policy, and gate remain authoritative.

## Terminal client status

The Rust terminal client in `apps/lbe-terminal` (Lockstep Boundary Engine terminal client, rebuilt 2026-10-18 to `LBE_TUI_SCREEN_SPEC.md`; status and held-back items in `docs/LBE_TERMINAL_UI.md`) is the UI redesign candidate. It is not the canonical or installed client. The Python terminal (`lbe_guard_inspector/terminal_ui.py`, opened by bare `lbe`) remains canonical until the product owner explicitly supersedes it, and it is also the runtime library the bridge reuses: fix bugs there, but add no new Python UI screens. The Rust client is presentation and operator control only, and talks to the runtime through `lbe_guard_inspector/tui_bridge.py`. Do not add a client screen without a bridge message that supplies its data; do not patch UI files with ad-hoc scripts.
