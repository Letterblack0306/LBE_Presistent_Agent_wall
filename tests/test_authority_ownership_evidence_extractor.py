from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from lbe_guard_inspector.authority_ownership_evidence_extractor import AuthorityOwnershipEvidenceExtractor, PASS_FAIL_AUTHORIZED
from lbe_guard_inspector.authority_ownership_inspector import AuthorityOwnershipInspector


def _write(root: Path, name: str, text: str | bytes):
    path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text if isinstance(text, bytes) else text.encode())


def _spec(root: Path, **changes):
    spec = {"operation": "write", "canonical_state_or_side_effect": {"kind": "database", "identifier": "sessions"}, "workspace_root": str(root),
            "candidate_files": ["app.py"], "owner_declarations": [{"component_id": "app", "source_path": "app.py", "symbol": "save", "declared_role": "authoritative_owner"}],
            "mutation_call_names": ["commit"], "execution_call_names": ["run"], "persistence_call_names": [], "allowed_caller_selectors": ["api"],
            "relationship_declarations": [], "runtime_confirmation_required": False, "exclusions": []}
    spec.update(changes); return spec


def test_one_file_owner_mutation_and_inspector_compatibility(tmp_path):
    _write(tmp_path, "app.py", "def save():\n    db.commit()\n")
    result = AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path))
    assert result["owner_declarations"][0]["symbol"] == "save"
    assert result["mutation_sites"][0]["verified"] is True
    inspection = AuthorityOwnershipInspector().inspect(
        request=result["inspector_request"],
        evidence_package=result["evidence_package"],
    )
    assert inspection["pass_fail_authorized"] is False


def test_multi_file_async_class_edges_hashes_and_ordering(tmp_path):
    _write(tmp_path, "b.py", "class Store:\n    async def save(self):\n        db.commit()\n\ndef persist():\n    db.commit()\n")
    _write(tmp_path, "a.py", "def api():\n    persist()\n")
    spec = _spec(tmp_path, candidate_files=["b.py", "a.py", "a.py"], owner_declarations=[{"component_id": "store", "source_path": "b.py", "symbol": "Store.save", "declared_role": "authoritative_owner"}], allowed_caller_selectors=[])
    first = AuthorityOwnershipEvidenceExtractor().extract(spec); second = AuthorityOwnershipEvidenceExtractor().extract(spec)
    assert first == second and [f["path"] for f in first["inspected_files"]] == ["a.py", "b.py"]
    assert any(s["symbol"] == "Store.save" and s["kind"] == "async_function" for s in first["symbols"])
    assert first["call_edges"] and first["caller_paths"]


@pytest.mark.parametrize("candidate", ["../outside.py", "{outside}"])
def test_path_escape_and_missing_rejected(tmp_path, candidate):
    outside = tmp_path.parent / "outside.py"; _write(tmp_path, "app.py", "pass\n")
    value = str(outside) if candidate == "{outside}" else candidate
    with pytest.raises(ValueError): AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path, candidate_files=[value]))


def test_missing_file_rejected(tmp_path):
    _write(tmp_path, "app.py", "pass\n")
    with pytest.raises(ValueError): AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path, candidate_files=["missing.py"]))


def test_invalid_utf8_syntax_dynamic_and_static_effects(tmp_path):
    _write(tmp_path, "bad.py", b"\xff")
    bad = AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path, candidate_files=["bad.py"], owner_declarations=[]))
    assert bad["inspected_files"][0]["utf8_parse_status"] == "invalid"
    _write(tmp_path, "app.py", "def save():\n    getattr(handler, name)()\n    open('x', 'w')\n    cur.execute('INSERT INTO x VALUES (1)')\n    subprocess.run(['x'])\n")
    result = AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path))
    assert result["unresolved_dynamic_evidence"] and {x["storage_kind"] for x in result["persistence_paths"]} == {"file", "sqlite"}
    assert result["execution_sites"]
    _write(tmp_path, "syntax.py", "def nope(:\n")
    assert AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path, candidate_files=["syntax.py"], owner_declarations=[]))["inspected_files"][0]["syntax_parse_status"] == "invalid"


def test_relationships_exclusions_reference_input_immutability_and_read_only(tmp_path):
    _write(tmp_path, "app.py", "def save():\n    db.commit()\n")
    spec = _spec(tmp_path, relationship_declarations=[{"component_id": "observer", "role": "observer", "owner_component_id": "app", "allowed_actions": [], "prohibited_actions": ["write"], "source_path": "app.py"}, {"component_id": "projection", "role": "projection", "owner_component_id": "app", "allowed_actions": [], "prohibited_actions": ["write"], "source_path": "app.py"}, {"component_id": "delegate", "role": "delegate", "owner_component_id": "app", "allowed_actions": ["write"], "prohibited_actions": [], "source_path": "app.py"}])
    original = deepcopy(spec); before = (tmp_path / "app.py").read_bytes()
    result = AuthorityOwnershipEvidenceExtractor().extract(spec)
    assert spec == original and (tmp_path / "app.py").read_bytes() == before and result["read_only"] is True
    assert all(item["verified"] is False for item in result["relationship_candidates"])
    assert PASS_FAIL_AUTHORIZED is False
    with pytest.raises(ValueError): AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path, reference_only=True))
    excluded = AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path, exclusions=[result["mutation_sites"][0]["callsite_ref"]]))
    assert not excluded["mutation_sites"]


def test_bounded_patterns_assignments_and_required_specification(tmp_path):
    _write(tmp_path, "src/app.py", "def save():\n    self.state = 1\n    value = 2\n    db.commit()\n")
    result = AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path, candidate_files=[], include_patterns=["src/*.py"], owner_declarations=[{"component_id": "app", "source_path": "src/app.py", "symbol": "save", "declared_role": "authoritative_owner"}]))
    kinds = {item["kind"] for item in result["symbols"]}
    assert {"assignment_target", "attribute_assignment_target"} <= kinds
    with pytest.raises(ValueError): AuthorityOwnershipEvidenceExtractor().extract({"workspace_root": str(tmp_path)})
    with pytest.raises(ValueError): AuthorityOwnershipEvidenceExtractor().extract(_spec(tmp_path, candidate_files=[], include_patterns=["**/*"]))
