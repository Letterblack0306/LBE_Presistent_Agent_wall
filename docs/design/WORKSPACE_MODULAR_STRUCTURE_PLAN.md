# Workspace Modular Structure Plan

## Status

- Planning status: design draft, not yet approved for execution
- Execution status: read-only planning document
- No code changes authorized until this plan is reviewed and approved

> **Governance Notice:** This is a planning document only. No file moves, renames, refactoring, or structural changes may be performed without explicit user approval of every step below. The workspace must remain intact until the plan is signed off.

## Purpose

Define a target modular layout where any component can be added or removed without breaking the rest. This document captures the current structure as-is, identifies the gaps, and proposes a target layout with a step-by-step migration plan.

The current workspace is **functional and stable**. This plan exists to document the path toward cleaner separation of concerns, not to fix a broken system.

## Current Structure (As-Is — No Changes Made)

```
project_root/
│
├── agent.py                              # Core runtime: Context, Governance, search, inspect
├── audit_controller.py                   # Rule registry + resolve_rule + run_rule + audit reporting
├── server.py                             # Local HTTP entry point
├── migrate_legacy_state.py               # Standalone migration utility
├── governance.json                       # Allowed-read / forbidden-glob config
├── MANIFEST.json
├── pyproject.toml
├── requirements.txt
│
├── lbe_guard_inspector/                  # Guard inspector framework (28 files)
│   ├── __init__.py                       # Exports 18 submodules
│   │
│   ├── # --- Authority Ownership (3 flat files, NOT a sub-package) ---
│   ├── authority_ownership.py            # Ownership contract + role model
│   ├── authority_ownership_inspector.py   # Deterministic read-only inspector
│   ├── authority_ownership_evidence_extractor.py  # AST-only evidence producer
│   │
│   ├── # --- Reasoning layer (4 flat files, NOT a sub-package) ---
│   ├── reasoning_config.py              # Provider config loader
│   ├── reasoning_contracts.py            # Typed reasoning contracts + protocols
│   ├── reasoning_provider.py             # OpenAI-compatible backend
│   ├── reasoning_runtime.py              # Composition root
│   │
│   ├── # --- Memory (existing sub-package, 7 files) ---
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── compaction.py
│   │   ├── context.py
│   │   ├── integration.py
│   │   ├── memory_schema.sql
│   │   ├── models.py
│   │   ├── promoter.py
│   │   └── store.py
│   │
│   ├── # --- Module Registry (existing sub-package, 4 files) ---
│   ├── module_registry/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── store.py
│   │   └── watcher.py
│   │
│   ├── # --- Vertical slices (2 files) ---
│   ├── callback_vertical_slice.py
│   ├── module_registry_vertical_slice.py

## Current Dependency Flow

All local imports flow one direction. No circular imports exist.

```
agent.py (god module)
    ↑
    ├── audit_controller.py (rule registry + execution)
    │       ↑

## Identified Gaps

### Gap 1: `authority_ownership/` is 3 flat files, not a sub-package

**Current:**
```
lbe_guard_inspector/
    authority_ownership.py
    authority_ownership_inspector.py
    authority_ownership_evidence_extractor.py
```

**Problem:** These 3 files form a cohesive self-contained module (contract + inspector + extractor) but are flat in the package namespace. They cannot be added or removed as a unit. Importing the inspector requires knowing all 3 file names.

**Fix:** Group into a sub-package `authority_ownership/` with `__init__.py` re-exporting the public API.

---

### Gap 2: `reasoning/` is 4 flat files, not a sub-package

**Current:**
```
lbe_guard_inspector/
    reasoning_config.py
    reasoning_contracts.py
    reasoning_provider.py
    reasoning_runtime.py
```

**Problem:** Same as Gap 1 — 4 cohesive files (config + contracts + provider + runtime) that form the LLM integration layer but are flat in the namespace. Cannot be removed as a unit.

**Fix:** Group into a sub-package `reasoning/` with `__init__.py` re-exporting the public API.

---

### Gap 3: `core/` foundational files are at root level

**Current:**
```
project_root/
    agent.py              ← imported by almost everything
    audit_controller.py   ← imported by guard framework + all rules
```

**Problem:** The two most depended-on files sit at the project root, mixed with `server.py` (HTTP entry point) and `migrate_legacy_state.py` (one-off utility). There is no `core/` boundary separating foundational runtime from application entry points.

**Fix:** Create `core/` package containing `agent.py` and `audit_controller.py`. Update all import paths.

