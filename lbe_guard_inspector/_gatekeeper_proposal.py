from __future__ import annotations

import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._gatekeeper_catalog import CatalogEntry
from ._gatekeeper_packages import PackageEvidence, evidence_refs, proposal_scope


def resolve_profile_target(root: Path, target_profile_path: str | Path | None) -> dict[str, Any]:
    """Resolve an existing JSON profile from current workspace evidence.

    A proposal may modify only a profile that already exists as a regular,
    non-symlink file inside the canonical workspace root.  Missing files are not
    treated as implicit creation targets because that would invent persistence
    structure rather than resolve it from current workspace evidence.
    """
    if target_profile_path is None or not str(target_profile_path).strip():
        return _profile_error(
            "No exact target profile or pack path was supplied; the gatekeeper will not invent a persistence target."
        )

    raw = Path(str(target_profile_path).strip())
    candidate = raw if raw.is_absolute() else root / raw
    try:
        parent = candidate.parent.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError):
        return _profile_error("The target profile parent directory does not exist.")

    lexical_target = parent / candidate.name
    if lexical_target.is_symlink():
        return _profile_error("The target profile must not be a symbolic link.")

    try:
        resolved = lexical_target.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError):
        return _profile_error(
            "The target profile file does not exist; the gatekeeper requires current workspace evidence and will not invent a new file."
        )

    try:
        resolved.relative_to(root)
    except ValueError:
        return _profile_error("The target profile path escapes the canonical workspace root.")

    if resolved.suffix.casefold() != ".json":
        return _profile_error("The first proposal slice supports exact JSON workspace profiles only.")
    if not resolved.is_file():
        return _profile_error("The target profile must be a regular file.")

    try:
        raw_bytes = resolved.read_bytes()
        document = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _profile_error(
            f"The target profile could not be read as JSON: {type(exc).__name__}: {exc}",
            existed=True,
        )
    if not isinstance(document, dict):
        return _profile_error("The target profile JSON root must be an object.", existed=True)

    return {
        "path": resolved,
        "document": document,
        "existed": True,
        "profile_hash": hashlib.sha256(raw_bytes).hexdigest(),
        "error": None,
    }


def build_proposal(
    *,
    root: Path,
    workspace_id: str,
    trigger: str,
    rule_id: str,
    pack_id: str,
    profile_path: Path,
    profile_document: dict[str, Any],
    profile_existed: bool,
    profile_hash: str,
    packages: Sequence[PackageEvidence],
    exceptions: Sequence[str],
    namespace_packages: set[str],
    severity: str,
    required_action: str | None,
    catalog: Sequence[CatalogEntry],
    created_at: datetime,
) -> dict[str, Any]:
    scope = proposal_scope(packages)
    module_refs = evidence_refs(packages, workspace_id)
    module_hashes = sorted({digest for item in packages for digest in item.module_hashes})
    relative = profile_path.relative_to(root).as_posix()
    profile_evidence_ref = f"workspace:{workspace_id}:{relative}#sha256:{profile_hash}"
    refs = sorted({profile_evidence_ref, *module_refs})
    snapshot_hash = catalog_hash(catalog)

    rule_payload = {
        "rule_id": rule_id,
        "pack": pack_id,
        "trigger": trigger,
        "scope": scope,
        "severity": severity,
        "exceptions": list(exceptions),
        "namespace_packages": sorted(namespace_packages),
        "auto_apply": False,
        "approval_required": True,
    }
    updated = profile_with_rule(profile_document, rule_id, rule_payload)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return {
        "proposal_id": proposal_id(
            workspace_id=workspace_id,
            rule_id=rule_id,
            trigger=trigger,
            target_profile_path=relative,
            profile_hash=profile_hash,
            scope=scope,
            hashes=module_hashes,
            catalog_snapshot_hash=snapshot_hash,
        ),
        "workspace_id": workspace_id,
        "rule_id": rule_id,
        "pack_id": pack_id,
        "target_profile_path": relative,
        "trigger": trigger,
        "rationale": "No equivalent registered rule covers deterministic Python package structure validation for the evidenced workspace scope.",
        "scope": scope,
        "required_action": required_action
        or (
            f"Add deterministic workspace-profile rule '{rule_id}' to validate that every regular Python package directory has __init__.py while preserving explicit namespace-package exceptions."
        ),
        "severity": severity,
        "exceptions": list(exceptions),
        "equivalent_rule_checked": True,
        "equivalent_rule_result": "NONE",
        "contradiction_result": "NONE",
        "evidence_refs": refs,
        "diff": unified_profile_diff(root, profile_path, profile_document, updated, profile_existed),
        "validation_plan": [
            "Validate the updated profile against rule_proposal and profile schemas.",
            "Revalidate the profile snapshot, catalog snapshot, and all workspace evidence hashes immediately before application.",
            "Run the focused rule-gatekeeper tests.",
            "Run the complete pytest suite.",
            "Execute the proposed deterministic package-structure guard in inspect mode and verify evidence-bound results.",
        ],
        "rollback_plan": [
            f"Restore {relative} from version control or the pre-application backup.",
            "Re-run focused and full validation to confirm the previous profile state is active.",
        ],
        "provenance": {
            "mode": "propose-rule",
            "generator": "lbe_guard_inspector.rule_gatekeeper",
            "workspace_root": str(root),
            "profile_path_source": "workspace_profile",
            "profile_snapshot_hash": profile_hash,
            "profile_evidence_ref": profile_evidence_ref,
            "profile_existed": bool(profile_existed),
            "catalog_snapshot_hash": snapshot_hash,
            "evidence_hashes": module_hashes,
        },
        "approval_required": True,
        "created_at": created_at.astimezone(timezone.utc).isoformat(),
    }


