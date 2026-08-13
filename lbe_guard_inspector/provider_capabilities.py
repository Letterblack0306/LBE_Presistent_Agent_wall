"""Typed P2 provider/model capability discovery substrate.

This module describes what a configured provider endpoint and selected model can
truthfully express. It does not grant workspace authority, change runtime mode,
project tools to a model, or execute provider probes by itself.

The first P2 slice is intentionally conservative: protocol-family evidence may
be derived from the configured endpoint shape, while every professional model
feature remains UNKNOWN until explicit evidence or a later deterministic probe
establishes it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Mapping
from urllib.parse import urlsplit


class CapabilitySupport(StrEnum):
    """Technical support state for a provider/model or runtime backend feature."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class ProviderProtocolFamily(StrEnum):
    """Provider wire/protocol family proven by configured endpoint semantics."""

    OPENAI_RESPONSES = "openai_responses"
    ANTHROPIC_MESSAGES = "anthropic_messages"
    GEMINI_INTERACTIONS = "gemini_interactions"
    GEMINI_GENERATE_CONTENT = "gemini_generate_content"
    OPENAI_COMPATIBLE_CHAT = "openai_compatible_chat"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CapabilityClaim:
    """One evidence-backed capability assertion.

    CONDITIONAL claims require an explicit reason. UNKNOWN is the safe default
    when no evidence proves support or lack of support.
    """

    support: CapabilitySupport
    reason: str | None = None
    source: str = "unproven"

    def __post_init__(self) -> None:
        if not isinstance(self.support, CapabilitySupport):
            raise TypeError("support must be CapabilitySupport")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("capability source must be a non-empty string")
        if self.reason is not None and (not isinstance(self.reason, str) or not self.reason.strip()):
            raise ValueError("capability reason must be non-empty when supplied")
        if self.support is CapabilitySupport.CONDITIONAL and self.reason is None:
            raise ValueError("conditional capability support requires a reason")


def _unknown_claim() -> CapabilityClaim:
    return CapabilityClaim(
        support=CapabilitySupport.UNKNOWN,
        reason="capability has not been proven for this endpoint/model",
        source="unproven",
    )


@dataclass(frozen=True)
class ProviderModelCapabilities:
    """Professional capability snapshot for one provider + endpoint + model.

    This object intentionally contains no workspace permission, runtime mode,
    authorization verdict, or provider-projection state. Those belong to later
    P1/P2 composition layers and existing R6C runtime authority.
    """

    provider_id: str
    model_id: str
    endpoint: str
    protocol_family: ProviderProtocolFamily
    protocol_evidence: str

    streaming_text: CapabilityClaim = field(default_factory=_unknown_claim)
    streaming_reasoning_summary: CapabilityClaim = field(default_factory=_unknown_claim)
    reasoning_visibility: CapabilityClaim = field(default_factory=_unknown_claim)
    client_tool_calls: CapabilityClaim = field(default_factory=_unknown_claim)
    server_tool_calls: CapabilityClaim = field(default_factory=_unknown_claim)
    parallel_tool_calls: CapabilityClaim = field(default_factory=_unknown_claim)
    streamed_tool_arguments: CapabilityClaim = field(default_factory=_unknown_claim)
    strict_tool_schema: CapabilityClaim = field(default_factory=_unknown_claim)
    tool_choice_modes: CapabilityClaim = field(default_factory=_unknown_claim)
    structured_output: CapabilityClaim = field(default_factory=_unknown_claim)
    native_mcp: CapabilityClaim = field(default_factory=_unknown_claim)
    server_side_state: CapabilityClaim = field(default_factory=_unknown_claim)
    previous_response_or_interaction_state: CapabilityClaim = field(default_factory=_unknown_claim)
    image_input: CapabilityClaim = field(default_factory=_unknown_claim)
    file_input: CapabilityClaim = field(default_factory=_unknown_claim)
    cache_controls: CapabilityClaim = field(default_factory=_unknown_claim)
    usage_reporting: CapabilityClaim = field(default_factory=_unknown_claim)
    cancellation: CapabilityClaim = field(default_factory=_unknown_claim)
    provider_request_id: CapabilityClaim = field(default_factory=_unknown_claim)
    retryable_error_signals: CapabilityClaim = field(default_factory=_unknown_claim)

    context_window: int | None = None
    max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        for name in ("provider_id", "model_id", "endpoint", "protocol_evidence"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.protocol_family, ProviderProtocolFamily):
            raise TypeError("protocol_family must be ProviderProtocolFamily")
        for name in ("context_window", "max_output_tokens"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, int) or value <= 0):
                raise ValueError(f"{name} must be positive when supplied")


