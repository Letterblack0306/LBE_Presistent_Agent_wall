"""Compose a professional provider transport from persistent LBE session identity.

This module is the professional provider/session entrypoint. It deliberately
reads the existing persisted provider/model identity without transferring
workspace roots, permissions, runtime policy, or tool authority into the
provider adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .cline_sidecar_adapter import ClineSidecarProviderAdapter
from .cline_sidecar_readiness import ClineSidecarReadiness, probe_cline_sidecar_readiness
from .memory import SessionState
from .professional_provider_events import ProfessionalProviderAdapter
from .professional_provider_resolver import (
    ProfessionalProviderResolution,
    ProfessionalTransportRequirements,
    resolve_cline_professional_transport,
)
from .provider_capabilities import ProviderModelCapabilities


class ProfessionalSessionProviderError(RuntimeError):
    """Raised when persisted session/provider composition is inconsistent."""


@dataclass(frozen=True)
class ProfessionalSessionProvider:
    session_id: str
    provider_id: str
    model_id: str
    resolution: ProfessionalProviderResolution

    @property
    def adapter(self) -> ProfessionalProviderAdapter:
        return self.resolution.adapter


ReadinessProbe = Callable[[], ClineSidecarReadiness]
AdapterFactory = Callable[[], ProfessionalProviderAdapter]


def compose_professional_session_provider(
    *,
    session_state: SessionState,
    capabilities: ProviderModelCapabilities,
    requirements: ProfessionalTransportRequirements,
    provider_config: Mapping[str, object],
    readiness_probe: ReadinessProbe | None = None,
    adapter_factory: AdapterFactory | None = None,
) -> ProfessionalSessionProvider:
    """Bind one persisted session to an evidence-backed professional transport.

    Session state remains the source of truth for provider/model identity.
    Provider config may contain credentials and transport options only; it must
    identify the same provider/model. No workspace or policy fields are copied
    into the adapter.
    """
    if not isinstance(session_state, SessionState):
        raise TypeError("session_state must be SessionState")
    if not isinstance(capabilities, ProviderModelCapabilities):
        raise TypeError("capabilities must be ProviderModelCapabilities")
    if not isinstance(requirements, ProfessionalTransportRequirements):
        raise TypeError("requirements must be ProfessionalTransportRequirements")
    if not isinstance(provider_config, Mapping):
        raise TypeError("provider_config must be a mapping")

    provider_id = session_state.provider_id
    model_id = session_state.provider_model
    if provider_id is None or model_id is None:
        raise ProfessionalSessionProviderError(
            "persistent session must declare provider_id and provider_model before professional transport composition"
        )
    if capabilities.provider_id != provider_id:
        raise ProfessionalSessionProviderError("capability provider_id does not match persistent session provider_id")
    if capabilities.model_id != model_id:
        raise ProfessionalSessionProviderError("capability model_id does not match persistent session provider_model")

    configured_provider = provider_config.get("providerId")
    configured_model = provider_config.get("modelId")
    if configured_provider != provider_id:
        raise ProfessionalSessionProviderError("provider_config providerId does not match persistent session provider_id")
    if configured_model != model_id:
        raise ProfessionalSessionProviderError("provider_config modelId does not match persistent session provider_model")

    forbidden = {
        "workspace_root",
        "workspaceRoot",
        "project_workspace_id",
        "session_id",
        "mode",
        "permission",
        "runtime_policy",
        "permission_policy_id",
        "evidence_policy_id",
        "tool_dispatcher",
        "authorization_resolver",
    }
    leaked = sorted(key for key in provider_config if key in forbidden)
    if leaked:
        raise ProfessionalSessionProviderError(
            "provider_config contains runtime-authority fields: " + ", ".join(leaked)
        )

    probe = readiness_probe or probe_cline_sidecar_readiness
    factory = adapter_factory or (lambda: ClineSidecarProviderAdapter(provider_config=provider_config))
    resolution = resolve_cline_professional_transport(
        capabilities=capabilities,
        requirements=requirements,
        readiness_probe=probe,
        adapter_factory=factory,
    )
    return ProfessionalSessionProvider(
        session_id=session_state.session_id,
        provider_id=provider_id,
        model_id=model_id,
        resolution=resolution,
    )
