# AUDIT Mode Enforcement Finding

Date: 2026-09-29 (original), corrected 2026-09-29 at
`LBE-INTENT-AUDIT-ENFORCEMENT-RECORD-CORRECTION-001`
Revision examined: 1c54f2e

## Status

COMPOSED INTO THE PRODUCTION PATH
With one bounded residual (C0.5), recorded below.

**This record previously said the opposite. The prior text was wrong and
was corrected against source, not against a document.**

## Correction trail

- `430b0dc` framed the defect as "`validate_mode_behavior` has no
  production caller."
- `4ac446a` corrected that to the composition-path framing and cited
  `MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md` as primary.
- That was still wrong, and this entry corrects it. The correction trail
  is retained deliberately: each version asserted less evidence than the
  one before, and the repository should show that rather than hide it.

## What the current source actually shows

`lbe_guard_inspector/memory/memory_schema.sql`, `session_state`:

    permission     TEXT CHECK (permission IN
                     ('read_only','write_allowed','audit_only','elevated'))
    runtime_policy TEXT CHECK (runtime_policy IN
                     ('audit','development','strict','permissive'))

`lbe_guard_inspector/memory/models.py`, `SessionState` carries both fields
with the same vocabulary as R6B's `Permission` and `RuntimePolicy`.

`lbe_guard_inspector/runtime/governed_coding.py:791-797`:

    state = runtime.session_state
    decision = resolve_mode(ModeRequest(
        intent="fix_issue",
        permission=state.permission or "read_only",
        runtime_policy=state.runtime_policy or "audit",
        workspace_root=str(runtime.workspace_root),
    ))
    if decision.mode != "coding":
        raise ValueError("governed coding controller requires resolved coding mode")

`lbe_guard_inspector/product_entry.py:609-618` performs the same resolution
on the installed CLI path, and additionally forbids `workspace.patch` and
`process.run_registered` when the permission is `read_only` or `audit_only`.

`lbe_guard_inspector/runtime/tool_orchestration.py`:

    line 80    mode_decision: ModeDecision      (required field)
    line 94-95 raises TypeError if it is not a ModeDecision
    line 199   authorization_resolver defaults to resolve_authorization

`lbe_guard_inspector/runtime/cline_governed_birdeye.py:370` and
`lbe_guard_inspector/runtime/external_capabilities.py:316` resolve mode on
their respective paths.

Therefore the chain the C0 roadmap specifies is present:

    persisted typed policy -> resolve_mode() -> ModeDecision
      -> ToolExecutionContext.mode_decision -> resolve_authorization()
      -> GovernedToolOrchestrator

## Why the earlier records were wrong

`docs/reference/MODE_POLICY_PRODUCTION_WIRING_EVIDENCE.md` recorded
`MODE_HIT_COUNT=0` and `AUTH_HIT_COUNT=0` on 2026-08-10. Those counts
were true when taken. The typed schema fields and the production call
sites were added afterwards. The evidence document is now stale; it is
not edited here, because it is a dated historical record.

## The real residual: C0.5 fail-closed on absent typed policy

`governed_coding.py:794`, `product_entry.py:611` and `:617` all read

    permission=state.permission or "read_only"

When `state.permission` is `None`, the session silently resolves as
read-only. The C0 roadmap requires a bounded policy-state error or
escalation instead.

Two things must be stated precisely:

- This is NOT a live write hole. The default is read-only, so a session
  lacking typed policy cannot obtain write authority. The roadmap's
  prohibitions against assuming `write_allowed` from `mode=coding`,
  reinterpreting opaque policy IDs, or accepting provider-proposed
  authority are all satisfied.
- It IS a deviation. The affirmative requirement is to surface the
  absence, not to proceed quietly.

Whether to raise, escalate, or record the resolution basis is an
ownership decision about the behavior-contract owner. It is not made
here, and no runtime change is made under this intent.

## What this record does NOT claim

- It does not claim the C0.5 residual is exploitable. It is not; the
  default is the safe direction.
- It does not claim any write succeeded in audit mode. That was never
  observed and was never attempted.
- It does not delete or edit the dated evidence document.
- It does not authorize a runtime change.
