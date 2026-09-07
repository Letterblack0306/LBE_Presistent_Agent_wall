# Terminal Workspace Foundation Gate

Status: **SUPERSEDED — RETAINED HISTORICAL ACCEPTANCE RECORD**

This gate is preserved as evidence for the earlier terminal-workspace slice. It is not the active
machine-gate plan and does not authorize implementation. The active plan is declared by
`.lbe/governance/implementation-gates.json`.

## Scope

Build the first usable, visible LBE terminal-workspace foundation over existing persisted runtime
owners. The product must expose LBE identity and discoverable, functional controls; it must not
be a generic transcript, copied external CLI, or decorative mock.

## Existing owners to reuse

- `lbe_guard_inspector/textual_tui.py` — terminal client;
- `lbe_guard_inspector/cli.py::_tui` — session launch and provider wiring;
- `SessionOperationalHistory` and `terminal_projection.py` — persisted event truth;
- `PersistentTurnControl` — start/steer/interrupt/cancel controls.

## Required first-slice outcomes

1. LBE mark/title and truthful workspace/provider status appear in top-level chrome.
2. A visible command palette/help entry point invokes real supported session/control actions.
3. Session, provider, evidence, and control state are discoverable and never fabricated.
4. Every visible control has a tested handler outcome; unsupported features state why.
5. Ordinary policy-covered work remains automatic; no approval queue is introduced.

## Proof required before PASS

- focused Textual/client tests;
- persisted event/receipt projection tests;
- manual local TUI launch from current source;
- `git diff --check`.

## Explicit exclusions

- no second session, provider, execution, authorization, or completion owner;
- no external CLI code or product naming;
- no publication, tag, or release dispatch.
