from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from agent import Context, GovernanceError
from audit_controller import AuditError, RuleResult, register_rule

RULE_ID = "module_registry.loaded_module_registration"
REGISTRY_RELATIVE_PATH = ".lbe/module-registry.json"
_MAX_DECLARATIONS = 2_000
_MAX_RECEIPTS = 10_000


def _rule(ctx: Context, params: dict[str, Any], logic) -> RuleResult:
    try:
        return logic(ctx, params)
    except (GovernanceError, AuditError) as exc:
        return RuleResult(rule_id=RULE_ID, status="blocked", message=str(exc))
    except Exception as exc:  # pragma: no cover - defensive boundary
        return RuleResult(
            rule_id=RULE_ID,
            status="failed",
            message=f"{type(exc).__name__}: {exc}",
        )


def _configured_root_for(ctx: Context, target: Path, roots: list[str]) -> Any:
    selected = set(roots or [])
    matches = []
    for root in ctx.roots:
        if selected and root.name not in selected:
            continue
        configured = root.path.expanduser().resolve()
        if target == configured:
            matches.append(root)
    if not matches:
        raise GovernanceError(f"Workspace root is not an exact configured knowledge root: {target}")
    if len(matches) > 1:
        raise GovernanceError(f"Workspace root resolves ambiguously: {target}")
    return matches[0]


def _module_id(item: Mapping[str, Any]) -> str | None:
    value = item.get("module_id", item.get("id"))
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _receipt_type(item: Mapping[str, Any]) -> str:
    value = item.get("type", item.get("event_type", ""))
    return str(value).strip().lower()


