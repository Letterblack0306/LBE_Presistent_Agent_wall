"""Deterministic, read-only authority ownership evidence analysis.

This module deliberately does not inspect a workspace, query the reference
index, execute a guard, or authorize a compliance verdict.  Callers supply a
single, already live-inspected evidence package for one operation.  The module
normalizes that package into a stable finding and never mutates the input.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, TypedDict


INSPECTOR_ID = "architecture.authority_ownership"
INSPECTOR_VERSION = "1.0.0"
PASS_FAIL_AUTHORIZED = False

SINGLE_OWNER_CONFIRMED = "SINGLE_OWNER_CONFIRMED"
DUPLICATE_AUTHORITY = "DUPLICATE_AUTHORITY"
UNDECLARED_AUTHORITY = "UNDECLARED_AUTHORITY"
OWNER_CONTRACT_BROKEN = "OWNER_CONTRACT_BROKEN"
STALE_OWNER_RECORD = "STALE_OWNER_RECORD"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
NOT_APPLICABLE = "NOT_APPLICABLE"

FINDING_TYPES = frozenset(
    {
        SINGLE_OWNER_CONFIRMED,
        DUPLICATE_AUTHORITY,
        UNDECLARED_AUTHORITY,
        OWNER_CONTRACT_BROKEN,
        STALE_OWNER_RECORD,
        INSUFFICIENT_EVIDENCE,
        NOT_APPLICABLE,
    }
)

_MUTATING_OPERATIONS = frozenset(
    {"create", "write", "update", "delete", "execute", "transition", "approve", "persist"}
)
_NON_OWNER_ROLES = frozenset({"delegate", "observer", "subscriber", "projection"})


class AuthorityOwnershipEvidence(TypedDict, total=False):
    """Typed input boundary for one explicitly supplied workspace evidence set."""

    workspace_id: str
    authoritative_operation: str
    canonical_target: dict[str, Any]
    owner_declarations: list[dict[str, Any]]
    mutation_sites: list[dict[str, Any]]
    call_paths: list[dict[str, Any]]
    persistence_paths: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    runtime_observations: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    validation: dict[str, Any]
    current_source_hashes: dict[str, str]
    current_symbols: dict[str, list[str]]
    requires_runtime_confirmation: bool
    reference_only: bool


@dataclass(frozen=True)
class _Assessment:
    declarations: list[dict[str, Any]]
    sites: list[dict[str, Any]]
    call_paths: list[dict[str, Any]]
    persistence: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    runtime: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    missing: list[str]
    refs: list[str]
    stale_declarations: list[dict[str, Any]]


class AuthorityOwnershipInspector:
    """Analyze one supplied authority evidence package without workspace access.

    The input follows the sections in
    ``AUTHORITY_OWNERSHIP_INSPECTOR_CONTRACT.md``.  Two optional current-source
    ledgers make stale-record checks deterministic: ``current_source_hashes``
    maps source paths to hashes and ``current_symbols`` maps source paths to a
    list of live symbols.  Set ``requires_runtime_confirmation`` when runtime
    observation is essential.  ``reference_only: true`` (or an evidence source
    classified as ``reference`` without any current source) is always blocked.
    """

    def inspect(self, evidence: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(evidence, Mapping):
            raise ValueError("authority ownership evidence must be a mapping")
        package = deepcopy(dict(evidence))
        operation = package.get("authoritative_operation")
        if package.get("supported") is False or package.get("project_scope_supported") is False:
            return self._result(package, operation, NOT_APPLICABLE, _Assessment([], [], [], [], [], [], [], [], [], []))
        if not isinstance(operation, str) or not operation.strip():
            return self._result(package, operation, NOT_APPLICABLE, _Assessment([], [], [], [], [], [], [], [], [], []))

        assessment = self._assess(package)
        if self._is_reference_only(package, assessment.refs):
            assessment.missing.append("current_workspace_evidence")
        if assessment.missing or assessment.contradictions:
            return self._result(package, operation, INSUFFICIENT_EVIDENCE, assessment)

        declared_by_component = {item["component_id"]: item for item in assessment.declarations}
        canonical_sites = assessment.sites
        broken = [
            site for site in canonical_sites
            if declared_by_component.get(site["component_id"], {}).get("declared_role")
            in {"observer", "subscriber", "projection"}
        ]
        if broken:
            assessment.contradictions.extend(
                self._contract_break(site, declared_by_component[site["component_id"]]) for site in broken
            )
            return self._result(package, operation, OWNER_CONTRACT_BROKEN, assessment)

        if assessment.stale_declarations:
            return self._result(package, operation, STALE_OWNER_RECORD, assessment)

        undeclared = [site for site in canonical_sites if site["component_id"] not in declared_by_component]
        if undeclared:
            return self._result(package, operation, UNDECLARED_AUTHORITY, assessment)

        independent = []
        for site in canonical_sites:
            declaration = declared_by_component[site["component_id"]]
            if declaration["declared_role"] == "authoritative_owner":
                independent.append(site)
            elif declaration["declared_role"] == "delegate" and not self._delegate_is_bounded(
                site, declaration, assessment.relationships, assessment.call_paths
            ):
                assessment.contradictions.append(
                    {"claim_a": f"delegate:{site['component_id']}", "claim_b": "mutation outside declared boundary", "evidence_refs": [site["callsite_ref"]]}
                )
                return self._result(package, operation, OWNER_CONTRACT_BROKEN, assessment)

        independent_components = sorted({site["component_id"] for site in independent})
        if len(independent_components) > 1:
            return self._result(package, operation, DUPLICATE_AUTHORITY, assessment)
        if len(independent_components) != 1:
            assessment.missing.append("effective_authoritative_owner")
            return self._result(package, operation, INSUFFICIENT_EVIDENCE, assessment)
        return self._result(package, operation, SINGLE_OWNER_CONFIRMED, assessment)

    def _assess(self, package: dict[str, Any]) -> _Assessment:
        target = package.get("canonical_target")
        declarations = self._records(package, "owner_declarations")
        sites = self._records(package, "mutation_sites")
        paths = self._records(package, "call_paths")
        persistence = self._records(package, "persistence_paths")
        relationships = self._records(package, "relationships")
        runtime = self._records(package, "runtime_observations")
        contradictions = self._records(package, "contradictions")
        missing = self._string_list(package.get("missing_evidence"))

        if not isinstance(package.get("workspace_id"), str) or not package["workspace_id"].strip():
            missing.append("workspace_id")
        if not isinstance(target, Mapping) or not target.get("identifier") or not target.get("kind"):
            missing.append("canonical_target")
            target_id = None
        else:
            target_id = str(target["identifier"])
        if not declarations:
            missing.append("owner_declarations")
        if not sites:
            missing.append("mutation_site_coverage")
        if not paths:
            missing.append("caller_coverage")
        if not persistence:
            missing.append("persistence_evidence")
        validation = package.get("validation")
        if not isinstance(validation, Mapping) or not isinstance(validation.get("checks_run"), list):
            missing.append("validation")
        if package.get("requires_runtime_confirmation") and not runtime:
            missing.append("runtime_confirmation")

        normalized_declarations = []
        for item in declarations:
            if self._has_fields(item, "component_id", "source_path", "symbol", "declared_role", "evidence_ref"):
                normalized_declarations.append(item)
            else:
                missing.append("complete_owner_declaration")
        normalized_sites = []
        for item in sites:
            if not self._has_fields(item, "component_id", "source_path", "symbol", "operation", "target_identifier", "callsite_ref", "source_hash"):
                missing.append("complete_mutation_site")
                continue
            if item["operation"] not in _MUTATING_OPERATIONS or (target_id and item["target_identifier"] != target_id):
                continue
            if item.get("verified", True) is not True:
                missing.append("verified_mutation_site")
                continue
            normalized_sites.append(item)
        if target_id and not normalized_sites:
            missing.append("canonical_mutation_site")
        for declaration in normalized_declarations:
            if declaration["declared_role"] != "authoritative_owner":
                continue
            has_hash = any(
                site["source_path"] == declaration["source_path"]
                and site["symbol"] == declaration["symbol"]
                and bool(site.get("source_hash"))
                for site in normalized_sites
            ) or bool(declaration.get("source_hash"))
            if not has_hash:
                missing.append("owner_source_hash")
        for item in persistence:
            if not self._has_fields(item, "component_id", "storage_kind", "storage_location", "write_symbol", "canonical"):
                missing.append("complete_persistence_path")
        for item in paths:
            if not self._has_fields(item, "entrypoint", "caller_chain", "terminal_mutation_site"):
                missing.append("complete_call_path")
        for item in relationships:
            if not self._has_fields(item, "component_id", "role", "owner_component_id", "allowed_actions", "prohibited_actions"):
                missing.append("complete_relationship")

        stale = self._stale_declarations(package, normalized_declarations)
        refs = self._refs(normalized_declarations, normalized_sites, paths, persistence, relationships, runtime, contradictions, validation)
        return _Assessment(
            self._sort(normalized_declarations, "component_id"), self._sort(normalized_sites, "component_id"),
            self._sort(paths, "entrypoint"), self._sort(persistence, "storage_location"),
            self._sort(relationships, "component_id"), self._sort(runtime, "observation_id"),
            self._sort(contradictions, "claim_a"), sorted(set(missing)), sorted(set(refs)), stale,
        )

    def _stale_declarations(self, package: dict[str, Any], declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        hashes = package.get("current_source_hashes") if isinstance(package.get("current_source_hashes"), Mapping) else {}
        symbols = package.get("current_symbols") if isinstance(package.get("current_symbols"), Mapping) else {}
        stale = []
        for item in declarations:
            if item["declared_role"] != "authoritative_owner":
                continue
            path = item["source_path"]
            declaration_hash = item.get("source_hash")
            hash_stale = declaration_hash is not None and path in hashes and hashes[path] != declaration_hash
            symbol_stale = path in symbols and item["symbol"] not in symbols[path]
            if hash_stale or symbol_stale:
                stale.append(item)
        return self._sort(stale, "component_id")

    @staticmethod
    def _delegate_is_bounded(site: dict[str, Any], declaration: dict[str, Any], relationships: list[dict[str, Any]], paths: list[dict[str, Any]]) -> bool:
        boundary = next((r for r in relationships if r.get("component_id") == site["component_id"] and r.get("role") == "delegate"), None)
        if not boundary or site["operation"] not in boundary.get("allowed_actions", []):
            return False
        return any(
            path.get("terminal_mutation_site") == site.get("callsite_ref")
            and path.get("authority_source") == boundary.get("owner_component_id")
            for path in paths
        )

    @staticmethod
    def _contract_break(site: dict[str, Any], declaration: dict[str, Any]) -> dict[str, Any]:
        return {"claim_a": f"{declaration['declared_role']}:{site['component_id']}", "claim_b": "canonical mutation", "evidence_refs": [site["callsite_ref"]]}

    def _result(self, package: dict[str, Any], operation: Any, finding: str, assessment: _Assessment) -> dict[str, Any]:
        owner = next((d for d in assessment.declarations if d.get("declared_role") == "authoritative_owner"), None)
        authorities = self._sort(
            [{"component_id": s["component_id"], "symbol": s["symbol"], "operation": s["operation"], "source_path": s["source_path"]} for s in assessment.sites],
            "component_id",
        )
        return {
            "inspector_id": INSPECTOR_ID, "inspector_version": INSPECTOR_VERSION,
            "workspace_id": package.get("workspace_id"), "operation": operation,
            "authoritative_operation": operation, "finding_type": finding,
            "finding": finding, "applicable": finding != NOT_APPLICABLE,
            "evidence_complete": not assessment.missing and not assessment.contradictions and finding != INSUFFICIENT_EVIDENCE,
            "declared_owner": owner, "authoritative_owner": owner,
            "verified_authorities": authorities, "participants": assessment.declarations,
            "mutation_sites": assessment.sites, "caller_paths": assessment.call_paths,
            "call_paths": assessment.call_paths, "persistence_paths": assessment.persistence,
            "relationship_findings": assessment.relationships, "runtime_observations": assessment.runtime,
            "contradictions": assessment.contradictions, "missing_evidence": sorted(set(assessment.missing)),
            "evidence_references": assessment.refs, "evidence_refs": assessment.refs,
            "validation": deepcopy(package.get("validation", {})), "pass_fail_authorized": PASS_FAIL_AUTHORIZED,
        }

    @staticmethod
    def _records(package: dict[str, Any], key: str) -> list[dict[str, Any]]:
        value = package.get(key, [])
        return [dict(item) for item in value] if isinstance(value, list) and all(isinstance(item, Mapping) for item in value) else []

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        return [str(item) for item in value] if isinstance(value, list) else []

    @staticmethod
    def _has_fields(item: Mapping[str, Any], *fields: str) -> bool:
        return all(item.get(field) not in (None, "") for field in fields)

    @staticmethod
    def _sort(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        return sorted((deepcopy(item) for item in items), key=lambda item: (str(item.get(key, "")), str(item)))

    @staticmethod
    def _refs(*groups: Any) -> list[str]:
        refs: set[str] = set()
        for group in groups:
            if isinstance(group, Mapping):
                group = [group]
            if not isinstance(group, list):
                continue
            for item in group:
                if not isinstance(item, Mapping):
                    continue
                for key in ("evidence_ref", "callsite_ref"):
                    if isinstance(item.get(key), str): refs.add(item[key])
                for ref in item.get("evidence_refs", []):
                    if isinstance(ref, str): refs.add(ref)
        return sorted(refs)

    @staticmethod
    def _is_reference_only(package: dict[str, Any], refs: list[str]) -> bool:
        if package.get("reference_only") is True:
            return True
        sources = package.get("evidence_sources")
        if not isinstance(sources, list) or not sources:
            return False
        by_ref = {source.get("ref"): source for source in sources if isinstance(source, Mapping)}
        relevant = [by_ref[ref] for ref in refs if ref in by_ref]
        return bool(relevant) and not any(source.get("classification") == "current_workspace" for source in relevant)
