from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from lbe_guard_inspector.provider_registry import (
    CLINE_ENGINE_ID,
    NATIVE_LBE_ENGINE_ID,
    EngineProviderBinding,
    ProviderCapabilities,
    ProviderDescriptor,
    ProviderHandle,
    ProviderRegistry,
    ReasoningEngineUnavailableError,
    default_provider_registry,
    normalize_provider_descriptor,
)
from lbe_guard_inspector.coding_reasoning_provider import (
    ToolAwareOpenAICompatibleReasoningBackend,
)
from lbe_guard_inspector.cline_reasoning_provider import ClineReasoningBackend
from lbe_guard_inspector.first_party_reasoning_provider import (
    AnthropicReasoningBackend,
    GeminiReasoningBackend,
)
from lbe_guard_inspector.professional_capabilities import (
    CapabilityClaim,
    CapabilitySupport,
)
from lbe_guard_inspector.provider_capability_discovery import (
    discover_provider_model_capabilities,
)
from lbe_guard_inspector.professional_provider_events import ProviderProtocolFamily
from lbe_guard_inspector.reasoning_contracts import ExplanationResult, ReasoningPlan
from lbe_guard_inspector.reasoning_provider import (
    OpenAICompatibleReasoningBackend,
    ProviderConfig,
)
from lbe_guard_inspector.reasoning_runtime import (
    build_openai_compatible_controller,
    build_provider_controller,
)
from lbe_guard_inspector.request_controller import LBERequestController


class FakeBackend:
    def plan(self, request):
        return ReasoningPlan(
            interpreted_problem="bounded",
            ambiguities=(),
            candidate_guard_ids=(),
            evidence_requests=(),
            validation_requests=(),
            explanation_focus=(),
        )

    def explain(self, request):
        return ExplanationResult(explanation="bounded")


def config(model: str = "model-a") -> ProviderConfig:
    return ProviderConfig(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model=model,
        timeout_seconds=30,
    )


def test_registry_builds_registered_provider_with_identity_and_capabilities():
    backend = FakeBackend()

    def factory(provider_config):
        return ProviderHandle(
            descriptor=ProviderDescriptor(
                provider_id="fake",
                model_id=provider_config.model,
                capabilities=ProviderCapabilities(
                    streaming=True,
                    tool_calls=True,
                    structured_output=False,
                    context_limit=8192,
                ),
            ),
            backend=backend,
        )

    registry = ProviderRegistry({"fake": factory})
    handle = registry.build(provider_id="fake", config=config())

    assert handle.backend is backend
    assert handle.engine_id == NATIVE_LBE_ENGINE_ID
    assert handle.descriptor.provider_id == "fake"
    assert handle.descriptor.model_id == "model-a"
    assert handle.descriptor.capabilities.streaming is True
    assert handle.descriptor.capabilities.tool_calls is True
    assert handle.descriptor.capabilities.context_limit == 8192


def test_registry_rejects_unknown_provider():
    with pytest.raises(KeyError, match="not registered"):
        ProviderRegistry().build(provider_id="missing", config=config())


def test_registry_rejects_duplicate_provider_registration():
    registry = ProviderRegistry(
        {
            "fake": lambda cfg: ProviderHandle(
                descriptor=ProviderDescriptor(
                    "fake", cfg.model, ProviderCapabilities()
                ),
                backend=FakeBackend(),
            )
        }
    )
    with pytest.raises(ValueError, match="already registered"):
        registry.register("fake", lambda cfg: None)


def test_registry_rejects_duplicate_engine_provider_binding():
    registry = ProviderRegistry()
    registry.register_binding(
        engine_id="engine-a",
        provider_id="fake",
        factory=lambda cfg: ProviderHandle(
            descriptor=ProviderDescriptor(
                "fake", cfg.model, ProviderCapabilities()
            ),
            backend=FakeBackend(),
            engine_id="engine-a",
        ),
        default=True,
    )
    with pytest.raises(ValueError, match="already registered"):
        registry.register_binding(
            engine_id="engine-a",
            provider_id="fake",
            factory=lambda cfg: None,
        )


def test_registry_rejects_factory_identity_mismatch():
    registry = ProviderRegistry(
        {
            "fake": lambda cfg: ProviderHandle(
                descriptor=ProviderDescriptor(
                    "other", cfg.model, ProviderCapabilities()
                ),
                backend=FakeBackend(),
            )
        }
    )
    with pytest.raises(ValueError, match="provider_id"):
        registry.build(provider_id="fake", config=config())


def test_registry_rejects_factory_model_mismatch():
    registry = ProviderRegistry(
        {
            "fake": lambda cfg: ProviderHandle(
                descriptor=ProviderDescriptor(
                    "fake", "different", ProviderCapabilities()
                ),
                backend=FakeBackend(),
            )
        }
    )
    with pytest.raises(ValueError, match="model_id"):
        registry.build(provider_id="fake", config=config())


