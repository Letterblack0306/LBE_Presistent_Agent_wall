# FIRST_RUN_LIVE_SESSION_ENTRY — Acceptance Checkpoint

Status: **PASS**

Date: 2026-08-25

## Scope

Product-level `lbe start` composition over the existing persistent LBE session, provider, provider-turn, and Textual interface owners.

## Canonical implementation

Validated implementation head:

`dbefbc0884cb78be5327100d3e9e648bea5a6e52`

The product entry point is `lbe_guard_inspector.product_entry:main`; non-`start` commands continue to delegate to the pre-existing CLI owner.

## Decisive local validation

```text
LoopTool command hash = 7C462B292C3978B957701FAB5F8AC719673EFA18207AAB8633C704411C78C736
MACHINE_AND_PACKAGE_BINDING = PASS
focused regression = 63 passed in 64.98s
full regression = 740 passed in 210.17s
FIRST_RUN_LIVE_SESSION_ENTRY = PASS
HEAD = dbefbc0884cb78be5327100d3e9e648bea5a6e52
branch = main...origin/main
local exception = ?? lbe-tui/
```

## Proven

- `lbe` package entry resolves through the product-level start wrapper.
- A new start path creates one persisted session through the existing session owner.
- An existing start path restores the same persisted session identity.
- Provider/model pairing is validated through the existing provider registry.
- Provider configuration mismatch fails closed.
- No silent provider/model fallback is introduced.
- Live entry delegates to the existing `_tui` / provider-turn / persistent-session owners.
- No second session, provider, terminal, execution, receipt, or completion authority is introduced.
- Full repository regression remains green.
- `lbe-tui/` remained reference-only, untracked, and untouched.

## Boundary

This checkpoint proves the first-run/live-session entry composition only. It does not prove installed MCP/plugin/service discovery or concrete external-capability configuration. Those remain successor product work behind the already-proven governed external-capability registration contract.
