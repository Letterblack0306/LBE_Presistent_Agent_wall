from __future__ import annotations

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
    assert len(backend.requests) == 1
    request = backend.requests[0]
    assert request.workspace_identity == {"workspace_id": "provider-check"}
    assert request.approved_guard_ids == ()
    assert request.approved_tools == ()


def test_provider_resolution_uses_matching_saved_profile_not_unrelated_active(tmp_path):
    from lbe_guard_inspector.cli import resolve_provider_config
    from lbe_guard_inspector.user_state import ProviderProfile, UserStateStore

    state = UserStateStore(tmp_path)
    state.save_profile("local", ProviderProfile(
        provider_id="lmstudio", model="local-1",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        timeout_seconds=10,
    ), activate=True)
    state.save_profile("cloud", ProviderProfile(
        provider_id="openai", model="cloud-1",
        endpoint="https://api.openai.com/v1/chat/completions",
        timeout_seconds=20,
    ))
    name, config = resolve_provider_config(provider_config=None, state_root=str(tmp_path),
                                           expected_provider_id="openai")
    assert name == "cloud"
    assert config.provider_id == "openai"
    assert config.model == "cloud-1"
    assert state.active_profile_name() == "local"


def test_provider_resolution_does_not_claim_missing_provider_is_configured(tmp_path):
    import pytest
    from lbe_guard_inspector.cli import resolve_provider_config
    from lbe_guard_inspector.user_state import ProviderProfile, UserStateStore

    state = UserStateStore(tmp_path)
    state.save_profile("local", ProviderProfile(
        provider_id="lmstudio", model="local-1",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        timeout_seconds=10,
    ), activate=True)
    with pytest.raises(ValueError, match="provider anthropic is not configured"):
        resolve_provider_config(provider_config=None, state_root=str(tmp_path),
                                expected_provider_id="anthropic")
    assert state.active_profile_name() == "local"
