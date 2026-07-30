from __future__ import annotations

from typing import Any

from agent import Context
from audit_controller import AuditError, RuleResult, register_rule


def rule_generic_index_present(ctx: Context, params: dict[str, Any]) -> RuleResult:
    inventory = params.get("inventory") or {}
    file_count = int(inventory.get("files_considered", 0))
    roots = list(inventory.get("roots", []))
    if file_count <= 0:
        return RuleResult(
            rule_id="generic.index_present",
            status="failed",
            message="Selected workspace inventory contains zero files.",
            evidence={
                "files_considered": file_count,
                "roots": roots,
                "evidence_source": "current_workspace_inventory",
            },
        )
    return RuleResult(
        rule_id="generic.index_present",
        status="passed",
        message="Selected workspace inventory contains files.",
        evidence={
            "files_considered": file_count,
            "roots": roots,
            "evidence_source": "current_workspace_inventory",
        },
    )


register_rule("generic", "generic.index_present", rule_generic_index_present)


def rule_generic_forbidden_roots(ctx: Context, params: dict[str, Any]) -> RuleResult:
    gov = ctx.governance if hasattr(ctx, "governance") else {}
    forbidden = gov.get("forbidden_globs", [])
    if not forbidden:
        return RuleResult(
            rule_id="generic.forbidden_roots",
            status="blocked",
            message="No forbidden_globs configured.",
        )
    return RuleResult(
        rule_id="generic.forbidden_roots",
        status="passed",
        message="forbidden_globs are configured.",
        evidence={"count": len(forbidden)},
    )


register_rule("generic", "generic.forbidden_roots", rule_generic_forbidden_roots)
