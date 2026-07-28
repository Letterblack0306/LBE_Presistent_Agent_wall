from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .contracts import validate_contract


class OwnershipFinding(str, Enum):
    SINGLE_OWNER_CONFIRMED = "SINGLE_OWNER_CONFIRMED"
    DUPLICATE_AUTHORITY = "DUPLICATE_AUTHORITY"
    UNDECLARED_AUTHORITY = "UNDECLARED_AUTHORITY"
    OWNER_CONTRACT_BROKEN = "OWNER_CONTRACT_BROKEN"
    STALE_OWNER_RECORD = "STALE_OWNER_RECORD"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


Clock = Callable[[], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _refs(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item["ref"]) for item in items if item.get("ref")))


def _details(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(str(item.get("detail", "")) for item in items)


class AuthorityOwnershipInspector:
    """Deterministic, read-only authority ownership classification.

    The inspector consumes an already-bounded ten-section evidence package. It
    does not search, mutate, activate, persist, or execute workspace code.
    """

    def __init__(self, *, clock: Clock = _utc_now) -> None:
        self._clock = clock

    def inspect(
        self,
        *,
        request: Mapping[str, Any],
        evidence_package: Mapping[str, Any],
    ) -> dict[str, Any]:
        request_data = validate_contract("authority_ownership_request", request)
        package = validate_contract(
            "authority_ownership_evidence_package", evidence_package
        )
        package_request = package["request"]
        if package_request["operation_id"] != request_data["operation_id"]:
            raise ValueError("evidence operation_id does not match request")
        if package_request["canonical_target"] != request_data["canonical_target"]:
            raise ValueError("evidence canonical_target does not match request")

        finding, summary, refs = self._classify(request_data, package)
        result = {
            "result_id": f"ownership-{uuid.uuid4()}",
            "operation_id": request_data["operation_id"],
            "finding": finding.value,
            "summary": summary,
            "evidence_refs": list(dict.fromkeys(refs)),
            "pass_fail_authorized": False,
            "inspected_at": self._clock(),
        }
        return validate_contract("authority_ownership_result", result)

    def _classify(
        self,
        request: Mapping[str, Any],
        package: Mapping[str, Any],
    ) -> tuple[OwnershipFinding, str, tuple[str, ...]]:
        sections = {
            name: tuple(package[name])
            for name in (
                "registry",
                "lifecycle",
                "canonical_state",
                "owner_declarations",
                "mutation_sites",
                "call_paths",
                "persistence",
                "runtime_confirmation",
            )
        }
        all_refs = tuple(
            ref for name in sections for ref in _refs(sections[name])
        )
        contradictions = tuple(package["contradictions"])

        applicability = " ".join(_details(sections["owner_declarations"])).lower()
        if "not applicable" in applicability:
            return (
                OwnershipFinding.NOT_APPLICABLE,
                "The declared operation is not applicable to the resolved target.",
                _refs(sections["owner_declarations"]),
            )

        if contradictions:
            refs = all_refs or ("contradiction:unresolved",)
            return (
                OwnershipFinding.INSUFFICIENT_EVIDENCE,
                "Unresolved evidence contradictions prevent a current ownership conclusion.",
                refs,
            )

        required = (
            "registry",
            "canonical_state",
            "owner_declarations",
            "mutation_sites",
            "persistence",
        )
        if any(not sections[name] for name in required):
            refs = all_refs or ("evidence:missing-required-section",)
            return (
                OwnershipFinding.INSUFFICIENT_EVIDENCE,
                "Required current ownership evidence is incomplete.",
                refs,
            )

        declarations = sections["owner_declarations"]
        declaration_details = _details(declarations)
        owner_claims = tuple(
            detail for detail in declaration_details if "owner=" in detail.lower()
        )
        if not owner_claims:
            return (
                OwnershipFinding.UNDECLARED_AUTHORITY,
                "Mutation authority exists but no authoritative owner is declared.",
                _refs(declarations) + _refs(sections["mutation_sites"]),
            )

        normalized_owners = {
            detail.lower().split("owner=", 1)[1].split()[0].strip(";,.")
            for detail in owner_claims
        }
        if len(normalized_owners) > 1:
            return (
                OwnershipFinding.DUPLICATE_AUTHORITY,
                "More than one participant claims authoritative ownership of the operation.",
                _refs(declarations),
            )

        owner = next(iter(normalized_owners))
        mutation_details = " ".join(_details(sections["mutation_sites"])).lower()
        if "unauthorized" in mutation_details or (
            "mutator=" in mutation_details and f"mutator={owner}" not in mutation_details
        ):
            return (
                OwnershipFinding.OWNER_CONTRACT_BROKEN,
                "Observed mutation authority violates the declared owner contract.",
                _refs(declarations) + _refs(sections["mutation_sites"]),
            )

        current_details = " ".join(
            _details(sections["lifecycle"])
            + _details(sections["runtime_confirmation"])
        ).lower()
        if "stale" in current_details or "owner mismatch" in current_details:
            return (
                OwnershipFinding.STALE_OWNER_RECORD,
                "The owner declaration conflicts with current lifecycle or runtime evidence.",
                _refs(declarations)
                + _refs(sections["lifecycle"])
                + _refs(sections["runtime_confirmation"]),
            )

        indexed_only = all(
            item.get("kind") == "indexed_reference"
            for name in sections
            for item in sections[name]
        )
        if indexed_only:
            return (
                OwnershipFinding.INSUFFICIENT_EVIDENCE,
                "Indexed reference knowledge cannot prove current ownership state.",
                all_refs,
            )

        return (
            OwnershipFinding.SINGLE_OWNER_CONFIRMED,
            "One authoritative owner is confirmed by current declaration, mutation, persistence, and runtime evidence.",
            all_refs,
        )
