"""Resolve an optional professional provider transport without weakening LBE authority.

This composition layer is intentionally separate from ``ProviderRegistry``. The
legacy registry owns accepted bounded ``ReasoningBackend`` factories. Professional
streaming/tool transport is selected only when both the host backend and the
provider/model capability evidence satisfy the requested contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .cline_sidecar_adapter import ClineSidecarProviderAdapter
from .cline_sidecar_readiness import ClineSidecarReadiness, ClineSidecarReadinessStatus
from .provider_capabilities import CapabilityClaim, CapabilitySupport, ProviderModelCapabilities
from .professional_provider_events import ProfessionalProviderAdapter


class ProfessionalProviderResolutionError(RuntimeError):
    """Raised when a requested professional backend cannot be selected truthfully."""


@dataclass(frozen=True)
class ProfessionalTransportRequirements:
    streaming_text: bool = True
    client_tool_calls: bool = False
    usage_reporting: bool = False
    cancellation: bool = False


@dataclass(frozen=True)
class ProfessionalProviderResolution:
    backend_id: str
    adapter: ProfessionalProviderAdapter
    readiness: ClineSidecarReadiness
    capabilities: ProviderModelCapabilities


ReadinessProbe = Callable[[], ClineSidecarReadiness]
AdapterFactory = Callable[[], ProfessionalProviderAdapter]


def resolve_cline_professional_transport(
    *,
    capabilities: ProviderModelCapabilities,
    requirements: ProfessionalTransportRequirements,
    readiness_probe: ReadinessProbe,
    adapter_factory: AdapterFactory,
) -> ProfessionalProviderResolution:
    """Select the Cline transport only with explicit host + model evidence.

    Readiness proves that the pinned optional sidecar can launch on this host.
    ``ProviderModelCapabilities`` proves provider/model semantics. Neither fact is
    allowed to stand in for the other.
    """
    if not isinstance(capabilities, ProviderModelCapabilities):
        raise TypeError("capabilities must be ProviderModelCapabilities")
    if not isinstance(requirements, ProfessionalTransportRequirements):
        raise TypeError("requirements must be ProfessionalTransportRequirements")
    if not callable(readiness_probe):
        raise TypeError("readiness_probe must be callable")
    if not callable(adapter_factory):
        raise TypeError("adapter_factory must be callable")

    readiness = readiness_probe()
    if not isinstance(readiness, ClineSidecarReadiness):
        raise TypeError("readiness_probe must return ClineSidecarReadiness")
    if readiness.status is not ClineSidecarReadinessStatus.READY:
        raise ProfessionalProviderResolutionError(
            f"Cline professional transport is not ready: {readiness.status.value}: {readiness.reason}"
        )

    required_claims: dict[str, CapabilityClaim] = {}
    if requirements.streaming_text:
        required_claims["streaming_text"] = capabilities.streaming_text
    if requirements.client_tool_calls:
        required_claims["client_tool_calls"] = capabilities.client_tool_calls
    if requirements.usage_reporting:
        required_claims["usage_reporting"] = capabilities.usage_reporting
    if requirements.cancellation:
        required_claims["cancellation"] = capabilities.cancellation

    unsupported = [name for name, claim in required_claims.items() if claim.support is CapabilitySupport.UNSUPPORTED]
    unproven = [name for name, claim in required_claims.items() if claim.support is not CapabilitySupport.SUPPORTED]
    if unsupported:
        raise ProfessionalProviderResolutionError(
            "requested professional capabilities are unsupported: " + ", ".join(sorted(unsupported))
        )
    if unproven:
        raise ProfessionalProviderResolutionError(
            "requested professional capabilities are not proven SUPPORTED: " + ", ".join(sorted(unproven))
        )

    adapter = adapter_factory()
    if not isinstance(adapter, ProfessionalProviderAdapter):
        # Protocol runtime checks are unavailable unless marked runtime_checkable;
        # validate the required provider-I/O surface directly without granting authority.
        for name in ("stream_turn", "continue_with_tool_result", "cancel"):
            if not callable(getattr(adapter, name, None)):
                raise TypeError("adapter_factory returned an invalid ProfessionalProviderAdapter")

    return ProfessionalProviderResolution(
        backend_id="cline-llms-sidecar",
        adapter=adapter,
        readiness=readiness,
        capabilities=capabilities,
    )
