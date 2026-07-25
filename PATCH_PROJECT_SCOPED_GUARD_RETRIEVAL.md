# Exact Patch Specification — Project-Scoped Guard Retrieval

## Authority

This file is the complete implementation contract for branch:

`agent/project-scoped-guard-retrieval`

Required base commit:

`f5970b225cfb06680f7ee15a0e7d6c40843c7b81`

Do not infer additional work from chat history, README text, local untracked files, or adjacent plans.

## Stop conditions

Before editing, run:

```powershell
git fetch origin
git checkout agent/project-scoped-guard-retrieval
git reset --hard origin/agent/project-scoped-guard-retrieval
git status --short
git rev-parse HEAD
```

The working tree must be clean.

Do not continue if HEAD is not this patch-spec commit or one of its descendants on the named branch.

After one implementation commit is pushed, stop all repository modifications. Report newly discovered defects only.

## Scope

Fix three verified defects:

1. A configured root such as `dev` is being used as project identity.
2. Structural guards receive broad natural-language retrieval instead of exact project evidence.
3. Validation checks query words inside files instead of validating each rule claim.

Preserve the existing complete SQLite index. Do not run a full re-index.

## Files allowed to change

Only these implementation files may change:

```text
lbe_guard_inspector/workspace_identity.py
lbe_guard_inspector/evidence_service.py
lbe_guard_inspector/guard_runner.py
rules/cep.py
tests/test_workspace_identity.py
tests/test_evidence_service.py
tests/test_guard_runner.py
acceptance/post_fix_acceptance_plan.json
VALIDATION_CURRENT.md
```

This patch-spec file must not be edited by the implementation agent.

Do not add or stage:

```text
lbe_guard_inspector/rule_gatekeeper.py
tests/test_rule_gatekeeper.py
state/*
_run*.py
```

Do not implement proposal installation, approval transitions, memory promotion, reasoning-model integration, autonomous repair, or unrelated cleanup.

## 1. Canonical project identity

Create `lbe_guard_inspector/workspace_identity.py` with these public functions:

```python
from __future__ import annotations

import hashlib
import re
from pathlib import Path


def canonical_workspace_root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(
            f"Workspace root does not exist or is not a directory: {root}"
        )
    return root


def project_workspace_id(
    workspace_root: str | Path,
    requested_id: str | None = None,
) -> str:
    root = canonical_workspace_root(workspace_root)
    canonical = str(root).replace("\\", "/").rstrip("/").casefold()
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    label_source = requested_id or root.name or "workspace"
    label = re.sub(
        r"[^a-zA-Z0-9_.-]+",
        "-",
        label_source.strip(),
    ).strip("-.").lower()

    if not label:
        label = "workspace"

    return f"{label}-{fingerprint}"
```

Required behavior:

- canonical project root is authoritative;
- caller-supplied `workspace_id` is only a readable prefix;
- sibling projects under one configured root receive different IDs;
- clones at different canonical paths receive different IDs;
- configured root name alone is never the project identity;
- repeated calls for the same canonical root return the same ID.

## 2. Explicit retrieval modes

Extend `EvidenceService.build_evidence_package()` with:

```python
retrieval_mode: str = "diagnostic"
path_patterns: list[str] | None = None
content_search: bool = True
```

Allowed values:

```text
diagnostic
guard
investigation
```

Reject all other values with `ValueError`.

### Diagnostic mode

Keep broad indexed semantic search behavior.

### Guard mode

When `workspace_root` is supplied:

- derive canonical project root;
- derive authoritative project workspace ID;
- do not run broad indexed semantic search;
- set `indexed_reference_evidence` to `[]` unless a separate explicit reference-search request exists;
- inspect only the canonical target project;
- use exact `path_patterns` where supplied;
- do not combine query with reason, planning text, rule descriptions, or commentary.

### Investigation mode

Reference search may remain semantic, but current-workspace inspection must stay bounded to the canonical project root.

Every current-workspace evidence item must include:

