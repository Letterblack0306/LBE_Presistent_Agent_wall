from __future__ import annotations

import pytest

from lbe_guard_inspector.cline_sidecar_readiness import (
    ClineSidecarReadiness,
    ClineSidecarReadinessStatus,
)
from lbe_guard_inspector.professional_provider_resolver import (
    ProfessionalProviderResolutionError,
    ProfessionalTransportRequirements,
    resolve_cline_professional_transport,
)
from lbe_guard_inspector.provider_capabilities import (
    CapabilityClaim,
    CapabilitySupport,
    ProviderModelCapabilities,
    ProviderProtocolFamily,
)


class FakeAdapter:
    def stream_turn(self, request):
        return ()

    def continue_with_tool_result(self, request, result):
        return ()

    def cancel(self):
        return None


def _readiness(status=ClineSidecarReadinessStatus.READY):
    return ClineSidecarReadiness(
        status=status,
        node_version="v24.15.0",
        bridge_path="C:/bridge.mjs",
        package_manifest_path="C:/package.json",
        cline_package_version="0.0.73",
        reason="ready" if status is ClineSidecarReadinessStatus.READY else "not ready",
    )


def _claim(support: CapabilitySupport) -> CapabilityClaim:
    return CapabilityClaim(
        support=support,
        reason="conditional" if support is CapabilitySupport.CONDITIONAL else None,
        source="test-evidence",
    )


def _caps(**claims):
    return ProviderModelCapabilities(
        provider_id="openai-compatible",
        model_id="model-a",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        protocol_family=ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
        protocol_evidence="test",
        **claims,
    )


def test_ready_backend_and_supported_required_features_resolve() -> None:
    adapter = FakeAdapter()
    result = resolve_cline_professional_transport(
        capabilities=_caps(
            streaming_text=_claim(CapabilitySupport.SUPPORTED),
            client_tool_calls=_claim(CapabilitySupport.SUPPORTED),
        ),
        requirements=ProfessionalTransportRequirements(streaming_text=True, client_tool_calls=True),
        readiness_probe=lambda: _readiness(),
        adapter_factory=lambda: adapter,
    )
    assert result.backend_id == "cline-llms-sidecar"
    assert result.adapter is adapter
    assert result.readiness.ready is True


def test_unready_backend_fails_before_adapter_construction() -> None:
    built = False

    def factory():
        nonlocal built
        built = True
        return FakeAdapter()

    with pytest.raises(ProfessionalProviderResolutionError, match="not ready"):
        resolve_cline_professional_transport(
            capabilities=_caps(streaming_text=_claim(CapabilitySupport.SUPPORTED)),
            requirements=ProfessionalTransportRequirements(),
            readiness_probe=lambda: _readiness(ClineSidecarReadinessStatus.UNAVAILABLE),
            adapter_factory=factory,
        )
    assert built is False


def test_unknown_required_capability_fails_closed() -> None:
    with pytest.raises(ProfessionalProviderResolutionError, match="not proven SUPPORTED"):
        resolve_cline_professional_transport(
            capabilities=_caps(),
            requirements=ProfessionalTransportRequirements(streaming_text=True),
            readiness_probe=lambda: _readiness(),
            adapter_factory=FakeAdapter,
        )


def test_conditional_required_capability_fails_closed() -> None:
    with pytest.raises(ProfessionalProviderResolutionError, match="not proven SUPPORTED"):
        resolve_cline_professional_transport(
            capabilities=_caps(streaming_text=_claim(CapabilitySupport.CONDITIONAL)),
            requirements=ProfessionalTransportRequirements(streaming_text=True),
            readiness_probe=lambda: _readiness(),
            adapter_factory=FakeAdapter,
        )


def test_unsupported_required_capability_reports_unsupported() -> None:
    with pytest.raises(ProfessionalProviderResolutionError, match="unsupported: client_tool_calls"):
        resolve_cline_professional_transport(
            capabilities=_caps(
                streaming_text=_claim(CapabilitySupport.SUPPORTED),
                client_tool_calls=_claim(CapabilitySupport.UNSUPPORTED),
            ),
            requirements=ProfessionalTransportRequirements(client_tool_calls=True),
            readiness_probe=lambda: _readiness(),
            adapter_factory=FakeAdapter,
        )


def test_unrequested_unknown_capabilities_do_not_block_resolution() -> None:
    result = resolve_cline_professional_transport(
        capabilities=_caps(streaming_text=_claim(CapabilitySupport.SUPPORTED)),
        requirements=ProfessionalTransportRequirements(
            streaming_text=True,
            client_tool_calls=False,
            usage_reporting=False,
            cancellation=False,
        ),
        readiness_probe=lambda: _readiness(),
        adapter_factory=FakeAdapter,
    )
    assert result.backend_id == "cline-llms-sidecar"


def test_adapter_factory_must_return_required_provider_io_surface() -> None:
    with pytest.raises(TypeError, match="invalid ProfessionalProviderAdapter"):
        resolve_cline_professional_transport(
            capabilities=_caps(streaming_text=_claim(CapabilitySupport.SUPPORTED)),
            requirements=ProfessionalTransportRequirements(),
            readiness_probe=lambda: _readiness(),
            adapter_factory=lambda: object(),
        )
