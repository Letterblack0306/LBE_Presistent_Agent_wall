"""Tests for public behavior contracts."""
from __future__ import annotations

from lbe_guard_inspector.behavior.contracts import (
    BEHAVIOR_CONTRACT_VERSION,
    BehaviorContract,
    BEHAVIOR_CONTRACTS,
    MODE_BEHAVIOR_MAP,
    INTENT_BEHAVIOR_MAP,
    get_behavior,
    get_behaviors_for_mode,
    get_all_behaviors,
    get_behavior_names,
    validate_mode_behavior,
    get_behaviors_for_intent,
    get_supported_intents,
)


def test_version_is_string() -> None:
    assert isinstance(BEHAVIOR_CONTRACT_VERSION, str)
    assert BEHAVIOR_CONTRACT_VERSION == "1.0"


def test_all_contracts_are_frozen() -> None:
    for b in BEHAVIOR_CONTRACTS.values():
        assert isinstance(b, BehaviorContract)


def test_all_contracts_have_required_fields() -> None:
    for name, b in BEHAVIOR_CONTRACTS.items():
        assert b.name == name
        assert isinstance(b.description, str)
        assert len(b.modes) > 0
        assert len(b.forbidden_actions) > 0
        assert isinstance(b.authority, str)


def test_no_private_guard_ids_in_contracts() -> None:
    leaked = ["internal_guard", "internal_gate", "LBE_CORE_GATE",
              "workspace-trust-guard", "generic.index", "cep."]
    for name, b in BEHAVIOR_CONTRACTS.items():
        full = f"{name} {b.description} {b.authority}"
        for p in leaked:
            assert p not in full


def test_all_behaviors_have_valid_modes() -> None:
    valid = {"audit", "development"}
    for name, b in BEHAVIOR_CONTRACTS.items():
        for m in b.modes:
            assert m in valid


def test_mode_map_contains_all_audit_behaviors() -> None:
    audit = set(MODE_BEHAVIOR_MAP["audit"])
    for n, b in BEHAVIOR_CONTRACTS.items():
        if "audit" in b.modes:
            assert n in audit


def test_mode_map_contains_all_development_behaviors() -> None:
    dev = set(MODE_BEHAVIOR_MAP["development"])
    for n, b in BEHAVIOR_CONTRACTS.items():
        if "development" in b.modes:
            assert n in dev


def test_audit_has_read_only_constraint() -> None:
    assert "audit_mode_constraints" in MODE_BEHAVIOR_MAP["audit"]

def test_get_behavior_returns_contract() -> None:
    b = get_behavior("require_current_workspace_evidence")
    assert isinstance(b, BehaviorContract)
    assert b.name == "require_current_workspace_evidence"


def test_get_behavior_raises_for_unknown() -> None:
    try:
        get_behavior("nonexistent")
        assert False
    except KeyError:
        pass


def test_get_behaviors_for_mode_audit() -> None:
    behaviors = get_behaviors_for_mode("audit")
    assert len(behaviors) > 0
    for b in behaviors:
        assert "audit" in b.modes


def test_get_behaviors_for_mode_development() -> None:
    behaviors = get_behaviors_for_mode("development")
    assert len(behaviors) > 0
    for b in behaviors:
        assert "development" in b.modes


def test_get_all_behaviors_returns_all() -> None:
    assert len(get_all_behaviors()) == len(BEHAVIOR_CONTRACTS)


def test_behavior_names_are_sorted() -> None:
    names = get_behavior_names()
    assert names == tuple(sorted(names))

def test_supported_intents_are_sorted() -> None:
    assert get_supported_intents() == tuple(sorted(get_supported_intents()))


def test_audit_intents_map_to_audit_behaviors() -> None:
    audit = {"inspect_workspace", "verify_compliance", "audit_workspace",
             "check_finding", "review_memory"}
    for intent in audit:
        behaviors = get_behaviors_for_intent(intent)
        assert len(behaviors) > 0
        for b_name in behaviors:
            assert validate_mode_behavior("audit", b_name)


def test_development_intents_map_to_development_behaviors() -> None:
    dev = {"fix_issue", "propose_rule", "discover_patterns", "test_candidate"}
    for intent in dev:
        behaviors = get_behaviors_for_intent(intent)
        assert len(behaviors) > 0
        for b_name in behaviors:
            assert validate_mode_behavior("development", b_name)


def test_unknown_intent_returns_empty() -> None:
    assert get_behaviors_for_intent("nonexistent_intent") == ()


def test_each_behavior_used_in_intent_map() -> None:
    used: set[str] = set()
    for behaviors in INTENT_BEHAVIOR_MAP.values():
        used.update(behaviors)
    for name in BEHAVIOR_CONTRACTS:
        assert name in used


def test_behavior_contracts_are_immutable() -> None:
    b = BEHAVIOR_CONTRACTS["require_current_workspace_evidence"]
    try:
        b.name = "changed"  # type: ignore
        assert False
    except AttributeError:
        pass


def test_mode_map_only_contains_known_behaviors() -> None:
    for mode, names in MODE_BEHAVIOR_MAP.items():
        for name in names:
            assert name in BEHAVIOR_CONTRACTS


def test_contract_count_is_stable() -> None:
    assert len(BEHAVIOR_CONTRACTS) == 9


def test_intent_count_is_stable() -> None:
    assert len(INTENT_BEHAVIOR_MAP) == 9

def test_validate_mode_behavior() -> None:
    assert validate_mode_behavior("audit", "audit_mode_constraints") is True
    assert validate_mode_behavior("development", "audit_mode_constraints") is False
    assert validate_mode_behavior("development", "development_mode_capabilities") is True
    assert validate_mode_behavior("audit", "development_mode_capabilities") is False

def test_development_has_proposed_rules_constraint() -> None:
    assert "proposed_rules_require_validation" in MODE_BEHAVIOR_MAP["development"]