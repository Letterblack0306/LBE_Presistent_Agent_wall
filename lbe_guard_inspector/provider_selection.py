"""Turn a provider + model choice into a session provider config (LET-44).

The choices come from the provider catalog (``provider_catalog``) plus the
OpenAI-compatible providers the owner declared in the custom providers file
(``custom_providers``). Nothing here is a hand-written provider list.

Keys are never written anywhere. The session config file holds only the
endpoint, model and provider id. The key's environment variable *name* is
declared in a custom providers file; the runtime reads the value when a turn
runs (``custom_providers.resolve_credentials``).

Only providers LBE's native engine speaks (OpenAI-compatible chat) can be
started here. Providers that need the Cline engine are listed but refused with
that reason, never started half-way.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from . import provider_catalog as pc

DEFAULT_TIMEOUT_SECONDS = 120
_COMPLETION_SUFFIXES = ("/chat/completions", "/completions")


class SelectionError(ValueError):
    """The choice cannot start a session (reason in the message)."""


def completion_endpoint(base_url: str) -> str:
    return str(base_url).rstrip("/") + "/chat/completions"


def _base_url(endpoint: str) -> str:
    clean = str(endpoint).rstrip("/")
    for suffix in _COMPLETION_SUFFIXES:
        if clean.endswith(suffix):
            return clean[: -len(suffix)]
    return clean


def _custom_file(environ: Mapping[str, str]) -> Path | None:
    location = environ.get("LBE_CUSTOM_PROVIDERS_FILE") or environ.get("LBE_LOGIN_AGENTS_FILE")
    return Path(location) if location else None


def _read_custom(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SelectionError("custom providers file must be a JSON object keyed by provider id")
    return data


def merged_catalog(
    catalog: Mapping[str, Any], *, environ: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """The catalog plus the owner's declared OpenAI-compatible providers (theirs win)."""
    from .custom_providers import _ENV_REF, load_openai_providers

    env = os.environ if environ is None else environ
    path = _custom_file(env)
    declared = load_openai_providers(str(path)) if path is not None and path.is_file() else {}
    custom = []
    for provider_id, entry in declared.items():
        if not entry.endpoint:
            continue
        key_env = [entry.api_key_env] if entry.api_key_env else []
        for value in entry.headers.values():
            key_env.extend(m.group(1) for m in _ENV_REF.finditer(value))
        custom.append({
            "id": provider_id,
            "name": provider_id,
            "protocol": "openai-chat",
            "client": "openai-compatible",
            "base_url": _base_url(entry.endpoint),
            "key_env": key_env,
            "default_model": entry.default_model,
            "source": "custom",
        })
    ids = {p["id"] for p in custom}
    providers = custom + [
        dict(p) for p in catalog.get("providers") or [] if isinstance(p, dict) and p.get("id") not in ids
    ]
    return {**dict(catalog), "providers": providers}


def _provider(catalog: Mapping[str, Any], provider_id: str) -> dict[str, Any]:
    for provider in catalog.get("providers") or []:
        if isinstance(provider, dict) and provider.get("id") == provider_id:
            return provider
    raise SelectionError(f"provider is not in the catalog: {provider_id}")


def _present_key(provider: Mapping[str, Any], env: Mapping[str, str]) -> tuple[str | None, str | None]:
    for name in provider.get("key_env") or []:
        if env.get(str(name)):
            return str(name), env.get(str(name))
    return None, None


def provider_models(
    catalog: Mapping[str, Any],
    provider_id: str,
    *,
    environ: Mapping[str, str] | None = None,
    fetch: Callable[[Any], list[dict[str, Any]]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Models the provider serves now (``"live"``, from its own /models), or the
    catalog's list (``"catalog"``) when the provider cannot be asked."""
    provider = _provider(catalog, provider_id)
    static = pc.catalog_models(catalog, provider_id) if provider.get("source") != "custom" else []
    if pc.engine_for(provider) != "native":
        return "catalog", static
    from .reasoning_provider import ProviderConfig, ProviderError, _openai_compatible_catalog

    env = os.environ if environ is None else environ
    _name, key = _present_key(provider, env)
    config = ProviderConfig(
        endpoint=completion_endpoint(provider["base_url"]),
        model="catalog",
        timeout_seconds=5,
        api_key=key,
        provider_id=provider_id,
    )
    try:
        items = (fetch or _openai_compatible_catalog)(config)
    except ProviderError:
        return "catalog", static
    known = {m["id"]: m for m in static}
    rows = []
    for item in items:
        model_id = str(item.get("id") or "") if isinstance(item, dict) else ""
        if model_id:
            rows.append(dict(known.get(model_id) or {
                "id": model_id, "name": model_id, "context_window": None,
                "max_tokens": None, "capabilities": [], "status": None,
            }))
    return "live", rows


def _declare_key_env(
    provider: Mapping[str, Any], key_name: str | None, *, state_dir: Path, env: Mapping[str, str]
) -> Path:
    """Write a custom providers file for this bridge that declares the key's
    environment variable name. The owner's own file is copied, never changed."""
    own = _custom_file(env)
    target = state_dir / "custom-providers.json"
    entries = _read_custom(own) if own is not None and own.resolve() != target.resolve() else {}
    entries.update({k: v for k, v in _read_custom(target).items() if k not in entries})
    if provider.get("source") != "custom":  # an owner-declared entry is already copied as-is
        entry: dict[str, Any] = {"kind": "openai-compatible", "endpoint": completion_endpoint(provider["base_url"])}
        if key_name:
            entry["api_key_env"] = key_name
        entries[provider["id"]] = entry
    target.write_text(json.dumps(entries, indent=2, sort_keys=True), encoding="utf-8")
    return target


def select(
    catalog: Mapping[str, Any],
    provider_id: str,
    model_id: str,
    *,
    state_dir: Path,
    environ: Mapping[str, str] | None = None,
    probe: pc.Probe = pc._tcp_listening,
) -> dict[str, Any]:
    """Write the session provider config for this choice; return where it is."""
    provider = _provider(catalog, provider_id)
    if pc.engine_for(provider) != "native":
        raise SelectionError(
            f"{provider_id} runs through the Cline engine; starting it from provider selection is not built yet"
        )
    model = str(model_id or "").strip()
    if not model:
        raise SelectionError("choose a model")
    env = os.environ if environ is None else environ
    ready, state = pc.readiness(provider, environ=env, probe=probe)
    if not ready:
        raise SelectionError(f"{provider_id} is not ready: {state}")
    key_name, _value = _present_key(provider, env)
    state_dir.mkdir(parents=True, exist_ok=True)
    config_path = state_dir / f"provider-{provider_id}.json"
    config_path.write_text(json.dumps({
        "endpoint": completion_endpoint(provider["base_url"]),
        "model": model,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "provider_id": provider_id,
    }, indent=2), encoding="utf-8")
    custom_file = _declare_key_env(provider, key_name, state_dir=state_dir, env=env)
    return {
        "provider_id": provider_id,
        "model": model,
        "provider_config": str(config_path),
        "custom_providers_file": str(custom_file),
        "key_env": key_name,
        "state": state,
    }
