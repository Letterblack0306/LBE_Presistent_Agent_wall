"""Provider-layer readiness check for registered reasoning backends.

The check proves that a configured provider can execute LBE's structured planning
contract. It does not inspect a workspace, resolve runtime mode, grant
permissions, run guards, or produce completion evidence.
"""
from __future__ import annotations

from dataclasses import dataclass

from .provider_capabilities import (
    ProviderModelCapabilities,
    discover_provider_model_capabilities,
)
from .provider_registry import ProviderCapabilities, ProviderRegistry, default_provider_registry
from .reasoning_contracts import ReasoningRequest
from .reasoning_provider import ProviderConfig


@dataclass(frozen=True)
class ProviderHealthResult:
    provider_id: str
    model_id: str
    status: str
    capabilities: ProviderCapabilities
    professional_capabilities: ProviderModelCapabilities


def check_provider_health(
    *,
    provider_id: str,
    provider_config: ProviderConfig,
    provider_registry: ProviderRegistry | None = None,
) -> ProviderHealthResult:
    """Probe one registered provider against the bounded planning contract.

    The legacy ``capabilities`` field continues to describe the accepted bounded
    adapter path. ``professional_capabilities`` is a separate P2 provider/model
    snapshot and remains conservative: endpoint syntax may establish protocol
    family, but unproven professional features stay UNKNOWN.
    """
    if not isinstance(provider_config, ProviderConfig):
        raise TypeError("provider_config must be a ProviderConfig")
    registry = provider_registry or default_provider_registry()
    if not isinstance(registry, ProviderRegistry):
        raise TypeError("provider_registry must be a ProviderRegistry")

    handle = registry.build(provider_id=provider_id, config=provider_config)
    professional_capabilities = discover_provider_model_capabilities(
        provider_id=handle.descriptor.provider_id,
        model_id=handle.descriptor.model_id,
        endpoint=provider_config.endpoint,
        context_window=handle.descriptor.capabilities.context_limit,
    )
    handle.backend.plan(
        ReasoningRequest(
            problem="Provider capability check. Return a minimal valid planning response.",
            workspace_identity={"workspace_id": "provider-check"},
            workspace_profile={},
            approved_guard_ids=(),
            approved_tools=(),
            reference_context=(),
        )
    )
    return ProviderHealthResult(
        provider_id=handle.descriptor.provider_id,
        model_id=handle.descriptor.model_id,
        status="READY",
        capabilities=handle.descriptor.capabilities,
        professional_capabilities=professional_capabilities,
    )
