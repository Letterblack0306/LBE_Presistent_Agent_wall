from __future__ import annotations

import pytest

from lbe_guard_inspector.authority_ownership import (
    AuthorityOwnershipDeclaration,
    OwnershipEvidenceState,
    OwnershipRole,
    PersistenceContract,
    require_single_operation,
)


def declaration(**overrides: object) -> AuthorityOwnershipDeclaration:
    values: dict[str, object] = {
        "operation_id": "workspace.module-state.update",
        "canonical_target": "workspace://dev/module-state/browser.loop-controller",
        "authoritative_owner": "module.registry",
        "canonical_state_location": ".lbe/module-registry.json",
        "allowed_mutation_capabilities": ("module.state.write",),
        "persistence": PersistenceContract(
            mechanism="atomic-json-replace",
            durable=True,
            confirmation_source="runtime receipt",
        ),
        "runtime_confirmation_required": True,
        "applicability": ("configured workspace", "registered module"),
        "evidence_requirements": (
            "current declaration",
            "current runtime receipt",
        ),
        "delegates": ("module.watcher",),
        "observers": ("guard.inspector",),
        "subscribers": ("agent.http-server",),
        "projections": ("ui.module-status",),
    }
    values.update(overrides)
    return AuthorityOwnershipDeclaration(**values)


def test_contract_defines_one_explicit_authoritative_operation() -> None:
    item = require_single_operation((declaration(),))

    assert item.operation_id == "workspace.module-state.update"
    assert item.canonical_target.startswith("workspace://dev/")
    assert item.authoritative_owner == "module.registry"
    assert item.canonical_state_location == ".lbe/module-registry.json"


@pytest.mark.parametrize("items", [(), (declaration(), declaration())])
def test_one_operation_per_inspection_is_enforced(
    items: tuple[AuthorityOwnershipDeclaration, ...],
) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        require_single_operation(items)


def test_owner_delegate_observer_and_projection_roles_are_unambiguous() -> None:
    item = declaration()

    assert item.role_of("module.registry") is OwnershipRole.OWNER
    assert item.role_of("module.watcher") is OwnershipRole.DELEGATE
    assert item.role_of("guard.inspector") is OwnershipRole.OBSERVER
    assert item.role_of("agent.http-server") is OwnershipRole.SUBSCRIBER
    assert item.role_of("ui.module-status") is OwnershipRole.PROJECTION
    assert item.role_of("unknown") is None


def test_participant_cannot_hold_multiple_roles() -> None:
    with pytest.raises(ValueError, match="roles must be unambiguous"):
        declaration(observers=("module.watcher",))


def test_duplicate_storage_is_not_automatically_duplicate_authority() -> None:
    item = declaration(
        subscribers=("runtime.cache",),
        projections=("ui.module-status", "runtime.snapshot"),
    )

    assert item.role_of("runtime.snapshot") is OwnershipRole.PROJECTION
    assert item.role_of("runtime.cache") is OwnershipRole.SUBSCRIBER
    assert item.may_mutate("runtime.snapshot", "module.state.write") is False
    assert item.may_mutate("runtime.cache", "module.state.write") is False
    assert item.may_mutate("module.registry", "module.state.write") is True
    assert item.may_mutate("module.watcher", "module.state.write") is True


def test_mutation_requires_both_authorized_role_and_capability() -> None:
    item = declaration()

    assert item.may_mutate("module.registry", "module.state.write") is True
    assert item.may_mutate("module.registry", "module.delete") is False
    assert item.may_mutate("guard.inspector", "module.state.write") is False


def test_complete_evidence_and_runtime_confirmation_are_sufficient() -> None:
    item = declaration()

    state = item.evidence_state(
        supplied_evidence=("current declaration", "current runtime receipt"),
        runtime_confirmed=True,
    )

    assert state is OwnershipEvidenceState.SUFFICIENT


@pytest.mark.parametrize(
    ("supplied", "contradictions", "runtime_confirmed"),
    [
        (("current declaration",), (), True),
        (
            ("current declaration", "current runtime receipt"),
            ("source and receipt disagree",),
            True,
        ),
        (("current declaration", "current runtime receipt"), (), False),
    ],
)
def test_unresolved_or_incomplete_evidence_is_insufficient(
    supplied: tuple[str, ...],
    contradictions: tuple[str, ...],
    runtime_confirmed: bool,
) -> None:
    item = declaration()

    state = item.evidence_state(
        supplied_evidence=supplied,
        contradictions=contradictions,
        runtime_confirmed=runtime_confirmed,
    )

    assert state is OwnershipEvidenceState.INSUFFICIENT


def test_contract_rejects_duplicate_role_members_and_empty_required_fields() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        declaration(delegates=("module.watcher", "module.watcher"))
    with pytest.raises(ValueError, match="operation_id must not be empty"):
        declaration(operation_id=" ")
    with pytest.raises(ValueError, match="allowed_mutation_capabilities must not be empty"):
        declaration(allowed_mutation_capabilities=())
