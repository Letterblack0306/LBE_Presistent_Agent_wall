"""Explicit file-backed configuration for the bounded reasoning provider."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .reasoning_provider import ProviderConfig

_ALLOWED_FIELDS = frozenset({"endpoint", "model", "timeout_seconds", "api_key"})
_REQUIRED_FIELDS = frozenset({"endpoint", "model", "timeout_seconds"})


def load_provider_config(path: str | Path) -> ProviderConfig:
    """Load one explicit provider config file without environment or runtime defaults."""
    config_path = Path(path).expanduser().resolve()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
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
    return ProviderConfig(
        endpoint=raw["endpoint"],
        model=raw["model"],
        timeout_seconds=raw["timeout_seconds"],
        api_key=api_key.strip() if isinstance(api_key, str) else None,
    )
