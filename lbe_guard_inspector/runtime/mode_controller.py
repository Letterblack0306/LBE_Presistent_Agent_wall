"""
Mode Controller — policy enforcement boundary.

The controller sits between the LLM and the private Core. It:
1. Accepts LLM intent + permission + runtime policy
2. Determines mode (audit / development)
3. Maps intent → allowed behaviors
4. Returns mode + allowed_behaviors + capabilities

It does NOT:
- run guards
- know guard IDs
- modify files
- decide verdicts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lbe_guard_inspector.behavior.contracts import (
    Mode,
    get_behaviors_for_intent,
    get_behaviors_for_mode,
    validate_mode_behavior,
)


Permission = Literal["read_only", "write_allowed", "audit_only", "elevated"]
RuntimePolicy = Literal["audit", "development", "strict", "permissive"]


@dataclass(frozen=True)
class ModeRequest:
    """Input to the mode controller. LLM proposes intent; controller decides."""
    intent: str
    permission: Permission = "read_only"
    workspace_root: str = ""
    runtime_policy: RuntimePolicy = "audit"


@dataclass(frozen=True)
class ModeDecision:
    """Output from the mode controller. Determines what the LLM may do."""
    mode: Mode
    allowed_behaviors: tuple[str, ...]
    capabilities: tuple[str, ...]
    rationale: str


_PERMISSION_MODE: dict[Permission, Mode] = {
    "read_only": "audit",
    "audit_only": "audit",
    "write_allowed": "development",
    "elevated": "development",
}

_POLICY_MODE_OVERRIDE: dict[RuntimePolicy, Mode | None] = {
    "audit": "audit",
    "development": "development",
    "strict": "audit",
    "permissive": None,
}


def _resolve_mode(
    intent: str,
    permission: Permission,
    runtime_policy: RuntimePolicy,
) -> tuple[Mode, str]:
    """Determine the effective mode. Policy overrides permission; intent may override both."""
    forced = _POLICY_MODE_OVERRIDE.get(runtime_policy)
    if forced is not None:
        return forced, f"Runtime policy '{runtime_policy}' forces {forced} mode"
    base = _PERMISSION_MODE.get(permission, "audit")
    audit_intents = {"audit_workspace", "check_finding", "review_memory",
                     "inspect_workspace", "verify_compliance"}
    if intent in audit_intents and base == "development":
        return "audit", f"Intent '{intent}' requires audit mode despite {permission} permission"
    return base, f"Permission '{permission}' maps to {base} mode"


def _resolve_capabilities(mode: Mode, allowed_behaviors: tuple[str, ...]) -> tuple[str, ...]:
    """Derive concrete capabilities from allowed behaviors."""
    behavior_caps: dict[str, tuple[str, ...]] = {
        "require_current_workspace_evidence": ("inspect", "search", "compare", "verify"),
        "validation_before_acceptance": ("validate", "verify", "corroborate", "cross_check"),
        "evidence_boundary_enforcement": ("reference_inform", "workspace_prove", "guard_detect", "validation_confirm"),
        "audit_mode_constraints": ("inspect", "collect_evidence", "report_findings", "register_finding"),
        "development_mode_capabilities": ("discover", "propose", "test_candidate", "validate_proposal", "promote_after_validation"),
        "finding_review_required": ("record_finding", "request_review", "verify_against_current", "categorize_finding"),
        "memory_is_historical_context": ("read_memory", "use_as_context", "correlate_with_current"),
        "use_only_approved_guards": ("list_approved_guards", "execute_approved_guard", "request_guard_execution"),
        "proposed_rules_require_validation": ("propose_rule", "test_proposal", "validate_proposal", "submit_for_approval"),
    }
    seen: set[str] = set()
    caps: list[str] = []
    for behavior in allowed_behaviors:
        for cap in behavior_caps.get(behavior, ()):
            if cap not in seen:
                caps.append(cap)
                seen.add(cap)
    if mode == "audit":
        write_caps = {"modify", "propose", "test_candidate", "promote_after_validation",
                      "propose_rule", "test_proposal", "submit_for_approval"}
        caps = [c for c in caps if c not in write_caps]
    return tuple(caps)


def resolve_mode(request: ModeRequest) -> ModeDecision:
    """
    Resolve the effective mode, allowed behaviors, and capabilities.

    Main entry point:
    1. Detect mode from intent + permission + policy
    2. Map intent to allowed behaviors (controller decides, not LLM)
    3. Filter behaviors by mode
    4. Derive capabilities
    """
    mode, rationale = _resolve_mode(request.intent, request.permission, request.runtime_policy)
    intent_behaviors = get_behaviors_for_intent(request.intent)
    if not intent_behaviors:
        mode_behaviors = get_behaviors_for_mode(mode)
        return ModeDecision(
            mode=mode,
            allowed_behaviors=tuple(b.name for b in mode_behaviors),
            capabilities=_resolve_capabilities(mode, tuple(b.name for b in mode_behaviors)),
            rationale=f"Unknown intent '{request.intent}': fell back to {mode} mode defaults. {rationale}",
        )
    allowed = tuple(
        b_name for b_name in intent_behaviors
        if validate_mode_behavior(mode, b_name)
    )
    capabilities = _resolve_capabilities(mode, allowed)
    return ModeDecision(
        mode=mode,
        allowed_behaviors=allowed,
        capabilities=capabilities,
        rationale=f"Intent '{request.intent}' resolved in {mode} mode. {rationale}",
    )


def get_supported_permissions() -> tuple[Permission, ...]:
    return tuple(sorted(_PERMISSION_MODE.keys()))


def get_supported_policies() -> tuple[RuntimePolicy, ...]:
    return tuple(sorted(_POLICY_MODE_OVERRIDE.keys()))