def test_registry_rejects_factory_engine_mismatch():
    registry = ProviderRegistry()
    registry.register_binding(
        engine_id="engine-a",
        provider_id="fake",
        factory=lambda cfg: ProviderHandle(
            descriptor=ProviderDescriptor(
                "fake", cfg.model, ProviderCapabilities()
            ),
            backend=FakeBackend(),
            engine_id="engine-b",
        ),
        default=True,
    )
    with pytest.raises(ValueError, match="engine_id"):
        registry.build(provider_id="fake", config=config())


def test_provider_capabilities_validate_context_limit():
    with pytest.raises(ValueError, match="context_limit"):
        ProviderCapabilities(context_limit=0)


def test_default_registry_exposes_engine_provider_bindings():
    registry = default_provider_registry()
    handle = registry.build(provider_id="openai-compatible", config=config())

    assert registry.provider_ids() == (
        "anthropic",
        "bedrock",
        "gemini",
        "lmstudio",
        "ollama",
        "openai",
        "openai-compatible",
        "openai-native",
        "opencode",
        "openrouter",
        "vertex",
    )
    assert registry.engine_ids() == (CLINE_ENGINE_ID, NATIVE_LBE_ENGINE_ID)
    assert registry.engines_for_provider("lmstudio") == (
        CLINE_ENGINE_ID,
        NATIVE_LBE_ENGINE_ID,
    )
    assert handle.engine_id == NATIVE_LBE_ENGINE_ID
    assert handle.descriptor.provider_id == "openai-compatible"
    assert handle.descriptor.model_id == "model-a"
    assert handle.descriptor.protocol_family is ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT
    # Capabilities are unknown-by-default until typed discovery evidence proves them.
    assert handle.descriptor.capabilities.tool_calls is False
    assert handle.descriptor.capabilities.streaming is False
    assert isinstance(
        handle.backend, ToolAwareOpenAICompatibleReasoningBackend
    )


@pytest.mark.parametrize(
    ("provider_id", "backend_type"),
    [
        ("openai", ToolAwareOpenAICompatibleReasoningBackend),
        ("anthropic", AnthropicReasoningBackend),
        ("gemini", GeminiReasoningBackend),
    ],
)
def test_default_registry_builds_native_lbe_provider_adapters(
    provider_id, backend_type
):
    handle = default_provider_registry().build(
        provider_id=provider_id,
        config=ProviderConfig(
            endpoint="https://provider.invalid/v1/messages",
            model="model-a",
            timeout_seconds=30,
            api_key="test-key",
        ),
    )

    assert handle.engine_id == NATIVE_LBE_ENGINE_ID
    assert isinstance(handle.backend, backend_type)
    assert handle.descriptor.provider_id == provider_id


@pytest.mark.parametrize(
    "provider_id",
    [
        "openai-native",
        "vertex",
        "bedrock",
        "ollama",
        "openrouter",
        "opencode",
    ],
)
def test_default_registry_preserves_existing_cline_provider_routes(provider_id):
    handle = default_provider_registry().build(
        provider_id=provider_id,
        config=ProviderConfig(
            endpoint="https://provider.invalid/v1/messages",
            model="model-a",
            timeout_seconds=30,
            api_key="test-key",
        ),
    )

    assert handle.engine_id == CLINE_ENGINE_ID
    assert isinstance(handle.backend, ClineReasoningBackend)
    assert handle.descriptor.provider_id == provider_id


def test_lmstudio_has_native_default_and_explicit_cline_regression_binding():
    registry = default_provider_registry()
    native = registry.build(provider_id="lmstudio", config=config())
    cline = registry.build(
        provider_id="lmstudio",
        config=config(),
        engine_id=CLINE_ENGINE_ID,
    )

    assert native.engine_id == NATIVE_LBE_ENGINE_ID
    assert isinstance(native.backend, ToolAwareOpenAICompatibleReasoningBackend)
    assert cline.engine_id == CLINE_ENGINE_ID
    assert isinstance(cline.backend, ClineReasoningBackend)


@pytest.mark.parametrize("provider_id", ["openai", "anthropic", "gemini"])
def test_reused_provider_adapters_require_explicit_api_key(provider_id):
    with pytest.raises(ValueError, match="requires a non-empty api_key"):
        default_provider_registry().build(
            provider_id=provider_id, config=config()
        )


