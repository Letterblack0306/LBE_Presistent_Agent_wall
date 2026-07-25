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
    if target_profile_path is None or not str(target_profile_path).strip():
        return _profile_error("No exact target profile or pack path was supplied; the gatekeeper will not invent a persistence target.")
    raw = Path(target_profile_path)
    candidate = raw if raw.is_absolute() else root / raw
    try:
        parent = candidate.parent.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError):
        return _profile_error("The target profile parent directory does not exist.")
    resolved = parent / candidate.name
    try:
        resolved.relative_to(root)
    except ValueError:
        return _profile_error("The target profile path escapes the canonical workspace root.")
    if resolved.suffix.casefold() != ".json":
        return _profile_error("The first proposal slice supports exact JSON workspace profiles only.")
    if not resolved.exists():
        return {"path": resolved, "document": {}, "existed": False, "error": None}
    if not resolved.is_file() or resolved.is_symlink():
        return _profile_error("The target profile must be a regular file.")
    try:
        document = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _profile_error(f"The target profile could not be read as JSON: {type(exc).__name__}: {exc}", existed=True)
    if not isinstance(document, dict):
        return _profile_error("The target profile JSON root must be an object.", existed=True)
    return {"path": resolved, "document": document, "existed": True, "error": None}


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
    packages: Sequence[PackageEvidence],
    exceptions: Sequence[str],
    namespace_packages: set[str],
    severity: str,
    required_action: str | None,
    catalog: Sequence[CatalogEntry],
    created_at: datetime,
) -> dict[str, Any]:
    scope = proposal_scope(packages)
    refs = evidence_refs(packages, workspace_id)
    hashes = sorted({digest for item in packages for digest in item.module_hashes})
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
    relative = profile_path.relative_to(root).as_posix()
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return {
        "proposal_id": proposal_id(workspace_id, rule_id, trigger, scope, hashes),
        "workspace_id": workspace_id,
        "rule_id": rule_id,
        "pack_id": pack_id,
        "target_profile_path": relative,
        "trigger": trigger,
        "rationale": "No equivalent registered rule covers deterministic Python package structure validation for the evidenced workspace scope.",
        "scope": scope,
        "required_action": required_action or (
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
            "profile_path_source": "explicit_request",
            "catalog_snapshot_hash": catalog_hash(catalog),
            "evidence_hashes": hashes,
        },
        "approval_required": True,
        "created_at": created_at.astimezone(timezone.utc).isoformat(),
    }


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


def unified_profile_diff(root: Path, path: Path, original: Mapping[str, Any], updated: Mapping[str, Any], existed: bool) -> str:
    relative = path.relative_to(root).as_posix()
    before = json.dumps(dict(original), indent=2, sort_keys=True, ensure_ascii=False) + "\n" if existed else ""
    after = json.dumps(dict(updated), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{relative}" if existed else "/dev/null", tofile=f"b/{relative}",
    ))


def proposal_id(workspace_id: str, rule_id: str, trigger: str, scope: Sequence[str], hashes: Sequence[str]) -> str:
    normalized = {
        "workspace_id": workspace_id.strip().casefold(),
        "rule_id": rule_id.strip().casefold(),
        "trigger": " ".join(trigger.split()).casefold(),
        "scope": sorted(item.replace("\\", "/").casefold() for item in scope),
        "evidence_hashes": sorted(item.casefold() for item in hashes),
    }
    digest = hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"prop-{digest[:24]}"


def catalog_hash(catalog: Sequence[CatalogEntry]) -> str:
    encoded = json.dumps([item.as_dict() for item in catalog], sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _profile_error(message: str, existed: bool = False) -> dict[str, Any]:
    return {"path": None, "document": None, "existed": existed, "error": message}