---

### Gap 4: 15 flat framework files in `lbe_guard_inspector/` have no sub-grouping

**Current:** The `lbe_guard_inspector/` package has 28 files total. Only `memory/` and `module_registry/` are sub-packages. The remaining ~20 files are flat, including:
- Guard evaluation: `guard_inspector.py`, `guard_runner.py`, `guard_catalog.py`
- Evidence: `evidence_service.py`, `contracts.py`
- Runtime: `runtime_confirmation.py`, `runtime_integration_profile.py`, `runtime_slice.py`, `session_memory_runtime.py`
- Inspection: `registry_inspection.py`, `workspace_identity.py`, `project_profiler.py`, `project_snapshots.py`
- Orchestration: `request_controller.py`, `rule_gatekeeper.py`, `invocation_adapter.py`
- Vertical slices: `callback_vertical_slice.py`, `module_registry_vertical_slice.py`
- Config/server: `config.py`, `server.py`

## Proposed Target Structure

```
project_root/
│
├── core/                                 # ← Foundational: no local deps
│   ├── __init__.py
│   ├── agent.py                          # Context, Governance, search, inspect
│   ├── audit_controller.py               # Rule registry + resolve_rule + run_rule
│   └── governance.json                   # Allowed-read / forbidden-glob config
│
├── guards/                               # ← Guard framework: depends only on core/
│   ├── __init__.py
│   │
│   ├── lbe_guard_inspector/              # ← Inspector framework
│   │   ├── __init__.py
│   │   │
│   │   ├── evaluation/                   # ← Guard evaluation layer
│   │   │   ├── __init__.py
│   │   │   ├── guard_inspector.py
│   │   │   ├── guard_runner.py
│   │   │   └── guard_catalog.py
│   │   │
│   │   ├── evidence/                     # ← Evidence retrieval + contracts
│   │   │   ├── __init__.py
│   │   │   ├── contracts.py
│   │   │   └── evidence_service.py
│   │   │
│   │   ├── runtime/                      # ← Runtime layer
│   │   │   ├── __init__.py
│   │   │   ├── runtime_confirmation.py
│   │   │   ├── runtime_integration_profile.py
│   │   │   ├── runtime_slice.py
│   │   │   └── session_memory_runtime.py
│   │   │
│   │   ├── inspection/                   # ← Inspection layer
│   │   │   ├── __init__.py
│   │   │   ├── registry_inspection.py
│   │   │   ├── workspace_identity.py
│   │   │   ├── project_profiler.py
│   │   │   └── project_snapshots.py
│   │   │
│   │   ├── orchestration/                # ← Orchestration layer
│   │   │   ├── __init__.py
│   │   │   ├── request_controller.py
│   │   │   ├── rule_gatekeeper.py
│   │   │   └── invocation_adapter.py
│   │   │
│   │   ├── slices/                       # ← Vertical slices
│   │   │   ├── __init__.py
│   │   │   ├── callback_vertical_slice.py
│   │   │   └── module_registry_vertical_slice.py
│   │   │
│   │   ├── authority_ownership/          # ← Self-contained (Gap 1 fix)
│   │   │   ├── __init__.py
│   │   │   ├── contract.py               # was authority_ownership.py
│   │   │   ├── inspector.py              # was authority_ownership_inspector.py
│   │   │   └── evidence_extractor.py    # was authority_ownership_evidence_extractor.py
│   │   │
│   │   ├── reasoning/                    # ← Self-contained (Gap 2 fix)
│   │   │   ├── __init__.py
│   │   │   ├── config.py                 # was reasoning_config.py
│   │   │   ├── contracts.py              # was reasoning_contracts.py
│   │   │   ├── provider.py               # was reasoning_provider.py
│   │   │   └── runtime.py                # was reasoning_runtime.py
│   │   │
│   │   ├── memory/                       # ← Already modular, keep as-is
│   │   │   ├── __init__.py
│   │   │   ├── compaction.py
│   │   │   ├── context.py

## Target Dependency Flow

```
core/
  agent.py + audit_controller.py
      ↑
      │ (one-way: everything below depends on core, never the reverse)
      │
  guards/
      lbe_guard_inspector/          ← depends on core only
          authority_ownership/      ← self-contained, removable
          reasoning/                ← self-contained, removable
          memory/                   ← self-contained, removable
          module_registry/           ← self-contained, removable
          evaluation/               ← depends on core + evidence
          evidence/                 ← depends on core
          runtime/                  ← depends on core + memory + module_registry
          inspection/               ← depends on core
          orchestration/            ← depends on core + evaluation + evidence
          slices/                   ← depends on core + orchestration
      rules/                        ← depends on core (agent + audit_controller) only
      schemas/                     ← no code deps
      ↑
      │
  api/
      server.py                     ← depends on core + guards
      ↑
      │
  scripts/                          ← depends on core
