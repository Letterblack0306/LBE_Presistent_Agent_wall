from __future__ import annotations

import pytest

from lbe_guard_inspector.provider_capabilities import (
    CapabilityClaim,
    CapabilitySupport,
    ProviderProtocolFamily,
    detect_protocol_family,
    discover_provider_model_capabilities,
)


def test_openai_compatible_endpoint_does_not_infer_model_tool_or_streaming_support() -> None:
    snapshot = discover_provider_model_capabilities(
        provider_id="openai-compatible",
        model_id="local-model",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
    )

    assert snapshot.protocol_family is ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT
    assert snapshot.client_tool_calls.support is CapabilitySupport.UNKNOWN
    assert snapshot.streaming_text.support is CapabilitySupport.UNKNOWN
    assert snapshot.structured_output.support is CapabilitySupport.UNKNOWN


def test_explicit_capability_evidence_is_preserved_without_granting_authority() -> None:
    claim = CapabilityClaim(
        support=CapabilitySupport.SUPPORTED,
        source="provider-model-metadata",
        reason="selected endpoint/model explicitly advertises client tool calls",
    )
    snapshot = discover_provider_model_capabilities(
        provider_id="openai-compatible",
        model_id="tool-model",
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        explicit_evidence={"client_tool_calls": claim},
    )

    assert snapshot.client_tool_calls is claim
    assert not hasattr(snapshot, "permission")
    assert not hasattr(snapshot, "authorization")
    assert not hasattr(snapshot, "workspace_root")
    assert not hasattr(snapshot, "provider_projection")


def test_conditional_capability_requires_reason() -> None:
    with pytest.raises(ValueError, match="requires a reason"):
        CapabilityClaim(
            support=CapabilitySupport.CONDITIONAL,
            source="endpoint-config",
        )


def test_unknown_explicit_capability_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported capability evidence fields"):
        discover_provider_model_capabilities(
            provider_id="openai-compatible",
            model_id="model",
            endpoint="http://localhost/v1/chat/completions",
            explicit_evidence={
                "workspace_write": CapabilityClaim(
                    support=CapabilitySupport.SUPPORTED,
                    source="invalid-test",
                )
            },
        )


@pytest.mark.parametrize(
    ("provider_id", "endpoint", "expected"),
    [
        ("openai", "https://api.openai.com/v1/responses", ProviderProtocolFamily.OPENAI_RESPONSES),
        ("anthropic", "https://api.anthropic.com/v1/messages", ProviderProtocolFamily.ANTHROPIC_MESSAGES),
        ("gemini", "https://generativelanguage.googleapis.com/v1beta/interactions", ProviderProtocolFamily.GEMINI_INTERACTIONS),
        ("gemini", "https://generativelanguage.googleapis.com/v1beta/models/gemini:testGenerateContent", ProviderProtocolFamily.GEMINI_GENERATE_CONTENT),
        ("openai-compatible", "http://localhost:1234/v1/chat/completions", ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT),
    ],
)
def test_protocol_family_detection_uses_configured_endpoint_evidence(
    provider_id: str,
    endpoint: str,
    expected: ProviderProtocolFamily,
) -> None:
    family, evidence = detect_protocol_family(provider_id=provider_id, endpoint=endpoint)

    assert family is expected
    assert evidence


def test_unrecognized_endpoint_keeps_protocol_unknown() -> None:
    snapshot = discover_provider_model_capabilities(
        provider_id="routed-provider",
        model_id="model-a",
        endpoint="https://router.example/custom/inference",
    )

    assert snapshot.protocol_family is ProviderProtocolFamily.UNKNOWN
    assert snapshot.protocol_evidence == "configured endpoint does not prove a recognized protocol family"


def test_switching_model_changes_snapshot_identity_without_creating_capability_claims() -> None:
    first = discover_provider_model_capabilities(
        provider_id="openai-compatible",
        model_id="model-a",
        endpoint="http://localhost:1234/v1/chat/completions",
    )
    second = discover_provider_model_capabilities(
        provider_id="openai-compatible",
        model_id="model-b",
        endpoint="http://localhost:1234/v1/chat/completions",
    )

    assert first.model_id == "model-a"
    assert second.model_id == "model-b"
    assert first.client_tool_calls.support is CapabilitySupport.UNKNOWN
    assert second.client_tool_calls.support is CapabilitySupport.UNKNOWN


def test_resource_limits_validate_positive_values() -> None:
    with pytest.raises(ValueError, match="context_window"):
        discover_provider_model_capabilities(
            provider_id="openai",
            model_id="model-a",
            endpoint="https://api.openai.com/v1/responses",
            context_window=0,
        )
