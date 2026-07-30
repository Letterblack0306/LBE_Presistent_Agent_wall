from __future__ import annotations

import pytest

from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.reasoning_runtime import build_openai_compatible_controller
from lbe_guard_inspector.request_controller import LBERequestController


def provider_config() -> ProviderConfig:
    return ProviderConfig(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="local-model",
        timeout_seconds=30,
    )


def test_composition_builds_controller_without_invoking_provider(monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("transport must not run during composition")

    monkeypatch.setattr("urllib.request.urlopen", fail)

    controller = build_openai_compatible_controller(provider_config=provider_config())

    assert isinstance(controller, LBERequestController)
    assert calls == []


def test_composition_accepts_explicit_controller_dependencies():
    context = object()

    controller = build_openai_compatible_controller(
        provider_config=provider_config(),
        controller_kwargs={"context": context},
    )

    assert controller._context is context


def test_composition_rejects_backend_override():
    with pytest.raises(ValueError, match="must not override backend"):
        build_openai_compatible_controller(
            provider_config=provider_config(),
            controller_kwargs={"backend": object()},
        )


def test_composition_requires_typed_provider_config():
    with pytest.raises(TypeError, match="ProviderConfig"):
        build_openai_compatible_controller(provider_config={})