```

## What This Achieves

| Principle | How |
|---|---|
| **Add/remove any guard module** | `authority_ownership/`, `reasoning/`, `memory/`, `module_registry/` are independent sub-packages with their own `__init__.py` — no cross-imports between them |
| **Add/remove any rule pack** | `guards/rules/` — each file is self-registering, just add/remove a `.py` file |
| **Swap the API layer** | `api/server.py` is cleanly separated from `guards/` logic |
| **Replace agent.py** | `core/agent.py` is the only dependency of everything below it |
| **Run tests independently** | Test structure mirrors the module structure |
| **No circular imports** | `core/` → `guards/` → `api/` — one-way dependency flow |

## Migration Plan (Step-by-Step — NOT YET APPROVED)

Each step is independently committable and testable. No step may be executed until this plan is approved.

### Phase 1: Group authority_ownership (Gap 1)
1. Create `lbe_guard_inspector/authority_ownership/` directory
2. Move 3 files into it with renamed names
3. Add `__init__.py` re-exporting the public API
4. Update all import paths in tests and callers
5. Run `pytest tests/test_authority_ownership_*.py -q`
6. Commit only if all tests pass

### Phase 2: Group reasoning (Gap 2)
1. Create `lbe_guard_inspector/reasoning/` directory
2. Move 4 files into it with renamed names
3. Add `__init__.py` re-exporting the public API
4. Update all import paths in tests and callers
5. Run `pytest tests/test_reasoning_*.py -q`
6. Commit only if all tests pass

### Phase 3: Create core/ package (Gap 3)
1. Create `core/` directory with `__init__.py`
2. Move `agent.py` and `audit_controller.py` into `core/`
3. Move `governance.json` into `core/`
4. Update all import paths (largest impact: 15+ files)
5. Run full test suite
6. Commit only if all tests pass

### Phase 4: Group flat framework files (Gap 4)
1. Create sub-packages: `evaluation/`, `evidence/`, `runtime/`, `inspection/`, `orchestration/`, `slices/`
2. Move flat files into their respective sub-packages
3. Add `__init__.py` for each
4. Update all import paths
5. Run full test suite
6. Commit only if all tests pass

### Phase 5: Move rules/ and schemas/ under guards/ (Gap 5)
1. Move `rules/` into `guards/rules/`
2. Move `schemas/` into `guards/schemas/`
3. Update `audit_controller.py` RULES_DIR path
4. Update all import paths
5. Run full test suite
6. Commit only if all tests pass

### Phase 6: Separate api/ and scripts/
1. Move root `server.py` into `api/`
2. Move `migrate_legacy_state.py` and `tools/` into `scripts/`
3. Update all import paths
4. Run full test suite
5. Commit only if all tests pass

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Import path breakage | Each phase updates imports + runs tests before committing |
| `agent.py` is a god module — moving it touches 15+ files | Phase 3 is the highest-risk step; do it in isolation with full test suite |
| Rule loading depends on `RULES_DIR` path in `audit_controller.py` | Phase 5 must update the path constant |
| Tests import from old paths | Update test imports in the same phase as the source move |
| Build artifacts in `build/lib/` reference old paths | `build/` is git-ignored and regenerated; no action needed |

## Acceptance Criteria for This Plan

- [ ] All 5 gaps are acknowledged and understood
- [ ] The target structure is reviewed and approved
- [ ] The migration phases are ordered correctly (dependencies first)
- [ ] Each phase has a clear test gate
- [ ] No phase is executed until individually approved
- [ ] Rollback path exists for each phase (git revert)

## Non-Goals

- This plan does not split `agent.py` into smaller modules (that is a separate effort)
- This plan does not change any logic or behavior — only file organization
- This plan does not add or remove features
- This plan does not modify governance.json rules

│   │   │   ├── integration.py
│   │   │   ├── memory_schema.sql
│   │   │   ├── models.py
│   │   │   ├── promoter.py
│   │   │   └── store.py
│   │   │
│   │   ├── module_registry/              # ← Already modular, keep as-is
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── store.py
│   │   │   └── watcher.py
│   │   │
│   │   ├── config.py                     # Package-level config
│   │   └── server.py                     # HTTP server (inside package)
│   │
│   ├── rules/                            # ← Rule packs: depends on core/ only
│   │   ├── generic.py
│   │   ├── cep.py
│   │   ├── cep_callback.py
│   │   └── module_registry.py
│   │
│   └── schemas/                          # ← JSON schemas owned by guards
│
├── api/                                  # ← HTTP layer: depends on core/ + guards/
│   ├── __init__.py
│   └── server.py                         # was root-level server.py
│
├── scripts/                              # ← Standalone utilities
│   ├── migrate_legacy_state.py
│   └── run_post_fix_acceptance.py
│
├── tests/                                # ← Mirrors the structure above
├── docs/
├── state/                                # ← Generated runtime state (git-ignored)
├── pyproject.toml
├── requirements.txt
└── MANIFEST.json
```


