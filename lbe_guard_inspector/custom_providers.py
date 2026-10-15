"""User-defined providers and login methods, declared in one JSON file.

The file (``LBE_CUSTOM_PROVIDERS_FILE``, or ``LBE_LOGIN_AGENTS_FILE`` for older
setups) maps a provider id to an entry. Authentication classes follow
GPT-Knowledge provider-neutral-agent-auth-and-model-routing.md:

- ``"kind": "openai-compatible"`` - any OpenAI-compatible endpoint. Auth is
  ``none``, a bearer ``api_key_env`` (value read from that environment
  variable), and/or custom ``headers`` whose values may use ``${ENV_VAR}``.
- ``"kind": "login-agent"`` (default when ``executable`` is present) - a
  platform CLI that holds the user's own login; see login_agent_transport.

Secrets are never stored in this file: only environment variable names.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
BUILTIN_KINDS = ("openai-compatible", "login-agent")


@dataclass(frozen=True)
class CustomOpenAIProvider:
    provider_id: str
    endpoint: str | None = None
    api_key_env: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    default_model: str | None = None

    @property
    def auth_mode(self) -> str:
        return "api_key" if self.api_key_env or self.headers else "none"


def custom_providers_path() -> str | None:
    return os.environ.get("LBE_CUSTOM_PROVIDERS_FILE") or os.environ.get("LBE_LOGIN_AGENTS_FILE")


def _read(path: str | None) -> dict[str, Any]:
    location = path or custom_providers_path()
    if not location or not os.path.exists(location):
        return {}
    with open(location, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("custom providers file must be a JSON object keyed by provider id")
    return data


def _kind(entry: Mapping[str, Any]) -> str:
    kind = entry.get("kind")
    if kind is None:
        return "login-agent" if "executable" in entry else "openai-compatible"
    if kind not in BUILTIN_KINDS:
        raise ValueError(f"unknown provider kind {kind!r}; expected one of {BUILTIN_KINDS}")
    return kind


def load_openai_providers(path: str | None = None) -> dict[str, CustomOpenAIProvider]:
    result: dict[str, CustomOpenAIProvider] = {}
    for provider_id, entry in _read(path).items():
        if not isinstance(entry, dict) or _kind(entry) != "openai-compatible":
            continue
        if not _ID.match(provider_id):
            raise ValueError(f"invalid provider id {provider_id!r}")
        headers = entry.get("headers", {})
        if not isinstance(headers, dict) or not all(isinstance(v, str) for v in headers.values()):
            raise ValueError(f"provider {provider_id!r}: headers must map names to strings")
        for key in ("endpoint", "api_key_env", "default_model"):
            if entry.get(key) is not None and not isinstance(entry[key], str):
                raise ValueError(f"provider {provider_id!r}: {key} must be a string")
        result[provider_id] = CustomOpenAIProvider(
            provider_id, entry.get("endpoint"), entry.get("api_key_env"),
            dict(headers), entry.get("default_model"))
    return result


def login_agent_entries(path: str | None = None) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for provider_id, entry in _read(path).items():
        if isinstance(entry, dict) and _kind(entry) == "login-agent":
            if not _ID.match(provider_id):
                raise ValueError(f"invalid provider id {provider_id!r}")
            out[provider_id] = entry
    return out


def expand_env(value: str, environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return _ENV_REF.sub(lambda m: env.get(m.group(1), ""), value)


def resolve_credentials(provider: CustomOpenAIProvider,
                        environ: Mapping[str, str] | None = None) -> tuple[str | None, dict[str, str]]:
    """Return (bearer api key or None, headers) with env references resolved."""
    env = os.environ if environ is None else environ
    api_key = env.get(provider.api_key_env) if provider.api_key_env else None
    headers = {name: expand_env(value, env) for name, value in provider.headers.items()}
    return (api_key or None), headers
