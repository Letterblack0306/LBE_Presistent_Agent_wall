from __future__ import annotations

from agent import Context
from rules.generic import rule_generic_index_present


def test_generic_inventory_guard_uses_selected_workspace_inventory_only():
    result = rule_generic_index_present(
        Context(config={}, governance={}, roots=()),
        {"inventory": {"files_considered": 2, "roots": ["target"]}},
    )

    assert result.status == "passed"
    assert result.evidence == {
        "files_considered": 2,
        "roots": ["target"],
        "evidence_source": "current_workspace_inventory",
    }


def test_generic_inventory_guard_fails_without_selected_workspace_files():
    result = rule_generic_index_present(
        Context(config={}, governance={}, roots=()),
        {"inventory": {"files_considered": 0, "roots": ["target"]}},
    )

    assert result.status == "failed"
    assert result.evidence["roots"] == ["target"]
