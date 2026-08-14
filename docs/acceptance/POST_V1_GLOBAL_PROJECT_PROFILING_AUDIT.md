# Post-V1 Global Project-Profiling Audit

Updated: 2026-08-12
Status: **GLOBAL DEFAULT SELECTION VERIFIED**
Repository: `Letterblack0306/LBE_Presistent_Agent_wall`

## Finding and correction

The packaged `rules/` directory contains generic, CEP, CEP-callback, and
module-registry packs. These are compatible with a global LBE inspector only
when optional packs are selected from current, target-workspace evidence.

The active `ProjectProfiler` already profiles only direct approved markers in
the selected project root: `package.json`, `pyproject.toml`,
`CSXS/manifest.xml`, and `.lbe/module-registry.json`. It selects `generic`
foundation behavior for unknown/insufficient profiles and selects optional CEP
or module-registry packs only when their exact marker exists in that target.

This audit removed the obsolete `detect_project_type` helper from
`audit_controller.py`. That unused helper searched indexed `manifest.json`
content and could classify a workspace as CEP from historical or unrelated
content if reintroduced. The supported execution path now has no such
content-search classifier.

## Invariants proved

```text
selected target workspace
-> exact current-root marker profile
-> generic foundation guards
-> optional packs only from matching target markers

unknown target or unrelated sibling/nested legacy CEP material
-> project_type = generic
-> no CEP pack execution
```

Historical indexes, repository siblings, nested legacy examples, task history,
and training material are not profile evidence. Explicitly requested packs
remain an operator-controlled action; automatic selection remains
evidence-bound.

## Validation

Focused tests cover unknown/nested CEP text and a generic target beside a CEP
sibling. The full repository suite and installed package smoke remain required
before recording a later release revision.
