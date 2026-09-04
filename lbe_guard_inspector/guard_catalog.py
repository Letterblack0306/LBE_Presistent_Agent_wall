"""Approved deterministic guard catalog selected from a verified project profile."""
from __future__ import annotations

from typing import Any, Mapping


def _evidence_contract(
    *,
    path_patterns: tuple[str, ...],
    evidence_requirements: tuple[str, ...],
    extensions: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    return {
        "path_patterns": path_patterns,
        "evidence_requirements": evidence_requirements,
        "extensions": extensions,
    }


FOUNDATION_GUARDS = (
    {
        "guard_id": "generic.index_present",
        "pack_id": "generic",
        "condition": "always",
        "category": "mandatory_policy",
        "evidence_contract": _evidence_contract(
            path_patterns=("pyproject.toml", "package.json", "Cargo.toml", "README.md"),
            extensions=(".toml", ".json", ".md"),
            evidence_requirements=("bounded project metadata",),
        ),
    },
    {
        "guard_id": "generic.forbidden_roots",
        "pack_id": "generic",
        "condition": "always",
        "category": "mandatory_policy",
        "evidence_contract": _evidence_contract(
            path_patterns=("governance.json", "pyproject.toml", "package.json"),
            extensions=(".json", ".toml"),
            evidence_requirements=("bounded governance and project metadata",),
        ),
    },
)
FOUNDATION_GUARD_IDS = tuple(item["guard_id"] for item in FOUNDATION_GUARDS)

_OPTIONAL_GUARDS_BY_PACK = {
    "generic": (),
    "cep": (
        "cep.manifest_exists",
        "cep.host_version",
        "cep.menubar_extension",
        "cep.debug_mode",
        "cep.callback_contract",
        "cep.no_zip_in_repo",
        "cep.symlink_free",
    ),
    "module_registry": ("module_registry.loaded_module_registration",),
}


def select_guard_catalog(profile: dict[str, Any]) -> dict[str, Any]:
    """Return only registered, approved guard IDs for one confident profile.

    This is a catalog decision, not a verdict and not an execution mechanism.
    Unknown or insufficient profiles produce no optional guard IDs.
    """
    if profile.get("outcome") != "profiled":
        return {
            "foundation_guard_ids": list(FOUNDATION_GUARD_IDS),
            "optional_guard_ids": [],
            "selection_outcome": "insufficient_evidence",
            "rationale": "A confident project profile is required for optional guard selection.",
        }

    signals = [
        {"path": item.get("path"), "sha256": item.get("sha256")}
        for item in profile.get("signals", [])
        if isinstance(item, dict) and item.get("path") and item.get("sha256")
    ]
    optional: list[str] = []
    for pack_id in profile.get("guard_packs", []):
        for guard_id in _OPTIONAL_GUARDS_BY_PACK.get(str(pack_id), ()):
            if guard_id not in optional:
                optional.append(guard_id)
    return {
        "foundation_guard_ids": list(FOUNDATION_GUARD_IDS),
        "optional_guard_ids": optional,
        "selection_outcome": "selected",
        "rationale": "Optional guards were selected from approved project signals.",
        "evidence_references": signals,
    }


def resolve_foundation_guards(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve mandatory guard applicability solely from this approved catalog."""
    signals = (profile or {}).get("signals", [])
    package_metadata_present = any(
        isinstance(item, dict) and item.get("path") == "package.json"
        for item in signals
    )
    return {
        "guards": [dict(item) for item in FOUNDATION_GUARDS],
        "npm": {
            "applicable": package_metadata_present,
            "guard_ids": [],
            "reason": "No approved NPM/package foundation guard is registered.",
        },
        "lbe": {
            "applicable": False,
            "guard_ids": [],
            "reason": "No approved lbe.validation foundation guard is registered.",
        },
    }


_EVIDENCE_CONTRACTS: dict[str, dict[str, Any]] = {
    "cep.manifest_exists": _evidence_contract(
        path_patterns=("CSXS/manifest.xml",),
        extensions=(".xml",),
        evidence_requirements=("canonical CEP manifest",),
    ),
    "cep.host_version": _evidence_contract(
        path_patterns=("CSXS/manifest.xml",),
        extensions=(".xml",),
        evidence_requirements=("canonical CEP manifest",),
    ),
    "cep.menubar_extension": _evidence_contract(
        path_patterns=("CSXS/manifest.xml",),
        extensions=(".xml",),
        evidence_requirements=("canonical CEP manifest",),
    ),
    "cep.debug_mode": _evidence_contract(
        path_patterns=("CSXS/manifest.xml",),
        extensions=(".xml",),
        evidence_requirements=("canonical CEP manifest",),
    ),
    "cep.no_zip_in_repo": _evidence_contract(
        path_patterns=("**/*.zip",),
        extensions=(".zip",),
        evidence_requirements=("repository archive files",),
    ),
    "cep.symlink_free": _evidence_contract(
        path_patterns=("*",),
        evidence_requirements=("current workspace paths",),
    ),
    "cep.callback_contract": _evidence_contract(
        path_patterns=("**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx"),
        extensions=(".js", ".jsx", ".ts", ".tsx"),
        evidence_requirements=("CEP evalScript callback contracts",),
    ),
    "module_registry.loaded_module_registration": _evidence_contract(
        path_patterns=(".lbe/module-registry.json",),
        extensions=(".json",),
        evidence_requirements=("canonical module registry artifact",),
    ),
}


def evidence_contract_for_guard(guard_id: str) -> Mapping[str, Any]:
    """Return the registered deterministic evidence contract for one guard."""
    normalized = str(guard_id).strip()
    for item in (*FOUNDATION_GUARDS,):
        if item["guard_id"] == normalized:
            return item["evidence_contract"]
    contract = _EVIDENCE_CONTRACTS.get(normalized)
    if contract is None:
        raise KeyError(f"No evidence contract registered for guard: {normalized}")
    return contract
