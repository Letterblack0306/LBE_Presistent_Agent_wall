"""Explicit composition root for bounded provider-neutral reasoning."""
from __future__ import annotations

from typing import Any

from .provider_registry import ProviderHandle, ProviderRegistry, default_provider_registry
from .reasoning_provider import ProviderConfig
from .request_controller import LBERequestController


def build_provider_controller(
    *,
    provider_id: str,
    provider_config: ProviderConfig,
    provider_registry: ProviderRegistry | None = None,
    controller_kwargs: dict[str, Any] | None = None,
) -> tuple[LBERequestController, ProviderHandle]:
    """Compose one registered provider backend and the existing controller.

    This is dependency composition only. Provider selection does not grant
    workspace authority or alter mode, permission, guard, validation, or
    completion policy.
    """
    if not isinstance(provider_config, ProviderConfig):
        raise TypeError("provider_config must be a ProviderConfig")
    registry = provider_registry or default_provider_registry()
    if not isinstance(registry, ProviderRegistry):
        raise TypeError("provider_registry must be a ProviderRegistry")
    options = dict(controller_kwargs or {})
    if "backend" in options:
        raise ValueError("controller_kwargs must not override backend")
    handle = registry.build(provider_id=provider_id, config=provider_config)
    controller = LBERequestController(backend=handle.backend, **options)
    return controller, handle


def build_openai_compatible_controller(
    *,
    provider_config: ProviderConfig,
    controller_kwargs: dict[str, Any] | None = None,
) -> LBERequestController:
    """Backward-compatible composition wrapper for the existing provider."""
    controller, _ = build_provider_controller(
        provider_id="openai-compatible",
        provider_config=provider_config,
        controller_kwargs=controller_kwargs,
    )
    return controller
