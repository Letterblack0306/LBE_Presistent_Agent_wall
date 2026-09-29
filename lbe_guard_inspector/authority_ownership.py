from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatch
from typing import Mapping


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



class OwnerAuthorityStatus(str, Enum):
    OWNER_PROVEN = "OWNER_PROVEN"
    OWNER_UNPROVEN = "OWNER_UNPROVEN"
    OWNER_CONFLICT = "OWNER_CONFLICT"
    WRONG_SCOPE = "WRONG_SCOPE"


OWNER_AUTHORITY_BLOCKER = "OWNER_AUTHORITY_BLOCKER"
OWNER_SCOPE_VIOLATION = "OWNER_SCOPE_VIOLATION"


@dataclass(frozen=True, slots=True)
class OwnerAuthorityAuthorization:
    """LBE-owned authorization input for one bounded governed mutation."""

    issue_id: str
    owner_file_or_module: str
    owner_reason: str
    owner_evidence: tuple[str, ...]
    owner_status: OwnerAuthorityStatus
    allowed_paths: tuple[str, ...]
    validation_command: str
    forbidden_layers: tuple[str, ...] = ()
    issue_layer: str = "source"
    proposed_layer: str = "source"
    conflicting_owner_candidates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "issue_id", "owner_file_or_module", "owner_reason", "validation_command",
            "issue_layer", "proposed_layer",
        ):
            object.__setattr__(self, field_name, _clean(getattr(self, field_name), field_name))
        for field_name in (
            "owner_evidence", "allowed_paths", "forbidden_layers",
            "conflicting_owner_candidates",
        ):
            object.__setattr__(
                self, field_name, _clean_unique(tuple(getattr(self, field_name)), field_name)
            )
        if not self.owner_evidence:
            raise ValueError("owner_evidence must not be empty")
        if not self.allowed_paths:
            raise ValueError("allowed_paths must not be empty")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "OwnerAuthorityAuthorization":
        def strings(name: str) -> tuple[str, ...]:
            raw = value.get(name, ())
            if not isinstance(raw, (list, tuple)) or not all(isinstance(item, str) for item in raw):
                raise ValueError(f"{name} must be an array of strings")
            return tuple(raw)

        return cls(
            issue_id=str(value.get("issue_id", "")),
            owner_file_or_module=str(value.get("owner_file_or_module", value.get("proposed_owner", ""))),
            owner_reason=str(value.get("owner_reason", "")),
            owner_evidence=strings("owner_evidence"),
            owner_status=OwnerAuthorityStatus(str(value.get("owner_status", "")).strip()),
            allowed_paths=strings("allowed_paths"),
            validation_command=str(value.get("validation_command", "")),
            forbidden_layers=strings("forbidden_layers"),
            issue_layer=str(value.get("issue_layer", "source")),
            proposed_layer=str(value.get("proposed_layer", "source")),
            conflicting_owner_candidates=strings("conflicting_owner_candidates"),
        )

    def pre_execution_blocker(self, proposed_path: str) -> str | None:
        path = proposed_path.replace("\\", "/").strip()
        if self.owner_status is not OwnerAuthorityStatus.OWNER_PROVEN:
            return f"owner status is {self.owner_status.value}"
        if self.conflicting_owner_candidates:
            return "owner conflict remains unresolved"
        if not any(fnmatch(path, pattern.replace("\\", "/")) for pattern in self.allowed_paths):
            return f"proposed path is outside allowed_paths: {path}"
        if self.proposed_layer.lower() in {layer.lower() for layer in self.forbidden_layers}:
            return f"proposed layer is forbidden: {self.proposed_layer}"
        if self.issue_layer.lower() in {"runtime", "backend"} and self.proposed_layer.lower() == "docs":
            return f"{self.issue_layer.lower()} defect cannot be repaired by a docs-only patch"
        if self.issue_layer.lower() == "backend" and self.proposed_layer.lower() == "ui":
            return "backend defect cannot be repaired by a UI-only patch without owner evidence"
        return None

    def decision_payload(
        self, *, decision: str, actual_paths: tuple[str, ...] = (),
        blocking_reason: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "rule": OWNER_AUTHORITY_BLOCKER,
            "post_execution_rule": OWNER_SCOPE_VIOLATION,
            "issue": self.issue_id,
            "decision": decision,
            "owner": {
                "path": self.owner_file_or_module,
                "status": self.owner_status.value,
                "reason": self.owner_reason,
                "evidence_refs": list(self.owner_evidence),
            },
            "scope": {
                "allowed_paths": list(self.allowed_paths),
                "forbidden_layers": list(self.forbidden_layers),
                "actual_paths": list(actual_paths),
            },
            "validation_command": self.validation_command,
        }
        if blocking_reason:
            payload["blocking_reason"] = blocking_reason
        return payload


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
