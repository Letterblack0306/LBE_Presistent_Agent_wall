"""Provider registry for replaceable reasoning backends.

Provider metadata describes transport/model capabilities only. It never grants
workspace permissions, guard authority, validation authority, or completion
truth.

Reference-derived design boundary:
- Cline SDK package separation:
  cline/cline@9a2512bb9835869d74774da99708a7f9d80b0fe8
  sdk/packages/README.md
- OpenCode registry separation:
  anomalyco/opencode@ebb7b76eca82342642c78645109e865614533827
  packages/opencode/src/tool/registry.ts

Those references inform composition only. LBE remains the authority owner.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable, Mapping

from .coding_reasoning_provider import ToolAwareOpenAICompatibleReasoningBackend
from .first_party_reasoning_provider import (
    AnthropicReasoningBackend,
    GeminiReasoningBackend,
    require_api_key,
)
from .professional_capabilities import CapabilitySupport
from .provider_capability_discovery import (
    ProviderModelCapabilitySnapshot,
    discover_provider_model_capabilities,
)
from .professional_provider_events import ProviderProtocolFamily
from .reasoning_contracts import ReasoningBackend
from .reasoning_provider import ProviderConfig


NATIVE_LBE_ENGINE_ID = "native-lbe"
CLINE_ENGINE_ID = "cline"


class ReasoningEngineUnavailableError(RuntimeError):
    """Selected reasoning engine cannot be loaded.

    This is intentionally distinct from provider fallback. Callers must surface
    the selected engine failure rather than silently selecting another engine.
    """


@dataclass(frozen=True)
class ProviderCapabilities:
    streaming: bool = False
    tool_calls: bool = False
    structured_output: bool = True
    context_limit: int | None = None

    def __post_init__(self) -> None:
        if self.context_limit is not None and self.context_limit <= 0:
            raise ValueError("provider context_limit must be positive when supplied")


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    model_id: str
    capabilities: ProviderCapabilities
    protocol_family: ProviderProtocolFamily = ProviderProtocolFamily.UNKNOWN

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise ValueError("provider_id must be a non-empty string")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("model_id must be a non-empty string")
        if not isinstance(self.protocol_family, ProviderProtocolFamily):
            raise TypeError("protocol_family must be ProviderProtocolFamily")


@dataclass(frozen=True)
class ProviderHandle:
    descriptor: ProviderDescriptor
    backend: ReasoningBackend
    engine_id: str = NATIVE_LBE_ENGINE_ID

    def __post_init__(self) -> None:
        _engine_id(self.engine_id)


ProviderFactory = Callable[[ProviderConfig], ProviderHandle]


@dataclass(frozen=True)
class EngineProviderBinding:
    """One explicit reasoning-engine/provider binding.

    A provider may have more than one engine binding. One binding may be the
    default, but selection of a non-default binding is always explicit.
    """

    engine_id: str
    provider_id: str
    factory: ProviderFactory
    default: bool = False

    def __post_init__(self) -> None:
        _engine_id(self.engine_id)
        _provider_id(self.provider_id)
        if not callable(self.factory):
            raise TypeError("provider factory must be callable")


class ProviderRegistry:
    """Explicit registry of engine/provider factories.

    Registration is composition metadata only. Runtime policy/capability
    authorization remains owned by LBE's existing mode/governance layers.

    The legacy provider->factory constructor remains supported and registers
    native-LBE default bindings. New code should use register_binding().
    """

    def __init__(self, factories: Mapping[str, ProviderFactory] | None = None) -> None:
        self._bindings: dict[tuple[str, str], EngineProviderBinding] = {}
        self._defaults: dict[str, str] = {}
        for provider_id, factory in dict(factories or {}).items():
            self.register(provider_id, factory)

    def register(self, provider_id: str, factory: ProviderFactory) -> None:
        """Backward-compatible native-LBE registration."""
        self.register_binding(
            engine_id=NATIVE_LBE_ENGINE_ID,
            provider_id=provider_id,
            factory=factory,
            default=True,
        )

    def register_binding(
        self,
        *,
        engine_id: str,
        provider_id: str,
        factory: ProviderFactory,
        default: bool = False,
    ) -> None:
        binding = EngineProviderBinding(
            engine_id=_engine_id(engine_id),
            provider_id=_provider_id(provider_id),
            factory=factory,
            default=bool(default),
        )
        key = (binding.provider_id, binding.engine_id)
        if key in self._bindings:
            raise ValueError(
                f"engine/provider binding already registered: "
                f"{binding.engine_id}/{binding.provider_id}"
            )
        if binding.default and binding.provider_id in self._defaults:
            raise ValueError(
                f"default engine already registered for provider: "
                f"{binding.provider_id}"
            )
        self._bindings[key] = binding
        if binding.default:
            self._defaults[binding.provider_id] = binding.engine_id

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted({provider_id for provider_id, _ in self._bindings}))

    def engine_ids(self) -> tuple[str, ...]:
        return tuple(sorted({engine_id for _, engine_id in self._bindings}))

    def engines_for_provider(self, provider_id: str) -> tuple[str, ...]:
        clean_id = _provider_id(provider_id)
        return tuple(
            sorted(
                engine_id
                for registered_provider, engine_id in self._bindings
                if registered_provider == clean_id
            )
        )

    def bindings(self) -> tuple[EngineProviderBinding, ...]:
        return tuple(
            self._bindings[key]
            for key in sorted(self._bindings)
        )

    def build(
        self,
        *,
        provider_id: str,
        config: ProviderConfig,
        engine_id: str | None = None,
    ) -> ProviderHandle:
        clean_provider = _provider_id(provider_id)
        if not isinstance(config, ProviderConfig):
            raise TypeError("config must be a ProviderConfig")
        selected_engine = self._resolve_engine(
            provider_id=clean_provider,
            engine_id=engine_id,
        )
        binding = self._bindings.get((clean_provider, selected_engine))
        if binding is None:
            raise KeyError(
                f"engine/provider binding is not registered: "
                f"{selected_engine}/{clean_provider}"
            )
        handle = binding.factory(config)
        if not isinstance(handle, ProviderHandle):
            raise TypeError("provider factory must return ProviderHandle")
        if handle.descriptor.provider_id != clean_provider:
            raise ValueError(
                "provider factory descriptor does not match registered provider_id"
            )
        if handle.descriptor.model_id != config.model.strip():
            raise ValueError(
                "provider factory descriptor model_id does not match config model"
            )
        if handle.engine_id != selected_engine:
            raise ValueError(
                "provider factory engine_id does not match selected engine binding"
            )
        return handle

    def _resolve_engine(self, *, provider_id: str, engine_id: str | None) -> str:
        if engine_id is not None:
            return _engine_id(engine_id)
        default_engine = self._defaults.get(provider_id)
        if default_engine is not None:
            return default_engine
        engines = self.engines_for_provider(provider_id)
        if not engines:
            raise KeyError(f"provider is not registered: {provider_id}")
        if len(engines) == 1:
            return engines[0]
        raise ValueError(
            f"provider has multiple engine bindings and no default: {provider_id}"
        )


def openai_compatible_factory(config: ProviderConfig) -> ProviderHandle:
    return _handle(
        "openai-compatible",
        config,
        ToolAwareOpenAICompatibleReasoningBackend(config=config),
        engine_id=NATIVE_LBE_ENGINE_ID,
    )


def native_openai_compatible_factory(provider_id: str) -> ProviderFactory:
    clean_provider = _provider_id(provider_id)

    def factory(config: ProviderConfig) -> ProviderHandle:
        return _handle(
            clean_provider,
            config,
            ToolAwareOpenAICompatibleReasoningBackend(config=config),
            engine_id=NATIVE_LBE_ENGINE_ID,
        )

    return factory


def openai_factory(config: ProviderConfig) -> ProviderHandle:
    require_api_key(config, "openai")
    return _handle(
        "openai",
        config,
        ToolAwareOpenAICompatibleReasoningBackend(config=config),
        engine_id=NATIVE_LBE_ENGINE_ID,
    )


def anthropic_factory(config: ProviderConfig) -> ProviderHandle:
    return _handle(
        "anthropic",
        config,
        AnthropicReasoningBackend(config=config),
        engine_id=NATIVE_LBE_ENGINE_ID,
    )


def gemini_factory(config: ProviderConfig) -> ProviderHandle:
    return _handle(
        "gemini",
        config,
        GeminiReasoningBackend(config=config),
        engine_id=NATIVE_LBE_ENGINE_ID,
    )


def cline_factory(provider_id: str) -> ProviderFactory:
    """Create a Cline binding without importing Cline at module import time."""
    clean_provider = _provider_id(provider_id)

    def factory(config: ProviderConfig) -> ProviderHandle:
        try:
            module = import_module(
                f"{__package__}.cline_reasoning_provider"
            )
            backend_type = getattr(module, "ClineReasoningBackend")
        except (ImportError, AttributeError) as exc:
            raise ReasoningEngineUnavailableError(
                "reasoning engine unavailable: cline"
            ) from exc
        return _handle(
            clean_provider,
            config,
            backend_type(provider_id=clean_provider, config=config),
            engine_id=CLINE_ENGINE_ID,
        )

    return factory


def _handle(
    provider_id: str,
    config: ProviderConfig,
    backend: ReasoningBackend,
    *,
    engine_id: str,
) -> ProviderHandle:
    snapshot = discover_provider_model_capabilities(
        provider_id=provider_id,
        model_id=config.model.strip(),
        endpoint=config.endpoint.strip(),
    )
    return ProviderHandle(
        descriptor=normalize_provider_descriptor(snapshot),
        backend=backend,
        engine_id=engine_id,
    )


def default_provider_registry() -> ProviderRegistry:
    """Return built-in engine/provider adapters without provider I/O.

    Cline is optional at composition time. Existing Cline-backed routes remain
    registered, while LM Studio additionally has a native OpenAI-compatible
    default binding. No provider silently falls back to another engine.
    """
    registry = ProviderRegistry()

    registry.register_binding(
        engine_id=NATIVE_LBE_ENGINE_ID,
        provider_id="openai-compatible",
        factory=openai_compatible_factory,
        default=True,
    )
    registry.register_binding(
        engine_id=NATIVE_LBE_ENGINE_ID,
        provider_id="openai",
        factory=openai_factory,
        default=True,
    )
    registry.register_binding(
        engine_id=NATIVE_LBE_ENGINE_ID,
        provider_id="anthropic",
        factory=anthropic_factory,
        default=True,
    )
    registry.register_binding(
        engine_id=NATIVE_LBE_ENGINE_ID,
        provider_id="gemini",
        factory=gemini_factory,
        default=True,
    )

    # LM Studio speaks an OpenAI-compatible protocol. Keep the existing Cline
    # route explicitly available while making the native binding the default.
    registry.register_binding(
        engine_id=NATIVE_LBE_ENGINE_ID,
        provider_id="lmstudio",
        factory=native_openai_compatible_factory("lmstudio"),
        default=True,
    )
    registry.register_binding(
        engine_id=CLINE_ENGINE_ID,
        provider_id="lmstudio",
        factory=cline_factory("lmstudio"),
    )

    for provider_id in (
        "openai-native",
        "vertex",
        "bedrock",
        "ollama",
        "openrouter",
        "opencode",
    ):
        registry.register_binding(
            engine_id=CLINE_ENGINE_ID,
            provider_id=provider_id,
            factory=cline_factory(provider_id),
            default=True,
        )

    return registry


def normalize_provider_descriptor(
    snapshot: ProviderModelCapabilitySnapshot,
) -> ProviderDescriptor:
    """Convert configuration/evidence discovery into a provider-neutral descriptor.

    Technical capability claims remain separate from LBE authorization. Unknown
    claims are never promoted to supported execution features.
    """
    if not isinstance(snapshot, ProviderModelCapabilitySnapshot):
        raise TypeError("snapshot must be ProviderModelCapabilitySnapshot")
    tool_calls = (
        snapshot.capabilities.claim("client_tool_calls").support
        is CapabilitySupport.SUPPORTED
    )
    streaming = (
        snapshot.capabilities.claim("streaming_text").support
        is CapabilitySupport.SUPPORTED
    )
    structured_output = (
        snapshot.capabilities.claim("structured_output").support
        is CapabilitySupport.SUPPORTED
    )
    return ProviderDescriptor(
        provider_id=snapshot.capabilities.provider_id,
        model_id=snapshot.capabilities.model_id,
        capabilities=ProviderCapabilities(
            streaming=streaming,
            tool_calls=tool_calls,
            structured_output=structured_output,
            context_limit=snapshot.context_window,
        ),
        protocol_family=snapshot.capabilities.protocol_family,
    )


def _provider_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("provider_id must be a non-empty string")
    return value.strip()


def _engine_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("engine_id must be a non-empty string")
    return value.strip()
