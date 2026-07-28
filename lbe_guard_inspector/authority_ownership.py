from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OwnershipRole(str, Enum):
    OWNER = "owner"
    DELEGATE = "delegate"
    OBSERVER = "observer"
    SUBSCRIBER = "subscriber"
    PROJECTION = "projection"


class OwnershipEvidenceState(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


def _clean(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned


def _clean_unique(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    cleaned = tuple(_clean(value, field_name) for value in values)
    if len(set(cleaned)) != len(cleaned):
        raise ValueError(f"{field_name} must not contain duplicates")
    return cleaned


@dataclass(frozen=True, slots=True)
class PersistenceContract:
    mechanism: str
    durable: bool
    confirmation_source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "mechanism", _clean(self.mechanism, "mechanism"))
        object.__setattr__(
            self,
            "confirmation_source",
            _clean(self.confirmation_source, "confirmation_source"),
        )


@dataclass(frozen=True, slots=True)
class AuthorityOwnershipDeclaration:
    operation_id: str
    canonical_target: str
    authoritative_owner: str
    canonical_state_location: str
    allowed_mutation_capabilities: tuple[str, ...]
    persistence: PersistenceContract
    runtime_confirmation_required: bool
    applicability: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    delegates: tuple[str, ...] = ()
    observers: tuple[str, ...] = ()
    subscribers: tuple[str, ...] = ()
    projections: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_id", _clean(self.operation_id, "operation_id"))
        object.__setattr__(
            self,
            "canonical_target",
            _clean(self.canonical_target, "canonical_target"),
        )
        object.__setattr__(
            self,
            "authoritative_owner",
            _clean(self.authoritative_owner, "authoritative_owner"),
        )
        object.__setattr__(
            self,
            "canonical_state_location",
            _clean(self.canonical_state_location, "canonical_state_location"),
        )
        for field_name in (
            "allowed_mutation_capabilities",
            "applicability",
            "evidence_requirements",
            "delegates",
            "observers",
            "subscribers",
            "projections",
        ):
            values = getattr(self, field_name)
            object.__setattr__(self, field_name, _clean_unique(values, field_name))

        if not self.allowed_mutation_capabilities:
            raise ValueError("allowed_mutation_capabilities must not be empty")
        if not self.applicability:
            raise ValueError("applicability must not be empty")
        if not self.evidence_requirements:
            raise ValueError("evidence_requirements must not be empty")

        role_members = {
            OwnershipRole.OWNER: {self.authoritative_owner},
            OwnershipRole.DELEGATE: set(self.delegates),
            OwnershipRole.OBSERVER: set(self.observers),
            OwnershipRole.SUBSCRIBER: set(self.subscribers),
            OwnershipRole.PROJECTION: set(self.projections),
        }
        roles = tuple(role_members)
        for index, role in enumerate(roles):
            for other in roles[index + 1 :]:
                overlap = role_members[role] & role_members[other]
                if overlap:
                    names = ", ".join(sorted(overlap))
                    raise ValueError(
                        f"ownership roles must be unambiguous; {names} appears in "
                        f"both {role.value} and {other.value}"
                    )

    def role_of(self, participant: str) -> OwnershipRole | None:
        clean_participant = _clean(participant, "participant")
        if clean_participant == self.authoritative_owner:
            return OwnershipRole.OWNER
        role_groups = (
            (OwnershipRole.DELEGATE, self.delegates),
            (OwnershipRole.OBSERVER, self.observers),
            (OwnershipRole.SUBSCRIBER, self.subscribers),
            (OwnershipRole.PROJECTION, self.projections),
        )
        for role, members in role_groups:
            if clean_participant in members:
                return role
        return None

    def may_mutate(self, participant: str, capability: str) -> bool:
        role = self.role_of(participant)
        return (
            role in {OwnershipRole.OWNER, OwnershipRole.DELEGATE}
            and _clean(capability, "capability") in self.allowed_mutation_capabilities
        )

    def evidence_state(
        self,
        *,
        supplied_evidence: tuple[str, ...],
        contradictions: tuple[str, ...] = (),
        runtime_confirmed: bool = False,
    ) -> OwnershipEvidenceState:
        supplied = set(_clean_unique(supplied_evidence, "supplied_evidence"))
        unresolved = _clean_unique(contradictions, "contradictions")
        if unresolved:
            return OwnershipEvidenceState.INSUFFICIENT
        if not set(self.evidence_requirements).issubset(supplied):
            return OwnershipEvidenceState.INSUFFICIENT
        if self.runtime_confirmation_required and not runtime_confirmed:
            return OwnershipEvidenceState.INSUFFICIENT
        return OwnershipEvidenceState.SUFFICIENT


def require_single_operation(
    declarations: tuple[AuthorityOwnershipDeclaration, ...],
) -> AuthorityOwnershipDeclaration:
    if len(declarations) != 1:
        raise ValueError("exactly one authoritative operation is required per inspection")
    return declarations[0]
