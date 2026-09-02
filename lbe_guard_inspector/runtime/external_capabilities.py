"""Governed registration for external LBE capabilities.

This module does not execute external systems by itself. It classifies and
validates preconfigured adapters, then registers them into the existing
ToolRegistry so R6C authorization, R6E execution ordering, ToolReceipt evidence,
provider continuation, session ownership, and completion truth remain canonical.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping

from ..reasoning_provider import ProviderConfig
from ..session_memory_runtime import SessionMemoryRuntimeBridge
from .agent_guidance import build_agent_guidance
from .governed_coding import GovernedProviderReasoningController
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


def birdeye_mcp_tool_spec(tool: str) -> ToolSpec:
    """Return the bounded LBE-facing spec for one BirdEye read-only MCP tool."""
    normalized = str(tool).strip()
    if not normalized:
        raise ValueError("BirdEye MCP tool must be non-empty")
    return ToolSpec(
        tool_id=f"mcp.birdeye.{normalized}",
        capability="inspect",
        required_arguments=("arguments",),
        access_class=ToolAccessClass.READ,
        network_behavior=ToolNetworkBehavior.NONE,
        risk_class=ToolRiskClass.LOW,
        timeout_seconds=60.0,
        retry_policy="none",
        preconditions=(
            "BirdEye MCP tool is explicitly registered by LBE",
            "provider cannot select transport or endpoint",
            "LBE authorization precedes BirdEye invocation",
        ),
        expected_evidence=("BirdEye MCP result",),
        failure_modes=("invalid arguments", "BirdEye unavailable", "authorization failure"),
    )


def build_birdeye_mcp_handler(tool: str) -> ToolHandler:
    """Adapt one installed BirdEye stdio tool behind the LBE handler boundary."""
    normalized = str(tool).strip()
    if not normalized:
        raise ValueError("BirdEye MCP tool must be non-empty")

    def handler(request: ToolRequest) -> ToolExecutionResult:
        arguments = request.arguments["arguments"]
        if not isinstance(arguments, Mapping):
            raise ValueError("BirdEye MCP arguments must be an object")
        server = Path(os.environ.get(
            "LBE_BIRDEYE_MCP_SERVER",
            r"C:\MCP Local\Letterblack_BirdEye\mcp_server.py",
        ))
        python = os.environ.get("LBE_BIRDEYE_MCP_PYTHON", "python")
        if not server.is_file():
            raise FileNotFoundError(f"BirdEye MCP server is unavailable: {server}")
        request_message = lambda identifier, method, params: {
            "jsonrpc": "2.0", "id": identifier, "method": method, "params": params,
        }
        messages = [
            request_message(1, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "lbe-guard-inspector", "version": "0.1.0"},
            }),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            request_message(2, "tools/list", {}),
            request_message(3, "tools/call", {"name": normalized, "arguments": dict(arguments)}),
            request_message(4, "shutdown", {}),
        ]
        encoded = "\n".join(json.dumps(message, ensure_ascii=False) for message in messages) + "\n"
        completed = subprocess.run(
            [python, str(server), "--stdio"],
            cwd=str(server.parent),
            input=encoded,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"BirdEye MCP exited unsuccessfully: {completed.returncode}")
        responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
        initialize = next((item for item in responses if item.get("id") == 1), None)
        if initialize is None or initialize.get("result", {}).get("serverInfo", {}).get("name") != "birdeye":
            raise ValueError("BirdEye MCP server identity mismatch")
        tools = next((item for item in responses if item.get("id") == 2), {}).get("result", {}).get("tools", [])
        if not any(item.get("name") == normalized for item in tools):
            raise ValueError(f"BirdEye MCP tool was not advertised: {normalized}")
        call = next((item for item in responses if item.get("id") == 3), None)
        if call is None:
            raise ValueError("BirdEye MCP response omitted tools/call result")
        content = call.get("result", {}).get("content", [])
        text = next((item.get("text") for item in content if item.get("type") == "text"), None)
        if not isinstance(text, str):
            raise ValueError("BirdEye MCP tools/call omitted text content")
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("BirdEye MCP result must be an object")
        evidence = tuple(dict(item) for item in payload.get("evidence", []) if isinstance(item, dict))
        return ToolExecutionResult(output=payload, evidence=evidence)

    return handler


class GovernedExternalCapabilityController(GovernedProviderReasoningController):
    """Existing governed provider loop with pre-registered external adapters.

    This is an integration seam, not a second runtime or executor. It inherits
    the canonical provider loop and registers adapters into the controller's
    existing ToolRegistry before any provider turn executes.
    """

    def __init__(
        self,
        *,
        runtime: SessionMemoryRuntimeBridge,
        provider_id: str,
        provider_config: ProviderConfig,
        external_capabilities: Iterable[ExternalCapabilityRegistration],
    ) -> None:
        super().__init__(
            runtime=runtime,
            provider_id=provider_id,
            provider_config=provider_config,
        )
        self._external_capabilities = register_external_capabilities(
            self._registry,
            external_capabilities,
        )
        # The base controller already owns guidance projection. Rebuild that
        # projection after registration so the provider sees only the final
        # governed registry, never adapter transport details.
        self._guidance = build_agent_guidance(
            mode_decision=self._context.mode_decision,
            workspace_root=self._runtime.workspace_root,
            tools=self._registry.specs(),
        )

    @property
    def external_capabilities(self) -> tuple[ExternalCapabilityRegistration, ...]:
        return self._external_capabilities

    def external_capability_audit_payload(self) -> tuple[dict[str, object], ...]:
        return tuple(item.audit_payload() for item in self._external_capabilities)
