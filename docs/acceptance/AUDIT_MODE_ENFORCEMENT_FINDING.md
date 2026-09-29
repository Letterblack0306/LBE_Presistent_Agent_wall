# AUDIT Mode Enforcement Finding

Date: 2026-09-29
Revision examined: 1874461 (and origin/main for documentation claims)
Method: source trace from TUI mode selection to the execution-time guard

## Status

DECLARED, NOT ENFORCED

## Claim under examination

Upstream `README.md` states:

> "Audit and investigation routes remain read-only; coding actions are
> limited to registered capabilities and their active policy."

`lbe_guard_inspector/behavior/contracts.py:112-137` declares the same
guarantee as a typed contract (`audit_mode_constraints`), with
`forbidden_actions` including `modify`, `execute_changes`,
`create_guards`, and `bypass_guards`.

The question this record answers: is the mode decision actually composed
into the production request path, such that a write in audit mode is
refused?

## Primary evidence — this finding was already documented

The authoritative analysis is
`docs/reference/MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md` (updated
2026-08-10). It predates this record and states the gap more precisely
than a fresh trace can. Key citations:

- line 8: the typed R6B mode engine, R6C authorization resolver, and
  R6E governed tool orchestration "exist and are tested, but are not yet
  composed into the normal agent/CLI request path"
- lines 13-15: `MODE_HIT_COUNT=0`, `AUTH_HIT_COUNT=0`
- line 70: R6B "does not grant these values; it consumes them. Current
  production inspection found no normal-path consumer supplying them"
- line 76: R6C has "no external normal-path callers; it is currently
  consumed by the standalone R6E orchestrator implementation rather than
  by the gateway/CLI composition path"
- line 80: R6E **already** requires `ToolExecutionContext.mode_decision`
  and routes registered capabilities through R6C before execution

**Correction to an earlier draft of this record.** An initial revision of
this file framed the defect as "`validate_mode_behavior` has no
production caller." That observation was true of a side function but
understated the defect. Per line 80, the R6B-to-R6C-to-R6E wiring exists
*inside* R6E. The break is upstream, at the composition boundary where
authoritative runtime policy would be resolved and supplied. Adding a
call to `validate_mode_behavior` would not close the gap.

- line 19: "C0 must be broader than merely calling `resolve_mode()`. It
  must establish the smallest authoritative runtime-policy composition
  path using the owners already implemented."
- line 31: classified as "informative engineering discipline, not a hard
  runtime blocker" — which is why the gap persisted while the read-only
  guarantee shipped in the README and the Audit label shipped in the TUI.

## What a fresh source trace adds

1. `lbe_guard_inspector/runtime/mode_controller.py:105-114` resolves the
   mode correctly and fail-closed:
   - unknown permission defaults to `audit`
   - an audit intent downgrades to `audit` even when the request carries
     `write_allowed` (line 112-113)
   - the module docstring (line 4) states it cannot modify files or grant
     permissions beyond its supplied policy inputs

2. The mode decision is therefore sound, and the TUI cannot influence it.
   `app.rs::set_mode` only issues `UserRequest::SetMode` through the
   wrapper.

3. `behavior/contracts.py:112-137` declares `audit_mode_constraints`
   with `forbidden_actions` including `modify`, `execute_changes`,
   `create_guards`, and `bypass_guards`, and states "Audit mode is
   read-only."

   ```python
   def validate_mode_behavior(mode: Mode, behavior_name: str) -> bool:
       return behavior_name in MODE_BEHAVIOR_MAP[mode]
   ```

   It returns a boolean. It raises nothing and denies nothing.

4. A repository-wide search for callers of `validate_mode_behavior`
   returns exactly one call site, and it is in a test:
   `tests/test_mode_controller.py:151`. This is a side observation, not
   the defect — see the correction above.

5. That test is self-referential. It calls `resolve_mode(...)` and then
   asserts each returned `allowed_behaviors` entry passes
   `validate_mode_behavior`. Since `resolve_mode` derives those entries
   from the same `MODE_BEHAVIOR_MAP`, the assertion holds regardless of
   whether the map itself is correct. It cannot fail for the reason that
   matters.

## Consequence

Selecting AUDIT mode changes the mode decision, the projected label, the
main-body layout (`ui.rs:509,515` suppress the welcome panel and split
transcript in audit), and scroll targeting. It does not currently cause a
write to be refused, because no production composition supplies the
resolved `ModeDecision` to the authorization layer on the normal request
path. The read-only guarantee is a correct declaration with no
enforcement behind it.

This is a real gap in the most important guarantee in the product, not a
documentation defect.

## What this record does NOT claim

- It does not claim a write has been demonstrated to succeed in audit
  mode. That was not observed and was not attempted.
- It does not claim the R6E orchestrator is incorrect. Per the wiring
  evidence line 80, R6E already requires `mode_decision` and routes
  through R6C. The finding is that nothing supplies it on the normal
  path.
- It does not claim the design work is missing.
  `MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md:208-263` already specifies
  the C0 boundary, the owning files, the prohibitions, and an 11-point
  acceptance proof. That work should be implemented, not redesigned.
- It does not supersede `R6B_TYPED_MODE_POLICY_ACCEPTANCE_GATE.md` or
  `R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_GATE.md`. Those govern
  different layers.

## Required to close

Route the resolved `ModeDecision` through the normal gateway/runtime
composition boundary so that a mutation attempt in audit mode is refused
and produces a ToolReceipt recording the refusal.

Per `MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md:208-247`, the owning
surfaces are `memory/models.py`, `memory_schema.sql`, `memory/store.py`,
`session_memory_runtime.py`, and `agent_integration.py`. R6C and R6E are
to be reused, not rewritten. The named prohibitions include creating a
parallel `RuntimePolicyResolver`, creating a second permission system,
reinterpreting opaque policy IDs as typed authority, and inferring write
authority from legacy `mode=coding`.

Acceptance requires the 11-point proof at lines 251-263 of that document,
executed through the installed/normal request path. Its item 9 —
"audit/investigation cannot gain coding capabilities through model output
alone" — is the direct test of the guarantee this record examines.

Until that evidence exists, no record may describe AUDIT as enforced
read-only. The contract may be cited as a declared invariant; it may not
be cited as an enforced control.
