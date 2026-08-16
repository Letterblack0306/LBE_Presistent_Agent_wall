# Deterministic Workspace Discovery

## Purpose

Prevent the reasoning layer from locking onto one apparent implementation before it has seen the complete structural map of the resolved target workspace.

This phase is mandatory before reasoning or guard selection.

## Runtime position

```text
target_workspace_resolution
→ deterministic_workspace_discovery
→ reference_knowledge_retrieval
→ reasoning / guard selection
→ targeted_workspace_inspection
→ deterministic_guard
→ validation
→ verdict
```

Discovery does not replace targeted inspection. It provides structural coverage first; targeted inspection then fetches exact evidence for selected candidates.

## Required behavior

For one resolved target workspace, the system must build a bounded structural inventory that identifies:

- entry points;
- declared modules;
- unregistered modules;
- parallel implementations;
- handler registrations;
- state owners;
- persistence paths;
- runtime adapters;
- validation surfaces;
- unresolved structural candidates;
- excluded areas and the reason for exclusion.

The reasoning layer must receive this inventory before selecting a failure domain or guard.

The reasoning layer must not lock onto one implementation while known parallel candidates remain unexamined.

## Discovery sources

Use deterministic sources in this order:

1. active workspace profile and policy;
2. module registry and lifecycle receipts, when present;
3. manifests, package metadata, and configured entry points;
4. bounded source inspection of imports, exports, registrations, mutation sites, persistence sites, and handler declarations;
5. unresolved candidates requiring later targeted inspection.

The Module Registry is preferred but is not the sole authority. Source inspection must supplement it when declarations are missing, stale, contradictory, or incomplete.

## Inventory contract

The discovery phase returns a compact `workspace_structure_inventory`:

```json
{
  "workspace_id": "stable-project-id",
  "workspace_root": "canonical/project/root",
  "inventory_version": 1,
  "project_types": [],
  "entry_points": [],
  "modules": [],
  "parallel_implementations": [],
  "handlers": [],
  "state_owners": [],
  "persistence_paths": [],
  "runtime_adapters": [],
  "validation_surfaces": [],
  "unresolved_structures": [],
  "excluded_areas": []
}
```

Each discovered item must preserve:

- exact workspace-relative path;
- current hash when applicable;
- source classification;
- language or file type;
- declared or inferred structural role;
- discovered relationships;
- discovery source;
- confidence;
- whether it came from registry declaration, runtime receipt, manifest metadata, or source inspection.

## Boundaries

Discovery is a structural coverage scan, not an unrestricted semantic scan.

It may inspect:

- the bounded file tree;
- manifests and package metadata;
- module registries;
- import and export relationships;
- entry points;
- handler registrations;
- state-write and persistence candidates;
- duplicate and parallel implementations;
- approved validation entry points.

It must not:

- inject all file contents into model context;
- treat reference-corpus records as target-workspace structure;
- execute workspace code;
- infer final guard truth;
- authorize writes;
- reopen protected checkpoints without a defined trigger;
- scan outside the canonical target root.

## Two-level inspection model

### Level 1 — mandatory structural inventory

Fast, deterministic, metadata-focused, and run before reasoning.

### Level 2 — targeted deep inspection

Reads exact source sections only for relevant modules, parallel candidates, and evidence required by selected guards.

## Failure behavior

Return `INSUFFICIENT_EVIDENCE` for guard selection when:

- workspace resolution is ambiguous;
- structural discovery cannot establish bounded coverage;
- parallel candidates are known but cannot be distinguished;
- registry and source evidence contradict without resolution;
- exclusions prevent the inventory from covering a required structural area.

Missing coverage must never be silently treated as absence.

## Acceptance requirements

1. Parallel implementations are surfaced before guard selection.
2. Registered and unregistered modules remain distinguishable.
3. Duplicate basenames are never collapsed without path and hash evidence.
4. Registry declarations and source-discovered structures retain separate provenance.
5. The inventory remains project-scoped and cannot admit sibling-project files.
6. Reasoning receives the compact inventory, not unrestricted source contents.
7. Targeted inspection occurs only after the inventory identifies relevant candidates.
8. Known unresolved candidates prevent unsupported `PASS` or `FAIL` claims.
9. Existing deterministic guard verdict ownership remains unchanged.
10. Workspace discovery is read-only and does not modify the existing broad reference index.
