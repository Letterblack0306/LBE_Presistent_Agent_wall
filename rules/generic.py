from __future__ import annotations

from typing import Any

from agent import Context
from audit_controller import AuditError, RuleResult, register_rule


def rule_generic_index_present(ctx: Context, params: dict[str, Any]) -> RuleResult:
    db = __import__("agent", fromlist=["database_status"]).database_status()
    file_count = int(db.get("file_count", 0))
    if file_count <= 0:
        return RuleResult(
            rule_id="generic.index_present",
            status="failed",
            message="Workspace index reports zero files.",
            evidence={"file_count": file_count},
        )
    return RuleResult(
        rule_id="generic.index_present",
        status="passed",
        message="Workspace index contains files.",
        evidence={"file_count": file_count},
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