def profile_rule_payload(document: Mapping[str, Any], rule_id: str) -> Mapping[str, Any] | None:
    rules = document.get("rules")
    if isinstance(rules, Mapping):
        item = rules.get(rule_id)
        return item if isinstance(item, Mapping) else None
    if isinstance(rules, list):
        for item in rules:
            if isinstance(item, Mapping) and item.get("rule_id") == rule_id:
                return item
    return None


def profile_with_rule(original: Mapping[str, Any], rule_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(dict(original)))
    rules = updated.get("rules")
    if rules is None:
        updated["rules"] = {rule_id: dict(payload)}
    elif isinstance(rules, dict):
        if rule_id in rules:
            raise ValueError(f"Profile already contains rule_id: {rule_id}")
        rules[rule_id] = dict(payload)
    elif isinstance(rules, list):
        if any(isinstance(item, Mapping) and item.get("rule_id") == rule_id for item in rules):
            raise ValueError(f"Profile already contains rule_id: {rule_id}")
        rules.append(dict(payload))
    else:
        raise ValueError("Profile 'rules' must be an object, array, or absent")
    return updated


def unified_profile_diff(
    root: Path,
    path: Path,
    original: Mapping[str, Any],
    updated: Mapping[str, Any],
    existed: bool,
) -> str:
    relative = path.relative_to(root).as_posix()
    before = json.dumps(dict(original), indent=2, sort_keys=True, ensure_ascii=False) + "\n" if existed else ""
    after = json.dumps(dict(updated), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{relative}" if existed else "/dev/null",
            tofile=f"b/{relative}",
        )
    )


def proposal_id(
    *,
    workspace_id: str,
    rule_id: str,
    trigger: str,
    target_profile_path: str,
    profile_hash: str,
    scope: Sequence[str],
    hashes: Sequence[str],
    catalog_snapshot_hash: str,
) -> str:
    normalized = {
        "workspace_id": workspace_id.strip().casefold(),
        "rule_id": rule_id.strip().casefold(),
        "trigger": " ".join(trigger.split()).casefold(),
        "target_profile_path": target_profile_path.replace("\\", "/").casefold(),
        "profile_hash": profile_hash.casefold(),
        "scope": sorted(item.replace("\\", "/").casefold() for item in scope),
        "evidence_hashes": sorted(item.casefold() for item in hashes),
        "catalog_snapshot_hash": catalog_snapshot_hash.casefold(),
    }
    digest = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"prop-{digest[:24]}"


def catalog_hash(catalog: Sequence[CatalogEntry]) -> str:
    encoded = json.dumps(
        [item.as_dict() for item in catalog], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _profile_error(message: str, existed: bool = False) -> dict[str, Any]:
    return {
        "path": None,
        "document": None,
        "existed": existed,
        "profile_hash": None,
        "error": message,
    }
