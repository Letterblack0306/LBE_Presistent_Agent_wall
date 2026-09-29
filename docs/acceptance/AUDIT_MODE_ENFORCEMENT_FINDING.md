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

The question this record answers: does any production path consult that
contract and refuse a write when the mode is audit?

## What the trace found

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

3. The enforcement point is `behavior/contracts.py:318-320`:

   ```python
   def validate_mode_behavior(mode: Mode, behavior_name: str) -> bool:
       return behavior_name in MODE_BEHAVIOR_MAP[mode]
   ```

   It returns a boolean. It raises nothing and denies nothing.

4. A repository-wide search for callers of `validate_mode_behavior`
   returns exactly one call site, and it is in a test:
   `tests/test_mode_controller.py:151`.

5. That test is self-referential. It calls `resolve_mode(...)` and then
   asserts each returned `allowed_behaviors` entry passes
   `validate_mode_behavior`. Since `resolve_mode` derives those entries
   from the same `MODE_BEHAVIOR_MAP`, the assertion holds regardless of
   whether the map itself is correct. It cannot fail for the reason that
   matters.

6. `docs/reference/MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md:74` already
   records this finding in the repository's own words: "current
   production inspection found no external normal-path callers; it is
   currently consumed by the standalone R6E orchestrator implementation
   rather than by the gateway/CLI composition path."

## Consequence

Selecting AUDIT mode changes the mode decision and the projected label.
It does not currently cause a write to be refused, because no execution
path consults the mode decision. The read-only guarantee is a correct
declaration with no enforcement behind it.

This is a real gap in the most important guarantee in the product, not a
documentation defect.

## What this record does NOT claim

- It does not claim a write has been demonstrated to succeed in audit
  mode. That was not observed and was not attempted.
- It does not claim the R6E orchestrator is incorrect. The finding is
  only that the mode policy is not on the normal tool path.
- It does not supersede `R6B_TYPED_MODE_POLICY_ACCEPTANCE_GATE.md` or
  `R6C_PERMISSION_AUTHORIZATION_ACCEPTANCE_GATE.md`. Those govern
  different layers.

## Required to close

Route tool execution through the mode decision, or through
`authorization_resolver`, so that a mutation attempt in audit mode is
refused and produces a ToolReceipt recording the refusal. Acceptance
requires an executed test proving a write in audit mode is denied at the
production tool path, not at the contract.

Until that evidence exists, no record may describe AUDIT as enforced
read-only. The contract may be cited as a declared invariant; it may not
be cited as an enforced control.