def test_generic_composition_uses_registered_backend_without_invoking_it():
    backend = FakeBackend()
    calls = []

    def factory(provider_config):
        calls.append(provider_config.model)
        return ProviderHandle(
            descriptor=ProviderDescriptor(
                "fake", provider_config.model, ProviderCapabilities()
            ),
            backend=backend,
        )

    controller, handle = build_provider_controller(
        provider_id="fake",
        provider_config=config("switchable-model"),
        provider_registry=ProviderRegistry({"fake": factory}),
    )

    assert isinstance(controller, LBERequestController)
    assert controller._backend is backend
    assert handle.backend is backend
    assert handle.engine_id == NATIVE_LBE_ENGINE_ID
    assert handle.descriptor.model_id == "switchable-model"
    assert calls == ["switchable-model"]


def test_generic_composition_can_select_explicit_engine_binding():
    registry = ProviderRegistry()
    backend = FakeBackend()

    registry.register_binding(
        engine_id="engine-a",
        provider_id="fake",
        factory=lambda cfg: ProviderHandle(
            descriptor=ProviderDescriptor(
                "fake", cfg.model, ProviderCapabilities()
            ),
            backend=backend,
            engine_id="engine-a",
        ),
        default=True,
    )

    controller, handle = build_provider_controller(
        provider_id="fake",
        engine_id="engine-a",
        provider_config=config(),
        provider_registry=registry,
    )

    assert isinstance(controller, LBERequestController)
    assert handle.engine_id == "engine-a"


def test_generic_composition_does_not_allow_backend_override():
    with pytest.raises(ValueError, match="must not override backend"):
        build_provider_controller(
            provider_id="openai-compatible",
            provider_config=config(),
            controller_kwargs={"backend": FakeBackend()},
        )


def test_existing_openai_builder_remains_compatible():
    controller = build_openai_compatible_controller(provider_config=config())
    assert isinstance(controller, LBERequestController)
    assert isinstance(controller._backend, OpenAICompatibleReasoningBackend)


def test_discovered_provider_capabilities_normalize_without_inventing_features():
    snapshot = discover_provider_model_capabilities(
        provider_id="anthropic",
        model_id="claude-test",
        endpoint="https://api.anthropic.com/v1/messages",
        context_window=200000,
        explicit_evidence={
            "client_tool_calls": CapabilityClaim(
                support=CapabilitySupport.SUPPORTED,
                reason="provider metadata declares tool calls",
                source="provider-model-metadata",
            )
        },
    )

    descriptor = normalize_provider_descriptor(snapshot)

    assert descriptor.provider_id == "anthropic"
    assert descriptor.model_id == "claude-test"
    assert descriptor.protocol_family is ProviderProtocolFamily.ANTHROPIC_MESSAGES
    assert descriptor.capabilities.tool_calls is True
    assert descriptor.capabilities.streaming is False
    assert descriptor.capabilities.context_limit == 200000


def test_unknown_protocol_discovery_remains_non_executable_metadata():
    snapshot = discover_provider_model_capabilities(
        provider_id="routed-provider",
        model_id="model-a",
        endpoint="https://router.example/custom/inference",
    )

    descriptor = normalize_provider_descriptor(snapshot)

    assert descriptor.protocol_family is ProviderProtocolFamily.UNKNOWN
    assert descriptor.capabilities.tool_calls is False
    assert descriptor.capabilities.streaming is False


def test_provider_registry_import_and_native_build_do_not_require_cline():
    repo_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import builtins
        import sys

        real_import = builtins.__import__

        def blocked(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "lbe_guard_inspector.cline_reasoning_provider":
                raise ImportError("cline intentionally unavailable")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = blocked

        from lbe_guard_inspector.provider_registry import (
            NATIVE_LBE_ENGINE_ID,
            ReasoningEngineUnavailableError,
            default_provider_registry,
        )
        from lbe_guard_inspector.reasoning_provider import ProviderConfig

        assert "lbe_guard_inspector.cline_reasoning_provider" not in sys.modules

        cfg = ProviderConfig(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="local-model",
            timeout_seconds=30,
        )
        registry = default_provider_registry()
        handle = registry.build(provider_id="openai-compatible", config=cfg)
        assert handle.engine_id == NATIVE_LBE_ENGINE_ID
        assert "lbe_guard_inspector.cline_reasoning_provider" not in sys.modules

        lmstudio = registry.build(provider_id="lmstudio", config=cfg)
        assert lmstudio.engine_id == NATIVE_LBE_ENGINE_ID
        assert "lbe_guard_inspector.cline_reasoning_provider" not in sys.modules

        try:
            registry.build(provider_id="openrouter", config=cfg)
        except ReasoningEngineUnavailableError:
            pass
        else:
            raise AssertionError("Cline-only binding must fail explicitly")

        assert "lbe_guard_inspector.cline_reasoning_provider" not in sys.modules
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_binding_records_keep_engine_provider_identity_explicit():
    binding = EngineProviderBinding(
        engine_id="cline",
        provider_id="example",
        factory=lambda cfg: None,
    )
    assert binding.engine_id == "cline"
    assert binding.provider_id == "example"
