# Phase 13 Callback Vertical Slice

Updated: 2026-07-28

## Scope

This phase proves one complete deterministic, read-only Guard Inspector path for:

```text
Provided callback is not a function
```

It does not implement repair, mutation, unrestricted planning, arbitrary guard execution, or external runtime integration.

## Runtime chain

```text
CallbackVerticalSlice
-> exact configured workspace resolution
-> GuardRunner
-> EvidenceService reference and workspace evidence collection
-> registered cep_callback.cep.callback_contract execution
-> evidence scoping to guard-supporting paths
-> independent validation
-> GuardInspector verdict
-> LBE authorization envelope
-> evidence-only explanation
```

## Authority boundaries

- Indexed reference evidence may suggest patterns but cannot prove a current defect.
- Current workspace evidence supplies current facts.
- The registered deterministic callback guard detects callback-contract state.
- Independent validation is required before `PASS`.
- LBE authorization remains read-only.
- The explanation may cite only current workspace or validation records referenced by the verdict.
- The target workspace is fingerprinted before and after execution; any mutation raises an error.

## Deterministic callback classifications

- definite non-function literals such as `null`, `undefined`, booleans, numbers, strings, arrays, and objects: failed;
- inline function expressions and arrow functions: passed candidate;
- omitted callback: passed candidate;
- unresolved identifiers or expressions: blocked and therefore `INSUFFICIENT_EVIDENCE`;
- no relevant `evalScript` call: `NOT_APPLICABLE`.

## Bounded inspection

The callback guard:

- accepts only the exact target workspace supplied by the vertical slice;
- scans supported JavaScript and TypeScript extensions;
- excludes generated and dependency directories;
- limits candidate files and findings;
- re-reads each selected file before classification;
- records canonical virtual path, physical workspace metadata, hash, line, snippet, source class, provenance, and read-only state.

## Validation record

Implementation head:

```text
c1b2877869b44db0030d0258c3ec97c53b2cc4e9
```

Validated results:

```text
29 focused tests passed
160 full-suite tests passed
git diff --check passed
working tree clean
branch synchronized with origin
```

Primary tests:

- `tests/test_cep_callback_guard.py`
- `tests/test_callback_vertical_slice.py`
- `tests/test_callback_vertical_slice_end_to_end.py`
- `tests/test_guard_runner.py`

## Rollback boundary

The Phase 13 implementation begins after foundation merge commit:

```text
7f212f406331dfaf7961143eefbf45f8ceaf6a17
```

The branch contains only the callback vertical-slice implementation, related runner evidence scoping, tests, and documentation after that point.

### Safe review rollback

Before merge, abandon or delete branch:

```text
feat/guard-inspector-vertical-slice
```

No change to `main` is required because the phase is isolated on its branch.

### Safe local reset

For a clean validation worktree that should match the remote branch:

```powershell
git fetch origin
git reset --hard origin/feat/guard-inspector-vertical-slice
git clean -fd
```

Use this only in the dedicated clean validation worktree. Do not run it in a workspace containing uncommitted work.

### Revert after merge

If Phase 13 is merged and must be removed, revert the merge commit rather than manually deleting files:

```powershell
git revert -m 1 <phase-13-merge-commit>
```

If the pull request is squash-merged, revert the resulting squash commit instead:

```powershell
git revert <phase-13-squash-commit>
```

After either rollback, run:

```powershell
python -m pytest -q
git diff --check
git status --short --branch
```

## Files introduced or materially changed

- `lbe_guard_inspector/callback_vertical_slice.py`
- `lbe_guard_inspector/guard_runner.py`
- `rules/cep_callback.py`
- `tests/test_callback_vertical_slice.py`
- `tests/test_callback_vertical_slice_end_to_end.py`
- `tests/test_cep_callback_guard.py`
- `docs/CURRENT_STATUS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/PHASE_13_CALLBACK_VERTICAL_SLICE.md`

## Non-regression requirements

Any later invocation surface or runtime integration must preserve:

- fixed registered callback guard selection;
- exact target workspace resolution;
- independent reference/workspace evidence domains;
- duplicate filename safety;
- bounded live inspection;
- independent validation before `PASS`;
- all four verdicts;
- read-only authorization;
- evidence-only explanation;
- no target workspace mutation;
- deterministic semantic fingerprints for identical input and workspace state.
