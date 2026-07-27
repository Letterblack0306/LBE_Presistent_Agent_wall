from __future__ import annotations

from copy import deepcopy

import pytest

from lbe_guard_inspector.authority_ownership_inspector import (
    AuthorityOwnershipInspector,
    DUPLICATE_AUTHORITY,
    INSUFFICIENT_EVIDENCE,
    NOT_APPLICABLE,
    OWNER_CONTRACT_BROKEN,
    SINGLE_OWNER_CONFIRMED,
    STALE_OWNER_RECORD,
    UNDECLARED_AUTHORITY,
)


def _declaration(component: str = "runtime", role: str = "authoritative_owner", **extra):
    return {"component_id": component, "source_path": f"src/{component}.py", "symbol": f"{component}_write", "declared_role": role, "declaration_source": "contract", "evidence_ref": f"workspace:{component}:declaration", **extra}


def _site(component: str = "runtime", operation: str = "write", **extra):
    return {"component_id": component, "source_path": f"src/{component}.py", "symbol": f"{component}_write", "operation": operation, "target_identifier": "sessions", "callsite_ref": f"workspace:{component}:callsite", "source_hash": f"hash-{component}", "verified": True, **extra}


def _package(**changes):
    package = {
        "workspace_id": "workspace-a", "authoritative_operation": "session persistence",
        "canonical_target": {"kind": "database", "identifier": "sessions", "physical_location": "state/sessions.db", "runtime_identity": None},
        "owner_declarations": [_declaration()], "mutation_sites": [_site()],
        "call_paths": [{"entrypoint": "api.save", "caller_chain": ["api.save", "runtime_write"], "terminal_mutation_site": "workspace:runtime:callsite", "authority_source": "runtime", "evidence_refs": ["workspace:runtime:callsite"]}],
        "persistence_paths": [{"component_id": "runtime", "storage_kind": "sqlite", "storage_location": "state/sessions.db", "write_symbol": "runtime_write", "read_symbol": "read", "canonical": True, "evidence_refs": ["workspace:runtime:persistence"]}],
        "relationships": [], "runtime_observations": [], "validation": {"checks_run": ["unit"], "checks_passed": ["unit"], "checks_failed": [], "unavailable_checks": [], "evidence_refs": ["validation:unit"]},
    }
    package.update(changes)
    return package


def _inspect(package):
    return AuthorityOwnershipInspector().inspect(package)


def test_complete_single_owner_case():
    result = _inspect(_package())
    assert result["finding_type"] == SINGLE_OWNER_CONFIRMED
    assert result["declared_owner"]["component_id"] == "runtime"


def test_duplicate_verified_writers():
    result = _inspect(_package(owner_declarations=[_declaration("runtime"), _declaration("adapter")], mutation_sites=[_site("runtime"), _site("adapter")], call_paths=[
        {"entrypoint": "a", "caller_chain": ["a"], "terminal_mutation_site": "workspace:runtime:callsite", "authority_source": "runtime"},
        {"entrypoint": "b", "caller_chain": ["b"], "terminal_mutation_site": "workspace:adapter:callsite", "authority_source": "adapter"},
    ]))
    assert result["finding_type"] == DUPLICATE_AUTHORITY


def test_undeclared_verified_writer():
    result = _inspect(_package(mutation_sites=[_site("runtime"), _site("rogue")], call_paths=[
        {"entrypoint": "a", "caller_chain": ["a"], "terminal_mutation_site": "workspace:runtime:callsite", "authority_source": "runtime"},
        {"entrypoint": "b", "caller_chain": ["b"], "terminal_mutation_site": "workspace:rogue:callsite", "authority_source": None},
    ]))
    assert result["finding_type"] == UNDECLARED_AUTHORITY


@pytest.mark.parametrize("role", ["observer", "projection"])
def test_non_owner_attempting_canonical_write(role):
    result = _inspect(_package(owner_declarations=[_declaration("runtime"), _declaration(role, role)], mutation_sites=[_site("runtime"), _site(role)], call_paths=[
        {"entrypoint": "a", "caller_chain": ["a"], "terminal_mutation_site": "workspace:runtime:callsite", "authority_source": "runtime"},
        {"entrypoint": "b", "caller_chain": ["b"], "terminal_mutation_site": f"workspace:{role}:callsite", "authority_source": "runtime"},
    ]))
    assert result["finding_type"] == OWNER_CONTRACT_BROKEN


