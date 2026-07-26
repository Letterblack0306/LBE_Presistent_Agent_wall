"""Read-only workspace rule gatekeeper."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from ._gatekeeper_catalog import CatalogEntry, check_catalog, normalize_catalog, source_catalog
from ._gatekeeper_common import canonical_root, normalize_relative_path, read_only_mutation_report, require_text
from ._gatekeeper_packages import PackageEvidence, evidence_refs, inspect_python_packages, proposal_scope, sha256_file
from ._gatekeeper_proposal import (
    build_proposal,
    catalog_hash,
    profile_rule_payload,
    resolve_profile_target,
)
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
        package_roots: Iterable[str],
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
            package_roots=package_roots,
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
        package_roots: Iterable[str],
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
            package_roots=package_roots,
            namespace_packages=namespace_packages,
            exceptions=exceptions,
            excluded_paths=excluded_paths,
            reference_evidence_refs=reference_evidence_refs,
            severity=severity,
            required_action=required_action,
        )

    def revalidate_proposal(
        self,
        *,
        workspace_root: str | Path,
        proposal: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Revalidate proposal evidence without mutating the workspace.

        Revalidation fails closed when the target profile, catalog, workspace
        root, or any evidence-bound file has changed since proposal generation.
        """
        root = canonical_root(workspace_root)
        validated = validate_contract("rule_proposal", proposal)
        provenance = validated["provenance"]
        stale: list[str] = []

        try:
            proposed_root = Path(provenance["workspace_root"]).expanduser().resolve(strict=True)
        except (OSError, RuntimeError):
            proposed_root = None
        if proposed_root != root:
            stale.append("The proposal workspace root no longer resolves to the requested canonical workspace root.")

        target = resolve_profile_target(root, validated["target_profile_path"])
        if target["error"] is not None:
            stale.append(target["error"])
        else:
            if target["profile_hash"] != provenance["profile_snapshot_hash"]:
                stale.append("The target profile content changed after proposal generation.")
            relative = target["path"].relative_to(root).as_posix()
            expected_profile_ref = (
                f"workspace:{validated['workspace_id']}:{relative}#sha256:{target['profile_hash']}"
            )
            if expected_profile_ref != provenance["profile_evidence_ref"]:
                stale.append("The target profile evidence reference no longer matches the current profile snapshot.")

        catalog = normalize_catalog(self._catalog_provider(root))
        if catalog_hash(catalog) != provenance["catalog_snapshot_hash"]:
            stale.append("The registered rule catalog changed after proposal generation.")

        for ref in validated["evidence_refs"]:
            error = _validate_workspace_evidence_ref(
                root=root,
                workspace_id=validated["workspace_id"],
                ref=ref,
            )
            if error is not None:
                stale.append(error)

        base = {
            "mode": "revalidate-proposal",
            "workspace_id": validated["workspace_id"],
            "workspace_root": str(root),
            "proposal_id": validated["proposal_id"],
            "mutation_report": read_only_mutation_report(),
        }
        if stale:
            reasons = sorted(set(stale))
            return {
                **base,
                "status": STATUS_INSUFFICIENT_EVIDENCE,
                "missing_evidence": reasons,
                "stale_evidence": reasons,
                "proposal": None,
            }
        return {
            **base,
            "status": STATUS_PROPOSAL_READY,
            "stale_evidence": [],
            "proposal": validated,
        }

    def apply_proposal(self, proposal: Mapping[str, Any]) -> None:
        """Fail closed: proposal application is outside this read-only slice."""
        validate_contract("rule_proposal", proposal)
        raise PermissionError(
            "RuleGatekeeper is read-only: automatic application is disabled and an approved mutation boundary is not implemented."
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
        package_roots: Iterable[str],
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
        package_root_set = {normalize_relative_path(value) for value in package_roots}
        namespace_set = {normalize_relative_path(value) for value in namespace_packages}
        exception_list = sorted({require_text(value, "exception") for value in exceptions})
        excluded_set = {normalize_relative_path(value) for value in excluded_paths}
        reference_refs = sorted({require_text(value, "reference_evidence_ref") for value in reference_evidence_refs})
        packages = inspect_python_packages(
            root,
            package_roots=package_root_set,
            namespace_packages=namespace_set,
            excluded_paths=excluded_set,
        )
        catalog = normalize_catalog(self._catalog_provider(root))
        coverage = check_catalog(catalog, pack_id=pack_id, rule_id=rule_id, trigger=trigger)
        base = {
            "mode": mode,
            "workspace_id": workspace_id,
            "workspace_root": str(root),
            "requested_rule_id": rule_id,
            "requested_pack_id": pack_id,
            "package_roots": sorted(package_root_set),
            "catalog_checked": [item.as_dict() for item in catalog],
            "package_evidence": [item.as_dict() for item in packages],
            "reference_evidence_refs": reference_refs,
            "mutation_report": read_only_mutation_report(),
        }
        if coverage["equivalent"] is not None:
            return {
                **base,
                "status": STATUS_ALREADY_COVERED,
                "equivalent_rule_result": coverage["equivalent"].as_dict(),
                "contradiction_result": None,
                "proposal": None,
            }
        if coverage["conflict"] is not None:
            return {
                **base,
                "status": STATUS_CONFLICT,
                "equivalent_rule_result": None,
                "contradiction_result": coverage["conflict"].as_dict(),
                "proposal": None,
            }

        target: dict[str, Any] | None = None
        if mode == "propose-rule":
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
            existing = profile_rule_payload(target["document"], rule_id)
            if existing is not None:
                return {
                    **base,
                    "status": STATUS_ALREADY_COVERED,
                    "equivalent_rule_result": {
                        "pack_id": str(existing.get("pack") or pack_id),
                        "rule_id": rule_id,
                        "trigger": str(existing.get("trigger") or ""),
                        "rationale": str(existing.get("rationale") or ""),
                        "source_path": target["path"].relative_to(root).as_posix(),
                    },
                    "contradiction_result": None,
                    "proposal": None,
                }

        if not packages:
            return {
                **base,
                "status": STATUS_INSUFFICIENT_EVIDENCE,
                "equivalent_rule_result": None,
                "contradiction_result": None,
                "missing_evidence": [
                    "No in-scope Python package directories containing importable modules were found."
                ],
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

        assert target is not None
        proposal = build_proposal(
            root=root,
            workspace_id=workspace_id,
            trigger=trigger,
            rule_id=rule_id,
            pack_id=pack_id,
            profile_path=target["path"],
            profile_document=target["document"],
            profile_existed=bool(target["existed"]),
            profile_hash=target["profile_hash"],
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


def _validate_workspace_evidence_ref(*, root: Path, workspace_id: str, ref: str) -> str | None:
    prefix = f"workspace:{workspace_id}:"
    if not ref.startswith(prefix):
        return f"Evidence reference is not bound to workspace '{workspace_id}': {ref}"

    body = ref[len(prefix):]
    relative_text, separator, expected_hash = body.rpartition("#sha256:")
    if not separator or len(expected_hash) != 64:
        return f"Evidence reference has an invalid SHA-256 binding: {ref}"
    try:
        relative = normalize_relative_path(relative_text)
    except ValueError:
        return f"Evidence reference contains an unsafe workspace path: {ref}"
    if not relative:
        return f"Evidence reference does not identify a workspace file: {ref}"

    lexical = root / relative
    if lexical.is_symlink():
        return f"Evidence file became a symbolic link: {relative}"
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, NotADirectoryError, ValueError):
        return f"Evidence file is missing or escapes the workspace root: {relative}"
    if not resolved.is_file():
        return f"Evidence path is no longer a regular file: {relative}"
    if sha256_file(resolved) != expected_hash:
        return f"Evidence file content changed after proposal generation: {relative}"
    return None


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
