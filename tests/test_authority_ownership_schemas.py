from __future__ import annotations

import pytest

from lbe_guard_inspector.contracts import ContractValidationError, validate_contract


def evidence_item(ref: str, kind: str = "source") -> dict[str, str]:
    return {"ref": ref, "kind": kind}


def evidence_package() -> dict[str, object]:
    return {
        "request": {
            "operation_id": "workspace.module-state.update",
            "canonical_target": "workspace://dev/module-state/browser.loop-controller",
        },
        "registry": [evidence_item("registry:module.registry", "registry")],
        "lifecycle": [evidence_item("receipt:loaded", "runtime")],
        "canonical_state": [evidence_item("file:.lbe/module-registry.json")],
        "owner_declarations": [evidence_item("declaration:module.registry")],
        "mutation_sites": [evidence_item("source:store.py:loaded")],
        "call_paths": [evidence_item("call:launcher->registry")],
        "persistence": [evidence_item("persistence:atomic-json-replace")],
        "runtime_confirmation": [evidence_item("receipt:runtime-confirmed", "runtime")],
        "contradictions": [],
    }


def test_request_schema_accepts_one_explicit_operation() -> None:
    payload = {
        "request_id": "req-1",
        "workspace_id": "dev",
        "operation_id": "workspace.module-state.update",
        "canonical_target": "workspace://dev/module-state/browser.loop-controller",
        "ownership_sensitive": True,
        "requested_at": "2026-07-28T00:00:00+00:00",
    }
    assert validate_contract("authority_ownership_request", payload) == payload


def test_request_schema_rejects_missing_operation() -> None:
    with pytest.raises(ContractValidationError):
        validate_contract(
            "authority_ownership_request",
            {"request_id": "req-1", "workspace_id": "dev", "canonical_target": "x"},
        )


def test_evidence_package_requires_all_ten_sections() -> None:
    payload = evidence_package()
    assert validate_contract("authority_ownership_evidence_package", payload) == payload
    payload.pop("runtime_confirmation")
    with pytest.raises(ContractValidationError):
        validate_contract("authority_ownership_evidence_package", payload)


def test_evidence_items_require_references() -> None:
    payload = evidence_package()
    payload["registry"] = [{"kind": "registry"}]
    with pytest.raises(ContractValidationError):
        validate_contract("authority_ownership_evidence_package", payload)


@pytest.mark.parametrize(
    "finding",
    [
        "SINGLE_OWNER_CONFIRMED",
        "DUPLICATE_AUTHORITY",
        "UNDECLARED_AUTHORITY",
        "OWNER_CONTRACT_BROKEN",
        "STALE_OWNER_RECORD",
        "INSUFFICIENT_EVIDENCE",
        "NOT_APPLICABLE",
    ],
)
def test_result_schema_accepts_required_findings(finding: str) -> None:
    payload = {
        "result_id": "result-1",
        "operation_id": "workspace.module-state.update",
        "finding": finding,
        "summary": "Deterministic ownership finding.",
        "evidence_refs": ["registry:module.registry"],
        "pass_fail_authorized": False,
        "inspected_at": "2026-07-28T00:00:00+00:00",
    }
    assert validate_contract("authority_ownership_result", payload) == payload


def test_result_rejects_missing_evidence_refs() -> None:
    with pytest.raises(ContractValidationError):
        validate_contract(
            "authority_ownership_result",
            {
                "result_id": "result-1",
                "operation_id": "workspace.module-state.update",
                "finding": "INSUFFICIENT_EVIDENCE",
                "summary": "Missing proof.",
                "evidence_refs": [],
                "pass_fail_authorized": False,
                "inspected_at": "2026-07-28T00:00:00+00:00",
            },
        )


def test_result_cannot_authorize_pass_fail() -> None:
    with pytest.raises(ContractValidationError):
        validate_contract(
            "authority_ownership_result",
            {
                "result_id": "result-1",
                "operation_id": "workspace.module-state.update",
                "finding": "SINGLE_OWNER_CONFIRMED",
                "summary": "Owner confirmed.",
                "evidence_refs": ["registry:module.registry"],
                "pass_fail_authorized": True,
                "inspected_at": "2026-07-28T00:00:00+00:00",
            },
        )
