"""Tests for mode controller — policy enforcement boundary."""
from __future__ import annotations

from lbe_guard_inspector.runtime.mode_controller import (
    ModeRequest,
    ModeDecision,
    resolve_mode,
    get_supported_permissions,
    get_supported_policies,
)


def test_supported_permissions_are_stable() -> None:
    perms = get_supported_permissions()
    assert len(perms) == 4
    assert "read_only" in perms
    assert "write_allowed" in perms
    assert "audit_only" in perms
    assert "elevated" in perms


def test_supported_policies_are_stable() -> None:
    policies = get_supported_policies()
    assert len(policies) == 4
    assert "audit" in policies
    assert "development" in policies
    assert "strict" in policies
    assert "permissive" in policies


def test_read_only_permission_maps_to_audit() -> None:
    d = resolve_mode(ModeRequest(intent="inspect_workspace", permission="read_only", runtime_policy="permissive"))
    assert d.mode == "audit"


def test_audit_only_permission_maps_to_audit() -> None:
    d = resolve_mode(ModeRequest(intent="inspect_workspace", permission="audit_only", runtime_policy="permissive"))
    assert d.mode == "audit"


def test_write_allowed_permission_maps_to_development() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="permissive"))
    assert d.mode == "development"


def test_elevated_permission_maps_to_development() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="elevated", runtime_policy="permissive"))
    assert d.mode == "development"
def test_audit_policy_forces_audit() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="audit"))
    assert d.mode == "audit"


def test_development_policy_forces_development() -> None:
    d = resolve_mode(ModeRequest(intent="inspect_workspace", permission="read_only", runtime_policy="development"))
    assert d.mode == "development"


def test_strict_policy_forces_audit() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="strict"))
    assert d.mode == "audit"


def test_permissive_policy_allows_permission_based() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="permissive"))
    assert d.mode == "development"


def test_permissive_with_read_only_still_audit() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="read_only", runtime_policy="permissive"))
    assert d.mode == "audit"


def test_audit_intent_overrides_write_permission() -> None:
    for intent in ("audit_workspace", "check_finding", "review_memory",
                   "inspect_workspace", "verify_compliance"):
        d = resolve_mode(ModeRequest(intent=intent, permission="write_allowed", runtime_policy="permissive"))
        assert d.mode == "audit", f"Intent '{intent}' should force audit mode"


def test_development_intent_respects_permission() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="permissive"))
    assert d.mode == "development"
from lbe_guard_inspector.behavior.contracts import validate_mode_behavior


def test_audit_intent_returns_only_audit_behaviors() -> None:
    d = resolve_mode(ModeRequest(intent="audit_workspace", permission="read_only"))
    for b_name in d.allowed_behaviors:
        assert validate_mode_behavior("audit", b_name), \
            f"Behavior '{b_name}' not allowed in audit mode"


def test_development_intent_returns_development_behaviors() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="permissive"))
    assert d.mode == "development"
    assert "development_mode_capabilities" in d.allowed_behaviors
    assert "require_current_workspace_evidence" in d.allowed_behaviors
    assert "validation_before_acceptance" in d.allowed_behaviors
    assert "proposed_rules_require_validation" in d.allowed_behaviors


def test_audit_behaviors_filtered_out_in_audit_mode() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="read_only"))
    assert "development_mode_capabilities" not in d.allowed_behaviors
    assert "proposed_rules_require_validation" not in d.allowed_behaviors


def test_unknown_intent_uses_mode_defaults() -> None:
    d = resolve_mode(ModeRequest(intent="nonexistent_intent", permission="read_only"))
    assert d.mode == "audit"
    assert len(d.allowed_behaviors) > 0
    assert "unknown" in d.rationale.lower()


def test_audit_mode_has_no_write_capabilities() -> None:
    d = resolve_mode(ModeRequest(intent="audit_workspace", permission="read_only"))
    write_caps = {"modify", "propose", "test_candidate", "promote_after_validation",
                  "propose_rule", "test_proposal", "submit_for_approval"}
    for cap in d.capabilities:
        assert cap not in write_caps, f"Audit mode should not have capability '{cap}'"


def test_development_mode_has_write_capabilities() -> None:
    d = resolve_mode(ModeRequest(intent="fix_issue", permission="write_allowed", runtime_policy="permissive"))
    assert "propose" in d.capabilities
    assert "test_candidate" in d.capabilities


def test_audit_mode_has_inspect_capabilities() -> None:
    d = resolve_mode(ModeRequest(intent="audit_workspace", permission="read_only"))
    assert "inspect" in d.capabilities
    assert "collect_evidence" in d.capabilities
    assert "report_findings" in d.capabilities


def test_mode_decision_is_frozen() -> None:
    d = resolve_mode(ModeRequest(intent="audit_workspace", permission="read_only"))
    try:
        d.mode = "development"  # type: ignore
        assert False, "Should be frozen"
    except AttributeError:
        pass


def test_rationale_is_present() -> None:
    d = resolve_mode(ModeRequest(intent="audit_workspace", permission="read_only"))
    assert isinstance(d.rationale, str)
    assert len(d.rationale) > 0


def test_public_functions_return_tuples() -> None:
    assert isinstance(get_supported_permissions(), tuple)
    assert isinstance(get_supported_policies(), tuple)