def rule_loaded_module_registration(ctx: Context, params: dict[str, Any]) -> RuleResult:
    """Detect loaded module receipts whose module IDs are absent from declarations."""
    raw_workspace = params.get("workspace_root")
    if not isinstance(raw_workspace, str) or not raw_workspace.strip():
        raise GovernanceError("workspace_root must be a non-empty string")

    target = Path(raw_workspace).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise GovernanceError(f"Workspace root does not exist or is not a directory: {target}")

    roots = [str(item) for item in (params.get("roots") or [])]
    configured = _configured_root_for(ctx, target, roots)
    registry_path = target / REGISTRY_RELATIVE_PATH
    virtual_path = f"{configured.name}/{REGISTRY_RELATIVE_PATH}"

    if not registry_path.is_file():
        return RuleResult(
            rule_id=RULE_ID,
            status="not_applicable",
            message="No canonical module registry artifact exists in the exact configured workspace.",
            evidence={
                "registry_path": virtual_path,
                "supporting_findings": [],
                "read_only": True,
                "bounded": True,
            },
        )

    try:
        raw = registry_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return RuleResult(
            rule_id=RULE_ID,
            status="blocked",
            message=f"The module registry artifact cannot be validated: {type(exc).__name__}: {exc}",
            evidence={
                "registry_path": virtual_path,
                "supporting_findings": [
                    {
                        "path": virtual_path,
                        "classification": "unresolved_registry",
                        "detail": str(exc),
                    }
                ],
                "read_only": True,
                "bounded": True,
            },
            severity="warning",
        )

    if not isinstance(payload, Mapping):
        return RuleResult(
            rule_id=RULE_ID,
            status="blocked",
            message="The module registry artifact must contain a JSON object.",
            evidence={
                "registry_path": virtual_path,
                "supporting_findings": [
                    {
                        "path": virtual_path,
                        "classification": "unresolved_registry",
                        "detail": "top-level value is not an object",
                    }
                ],
                "read_only": True,
                "bounded": True,
            },
            severity="warning",
        )

    declarations = payload.get("declarations")
    receipts = payload.get("receipts")
    if not isinstance(declarations, list) or not isinstance(receipts, list):
        return RuleResult(
            rule_id=RULE_ID,
            status="blocked",
            message="The module registry artifact requires declarations and receipts arrays.",
            evidence={
                "registry_path": virtual_path,
                "supporting_findings": [
                    {
                        "path": virtual_path,
                        "classification": "unresolved_registry",
                        "detail": "missing or malformed declarations/receipts",
                    }
                ],
                "read_only": True,
                "bounded": True,
            },
            severity="warning",
        )

    declarations = declarations[:_MAX_DECLARATIONS]
    receipts = receipts[:_MAX_RECEIPTS]
    declared_ids = {
        module_id
        for item in declarations
        if isinstance(item, Mapping)
        for module_id in [_module_id(item)]
        if module_id is not None
    }

    loaded_receipts = []
    malformed_receipts = []
    for index, item in enumerate(receipts):
        if not isinstance(item, Mapping):
            malformed_receipts.append(index)
            continue
        if _receipt_type(item) != "loaded":
            continue
        module_id = _module_id(item)
        if module_id is None:
            malformed_receipts.append(index)
            continue
        loaded_receipts.append((index, module_id, item))

    finding_base = {
        "path": virtual_path,
        "hash": __import__("hashlib").sha256(raw).hexdigest(),
    }

    if malformed_receipts:
        findings = [
            {
                **finding_base,
                "classification": "unresolved_receipt",
                "receipt_index": index,
            }
            for index in malformed_receipts[:50]
        ]
        return RuleResult(
            rule_id=RULE_ID,
            status="blocked",
            message="Loaded-receipt validation is incomplete because malformed receipts were found.",
            evidence={
                "registry_path": virtual_path,
                "declared_module_ids": sorted(declared_ids),
                "malformed_receipt_indexes": malformed_receipts[:50],
                "supporting_findings": findings,
                "read_only": True,
                "bounded": True,
            },
            severity="warning",
        )

    if not loaded_receipts:
        return RuleResult(
            rule_id=RULE_ID,
            status="blocked",
            message="The registry exists, but no loaded-module receipts are available to validate.",
            evidence={
                "registry_path": virtual_path,
                "declared_module_ids": sorted(declared_ids),
                "supporting_findings": [
                    {
                        **finding_base,
                        "classification": "missing_loaded_receipts",
                    }
                ],
                "read_only": True,
                "bounded": True,
            },
            severity="warning",
        )

    unknown = [
        {
            **finding_base,
            "classification": "loaded_module_unregistered",
            "receipt_index": index,
            "module_id": module_id,
            "instance_id": item.get("instance_id"),
        }
        for index, module_id, item in loaded_receipts
        if module_id not in declared_ids
    ]
    valid = [
        {
            **finding_base,
            "classification": "loaded_module_registered",
            "receipt_index": index,
            "module_id": module_id,
            "instance_id": item.get("instance_id"),
        }
        for index, module_id, item in loaded_receipts
        if module_id in declared_ids
    ]

    evidence = {
        "registry_path": virtual_path,
        "declared_module_ids": sorted(declared_ids),
        "loaded_module_ids": [module_id for _, module_id, _ in loaded_receipts],
        "unregistered_loaded_modules": unknown,
        "registered_loaded_modules": valid,
        "supporting_findings": unknown or valid,
        "read_only": True,
        "bounded": True,
        "declaration_limit": _MAX_DECLARATIONS,
        "receipt_limit": _MAX_RECEIPTS,
    }

    if unknown:
        return RuleResult(
            rule_id=RULE_ID,
            status="failed",
            message=f"Found {len(unknown)} loaded module receipt(s) without a matching declaration.",
            evidence=evidence,
        )

    return RuleResult(
        rule_id=RULE_ID,
        status="passed",
        message="Every loaded module receipt has a matching module declaration.",
        evidence=evidence,
    )


register_rule(
    "module_registry",
    RULE_ID,
    lambda ctx, params: _rule(ctx, params, rule_loaded_module_registration),
)
