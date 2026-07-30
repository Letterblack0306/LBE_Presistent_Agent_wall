from __future__ import annotations

import json

import pytest

from lbe_guard_inspector.reasoning_config import (
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