```json
{
  "configured_root": "dev",
  "canonical_workspace_root": "G:/Developments/...",
  "project_workspace_id": "...",
  "retrieval_mode": "guard",
  "path_patterns": ["CSXS/manifest.xml"],
  "content_search": false
}
```

Store the resolved project workspace ID in both the evidence item and evidence package.

## 3. Exact-path current workspace retrieval

Update `_search_current_workspace()` to accept `path_patterns`, `content_search`, retrieval mode, and the resolved project workspace ID.

When `path_patterns` is non-empty:

1. Reject absolute patterns.
2. Reject patterns containing a `..` path component.
3. Resolve each candidate relative to the canonical workspace root.
4. Verify the resolved candidate remains inside that root.
5. Reject symlinks that resolve outside the root.
6. Inspect only the exact matching files.
7. Do not call `root.rglob("*")`.

For `CSXS/manifest.xml`, inspect only:

`<workspace_root>/CSXS/manifest.xml`

When `content_search` is `False`, candidate selection must not depend on query terms.

Do not deduplicate current-workspace files solely by content hash. Distinct current paths with identical content must remain distinct evidence records.

## 4. Guard evidence requirements

Add this exact mapping in `guard_runner.py`:

```python
_GUARD_EVIDENCE_REQUIREMENTS = {
    "cep.manifest_exists": {
        "path_patterns": ["CSXS/manifest.xml"],
        "extensions": [".xml"],
        "content_search": False,
    },
    "cep.host_version": {
        "path_patterns": ["CSXS/manifest.xml"],
        "extensions": [".xml"],
        "content_search": False,
    },
    "cep.menubar_extension": {
        "path_patterns": ["CSXS/manifest.xml"],
        "extensions": [".xml"],
        "content_search": False,
    },
    "cep.symlink_free": {
        "path_patterns": [],
        "extensions": [],
        "content_search": False,
    },
}
```

When `workspace_root` is supplied:

- canonicalize it;
- derive the project workspace ID;
- write the resolved ID into the task;
- call `EvidenceService` using `retrieval_mode="guard"`;
- pass exact rule requirements;
- pass canonical `workspace_root` and resolved `workspace_id` to the rule runner.

Rule parameters must include:

```python
{
    "roots": ev_roots or [],
    "workspace_root": str(canonical_root),
    "workspace_id": resolved_workspace_id,
    "project_type": project_type,
    "inventory": {},
}
```

`reason` must never affect retrieval input or candidate selection.

## 5. Rule-specific validation

Remove query-term validation from `GuardRunner._run_validation()`.

Dispatch validation by `rule_id`.

### `cep.manifest_exists`

- inspect exactly `<workspace_root>/CSXS/manifest.xml`;
- require a regular readable file;
- compute SHA-256;
- emit validation evidence only when the file exists and is readable;
- do not require the word `manifest` in content.

### `cep.host_version`

Parse XML using `xml.etree.ElementTree`.

Validation succeeds only when the manifest contains at least one host declaration with:

- non-empty host name;
- non-empty version metadata such as `Version`, `MinVersion`, `MaxVersion`, or a valid version-range attribute.

Substring matching is not sufficient.

### `cep.menubar_extension`

Parse XML.

Validation succeeds only when an extension registration has:

- extension ID;
- dispatch entry;
- a UI type representing menu or panel registration;
- non-empty menu label where the manifest structure requires it.

Natural-language term matching is forbidden.

### `cep.symlink_free`

Walk only the canonical project subtree.

- exclude generated/vendor directories already recognized by repository policy;
- detect symlinks before following them;
- never follow directory symlinks;
- emit successful validation only after the complete readable bounded subtree contains no symlinks;
- if a directory cannot be inspected, do not emit successful validation evidence.

### `generic.index_present`

- do not emit current workspace validation evidence;
- keep the rule index-only;
- it must remain unable to produce `PASS` or `FAIL`.

Each validation evidence item must include:

