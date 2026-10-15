"""Repository-owned validation command policy for completion evidence.

The only initial entry mirrors the mandatory GitHub Actions validation command
in .github/workflows/ci.yml.  This is not a general command execution API.
"""
from __future__ import annotations

from dataclasses import dataclass
import shlex
from typing import Any, Literal, Mapping, Sequence


RuntimeMode = Literal["coding", "audit", "investigation"]


@dataclass(frozen=True)
class ValidationCommandPolicy:
    policy_id: str
    operation_id: str
    applicable_mode: RuntimeMode
    evidence_kind: str
    command: tuple[str, ...]
    timeout_seconds: float

    def __post_init__(self) -> None:
        for name in ("policy_id", "operation_id", "evidence_kind"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
            object.__setattr__(self, name, value.strip())
        if self.applicable_mode not in {"coding", "audit", "investigation"}:
            raise ValueError("applicable_mode must be a supported runtime mode")
        if not self.command or not all(isinstance(item, str) and item.strip() for item in self.command):
            raise ValueError("validation command must contain non-empty arguments")
        if self.timeout_seconds <= 0:
            raise ValueError("validation command timeout_seconds must be positive")


class ValidationCommandPolicyCatalog:
    """Fixed registered commands; unknown mappings intentionally return no command."""

    def __init__(self, policies: Sequence[ValidationCommandPolicy]) -> None:
        by_mapping: dict[tuple[str, RuntimeMode, str], ValidationCommandPolicy] = {}
        for policy in policies:
            if not isinstance(policy, ValidationCommandPolicy):
                raise TypeError("validation command policies must be ValidationCommandPolicy")
            mapping = (policy.operation_id, policy.applicable_mode, policy.evidence_kind)
            if mapping in by_mapping:
                raise ValueError(f"ambiguous validation command policy mapping: {mapping}")
            by_mapping[mapping] = policy
        self._by_mapping = by_mapping

    def find(
        self,
        *,
        operation_id: str,
        mode: RuntimeMode,
        evidence_kind: str,
    ) -> ValidationCommandPolicy | None:
        return self._by_mapping.get((operation_id.strip(), mode, evidence_kind.strip()))


DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG = ValidationCommandPolicyCatalog((
    ValidationCommandPolicy(
        policy_id="repository.ci.pytest.v1",
        operation_id="reasoning.inspect",
        applicable_mode="coding",
        evidence_kind="focused_test",
        # -p no:cacheprovider: validation must not create .pytest_cache (an
        # unauthorized workspace mutation) in the project it is validating.
        command=("python", "-m", "pytest", "-q", "-p", "no:cacheprovider"),
        timeout_seconds=300.0,
    ),
))


OWNER_AUTHORITY_VALIDATION_POLICY_ID = "owner.authority.validation.v1"


def catalog_for_owner_authority(
    package: Mapping[str, Any] | None,
) -> ValidationCommandPolicyCatalog:
    """Completion validation catalog for one governed coding task.

    The repository default stays in force unless a *validated* owner authority
    package supplies ``validation_command``. That field is human-authored owner
    evidence for this bounded mutation, not model output, so it may replace the
    default command for the same mapping. It is tokenized (never run through a
    shell) and keeps the default timeout bound. Anything that does not validate
    falls back to the fixed repository policy.
    """
    if not isinstance(package, Mapping):
        return DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG
    from ..authority_ownership import OwnerAuthorityAuthorization

    try:
        authorization = OwnerAuthorityAuthorization.from_mapping(package)
        tokens = tuple(shlex.split(authorization.validation_command))
    except (ValueError, TypeError):
        return DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG
    if not tokens:
        return DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG
    return ValidationCommandPolicyCatalog((
        ValidationCommandPolicy(
            policy_id=OWNER_AUTHORITY_VALIDATION_POLICY_ID,
            operation_id="reasoning.inspect",
            applicable_mode="coding",
            evidence_kind="focused_test",
            command=tokens,
            timeout_seconds=300.0,
        ),
    ))
