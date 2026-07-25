"""Read-only workspace rule gatekeeper."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from ._gatekeeper_catalog import CatalogEntry, check_catalog, normalize_catalog, source_catalog
from ._gatekeeper_common import canonical_root, normalize_relative_path, read_only_mutation_report, require_text
from ._gatekeeper_packages import PackageEvidence, evidence_refs, inspect_python_packages, proposal_scope
from ._gatekeeper_proposal import build_proposal, resolve_profile_target
from .contracts import validate_contract

STATUS_ALREADY_COVERED = "ALREADY_COVERED"
STATUS_CONFLICT = "CONFLICT"
STATUS_PROPOSAL_READY = "PROPOSAL_READY"
STATUS_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
VALID_GATEKEEPER_STATUSES = frozenset({
    STATUS_ALREADY_COVERED,
    STATUS_CONFLICT,
    STATUS_PROPOSAL_READY,
    STATUS_INSUFFICIENT_EVIDENCE,
})


class RuleGatekeeper:
    """Inspect and propose workspace-profile rules without performing writes."""

    def __init__(
        self,
        *,
        catalog_provider: Callable[[Path], Sequence[CatalogEntry | Mapping[str, Any]]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._catalog_provider = catalog_provider or source_catalog
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def inspect(
        self,
        *,
        workspace_root: str | Path,
        workspace_id: str,
        trigger: str,
        rule_id: str,
        pack_id: str,
        namespace_packages: Iterable[str] = (),
        exceptions: Iterable[str] = (),
        excluded_paths: Iterable[str] = (),
        reference_evidence_refs: Iterable[str] = (),
    ) -> dict[str, Any]:
        return self._evaluate(
            mode="inspect",
            workspace_root=workspace_root,
            workspace_id=workspace_id,
            trigger=trigger,
            rule_id=rule_id,
            pack_id=pack_id,
            target_profile_path=None,
            namespace_packages=namespace_packages,
            exceptions=exceptions,
            excluded_paths=excluded_paths,
            reference_evidence_refs=reference_evidence_refs,
            severity="error",
            required_action=None,
        )

    def propose_rule(
        self,
        *,
        workspace_root: str | Path,
        workspace_id: str,
        trigger: str,
        rule_id: str,
        pack_id: str,
        target_profile_path: str | Path | None,
        namespace_packages: Iterable[str] = (),
        exceptions: Iterable[str] = (),
        excluded_paths: Iterable[str] = (),
        reference_evidence_refs: Iterable[str] = (),
        severity: str = "error",
        required_action: str | None = None,
    ) -> dict[str, Any]:
        return self._evaluate(
            mode="propose-rule",
            workspace_root=workspace_root,
            workspace_id=workspace_id,
            trigger=trigger,
            rule_id=rule_id,
            pack_id=pack_id,
            target_profile_path=target_profile_path,
            namespace_packages=namespace_packages,
            exceptions=exceptions,
            excluded_paths=excluded_paths,
            reference_evidence_refs=reference_evidence_refs,
            severity=severity,
            required_action=required_action,
        )

    def _evaluate(
        self,
        *,
        mode: str,
        workspace_root: str | Path,
        workspace_id: str,
        trigger: str,
        rule_id: str,
        pack_id: str,
        target_profile_path: str | Path | None,
        namespace_packages: Iterable[str],
        exceptions: Iterable[str],
        excluded_paths: Iterable[str],
        reference_evidence_refs: Iterable[str],
        severity: str,
        required_action: str | None,
    ) -> dict[str, Any]:
        workspace_id = require_text(workspace_id, "workspace_id")
        trigger = require_text(trigger, "trigger")
        rule_id = require_text(rule_id, "rule_id")
        pack_id = require_text(pack_id, "pack_id")
        root = canonical_root(workspace_root)
        namespace_set = {normalize_relative_path(value) for value in namespace_packages}
        exception_list = sorted({require_text(value, "exception") for value in exceptions})
        excluded_set = {normalize_relative_path(value) for value in excluded_paths}
        reference_refs = sorted({require_text(value, "reference_evidence_ref") for value in reference_evidence_refs})
        packages = inspect_python_packages(root, namespace_packages=namespace_set, excluded_paths=excluded_set)
        catalog = normalize_catalog(self._catalog_provider(root))
        coverage = check_catalog(catalog, pack_id=pack_id, rule_id=rule_id, trigger=trigger)
        base = {
            "mode": mode,
            "workspace_id": workspace_id,
            "workspace_root": str(root),
            "requested_rule_id": rule_id,
            "requested_pack_id": pack_id,
            "catalog_checked": [item.as_dict() for item in catalog],
            "package_evidence": [item.as_dict() for item in packages],
            "reference_evidence_refs": reference_refs,
            "mutation_report": read_only_mutation_report(),
        }
        if coverage["equivalent"] is not None:
            return {**base, "status": STATUS_ALREADY_COVERED, "equivalent_rule_result": coverage["equivalent"].as_dict(), "contradiction_result": None, "proposal": None}
        if coverage["conflict"] is not None:
            return {**base, "status": STATUS_CONFLICT, "equivalent_rule_result": None, "contradiction_result": coverage["conflict"].as_dict(), "proposal": None}
        if not packages:
            return {
                **base,
                "status": STATUS_INSUFFICIENT_EVIDENCE,
                "equivalent_rule_result": None,
                "contradiction_result": None,
                "missing_evidence": ["No in-scope Python package directories containing importable modules were found."],
                "proposal": None,
            }
        if mode == "inspect":
            return {
                **base,
                "status": STATUS_PROPOSAL_READY,
                "equivalent_rule_result": None,
                "contradiction_result": None,
                "scope": proposal_scope(packages),
                "evidence_refs": evidence_refs(packages, workspace_id),
                "proposal": None,
            }
        target = resolve_profile_target(root, target_profile_path)
        if target["error"] is not None:
            return {
                **base,
                "status": STATUS_INSUFFICIENT_EVIDENCE,
                "equivalent_rule_result": None,
                "contradiction_result": None,
                "missing_evidence": [target["error"]],
                "proposal": None,
            }
        proposal = build_proposal(
            root=root,
            workspace_id=workspace_id,
            trigger=trigger,
            rule_id=rule_id,
            pack_id=pack_id,
            profile_path=target["path"],
            profile_document=target["document"],
            profile_existed=bool(target["existed"]),
            packages=packages,
            exceptions=exception_list,
            namespace_packages=namespace_set,
            severity=severity,
            required_action=required_action,
            catalog=catalog,
            created_at=self._clock(),
        )
        return {
            **base,
            "status": STATUS_PROPOSAL_READY,
            "equivalent_rule_result": None,
            "contradiction_result": None,
            "proposal": validate_contract("rule_proposal", proposal),
        }


__all__ = [
    "CatalogEntry",
    "PackageEvidence",
    "RuleGatekeeper",
    "STATUS_ALREADY_COVERED",
    "STATUS_CONFLICT",
    "STATUS_INSUFFICIENT_EVIDENCE",
    "STATUS_PROPOSAL_READY",
    "VALID_GATEKEEPER_STATUSES",
]
