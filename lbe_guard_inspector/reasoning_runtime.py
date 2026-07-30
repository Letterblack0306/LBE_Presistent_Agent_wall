"""Explicit composition root for the bounded reasoning controller."""
from __future__ import annotations

from typing import Any

from .reasoning_provider import OpenAICompatibleReasoningBackend, ProviderConfig
from .request_controller import LBERequestController


def build_openai_compatible_controller(
    *,
    provider_config: ProviderConfig,
    controller_kwargs: dict[str, Any] | None = None,
) -> LBERequestController:
    """Compose the provider backend and controller without reading runtime state.

    This function performs dependency composition only. It does not read
    environment variables, files, CLI arguments, HTTP requests, or global
    configuration, and it does not invoke the provider or controller.
    """
    if not isinstance(provider_config, ProviderConfig):
        raise TypeError("provider_config must be a ProviderConfig")
    options = dict(controller_kwargs or {})
    if "backend" in options:
        raise ValueError("controller_kwargs must not override backend")
    backend = OpenAICompatibleReasoningBackend(config=provider_config)
    return LBERequestController(backend=backend, **options)
