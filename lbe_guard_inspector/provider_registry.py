"""Provider registry for replaceable reasoning backends.

Provider metadata describes transport/model capabilities only. It never grants
workspace permissions, guard authority, validation authority, or completion
truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .coding_reasoning_provider import ToolAwareOpenAICompatibleReasoningBackend
from .cline_reasoning_provider import ClineReasoningBackend
from .first_party_reasoning_provider import AnthropicReasoningBackend, GeminiReasoningBackend, require_api_key
from .professional_capabilities import CapabilitySupport
from .provider_capability_discovery import ProviderModelCapabilitySnapshot
from .professional_provider_events import ProviderProtocolFamily
from .reasoning_contracts import ReasoningBackend
from .reasoning_provider import ProviderConfig


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


ProviderFactory = Callable[[ProviderConfig], ProviderHandle]


class ProviderRegistry:
    """Explicit registry of reasoning provider factories.

    Registration is composition metadata only. Runtime policy/capability
    authorization remains owned by LBE's existing mode/governance layers.
    """

    def __init__(self, factories: Mapping[str, ProviderFactory] | None = None) -> None:
        self._factories: dict[str, ProviderFactory] = {}
        for provider_id, factory in dict(factories or {}).items():
            self.register(provider_id, factory)

    def register(self, provider_id: str, factory: ProviderFactory) -> None:
        clean_id = _provider_id(provider_id)
        if not callable(factory):
            raise TypeError("provider factory must be callable")
        if clean_id in self._factories:
            raise ValueError(f"provider already registered: {clean_id}")
        self._factories[clean_id] = factory

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

    def build(self, *, provider_id: str, config: ProviderConfig) -> ProviderHandle:
        clean_id = _provider_id(provider_id)
        if not isinstance(config, ProviderConfig):
            raise TypeError("config must be a ProviderConfig")
        factory = self._factories.get(clean_id)
        if factory is None:
            raise KeyError(f"provider is not registered: {clean_id}")
        handle = factory(config)
        if not isinstance(handle, ProviderHandle):
            raise TypeError("provider factory must return ProviderHandle")
        if handle.descriptor.provider_id != clean_id:
            raise ValueError("provider factory descriptor does not match registered provider_id")
        if handle.descriptor.model_id != config.model.strip():
            raise ValueError("provider factory descriptor model_id does not match config model")
        return handle


def openai_compatible_factory(config: ProviderConfig) -> ProviderHandle:
    return ProviderHandle(
        descriptor=ProviderDescriptor(
            provider_id="openai-compatible",
            model_id=config.model.strip(),
            capabilities=ProviderCapabilities(
                streaming=False,
                tool_calls=True,
                structured_output=True,
                context_limit=None,
            ),
            protocol_family=ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
        ),
        backend=ToolAwareOpenAICompatibleReasoningBackend(config=config),
    )


def openai_factory(config: ProviderConfig) -> ProviderHandle:
    require_api_key(config, "openai")
    return _handle("openai", config, ToolAwareOpenAICompatibleReasoningBackend(config=config))


def anthropic_factory(config: ProviderConfig) -> ProviderHandle:
    return _handle("anthropic", config, AnthropicReasoningBackend(config=config))


def gemini_factory(config: ProviderConfig) -> ProviderHandle:
    return _handle("gemini", config, GeminiReasoningBackend(config=config))


def cline_factory(provider_id: str) -> ProviderFactory:
    def factory(config: ProviderConfig) -> ProviderHandle:
        return _handle(provider_id, config, ClineReasoningBackend(provider_id=provider_id, config=config))
    return factory


def _handle(provider_id: str, config: ProviderConfig, backend: ReasoningBackend) -> ProviderHandle:
    return ProviderHandle(
        descriptor=ProviderDescriptor(
            provider_id=provider_id,
            model_id=config.model.strip(),
            capabilities=ProviderCapabilities(
                streaming=False,
                tool_calls=True,
                structured_output=True,
                context_limit=None,
            ),
        ),
        backend=backend,
    )


def default_provider_registry() -> ProviderRegistry:
    """Return built-in provider adapters without reading environment/runtime state."""
    return ProviderRegistry({
        "openai-compatible": openai_compatible_factory,
        "openai": openai_factory,
        "anthropic": anthropic_factory,
        "gemini": gemini_factory,
        "openai-native": cline_factory("openai-native"),
        "vertex": cline_factory("vertex"),
        "bedrock": cline_factory("bedrock"),
        "ollama": cline_factory("ollama"),
        "lmstudio": cline_factory("lmstudio"),
        "openrouter": cline_factory("openrouter"),
        "opencode": cline_factory("opencode"),
    })


def normalize_provider_descriptor(snapshot: ProviderModelCapabilitySnapshot) -> ProviderDescriptor:
    """Convert configuration/evidence discovery into a provider-neutral descriptor.

    Technical capability claims remain separate from LBE authorization. Unknown
    claims are never promoted to supported execution features.
    """
    if not isinstance(snapshot, ProviderModelCapabilitySnapshot):
        raise TypeError("snapshot must be ProviderModelCapabilitySnapshot")
    tool_calls = snapshot.capabilities.claim("client_tool_calls").support is CapabilitySupport.SUPPORTED
    streaming = snapshot.capabilities.claim("streaming_text").support is CapabilitySupport.SUPPORTED
    return ProviderDescriptor(
        provider_id=snapshot.capabilities.provider_id,
        model_id=snapshot.capabilities.model_id,
        capabilities=ProviderCapabilities(
            streaming=streaming,
            tool_calls=tool_calls,
            structured_output=True,
            context_limit=snapshot.context_window,
        ),
        protocol_family=snapshot.capabilities.protocol_family,
    )


def _provider_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("provider_id must be a non-empty string")
    return value.strip()