**Problem:** Adding or removing a feature (e.g., a new vertical slice) means dropping files into the flat namespace with no grouping.

**Fix:** Group the flat files into logical sub-packages (evaluation, evidence, runtime, inspection, orchestration, slices). This is the largest refactoring effort.

---

### Gap 5: `rules/` dependency direction not reflected in placement

**Current:** `rules/` imports `agent` and `audit_controller` (core), not `lbe_guard_inspector`. But `rules/` sits at the same level as `lbe_guard_inspector/` in the project root.

**Problem:** The placement suggests `rules/` is a sibling of the guard framework, but the dependency goes upward to core, not sideways. This is not a bug — it works — but the structure does not make the dependency direction explicit.

**Fix:** In the target structure, place `rules/` under `guards/` alongside `lbe_guard_inspector/`, with `core/` clearly above both. The one-way dependency (core → guards) becomes visible.

    │       ├── lbe_guard_inspector/ (28 files)
    │       │       ↑ imports agent + audit_controller
    │       │
    │       └── rules/ (4 files)
    │               ↑ imports agent + audit_controller
    │
    ├── server.py (HTTP entry point)
    │       ↑ imports agent + lbe_guard_inspector
    │
    └── migrate_legacy_state.py
            ↑ imports agent
```

**Key coupling facts:**
- `agent.py` is imported by 15 of 28 `lbe_guard_inspector/` files and all 4 rule files
- `audit_controller.py` is imported by 4 `lbe_guard_inspector/` files and all 4 rule files
- `lbe_guard_inspector/__init__.py` exports 18 submodules but omits `authority_ownership*`, `registry_inspection`, `runtime_slice`, `config`, `project_snapshots`

│   │
│   ├── # --- Core framework (15 flat files) ---
│   ├── config.py
│   ├── contracts.py                      # JSON schema validation
│   ├── evidence_service.py               # Evidence retrieval
│   ├── guard_catalog.py                  # Approved guard selection
│   ├── guard_inspector.py                # Evidence-policy evaluation
│   ├── guard_runner.py                   # Full vertical-slice runner
│   ├── invocation_adapter.py             # Transport-neutral invocation
│   ├── project_profiler.py               # Project profile detection
│   ├── project_snapshots.py              # Historical snapshot store
│   ├── registry_inspection.py            # Registry-first inspector
│   ├── request_controller.py             # Reasoning + guard orchestration
│   ├── rule_gatekeeper.py                # Read-only rule proposal boundary
│   ├── runtime_confirmation.py           # Bounded runtime observation
│   ├── runtime_integration_profile.py    # Configurable integration profile
│   ├── runtime_slice.py                  # Minimal runtime slice
│   ├── session_memory_runtime.py          # Session memory bridge
│   ├── server.py                         # HTTP server (inside package)
│   └── workspace_identity.py             # Workspace identity resolution
│
├── rules/                                # Deterministic rule packs (4 files)
│   ├── generic.py                        # Foundation: index_present, forbidden_roots
│   ├── cep.py                            # CEP: manifest, host, menu, debug, zip, symlink
│   ├── cep_callback.py                   # CEP callback contract
│   └── module_registry.py                # Module registry loaded-module guard
│
├── schemas/                              # JSON validation schemas (11 files)
├── tests/                                # Test suite (mirrors source structure)
├── tools/                                # Standalone utility scripts
├── docs/                                 # Documentation
├── state/                                # Generated runtime state (git-ignored)
└── build/                                # Build artifacts (git-ignored)
```

