import json

import pytest

from lbe_guard_inspector import custom_providers as cp
from lbe_guard_inspector.provider_registry import default_provider_registry
from lbe_guard_inspector.reasoning_provider import ProviderConfig, apply_credentials


def _file(tmp_path, data):
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_headers_and_bearer_are_applied_with_custom_winning() -> None:
    config = ProviderConfig(endpoint="http://x/v1/chat/completions", model="m", timeout_seconds=5,
                            api_key="k", headers={"x-api-key": "k", "Authorization": "Token k"})
    out = apply_credentials(config, {"Content-Type": "application/json"})
    assert out["x-api-key"] == "k" and out["Authorization"] == "Token k"


def test_secrets_come_from_env_not_the_file(tmp_path) -> None:
    path = _file(tmp_path, {"my-gw": {"endpoint": "https://gw/v1/chat/completions",
                                      "api_key_env": "GW_KEY",
                                      "headers": {"x-api-key": "${GW_KEY}", "X-Org": "acme"}}})
    provider = cp.load_openai_providers(path)["my-gw"]
    key, headers = cp.resolve_credentials(provider, {"GW_KEY": "s3cret"})
    assert key == "s3cret" and headers == {"x-api-key": "s3cret", "X-Org": "acme"}
    assert "s3cret" not in open(path, encoding="utf-8").read()
    assert provider.auth_mode == "api_key"


def test_kind_is_inferred_and_validated(tmp_path) -> None:
    path = _file(tmp_path, {"a": {"executable": "acme"}, "b": {"endpoint": "http://x"}})
    assert set(cp.login_agent_entries(path)) == {"a"}
    assert set(cp.load_openai_providers(path)) == {"b"}
    with pytest.raises(ValueError):
        cp._kind({"kind": "mystery"})
    with pytest.raises(ValueError):
        cp.load_openai_providers(_file(tmp_path, {"Bad Id": {"endpoint": "http://x"}}))


def test_registry_builds_custom_provider_with_resolved_credentials(tmp_path, monkeypatch) -> None:
    path = _file(tmp_path, {"my-gw": {"endpoint": "https://gw/v1/chat/completions",
                                      "api_key_env": "GW_KEY", "headers": {"X-Org": "acme"}}})
    monkeypatch.setenv("LBE_CUSTOM_PROVIDERS_FILE", path)
    monkeypatch.setenv("GW_KEY", "s3cret")
    registry = default_provider_registry()
    assert "my-gw" in registry.provider_ids()
    handle = registry.build(provider_id="my-gw", config=ProviderConfig(
        endpoint="https://gw/v1/chat/completions", model="m", timeout_seconds=5))
    cfg = handle.backend._config
    assert cfg.api_key == "s3cret" and cfg.headers == {"X-Org": "acme"}
