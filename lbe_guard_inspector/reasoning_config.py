"""Explicit file-backed configuration for the bounded reasoning provider."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from dataclasses import replace
from urllib.parse import urlsplit

from .reasoning_provider import LBE_MAX_REQUESTED_OUTPUT_TOKENS, ProviderConfig

_ALLOWED_FIELDS = frozenset({
    "endpoint",
    "model",
    "timeout_seconds",
    "api_key",
    "reasoning_effort",
    "provider_id",
    "max_output_tokens",
})
_REQUIRED_FIELDS = frozenset({"endpoint", "model", "timeout_seconds"})


def load_provider_config(path: str | Path) -> ProviderConfig:
    """Load one explicit provider config file without environment or runtime defaults."""
    config_path = Path(path).expanduser().resolve()
    try:
        # `utf-8-sig` accepts both plain UTF-8 and the BOM that Windows editors and
        # PowerShell `Set-Content -Encoding utf8` write by default. Rejecting a BOM here
        # made an otherwise valid provider config unusable.
        raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid provider config file: {config_path}: {exc}") from exc
    return provider_config_from_mapping(raw)


def provider_config_from_mapping(raw: Mapping[str, Any]) -> ProviderConfig:
    """Decode an exact provider configuration mapping into ProviderConfig."""
    if not isinstance(raw, Mapping):
        raise TypeError("provider config must be a JSON object")
    fields = set(raw)
    unknown = sorted(fields - _ALLOWED_FIELDS)
    if unknown:
        raise ValueError(f"unknown provider config fields: {unknown}")
    missing = sorted(_REQUIRED_FIELDS - fields)
    if missing:
        raise ValueError(f"missing provider config fields: {missing}")
    api_key = raw.get("api_key")
    if api_key is not None and (not isinstance(api_key, str) or not api_key.strip()):
        raise ValueError("provider api_key must be a non-empty string when supplied")
    reasoning_effort = raw.get("reasoning_effort")
    if reasoning_effort is not None and (not isinstance(reasoning_effort, str) or not reasoning_effort.strip()):
        raise ValueError("provider reasoning_effort must be a non-empty string when supplied")
    provider_id = raw.get("provider_id")
    if provider_id is not None and (not isinstance(provider_id, str) or not provider_id.strip()):
        raise ValueError("provider provider_id must be a non-empty string when supplied")
    max_output_tokens = raw.get("max_output_tokens")
    if max_output_tokens is not None:
        # Fail closed on a malformed or unsupported cap instead of silently clamping it.
        if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int):
            raise ValueError("provider max_output_tokens must be a positive integer when supplied")
        if max_output_tokens <= 0:
            raise ValueError("provider max_output_tokens must be a positive integer when supplied")
        if max_output_tokens > LBE_MAX_REQUESTED_OUTPUT_TOKENS:
            raise ValueError(
                "provider max_output_tokens exceeds the LBE request-policy maximum of "
                f"{LBE_MAX_REQUESTED_OUTPUT_TOKENS}"
            )
    return ProviderConfig(
        endpoint=raw["endpoint"],
        model=raw["model"],
        timeout_seconds=raw["timeout_seconds"],
        api_key=api_key.strip() if isinstance(api_key, str) else None,
        reasoning_effort=reasoning_effort.strip() if isinstance(reasoning_effort, str) else None,
        provider_id=provider_id.strip() if isinstance(provider_id, str) else None,
        max_output_tokens=max_output_tokens,
    )


def bind_provider_config_to_session(
    config: ProviderConfig, *, session_provider_id: str, session_model: str
) -> ProviderConfig:
    """Bind the persisted model only when the explicit endpoint belongs to its provider."""
    if not isinstance(config, ProviderConfig):
        raise TypeError("config must be a ProviderConfig")
    if not isinstance(session_provider_id, str) or not session_provider_id.strip():
        raise ValueError("persisted session does not have a selected provider")
    if not isinstance(session_model, str) or not session_model.strip():
        raise ValueError("persisted session does not have a selected model")

    configured_provider_id = config.provider_id
    if configured_provider_id is None:
        endpoint = urlsplit(config.endpoint)
        path = endpoint.path.rstrip("/")
        if endpoint.scheme not in {"http", "https"} or not endpoint.netloc or not (
            path.endswith("/chat/completions") or path.endswith("/completions")
        ):
            raise ValueError(
                "provider config must declare provider_id unless it uses an OpenAI-compatible completion endpoint"
            )
        configured_provider_id = "openai-compatible"
    if configured_provider_id != session_provider_id.strip():
        raise ValueError(
            "provider config identity does not match persisted session provider; refusing to route credentials"
        )
    return replace(config, model=session_model.strip(), provider_id=configured_provider_id)