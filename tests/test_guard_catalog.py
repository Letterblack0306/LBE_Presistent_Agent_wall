from lbe_guard_inspector.guard_catalog import (
    FOUNDATION_GUARD_IDS,
    resolve_foundation_guards,
    select_guard_catalog,
)


def test_catalog_selects_only_approved_cep_guards_from_profile_signals():
    catalog = select_guard_catalog({
        "outcome": "profiled",
        "guard_packs": ["generic", "cep"],
        "signals": [{"path": "CSXS/manifest.xml", "sha256": "abc"}],
    })

    assert catalog["foundation_guard_ids"] == list(FOUNDATION_GUARD_IDS)
    assert catalog["optional_guard_ids"][:3] == [
        "cep.manifest_exists", "cep.host_version", "cep.menubar_extension",
    ]
    assert catalog["evidence_references"] == [{"path": "CSXS/manifest.xml", "sha256": "abc"}]


def test_catalog_does_not_guess_optional_guards_without_a_profile():
    catalog = select_guard_catalog({"outcome": "insufficient_evidence"})

    assert catalog["selection_outcome"] == "insufficient_evidence"
    assert catalog["optional_guard_ids"] == []


def test_foundation_catalog_records_npm_metadata_without_inventing_a_guard():
    resolved = resolve_foundation_guards({"signals": [{"path": "package.json", "sha256": "abc"}]})

    assert resolved["npm"]["applicable"] is True
    assert resolved["npm"]["guard_ids"] == []
    assert resolved["lbe"]["guard_ids"] == []
