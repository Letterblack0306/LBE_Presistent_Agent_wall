"""Bounded tests for persisted-model / live-catalog reconciliation."""

from __future__ import annotations

import pytest

from lbe_guard_inspector.model_catalog_reconciliation import reconcile_persisted_model


def test_persisted_model_present_in_live_catalog_is_discovered() -> None:
    v = reconcile_persisted_model("gemma-4-e4b", ["gemma-4-e4b", "llama-3.2-3b"])
    assert v.reconciliation == "live_discovered"
    assert v.effective_model == "gemma-4-e4b"
    assert v.catalog_source == "live"
    assert v.catalog_size == 2
    assert v.is_divergent is False


def test_absent_model_is_reported_and_never_substituted() -> None:
    v = reconcile_persisted_model("vanished-model", ["llama-3.2-3b", "smollm3-3b"])
    assert v.reconciliation == "absent_from_live_catalog"
    assert v.is_divergent is True
    # The critical property: no silent substitution.
    assert v.effective_model == "vanished-model"
    assert "llama-3.2-3b" not in v.effective_model
    assert "smollm3-3b" not in v.effective_model


def test_unreachable_catalog_is_unknown_not_absent() -> None:
    v = reconcile_persisted_model("gemma-4-e4b", None)
    assert v.reconciliation == "catalog_unavailable"
    assert v.catalog_source == "unavailable"
    assert v.is_divergent is False
    assert v.effective_model == "gemma-4-e4b"


def test_empty_catalog_is_observed_empty_not_unavailable() -> None:
    v = reconcile_persisted_model("gemma-4-e4b", [])
    assert v.reconciliation == "absent_from_live_catalog"
    assert v.catalog_source == "live"
    assert v.catalog_size == 0


def test_catalog_entries_are_normalized_before_comparison() -> None:
    v = reconcile_persisted_model("gemma-4-e4b", ["  gemma-4-e4b  ", "", None, "other"])
    assert v.reconciliation == "live_discovered"
    assert v.catalog_size == 2


def test_persisted_model_is_trimmed() -> None:
    v = reconcile_persisted_model("  gemma-4-e4b  ", ["gemma-4-e4b"])
    assert v.persisted_model == "gemma-4-e4b"
    assert v.reconciliation == "live_discovered"


@pytest.mark.parametrize("bad", ["", "   ", None, 7])
def test_empty_or_non_string_persisted_model_is_refused(bad: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        reconcile_persisted_model(bad, ["gemma-4-e4b"])  # type: ignore[arg-type]
