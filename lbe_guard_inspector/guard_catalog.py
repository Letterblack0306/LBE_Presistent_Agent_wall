"""Approved deterministic guard catalog selected from a verified project profile."""
from __future__ import annotations

from typing import Any


FOUNDATION_GUARDS = (
    {
        "guard_id": "generic.index_present",
        "pack_id": "generic",
        "condition": "always",
        "category": "mandatory_policy",
    },
    {
        "guard_id": "generic.forbidden_roots",
        "pack_id": "generic",
        "condition": "always",
        "category": "mandatory_policy",
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
