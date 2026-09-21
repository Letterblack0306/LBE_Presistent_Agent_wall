# Visual Machine Acceptance Policy

Status: **ACTIVE — REQUIRED FOR VISIBLE PRODUCT ACCEPTANCE**

This is the acceptance authority for visible LBE clients. Automated result words
must never be used as a synonym for a working interface.

## Rule

`WORKING` may be recorded only when the exact target artifact is launched on the
target machine and the claimed keyboard or mouse action is visibly observed
changing the live UI.

If an interaction was not visibly exercised, it is **NOT ACCEPTED**. Untested
means unproven and the feature is not ready.

## Diagnostic evidence only

The following do not establish visible operation by themselves:

- source inspection, implementation claims, or compilation;
- unit, integration, regression, or mock-wrapper tests;
- screenshots without the live action that produced the changed state;
- exit codes, counters, labels, or automated result output;
- PTY input injection that produces no visible state transition.

## Prohibited acceptance shortcuts

- Do not use smoke, lightweight, or partial checks as working evidence.
- Do not use automated PASS/FAIL labels for visible UI readiness.
- Do not accept simulated providers, synthetic events, mocks, or source-only
  results as visible UI proof.
- Do not accept the whole interface after testing only a representative subset.

## Required evidence

For every claimed interaction, record the exact revision and artifact, machine
and terminal surface, visible state before and after, and every blocked,
untested, or failed interaction. Runtime configuration and provider/session
prerequisites must also be recorded.

Until all required interactions have direct visual machine evidence, visible
product status is **NOT READY**.