```text
workspace_id
rule_id
canonical inspected path
SHA-256 when a file is inspected
read_only: true
validation_strategy
```

## 6. CEP rule execution scope

Modify only these rules in `rules/cep.py`:

```text
cep.manifest_exists
cep.host_version
cep.menubar_extension
cep.symlink_free
```

When `params["workspace_root"]` exists:

- inspect that canonical project directly;
- do not search the entire configured root;
- do not select a sibling project's manifest;
- include canonical absolute path and project-relative path in evidence.

Legacy configured-root behavior may remain only when `workspace_root` is absent.

Do not modify unrelated CEP rules.

## 7. Required tests

Add deterministic tests for all of the following:

1. Sibling projects under one configured root derive different IDs.
2. The same canonical root derives the same ID repeatedly.
3. Different clone roots derive different IDs even with identical basenames.
4. Absolute path patterns are rejected.
5. `..` traversal is rejected.
6. Symlink escape outside the project is rejected.
7. Guard mode does not call broad indexed semantic search.
8. Diagnostic mode still performs broad reference search.
9. Reason text cannot change executed query or candidates.
10. `workspace_root` limits current evidence to the target project.
11. Distinct current files with identical hashes remain separate evidence records.
12. Sibling-project manifests cannot create contradictions.
13. Same project, same relative path, different hash creates a contradiction.
14. `cep.manifest_exists` validates without the literal word `manifest` in XML content.
15. `cep.host_version` passes only with parsed host/version metadata.
16. `cep.menubar_extension` passes only with valid parsed registration.
17. `cep.symlink_free` passes only after complete bounded inspection.
18. `generic.index_present` remains `INSUFFICIENT_EVIDENCE`.
19. Existing verdict behavior remains intact.
20. Normal guard execution does not rebuild or rewrite the SQLite index.

Do not weaken existing tests to make the patch pass.

## 8. Acceptance plan

Update `acceptance/post_fix_acceptance_plan.json` so the target project identity is derived from:

`G:\Developments\00_CEP_Developer\cep-dev-workspace`

Do not hardcode `workspace_id` as `dev`.

Do not add gatekeeper acceptance cases in this patch.

## 9. Validation commands

Run exactly:

```powershell
python -m pytest -q
python tools\run_post_fix_acceptance.py
git diff --check
git status --short
```

Acceptance requirements:

- no full-root timeout;
- no sibling-project contradiction;
- supported CEP rules include rule-specific validation references;
- `generic.index_present` remains non-authoritative;
- no full index rebuild;
- no `state/` files staged;
- no local gatekeeper files staged.

If acceptance fails because of a newly discovered defect outside the allowed files or scope, report it and stop. Do not widen the patch.

## 10. Staging, commit, push, and stop

Use path-explicit staging only:

```powershell
git add -- `
  lbe_guard_inspector/workspace_identity.py `
  lbe_guard_inspector/evidence_service.py `
  lbe_guard_inspector/guard_runner.py `
  rules/cep.py `
  tests/test_workspace_identity.py `
  tests/test_evidence_service.py `
  tests/test_guard_runner.py `
  acceptance/post_fix_acceptance_plan.json `
  VALIDATION_CURRENT.md
```

Never use:

```text
git add .
git add -A
git add -u
```

Commit message:

`fix: scope guards to project identity and rule validation`

Push only:

`origin/agent/project-scoped-guard-retrieval`

Do not merge into `main`.

Do not create a pull request.

After the push, stop all modifications.

## Final report contract

Report exactly:

1. starting commit;
2. implementation commit hash;
3. exact changed files;
4. project identity derivation;
5. retrieval-mode behavior;
6. validation strategy per rule;
7. pytest result;
8. acceptance exit code;
9. rule-by-rule verdict;
10. contradiction counts;
11. confirmation that no full re-index occurred;
12. confirmation that no `state/` or gatekeeper files were staged;
13. push result;
14. newly discovered defects, without repairing them.