_CAPABILITY_FIELDS = frozenset(
    {
        "streaming_text",
        "streaming_reasoning_summary",
        "reasoning_visibility",
        "client_tool_calls",
        "server_tool_calls",
        "parallel_tool_calls",
        "streamed_tool_arguments",
        "strict_tool_schema",
        "tool_choice_modes",
        "structured_output",
        "native_mcp",
        "server_side_state",
        "previous_response_or_interaction_state",
        "image_input",
        "file_input",
        "cache_controls",
        "usage_reporting",
        "cancellation",
        "provider_request_id",
        "retryable_error_signals",
    }
)


def discover_provider_model_capabilities(
    *,
    provider_id: str,
    model_id: str,
    endpoint: str,
    explicit_evidence: Mapping[str, CapabilityClaim] | None = None,
    context_window: int | None = None,
    max_output_tokens: int | None = None,
) -> ProviderModelCapabilities:
    """Build a conservative capability snapshot for one configured model.

    Endpoint shape may prove a protocol family. It does not prove professional
    feature support. Callers may supply explicit typed evidence gathered from
    current provider metadata, configuration, or later deterministic probes.
    Unknown evidence remains UNKNOWN rather than being inferred from provider
    brand or compatibility naming.
    """

    clean_provider = _required(provider_id, "provider_id")
    clean_model = _required(model_id, "model_id")
    clean_endpoint = _required(endpoint, "endpoint")
    family, protocol_evidence = detect_protocol_family(
        provider_id=clean_provider,
        endpoint=clean_endpoint,
    )
    snapshot = ProviderModelCapabilities(
        provider_id=clean_provider,
        model_id=clean_model,
        endpoint=clean_endpoint,
        protocol_family=family,
        protocol_evidence=protocol_evidence,
        context_window=context_window,
        max_output_tokens=max_output_tokens,
    )

    evidence = dict(explicit_evidence or {})
    unknown = sorted(set(evidence) - _CAPABILITY_FIELDS)
    if unknown:
        raise ValueError(f"unsupported capability evidence fields: {unknown}")
    for name, claim in evidence.items():
        if not isinstance(claim, CapabilityClaim):
            raise TypeError(f"explicit capability evidence for {name} must be CapabilityClaim")
        snapshot = replace(snapshot, **{name: claim})
    return snapshot


def detect_protocol_family(*, provider_id: str, endpoint: str) -> tuple[ProviderProtocolFamily, str]:
    """Classify only protocol syntax evidenced by the configured endpoint.

    This is not a model-capability inference. Provider identity is used only to
    disambiguate provider-specific endpoint families such as Gemini Interactions.
    """

    clean_provider = _required(provider_id, "provider_id").lower()
    clean_endpoint = _required(endpoint, "endpoint")
    parsed = urlsplit(clean_endpoint)
    path = parsed.path.lower()

    if path.rstrip("/").endswith("/responses"):
        return ProviderProtocolFamily.OPENAI_RESPONSES, "configured endpoint path ends with /responses"
    if path.rstrip("/").endswith("/v1/messages") or path.rstrip("/").endswith("/messages"):
        return ProviderProtocolFamily.ANTHROPIC_MESSAGES, "configured endpoint path identifies Messages API"
    if clean_provider == "gemini" and "interactions" in path:
        return ProviderProtocolFamily.GEMINI_INTERACTIONS, "configured Gemini endpoint path identifies Interactions API"
    if clean_provider == "gemini" and ("generatecontent" in path or "streamgeneratecontent" in path):
        return ProviderProtocolFamily.GEMINI_GENERATE_CONTENT, "configured Gemini endpoint path identifies GenerateContent API"
    if path.rstrip("/").endswith("/chat/completions"):
        return ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT, "configured endpoint path identifies chat/completions protocol"
    return ProviderProtocolFamily.UNKNOWN, "configured endpoint does not prove a recognized protocol family"


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()
