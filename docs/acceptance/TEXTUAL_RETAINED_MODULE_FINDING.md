# Retained Textual Module: Fabricates Values, Must Not Be Deleted

Date: 2026-09-29
Classification: FINDING RECORDED, DISPOSITION UNDECIDED
Status: RECORDED

## The two facts, kept separate

### Fact 1 — the module fabricates evidence-shaped values

`lbe_guard_inspector/textual_tui.py`, 285 lines:

    line 88, 228   runtime = reactive("PREVIEW")
                    The surface never attaches to an authoritative
                    runtime. It renders a preview state.

    line 226       self.session_id = session_id or f"lbe-{os.urandom(4).hex()}"
                    A session identifier is invented when none is supplied.

    line 312       conv.add_message("receipt", f"ToolReceipt: lbe-{os.urandom(4).hex()}")
                    A receipt-shaped value is generated with os.urandom and
                    presented as a ToolReceipt. It is not a persisted receipt
                    and has no ToolReceipt identity behind it.

The module imports the real owners — `EvidenceService`,
`authorization_resolver`, `tool_orchestration`, `governed_coding` — at its
top, and the visible methods do not call them. The defect named in
`docs/acceptance/INSTALLED_PTY_CONPTY_AND_FINAL_PRODUCT_ACCEPTANCE_CHECKPOINT.md:24`
is therefore accurate.

### Fact 2 — the module must not be deleted

    verify_clean_install.py:68-73
      "The legacy Textual TUI is a tracked, deliberately retained
       diagnostic module. Shipping it in the installed wheel is
       permitted; being reachable from the supported installed product
       path is not. This probe therefore tests reachability through the
       supported entrypoint instead of module absence."

    tests/test_cline_launcher_contract.py:51
      test_launcher_spawns_textual_ui_in_the_governed_workspace

    .lbe/governance/implementation-gates.json:278, 281
      the module and its test are registered structure

    apps/lbe-terminal/PROVENANCE.md:47
      names `lbe_guard_inspector.textual_tui` as the module the entry
      shim runs

The clean-install verifier's entire premise is that the module EXISTS and
is UNREACHABLE. Deleting it would break the verifier, a named contract
test, a registered structure, and a provenance claim.

## Correction of an earlier recommendation

An earlier pass in this work classified this module as dead code and
proposed governed deletion. That classification was wrong. It was
derived from searching only for Python imports within
`lbe_guard_inspector/**/*.py`, which returned zero, while four
non-import dependents were not checked.

`pyproject.toml` sets `lbe = lbe_guard_inspector.product_entry:main`, and
no module imports `textual_tui`, so the *supported entrypoint* does not
reach it. That is a different claim from "unreferenced".

## The real gap

The retention invariant is "shipped, not reachable". Nothing currently
prevents it from becoming reachable later. That is the live risk, and it
is a guard question rather than a deletion question.

## Disposition — not decided here

Candidate dispositions, none chosen:

1. Retain unchanged, with the fabrication documented. Cheapest; the
   reachability probe continues to guard the invariant.
2. Quarantine: move the module so it cannot be imported without an
   explicit opt-in, preserving the verifier's ability to probe it.
3. Replace the fabricated values with real projections, making the
   module honest without removing it.

Option 3 is the only one that removes the fabricated receipt at line 312.
All three are ownership decisions for the product-surface owner. This
record authorizes none of them.

## What this record does NOT claim

- It does not claim the module is reachable from the supported product
  path. The verifier's current evidence is that it is not.
- It does not claim a fabricated receipt was ever persisted or displayed
  in an accepted product run.
- It does not claim the module should be removed.
- It does not authorize a runtime change.
