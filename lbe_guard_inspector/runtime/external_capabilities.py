"""Governed registration for external LBE capabilities.

This module does not execute external systems by itself. It classifies and
validates preconfigured adapters, then registers them into the existing
ToolRegistry so R6C authorization, R6E execution ordering, ToolReceipt evidence,
provider continuation, session ownership, and completion truth remain canonical.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .tool_orchestration import (
    ToolAccessClass,
    ToolHandler,
    ToolNetworkBehavior,
    ToolRegistry,
    ToolRiskClass,
    ToolSpec,
)


class ExternalCapabilityKind(StrEnum):
    MCP = "mcp"
    PLUGIN = "plugin"
    SUBAGENT = "subagent"
    NETWORK = "network"
    HOSTED_SERVICE = "hosted_service"


_KIND_PREFIX: dict[ExternalCapabilityKind, str] = {
    ExternalCapabilityKind.MCP: "mcp.",
    ExternalCapabilityKind.PLUGIN: "plugin.",
    ExternalCapabilityKind.SUBAGENT: "subagent.",
    ExternalCapabilityKind.NETWORK: "network.",
    ExternalCapabilityKind.HOSTED_SERVICE: "hosted.",
}

# Transport selection is installation/configuration authority, not provider input.
# External tool schemas may describe domain arguments, but may not let the
# reasoning provider select an endpoint, executable, shell, or raw command path.
_RESERVED_TRANSPORT_ARGUMENTS = frozenset({
    "endpoint",
    "base_url",
    "url",
    "transport",
    "executable",
    "command",
    "argv",
    "shell",
})


@dataclass(frozen=True)
class ExternalCapabilityRegistration:
    """One preconfigured external adapter registered behind LBE authority."""

    adapter_id: str
    kind: ExternalCapabilityKind
    tool_id: str
    description: str
    handler: ToolHandler
    required_arguments: tuple[str, ...] = ()
    optional_arguments: tuple[str, ...] = ()
    access_class: ToolAccessClass = ToolAccessClass.READ
    network_behavior: ToolNetworkBehavior = ToolNetworkBehavior.NONE
    risk_class: ToolRiskClass = ToolRiskClass.MEDIUM
    timeout_seconds: float = 30.0
    retry_policy: str = "none"
    expected_evidence: tuple[str, ...] = ("external capability receipt",)
    failure_modes: tuple[str, ...] = (
        "authorization failure",
        "adapter unavailable",
        "adapter execution failure",
    )

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ExternalCapabilityKind):
            raise TypeError("kind must be ExternalCapabilityKind")
        adapter_id = str(self.adapter_id).strip()
        tool_id = str(self.tool_id).strip()
        description = str(self.description).strip()
        if not adapter_id:
            raise ValueError("adapter_id must be non-empty")
        if not tool_id:
            raise ValueError("tool_id must be non-empty")
        if not description:
            raise ValueError("description must be non-empty")
        if not callable(self.handler):
            raise TypeError("handler must be callable")
        prefix = _KIND_PREFIX[self.kind]
        if not tool_id.startswith(prefix) or tool_id == prefix:
            raise ValueError(f"tool_id for {self.kind.value} must start with '{prefix}'")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        argument_names = (*self.required_arguments, *self.optional_arguments)
        normalized = tuple(str(name).strip() for name in argument_names)
        if any(not name for name in normalized):
            raise ValueError("external tool argument names must be non-empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("external tool argument names must be unique")
        forbidden = sorted(set(normalized) & _RESERVED_TRANSPORT_ARGUMENTS)
        if forbidden:
            raise ValueError(
                "provider-controlled transport selection is forbidden: "
                + ", ".join(forbidden)
            )

        if self.kind in {ExternalCapabilityKind.NETWORK, ExternalCapabilityKind.HOSTED_SERVICE}:
            if self.network_behavior is not ToolNetworkBehavior.REQUIRED:
                raise ValueError(
                    f"{self.kind.value} registration requires network_behavior=REQUIRED"
                )

        # MCP and plugins may be in-process, stdio-backed, or local/network-backed;
        # the adapter registration owns that transport choice outside provider input.
        if self.kind is ExternalCapabilityKind.SUBAGENT and self.network_behavior is ToolNetworkBehavior.REQUIRED:
            # A subagent may use a networked provider internally, but its canonical
            # runtime identity remains parent-scoped. REQUIRED is allowed and explicit.
            pass

    @property
    def capability(self) -> str:
        return "modify" if self.access_class is ToolAccessClass.WRITE else "inspect"

    def tool_spec(self) -> ToolSpec:
        return ToolSpec(
            tool_id=self.tool_id,
            capability=self.capability,
            required_arguments=self.required_arguments,
            optional_arguments=self.optional_arguments,
            access_class=self.access_class,
            network_behavior=self.network_behavior,
            risk_class=self.risk_class,
            timeout_seconds=self.timeout_seconds,
            retry_policy=self.retry_policy,
            preconditions=(
                "adapter is pre-registered by LBE",
                "provider cannot select raw transport or endpoint",
                "existing R6C authorization precedes adapter execution",
            ),
            expected_evidence=self.expected_evidence,
            failure_modes=self.failure_modes,
        )

    def audit_payload(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "kind": self.kind.value,
            "tool_id": self.tool_id,
            "access_class": self.access_class.value,
            "network_behavior": self.network_behavior.value,
            "risk_class": self.risk_class.value,
        }


def register_external_capabilities(
    registry: ToolRegistry,
    registrations: Iterable[ExternalCapabilityRegistration],
) -> tuple[ExternalCapabilityRegistration, ...]:
    """Register validated external adapters into the existing ToolRegistry."""
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be ToolRegistry")

    items = tuple(registrations)
    adapter_ids: set[str] = set()
    tool_ids: set[str] = set()
    for registration in items:
        if not isinstance(registration, ExternalCapabilityRegistration):
            raise TypeError("registrations must contain ExternalCapabilityRegistration")
        if registration.adapter_id in adapter_ids:
            raise ValueError(f"duplicate external adapter_id: {registration.adapter_id}")
        if registration.tool_id in tool_ids:
            raise ValueError(f"duplicate external tool_id: {registration.tool_id}")
        adapter_ids.add(registration.adapter_id)
        tool_ids.add(registration.tool_id)

    for registration in items:
        registry.register(registration.tool_spec(), registration.handler)
    return items


def external_capability_descriptions(
    registrations: Iterable[ExternalCapabilityRegistration],
) -> dict[str, str]:
    return {item.tool_id: item.description for item in registrations}
