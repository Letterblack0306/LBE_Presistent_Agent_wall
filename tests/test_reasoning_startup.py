from pathlib import Path

import pytest

import server
from lbe_guard_inspector.reasoning_provider import ProviderConfig


def test_startup_preserves_existing_handler_when_reasoning_is_absent():
    handler = server._startup_handler(
        {},
        config_path=Path("C:/runtime/config.json"),
    )

    assert handler is server.Handler


def test_startup_rejects_invalid_explicit_provider_path():
    with pytest.raises(
        server.GovernanceError,
        match="reasoning_provider_config",
    ):
        server._startup_handler(
            {"reasoning_provider_config": "   "},
            config_path=Path("C:/runtime/config.json"),
        )


def test_startup_loads_relative_provider_config_and_binds_controller(monkeypatch):
    loaded_paths = []
    composed_configs = []
    provider_config = ProviderConfig(
        endpoint="http://127.0.0.1:1234",
        model="test-model",
        timeout_seconds=15,
    )
    controller = object()

    def fake_load(path):
        loaded_paths.append(path)
        return provider_config

    def fake_build(*, provider_config):
        composed_configs.append(provider_config)
        return controller

    monkeypatch.setattr(server, "load_provider_config", fake_load)
    monkeypatch.setattr(
        server,
        "build_openai_compatible_controller",
        fake_build,
    )

    handler = server._startup_handler(
        {"reasoning_provider_config": "providers/local.json"},
        config_path=Path("C:/runtime/config.json"),
    )

    assert loaded_paths == [Path("C:/runtime/providers/local.json")]
    assert composed_configs == [provider_config]
    assert handler.reasoning_controller is controller


def test_startup_construction_does_not_invoke_provider(monkeypatch, tmp_path):
    provider_path = tmp_path / "provider.json"
    provider_path.write_text(
        (
            '{"endpoint":"http://127.0.0.1:1234",'
            '"model":"test-model","timeout_seconds":15}'
        ),
        encoding="utf-8",
    )
    calls = []

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError(
            "provider transport must not run during startup composition"
        )

    monkeypatch.setattr("urllib.request.urlopen", fail)

    handler = server._startup_handler(
        {"reasoning_provider_config": provider_path.name},
        config_path=tmp_path / "config.json",
    )

    assert handler.reasoning_controller is not None
    assert calls == []
