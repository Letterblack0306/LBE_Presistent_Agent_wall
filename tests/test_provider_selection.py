"""Provider selection (LET-44): recorded catalog data, no provider is contacted."""
from __future__ import annotations

import json

import pytest

from lbe_guard_inspector import provider_selection as ps
from lbe_guard_inspector.reasoning_provider import ProviderError

CATALOG = {
    "source": "@cline/llms",
    "version": "0.0.75",
    "providers": [
        {"id": "openrouter", "name": "OpenRouter", "protocol": "openai-chat", "client": "openai-compatible",
         "base_url": "https://openrouter.ai/api/v1", "key_env": ["OPENROUTER_API_KEY"], "default_model": None},
        {"id": "lmstudio", "name": "LM Studio", "protocol": "openai-chat", "client": "openai-compatible",
         "base_url": "http://localhost:1234/v1", "key_env": ["LMSTUDIO_API_KEY"], "default_model": None},
        {"id": "anthropic", "name": "Anthropic", "protocol": "anthropic", "client": "anthropic",
         "base_url": "https://api.anthropic.com/v1", "key_env": ["ANTHROPIC_API_KEY"], "default_model": None},
    ],
    "models": {
        "openrouter": [{"id": "a/b", "name": "B", "context_window": 128000, "max_tokens": 8000,
                        "capabilities": ["tools"], "status": None}],
    },
}
SECRET = "sk-test-value-never-written"


def test_selection_writes_endpoint_and_key_name_but_never_the_key(tmp_path):
    env = {"OPENROUTER_API_KEY": SECRET}
    picked = ps.select(CATALOG, "openrouter", "a/b", state_dir=tmp_path, environ=env, probe=lambda h, p: False)
    config = json.loads((tmp_path / "provider-openrouter.json").read_text())
    assert config == {"endpoint": "https://openrouter.ai/api/v1/chat/completions", "model": "a/b",
                      "timeout_seconds": 120, "provider_id": "openrouter"}
    declared = json.loads((tmp_path / "custom-providers.json").read_text())
    assert declared["openrouter"]["api_key_env"] == "OPENROUTER_API_KEY"
    assert picked["key_env"] == "OPENROUTER_API_KEY"
    for path in tmp_path.iterdir():
        assert SECRET not in path.read_text()
    assert SECRET not in json.dumps(picked)


def test_cline_engine_and_unready_providers_are_refused_with_the_reason(tmp_path):
    with pytest.raises(ps.SelectionError, match="Cline engine"):
        ps.select(CATALOG, "anthropic", "m", state_dir=tmp_path, environ={"ANTHROPIC_API_KEY": "x"})
    with pytest.raises(ps.SelectionError, match="needs OPENROUTER_API_KEY"):
        ps.select(CATALOG, "openrouter", "a/b", state_dir=tmp_path, environ={}, probe=lambda h, p: False)
    with pytest.raises(ps.SelectionError, match="not running"):
        ps.select(CATALOG, "lmstudio", "m", state_dir=tmp_path, environ={}, probe=lambda h, p: False)
    with pytest.raises(ps.SelectionError, match="choose a model"):
        ps.select(CATALOG, "lmstudio", " ", state_dir=tmp_path, environ={}, probe=lambda h, p: True)
    assert not list(tmp_path.iterdir())  # nothing written for a refused choice


def test_models_are_live_when_the_provider_answers_else_the_catalog():
    seen = []

    def live(config):
        seen.append(config)
        return [{"id": "a/b"}, {"id": "c/d"}]

    source, rows = ps.provider_models(CATALOG, "openrouter", environ={"OPENROUTER_API_KEY": SECRET}, fetch=live)
    assert source == "live" and [r["id"] for r in rows] == ["a/b", "c/d"]
    assert rows[0]["context_window"] == 128000 and rows[1]["context_window"] is None
    assert seen[0].endpoint == "https://openrouter.ai/api/v1/chat/completions"

    def down(config):
        raise ProviderError("MODEL_DISCOVERY_FAILED", "provider model catalog request failed")

    source, rows = ps.provider_models(CATALOG, "openrouter", environ={}, fetch=down)
    assert source == "catalog" and [r["id"] for r in rows] == ["a/b"]
    assert ps.provider_models(CATALOG, "anthropic", environ={}, fetch=live) == ("catalog", [])


def test_owner_declared_providers_join_the_list_and_their_file_is_never_changed(tmp_path):
    own = tmp_path / "mine.json"
    own_text = json.dumps({"freellmapi": {"kind": "openai-compatible",
                                          "endpoint": "http://127.0.0.1:3001/v1/chat/completions",
                                          "api_key_env": "FREELLMAPI_KEY"}})
    own.write_text(own_text)
    env = {"LBE_CUSTOM_PROVIDERS_FILE": str(own), "FREELLMAPI_KEY": SECRET}
    merged = ps.merged_catalog(CATALOG, environ=env)
    first = merged["providers"][0]
    assert (first["id"], first["base_url"], first["key_env"], first["source"]) == (
        "freellmapi", "http://127.0.0.1:3001/v1", ["FREELLMAPI_KEY"], "custom")
    state = tmp_path / "state"
    ps.select(merged, "freellmapi", "auto", state_dir=state, environ=env, probe=lambda h, p: True)
    ps.select(merged, "openrouter", "a/b", state_dir=state,
              environ={**env, "OPENROUTER_API_KEY": "y"}, probe=lambda h, p: False)
    assert own.read_text() == own_text
    declared = json.loads((state / "custom-providers.json").read_text())
    assert declared["freellmapi"]["api_key_env"] == "FREELLMAPI_KEY"
    assert declared["openrouter"]["api_key_env"] == "OPENROUTER_API_KEY"


def test_native_binding_reads_the_declared_key_when_a_turn_runs(tmp_path, monkeypatch):
    from lbe_guard_inspector import provider_registry as pr
    from lbe_guard_inspector.reasoning_provider import ProviderConfig

    picked = ps.select(CATALOG, "openrouter", "a/b", state_dir=tmp_path,
                       environ={"OPENROUTER_API_KEY": SECRET}, probe=lambda h, p: False)
    monkeypatch.setenv("LBE_CUSTOM_PROVIDERS_FILE", picked["custom_providers_file"])
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)
    built = []
    monkeypatch.setattr(pr, "ToolAwareOpenAICompatibleReasoningBackend",
                        lambda config, **kw: built.append(config) or object())
    monkeypatch.setattr(pr, "_handle", lambda *a, **kw: None)
    config = ProviderConfig(endpoint="https://openrouter.ai/api/v1/chat/completions", model="a/b",
                            timeout_seconds=120, provider_id="openrouter")
    pr.native_openai_compatible_factory("openrouter")(config)
    assert built[0].api_key == SECRET
    monkeypatch.delenv("OPENROUTER_API_KEY")
    pr.native_openai_compatible_factory("openrouter")(config)
    assert built[1].api_key is None  # no value present: nothing invented
