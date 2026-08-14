from __future__ import annotations

import pytest

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadiness,
    ClineSidecarReadinessStatus,
)
from lbe_guard_inspector.memory import SessionState
from lbe_guard_inspector.professional_provider_resolver import ProfessionalTransportRequirements
from lbe_guard_inspector.professional_session_provider import (
    ProfessionalSessionProviderError,
    compose_professional_session_provider,
)
from lbe_guard_inspector.provider_capabilities import (
    CapabilityClaim,
    CapabilitySupport,
    ProviderModelCapabilities,
    ProviderProtocolFamily,
)


class _Adapter:
    def stream_turn(self, request):
        return ()

    def continue_with_tool_result(self, request, result):
        return ()

    def cancel(self):
        return None


def _session(**overrides) -> SessionState:
    values = dict(
        session_id="session-1",
        project_workspace_id="workspace-1",
        canonical_workspace_root="C:/work/example",
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
        provider_id="openai-compatible",
        provider_model="model-a",
        permission_policy_id="policy-1",
        evidence_policy_id="evidence-1",
    )
    values.update(overrides)
    return SessionState(**values)


def _capabilities(**claims) -> ProviderModelCapabilities:
    supported = CapabilityClaim(
        support=CapabilitySupport.SUPPORTED,
        reason="test evidence",
        source="test",
    )
    values = dict(
        provider_id="openai-compatible",
        model_id="model-a",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        protocol_family=ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
        protocol_evidence="test",
        streaming_text=supported,
        client_tool_calls=supported,
    )
    values.update(claims)
    return ProviderModelCapabilities(**values)


def _ready() -> ClineSidecarReadiness:
    return ClineSidecarReadiness(
        status=ClineSidecarReadinessStatus.READY,
        node_version="v24.15.0",
        bridge_path="C:/bridge/bridge.mjs",
        package_manifest_path="C:/bridge/package.json",
        cline_package_version="0.0.73",
        reason="ready",
    )


def test_composes_from_persisted_provider_identity_without_runtime_authority() -> None:
    made = []

    def factory():
        made.append(True)
        return _Adapter()

    composed = compose_professional_session_provider(
        session_state=_session(),
        capabilities=_capabilities(),
        requirements=ProfessionalTransportRequirements(streaming_text=True, client_tool_calls=True),
        provider_config={
            "providerId": "openai-compatible",
            "modelId": "model-a",
            "baseUrl": "http://127.0.0.1:1234/v1",
        },
        readiness_probe=_ready,
        adapter_factory=factory,
    )

    assert made == [True]
    assert composed.session_id == "session-1"
    assert composed.provider_id == "openai-compatible"
    assert composed.model_id == "model-a"
    assert composed.resolution.backend_id == "cline-llms-sidecar"


def test_missing_persisted_provider_identity_fails_closed() -> None:
    with pytest.raises(ProfessionalSessionProviderError, match="provider_id and provider_model"):
        compose_professional_session_provider(
            session_state=_session(provider_id=None, provider_model=None),
            capabilities=_capabilities(),
            requirements=ProfessionalTransportRequirements(),
            provider_config={"providerId": "openai-compatible", "modelId": "model-a"},
            readiness_probe=_ready,
            adapter_factory=_Adapter,
        )


def test_capability_identity_must_match_persisted_session() -> None:
    with pytest.raises(ProfessionalSessionProviderError, match="capability provider_id"):
        compose_professional_session_provider(
            session_state=_session(),
            capabilities=_capabilities(provider_id="anthropic"),
            requirements=ProfessionalTransportRequirements(),
            provider_config={"providerId": "openai-compatible", "modelId": "model-a"},
            readiness_probe=_ready,
            adapter_factory=_Adapter,
        )


def test_provider_config_identity_must_match_persisted_session() -> None:
    with pytest.raises(ProfessionalSessionProviderError, match="provider_config modelId"):
        compose_professional_session_provider(
            session_state=_session(),
            capabilities=_capabilities(),
            requirements=ProfessionalTransportRequirements(),
            provider_config={"providerId": "openai-compatible", "modelId": "other-model"},
            readiness_probe=_ready,
            adapter_factory=_Adapter,
        )


@pytest.mark.parametrize(
    "field",
    [
        "workspace_root",
        "project_workspace_id",
        "session_id",
        "mode",
        "permission",
        "runtime_policy",
        "permission_policy_id",
        "evidence_policy_id",
        "tool_dispatcher",
        "authorization_resolver",
    ],
)
def test_provider_config_rejects_runtime_authority_fields(field: str) -> None:
    config = {"providerId": "openai-compatible", "modelId": "model-a", field: "forbidden"}
    with pytest.raises(ProfessionalSessionProviderError, match="runtime-authority fields"):
        compose_professional_session_provider(
            session_state=_session(),
            capabilities=_capabilities(),
            requirements=ProfessionalTransportRequirements(),
            provider_config=config,
            readiness_probe=_ready,
            adapter_factory=_Adapter,
        )


def test_unproven_requested_capability_still_fails_through_resolver() -> None:
    unknown = CapabilityClaim(
        support=CapabilitySupport.UNKNOWN,
        reason="not proven",
        source="test",
    )
    with pytest.raises(RuntimeError, match="not proven SUPPORTED"):
        compose_professional_session_provider(
            session_state=_session(),
            capabilities=_capabilities(client_tool_calls=unknown),
            requirements=ProfessionalTransportRequirements(streaming_text=True, client_tool_calls=True),
            provider_config={"providerId": "openai-compatible", "modelId": "model-a"},
            readiness_probe=_ready,
            adapter_factory=_Adapter,
        )
