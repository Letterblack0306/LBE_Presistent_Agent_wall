"""Evaluation routing is descriptive and cannot supply completion evidence."""
import pytest

from lbe_guard_inspector.runtime.evaluation_discovery import discover_evaluations


def _ids(**kwargs):
    return {item.eval_id for item in discover_evaluations(**kwargs)}


def test_tui_change_requires_runtime_and_visual_evaluations():
    ids = _ids(changed_paths=["apps/lbe-terminal/src/ui.rs"])
    assert {"lbe.tui.bridge-contract.v1", "lbe.tui.rust-regression.v1", "lbe.tui.installed-interaction.v1", "lbe.tui.visual-board.v1"} <= ids


def test_bridge_change_routes_to_bridge_and_installed_acceptance():
    ids = _ids(changed_paths=[r"lbe_guard_inspector\tui_bridge.py"])
    assert ids == {"lbe.tui.bridge-contract.v1", "lbe.tui.installed-interaction.v1"}


def test_completion_change_routes_to_existing_policy_tests():
    assert "lbe.completion.policy-regression.v1" in _ids(changed_paths=["lbe_guard_inspector/runtime/completion_gate.py"])


def test_unrelated_change_does_not_invent_evaluations():
    assert discover_evaluations(changed_paths=["README.md"]) == ()


def test_task_kind_routes_without_changed_paths():
    assert "lbe.tui.installed-interaction.v1" in _ids(task_kind="TUI")


def test_rejects_absolute_or_parent_paths():
    for path in ["/tmp/file", "../other", "", "apps/../other"]:
        with pytest.raises(ValueError):
            discover_evaluations(changed_paths=[path])


def test_discovery_returns_no_execution_or_completion_verdict():
    result = discover_evaluations(changed_paths=["apps/lbe-terminal/src/main.rs"])
    assert all(recipe.success_criterion and recipe.evidence_level for recipe in result)
    assert any(recipe.manual and not recipe.commands for recipe in result)
    assert not any(hasattr(recipe, "verdict") or hasattr(recipe, "status") for recipe in result)
