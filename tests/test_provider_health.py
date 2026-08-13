from __future__ import annotations

from lbe_guard_inspector.provider_capabilities import CapabilitySupport, ProviderProtocolFamily
from lbe_guard_inspector.provider_health import check_provider_health
from lbe_guard_inspector.provider_registry import (
    ProviderCapabilities,
    ProviderDescriptor,
    ProviderHandle,
    ProviderRegistry,
)
from lbe_guard_inspector.reasoning_provider import ProviderConfig


class _Backend:
    def __init__(self) -> None:
        self.requests = []

    def plan(self, request):
        self.requests.append(request)
        return object()

    def explain(self, request):  # pragma: no cover - health probe only plans
        raise AssertionError("provider health must not request explanation")


def test_provider_health_probes_registered_backend_without_workspace_authority() -> None:
    backend = _Backend()

    def factory(config: ProviderConfig) -> ProviderHandle:
        return ProviderHandle(
            descriptor=ProviderDescriptor(
                provider_id="test-provider",
                model_id=config.model,
                capabilities=ProviderCapabilities(structured_output=True),
            ),
            backend=backend,
        )

    registry = ProviderRegistry({"test-provider": factory})
    result = check_provider_health(
        provider_id="test-provider",
        provider_config=ProviderConfig(
            endpoint="http://provider/v1/chat/completions",
            model="test-model",
            timeout_seconds=5,
        ),
        provider_registry=registry,
    )

    assert result.status == "READY"
    assert result.provider_id == "test-provider"
    assert result.model_id == "test-model"
    assert result.capabilities.structured_output is True
    assert result.professional_capabilities.protocol_family is ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT
    assert result.professional_capabilities.client_tool_calls.support is CapabilitySupport.UNKNOWN
    assert result.professional_capabilities.streaming_text.support is CapabilitySupport.UNKNOWN
    assert not hasattr(result.professional_capabilities, "permission")
    assert not hasattr(result.professional_capabilities, "authorization")
    assert len(backend.requests) == 1
    request = backend.requests[0]
    assert request.workspace_identity == {"workspace_id": "provider-check"}
    assert request.approved_guard_ids == ()
    assert request.approved_tools == ()


def test_provider_health_legacy_adapter_flags_do_not_become_model_capability_claims() -> None:
    backend = _Backend()

    def factory(config: ProviderConfig) -> ProviderHandle:
        return ProviderHandle(
            descriptor=ProviderDescriptor(
                provider_id="openai-compatible",
                model_id=config.model,
                capabilities=ProviderCapabilities(
                    streaming=False,
                    tool_calls=False,
                    structured_output=True,
                    context_limit=8192,
                ),
            ),
            backend=backend,
        )

    result = check_provider_health(
        provider_id="openai-compatible",
        provider_config=ProviderConfig(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="selected-model",
            timeout_seconds=5,
        ),
        provider_registry=ProviderRegistry({"openai-compatible": factory}),
    )

    assert result.capabilities.streaming is False
    assert result.capabilities.tool_calls is False
    assert result.professional_capabilities.streaming_text.support is CapabilitySupport.UNKNOWN
    assert result.professional_capabilities.client_tool_calls.support is CapabilitySupport.UNKNOWN
    assert result.professional_capabilities.context_window == 8192
