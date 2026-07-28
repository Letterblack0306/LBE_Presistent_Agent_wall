from __future__ import annotations

from copy import deepcopy

import pytest

from lbe_guard_inspector.authority_ownership_inspector import (
    AuthorityOwnershipInspector,
    OwnershipFinding,
)


def request() -> dict[str, object]:
    return {
        "request_id": "request-1",
        "workspace_id": "dev",
        "operation_id": "workspace.module-state.update",
        "canonical_target": "workspace://dev/module-state/browser.loop-controller",
        "ownership_sensitive": True,
        "requested_at": "2026-07-28T00:00:00+00:00",
    }


def item(ref: str, kind: str, detail: str) -> dict[str, str]:
    return {"ref": ref, "kind": kind, "detail": detail}


def package() -> dict[str, object]:
    return {
        "request": {
            "operation_id": "workspace.module-state.update",
            "canonical_target": "workspace://dev/module-state/browser.loop-controller",
        },
        "registry": [item("registry:module.registry", "current_registry", "module.registry loaded")],
        "lifecycle": [item("receipt:owner", "runtime_receipt", "owner active")],
        "canonical_state": [item("state:module", "current_source", ".lbe/module-registry.json")],
        "owner_declarations": [item("owner:module.registry", "current_declaration", "owner=module.registry")],
        "mutation_sites": [item("mutation:registry", "current_source", "mutator=module.registry capability=module.state.write")],
        "call_paths": [item("call:launcher-registry", "current_source", "app.launcher -> module.registry")],
        "persistence": [item("persistence:registry", "current_source", "atomic-json-replace durable")],
        "runtime_confirmation": [item("runtime:owner", "runtime_receipt", "owner confirmed")],
        "contradictions": [],
    }


def inspector() -> AuthorityOwnershipInspector:
    return AuthorityOwnershipInspector(clock=lambda: "2026-07-28T01:00:00+00:00")


def finding(evidence: dict[str, object]) -> OwnershipFinding:
    result = inspector().inspect(request=request(), evidence_package=evidence)
    assert result["pass_fail_authorized"] is False
    return OwnershipFinding(result["finding"])


def test_single_owner_confirmed() -> None:
    result = inspector().inspect(request=request(), evidence_package=package())

    assert result["finding"] == "SINGLE_OWNER_CONFIRMED"
    assert result["pass_fail_authorized"] is False
    assert result["evidence_refs"]
    assert result["inspected_at"] == "2026-07-28T01:00:00+00:00"


def test_duplicate_authority() -> None:
    evidence = package()
    evidence["owner_declarations"].append(
        item("owner:module.watcher", "current_declaration", "owner=module.watcher")
    )

    assert finding(evidence) is OwnershipFinding.DUPLICATE_AUTHORITY


def test_undeclared_authority() -> None:
    evidence = package()
    evidence["owner_declarations"] = [
        item("declaration:none", "current_declaration", "delegate=module.watcher")
    ]

    assert finding(evidence) is OwnershipFinding.UNDECLARED_AUTHORITY


def test_owner_contract_broken() -> None:
    evidence = package()
    evidence["mutation_sites"] = [
        item("mutation:watcher", "current_source", "mutator=module.watcher unauthorized")
    ]

    assert finding(evidence) is OwnershipFinding.OWNER_CONTRACT_BROKEN


def test_stale_owner_record() -> None:
    evidence = package()
    evidence["runtime_confirmation"] = [
        item("runtime:mismatch", "runtime_receipt", "owner mismatch stale")
    ]

    assert finding(evidence) is OwnershipFinding.STALE_OWNER_RECORD


def test_unresolved_contradiction_is_insufficient() -> None:
    evidence = package()
    evidence["contradictions"] = ["source and runtime disagree"]

    assert finding(evidence) is OwnershipFinding.INSUFFICIENT_EVIDENCE


def test_indexed_reference_knowledge_cannot_prove_current_defect() -> None:
    evidence = package()
    for section in (
        "registry",
        "lifecycle",
        "canonical_state",
        "owner_declarations",
        "mutation_sites",
        "call_paths",
        "persistence",
        "runtime_confirmation",
    ):
        for evidence_item in evidence[section]:
            evidence_item["kind"] = "indexed_reference"

    assert finding(evidence) is OwnershipFinding.INSUFFICIENT_EVIDENCE


def test_not_applicable() -> None:
    evidence = package()
    evidence["owner_declarations"] = [
        item("applicability:none", "current_declaration", "not applicable to target")
    ]

    assert finding(evidence) is OwnershipFinding.NOT_APPLICABLE


def test_duplicate_store_is_not_duplicate_authority() -> None:
    evidence = package()
    evidence["canonical_state"].append(
        item("projection:ui", "current_projection", "read-only duplicate projection")
    )
    evidence["persistence"].append(
        item("cache:runtime", "current_projection", "read-only cache")
    )

    assert finding(evidence) is OwnershipFinding.SINGLE_OWNER_CONFIRMED


def test_mismatched_operation_is_rejected() -> None:
    evidence = package()
    evidence["request"]["operation_id"] = "different.operation"

    with pytest.raises(ValueError, match="operation_id"):
        inspector().inspect(request=request(), evidence_package=evidence)


def test_inspection_does_not_mutate_inputs() -> None:
    req = request()
    evidence = package()
    req_before = deepcopy(req)
    evidence_before = deepcopy(evidence)

    inspector().inspect(request=req, evidence_package=evidence)

    assert req == req_before
    assert evidence == evidence_before
