"""Persisted installed-capability metadata behind LBE governed dispatch.

The registry persists integration metadata only. It never persists plaintext
credentials and never executes discovered integrations. Concrete execution is
materialized only when the host supplies a preconfigured adapter factory, which
produces a handler that is then wrapped by the existing
ExternalCapabilityRegistration -> ToolRegistry -> R6C/R6E path.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Mapping

from .external_capabilities import (
    ExternalCapabilityKind,
    ExternalCapabilityRegistration,
)
from .tool_orchestration import (
    ToolAccessClass,
    ToolHandler,
    ToolNetworkBehavior,
    ToolRiskClass,
)

_SCHEMA_VERSION = 1
_SECRET_FIELDS = frozenset({
    "api_key", "apikey", "token", "access_token", "refresh_token", "secret",
    "client_secret", "password", "authorization", "credential", "credentials",
})
_RESERVED_PROVIDER_TRANSPORT_FIELDS = frozenset({
    "endpoint", "base_url", "url", "transport", "executable", "command", "argv", "shell"
})


@dataclass(frozen=True)
class InstalledCapabilityRecord:
    integration_id: str
    adapter_id: str
    kind: ExternalCapabilityKind
    tool_id: str
    description: str
    enabled: bool = True
    credential_ref: str | None = None
    required_arguments: tuple[str, ...] = ()
    optional_arguments: tuple[str, ...] = ()
    access_class: ToolAccessClass = ToolAccessClass.READ
    network_behavior: ToolNetworkBehavior = ToolNetworkBehavior.NONE
    risk_class: ToolRiskClass = ToolRiskClass.MEDIUM
    timeout_seconds: float = 30.0
    retry_policy: str = "none"

    def __post_init__(self) -> None:
        for field_name, value in (
            ("integration_id", self.integration_id),
            ("adapter_id", self.adapter_id),
            ("tool_id", self.tool_id),
            ("description", self.description),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.kind, ExternalCapabilityKind):
            raise TypeError("kind must be ExternalCapabilityKind")
        if self.credential_ref is not None:
            if not isinstance(self.credential_ref, str) or not self.credential_ref.strip():
                raise ValueError("credential_ref must be a non-empty opaque reference")
            if any(ch in self.credential_ref for ch in ("\n", "\r")):
                raise ValueError("credential_ref must be one line")
        names = (*self.required_arguments, *self.optional_arguments)
        if len(set(names)) != len(names):
            raise ValueError("tool argument names must be unique")
        forbidden = sorted(set(names) & _RESERVED_PROVIDER_TRANSPORT_FIELDS)
        if forbidden:
            raise ValueError("provider-controlled transport arguments are forbidden: " + ", ".join(forbidden))
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.kind in {ExternalCapabilityKind.NETWORK, ExternalCapabilityKind.HOSTED_SERVICE}:
            if self.network_behavior is not ToolNetworkBehavior.REQUIRED:
                raise ValueError(f"{self.kind.value} requires network_behavior=required")

    def public_payload(self) -> dict[str, object]:
        return {
            "integration_id": self.integration_id,
            "adapter_id": self.adapter_id,
            "kind": self.kind.value,
            "tool_id": self.tool_id,
            "description": self.description,
            "enabled": self.enabled,
            "credential_ref_configured": self.credential_ref is not None,
            "required_arguments": list(self.required_arguments),
            "optional_arguments": list(self.optional_arguments),
            "access_class": self.access_class.value,
            "network_behavior": self.network_behavior.value,
            "risk_class": self.risk_class.value,
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": self.retry_policy,
        }

    def persisted_payload(self) -> dict[str, object]:
        payload = self.public_payload()
        payload.pop("credential_ref_configured", None)
        payload["credential_ref"] = self.credential_ref
        return payload


@dataclass(frozen=True)
class InstalledCapabilityStatus:
    record: InstalledCapabilityRecord
    availability: str
    rationale: str

    def public_payload(self) -> dict[str, object]:
        return {
            **self.record.public_payload(),
            "availability": self.availability,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class InstalledCapabilityRegistry:
    records: tuple[InstalledCapabilityRecord, ...]
    schema_version: int = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError(f"unsupported installed capability schema_version: {self.schema_version}")
        integration_ids = [item.integration_id for item in self.records]
        adapter_ids = [item.adapter_id for item in self.records]
        tool_ids = [item.tool_id for item in self.records]
        for label, values in (
            ("integration_id", integration_ids),
            ("adapter_id", adapter_ids),
            ("tool_id", tool_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate installed capability {label}")

    def persisted_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "integrations": [item.persisted_payload() for item in self.records],
        }

    def statuses(self, adapter_factories: Mapping[str, Callable[[InstalledCapabilityRecord], ToolHandler]]) -> tuple[InstalledCapabilityStatus, ...]:
        statuses: list[InstalledCapabilityStatus] = []
        for record in self.records:
            if not record.enabled:
                statuses.append(InstalledCapabilityStatus(record, "DISABLED", "integration is disabled in persisted LBE configuration"))
            elif record.adapter_id not in adapter_factories:
                statuses.append(InstalledCapabilityStatus(record, "UNAVAILABLE", "no host adapter factory is installed for adapter_id"))
            else:
                statuses.append(InstalledCapabilityStatus(record, "AVAILABLE", "host adapter factory is installed; execution still requires governed registration and authorization"))
        return tuple(statuses)

    def materialize(self, adapter_factories: Mapping[str, Callable[[InstalledCapabilityRecord], ToolHandler]]) -> tuple[ExternalCapabilityRegistration, ...]:
        registrations: list[ExternalCapabilityRegistration] = []
        for status in self.statuses(adapter_factories):
            record = status.record
            if status.availability != "AVAILABLE":
                continue
            handler = adapter_factories[record.adapter_id](record)
            if not callable(handler):
                raise TypeError(f"adapter factory returned non-callable handler: {record.adapter_id}")
            registrations.append(
                ExternalCapabilityRegistration(
                    adapter_id=record.adapter_id,
                    kind=record.kind,
                    tool_id=record.tool_id,
                    description=record.description,
                    handler=handler,
                    required_arguments=record.required_arguments,
                    optional_arguments=record.optional_arguments,
                    access_class=record.access_class,
                    network_behavior=record.network_behavior,
                    risk_class=record.risk_class,
                    timeout_seconds=record.timeout_seconds,
                    retry_policy=record.retry_policy,
                )
            )
        return tuple(registrations)


class InstalledCapabilityRegistryStore:
    """Atomic JSON persistence for non-secret installed integration metadata."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()

    def load(self) -> InstalledCapabilityRegistry:
        if not self.path.is_file():
            return InstalledCapabilityRegistry(records=())
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._reject_secret_fields(raw)
        if not isinstance(raw, dict):
            raise ValueError("installed capability registry must be a JSON object")
        if raw.get("schema_version") != _SCHEMA_VERSION:
            raise ValueError("installed capability registry schema_version must be 1")
        integrations = raw.get("integrations")
        if not isinstance(integrations, list):
            raise ValueError("installed capability registry integrations must be an array")
        records = tuple(self._parse_record(item) for item in integrations)
        return InstalledCapabilityRegistry(records=records)

    def save(self, registry: InstalledCapabilityRegistry) -> None:
        if not isinstance(registry, InstalledCapabilityRegistry):
            raise TypeError("registry must be InstalledCapabilityRegistry")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(registry.persisted_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(self.path.parent), prefix=".lbe-capabilities-", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
            temp_path = None
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    @classmethod
    def _reject_secret_fields(cls, value: object, path: str = "$") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                clean = str(key).strip().lower()
                if clean in _SECRET_FIELDS:
                    raise ValueError(f"plaintext credential field is forbidden in installed registry: {path}.{key}")
                cls._reject_secret_fields(nested, f"{path}.{key}")
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                cls._reject_secret_fields(nested, f"{path}[{index}]")

    @staticmethod
    def _parse_record(value: object) -> InstalledCapabilityRecord:
        if not isinstance(value, dict):
            raise ValueError("installed capability entries must be objects")
        allowed = {
            "integration_id", "adapter_id", "kind", "tool_id", "description", "enabled",
            "credential_ref", "required_arguments", "optional_arguments", "access_class",
            "network_behavior", "risk_class", "timeout_seconds", "retry_policy",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError("unsupported installed capability fields: " + ", ".join(unknown))
        try:
            kind = ExternalCapabilityKind(str(value["kind"]))
            access_class = ToolAccessClass(str(value.get("access_class", "read")))
            network_behavior = ToolNetworkBehavior(str(value.get("network_behavior", "none")))
            risk_class = ToolRiskClass(str(value.get("risk_class", "medium")))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"invalid installed capability enum value: {exc}") from exc
        required = value.get("required_arguments", [])
        optional = value.get("optional_arguments", [])
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            raise ValueError("required_arguments must be a string array")
        if not isinstance(optional, list) or not all(isinstance(item, str) for item in optional):
            raise ValueError("optional_arguments must be a string array")
        return InstalledCapabilityRecord(
            integration_id=str(value.get("integration_id", "")),
            adapter_id=str(value.get("adapter_id", "")),
            kind=kind,
            tool_id=str(value.get("tool_id", "")),
            description=str(value.get("description", "")),
            enabled=bool(value.get("enabled", True)),
            credential_ref=None if value.get("credential_ref") is None else str(value.get("credential_ref")),
            required_arguments=tuple(required),
            optional_arguments=tuple(optional),
            access_class=access_class,
            network_behavior=network_behavior,
            risk_class=risk_class,
            timeout_seconds=float(value.get("timeout_seconds", 30.0)),
            retry_policy=str(value.get("retry_policy", "none")),
        )
