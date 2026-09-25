from __future__ import annotations

import json

import pytest

from lbe_guard_inspector.reasoning_config import (
    bind_provider_config_to_session,
    load_provider_config,
    provider_config_from_mapping,
)
from lbe_guard_inspector.reasoning_provider import ProviderConfig


def valid_mapping() -> dict:
    return {
        "endpoint": "http://provider/v1/chat/completions",
        "model": "local-model",
        "timeout_seconds": 30,
    }


def test_mapping_decodes_explicit_provider_config() -> None:
    config = provider_config_from_mapping(valid_mapping())
    assert config == ProviderConfig(
        endpoint="http://provider/v1/chat/completions",
        model="local-model",
        timeout_seconds=30,
        api_key=None,
    )


def test_mapping_accepts_provider_identity_metadata_without_changing_adapter_config() -> None:
    config = provider_config_from_mapping({**valid_mapping(), "provider_id": "openai-compatible"})
    assert config == ProviderConfig(
        endpoint="http://provider/v1/chat/completions",
        model="local-model",
        timeout_seconds=30,
        api_key=None,
        provider_id="openai-compatible",
    )


def test_binding_rebinds_model_to_persisted_session_selection() -> None:
    config = provider_config_from_mapping({
        **valid_mapping(),
        "model": "stale-model",
        "provider_id": "openai-compatible",
    })

    bound = bind_provider_config_to_session(
        config,
        session_provider_id="openai-compatible",
        session_model="selected-model",
    )

    assert bound == ProviderConfig(
        endpoint=config.endpoint,
        model="selected-model",
        timeout_seconds=config.timeout_seconds,
        provider_id="openai-compatible",
    )


def test_binding_rejects_provider_identity_mismatch() -> None:
    config = provider_config_from_mapping({
        **valid_mapping(),
        "provider_id": "anthropic",
    })

    with pytest.raises(ValueError, match="does not match persisted session provider"):
        bind_provider_config_to_session(
            config,
            session_provider_id="openai-compatible",
            session_model="selected-model",
        )


def test_binding_rejects_unsupported_endpoint_without_provider_identity() -> None:
    config = provider_config_from_mapping({
        **valid_mapping(),
        "endpoint": "http://provider/v1/messages",
    })

    with pytest.raises(ValueError, match="must declare provider_id"):
        bind_provider_config_to_session(
            config,
            session_provider_id="openai-compatible",
            session_model="selected-model",
        )


def test_file_loader_accepts_a_utf8_bom_from_windows_editors(tmp_path) -> None:
    """PowerShell `Set-Content -Encoding utf8` and most Windows editors prepend a BOM.
    A valid provider config must load with or without it."""
    path = tmp_path / "provider.json"
    path.write_text(
        "﻿" + json.dumps({**valid_mapping(), "api_key": " secret "}),
        encoding="utf-8",
    )

    config = load_provider_config(path)

    assert config.endpoint == "http://provider/v1/chat/completions"
    assert config.model == "local-model"
    assert config.api_key == "secret"


def test_file_loader_reads_only_the_supplied_path(tmp_path) -> None:
    path = tmp_path / "provider.json"
    path.write_text(json.dumps({**valid_mapping(), "api_key": " secret "}), encoding="utf-8")
    config = load_provider_config(path)
    assert config.api_key == "secret"


@pytest.mark.parametrize(
    "raw, error",
    [
        ([], "JSON object"),
        ({"endpoint": "x"}, "missing provider config fields"),
        ({**valid_mapping(), "port": 1234}, "unknown provider config fields"),
        ({**valid_mapping(), "api_key": ""}, "api_key"),
        ({**valid_mapping(), "provider_id": " "}, "provider_id"),
    ],
)
def test_invalid_shapes_are_rejected(raw, error) -> None:
    with pytest.raises((TypeError, ValueError), match=error):
        provider_config_from_mapping(raw)


def test_provider_validation_remains_authoritative() -> None:
    raw = valid_mapping()
    raw["timeout_seconds"] = 0
    with pytest.raises(ValueError, match="timeout_seconds"):
        provider_config_from_mapping(raw)


def test_loader_has_no_implicit_default_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(TypeError):
        load_provider_config()  # type: ignore[call-arg]