def test_delegate_operating_within_declared_boundary():
    result = _inspect(_package(owner_declarations=[_declaration(), _declaration("delegate", "delegate")], mutation_sites=[_site(), _site("delegate")], relationships=[{"component_id": "delegate", "role": "delegate", "owner_component_id": "runtime", "allowed_actions": ["write"], "prohibited_actions": ["approve"]}], call_paths=[
        {"entrypoint": "a", "caller_chain": ["a"], "terminal_mutation_site": "workspace:runtime:callsite", "authority_source": "runtime"},
        {"entrypoint": "b", "caller_chain": ["b"], "terminal_mutation_site": "workspace:delegate:callsite", "authority_source": "runtime"},
    ]))
    assert result["finding_type"] == SINGLE_OWNER_CONFIRMED


def test_delegate_exceeding_declared_boundary():
    result = _inspect(_package(owner_declarations=[_declaration(), _declaration("delegate", "delegate")], mutation_sites=[_site(), _site("delegate", "delete")], relationships=[{"component_id": "delegate", "role": "delegate", "owner_component_id": "runtime", "allowed_actions": ["write"], "prohibited_actions": ["delete"]}], call_paths=[
        {"entrypoint": "a", "caller_chain": ["a"], "terminal_mutation_site": "workspace:runtime:callsite", "authority_source": "runtime"},
        {"entrypoint": "b", "caller_chain": ["b"], "terminal_mutation_site": "workspace:delegate:callsite", "authority_source": "runtime"},
    ]))
    assert result["finding_type"] == OWNER_CONTRACT_BROKEN


def test_stale_declared_symbol_or_hash():
    result = _inspect(_package(owner_declarations=[_declaration(source_hash="old")], current_source_hashes={"src/runtime.py": "new"}, current_symbols={"src/runtime.py": ["runtime_write"]}))
    assert result["finding_type"] == STALE_OWNER_RECORD


@pytest.mark.parametrize("field, expected", [("mutation_sites", "mutation_site_coverage"), ("call_paths", "caller_coverage"), ("persistence_paths", "persistence_evidence")])
def test_required_coverage_missing(field, expected):
    result = _inspect(_package(**{field: []}))
    assert result["finding_type"] == INSUFFICIENT_EVIDENCE
    assert expected in result["missing_evidence"]


def test_required_runtime_evidence_absent():
    result = _inspect(_package(requires_runtime_confirmation=True))
    assert result["finding_type"] == INSUFFICIENT_EVIDENCE
    assert "runtime_confirmation" in result["missing_evidence"]


def test_contradictory_runtime_and_source_evidence():
    result = _inspect(_package(contradictions=[{"claim_a": "source:one write", "claim_b": "runtime:two writes", "evidence_refs": ["workspace:source", "runtime:two"]}]))
    assert result["finding_type"] == INSUFFICIENT_EVIDENCE


def test_unsupported_operation():
    result = _inspect(_package(supported=False))
    assert result["finding_type"] == NOT_APPLICABLE
    assert result["applicable"] is False


def test_reference_only_evidence_is_blocked():
    result = _inspect(_package(reference_only=True))
    assert result["finding_type"] == INSUFFICIENT_EVIDENCE
    assert "current_workspace_evidence" in result["missing_evidence"]


def test_deterministic_ordering_and_stable_output():
    package = _package(owner_declarations=[_declaration("zeta"), _declaration("alpha")], mutation_sites=[_site("zeta"), _site("alpha")], call_paths=[
        {"entrypoint": "z", "caller_chain": ["z"], "terminal_mutation_site": "workspace:zeta:callsite", "authority_source": "zeta"},
        {"entrypoint": "a", "caller_chain": ["a"], "terminal_mutation_site": "workspace:alpha:callsite", "authority_source": "alpha"},
    ])
    first, second = _inspect(package), _inspect(package)
    assert first == second
    assert [item["component_id"] for item in first["mutation_sites"]] == ["alpha", "zeta"]


def test_input_immutability_and_pass_fail_always_false():
    package = _package()
    original = deepcopy(package)
    result = _inspect(package)
    assert package == original
    assert result["pass_fail_authorized"] is False
