"""Provider catalog (LET-44): recorded catalog data, no provider is contacted."""
from __future__ import annotations

import json
import subprocess

import pytest

from lbe_guard_inspector import provider_catalog as pc

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
        {"id": "claude-code", "name": "Claude Code", "protocol": "openai-chat", "client": "ai-sdk-community",
         "base_url": None, "key_env": [], "default_model": None},
    ],
    "models": {
        "openrouter": [{"id": "a/b", "name": "B", "context_window": 128000, "max_tokens": 8000,
                        "capabilities": ["tools"], "status": None}],
    },
}


def test_engine_is_native_only_for_openai_compatible_chat():
    by_id = {p["id"]: p for p in CATALOG["providers"]}
    assert pc.engine_for(by_id["openrouter"]) == "native"
    assert pc.engine_for(by_id["lmstudio"]) == "native"
    assert pc.engine_for(by_id["anthropic"]) == "cline"
    assert pc.engine_for(by_id["claude-code"]) == "cline"


def test_readiness_is_a_checked_fact_and_never_reads_the_key_value():
    class Env(dict):
        def get(self, key, default=None):
            if key == "OPENROUTER_API_KEY":
                return "present"
            return default

    rows = {r["id"]: r for r in pc.provider_rows(CATALOG, environ=Env(), probe=lambda h, p: p == 1234)}
    assert (rows["openrouter"]["ready"], rows["openrouter"]["state"]) == (True, "key set: OPENROUTER_API_KEY")
    assert (rows["lmstudio"]["ready"], rows["lmstudio"]["state"]) == (True, "listening")
    assert (rows["anthropic"]["ready"], rows["anthropic"]["state"]) == (False, "needs ANTHROPIC_API_KEY")
    assert (rows["claude-code"]["ready"], rows["claude-code"]["state"]) == (False, "own login")
    assert "present" not in json.dumps(list(rows.values()))  # no key value leaks into rows


def test_local_endpoint_that_refuses_is_not_running():
    rows = {r["id"]: r for r in pc.provider_rows(CATALOG, environ={}, probe=lambda h, p: False)}
    assert (rows["lmstudio"]["ready"], rows["lmstudio"]["state"]) == (False, "not running")


def test_ready_providers_come_first_with_model_counts():
    rows = pc.provider_rows(CATALOG, environ={"OPENROUTER_API_KEY": "x"}, probe=lambda h, p: False)
    assert rows[0]["id"] == "openrouter" and rows[0]["models"] == 1
    assert [r["ready"] for r in rows] == sorted((r["ready"] for r in rows), reverse=True)


def test_models_come_only_from_the_catalog():
    assert pc.catalog_models(CATALOG, "openrouter")[0]["context_window"] == 128000
    assert pc.catalog_models(CATALOG, "anthropic") == []
    with pytest.raises(ValueError):
        pc.catalog_models(CATALOG, "nope")


def test_catalog_is_cached_per_version_and_failures_are_explained(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "catalog_version", lambda: "9.9.9")
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(CATALOG), stderr="")

    first = pc.load_catalog(run=run, cache_dir=tmp_path)
    second = pc.load_catalog(run=run, cache_dir=tmp_path)
    assert first == second == CATALOG and len(calls) == 1
    assert (tmp_path / "provider-catalog-9.9.9.json").is_file()

    def broken(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="Error: Cannot find module '@cline/llms'")

    with pytest.raises(pc.CatalogUnavailable, match="Cannot find module"):
        pc.load_catalog(run=broken, cache_dir=tmp_path, refresh=True)


@pytest.mark.skipif(not pc._LLMS_PACKAGE.is_file(), reason="Cline worker dependencies are not installed")
def test_real_catalog_reads_from_the_installed_package(tmp_path):
    catalog = pc.load_catalog(cache_dir=tmp_path)
    ids = {p["id"] for p in catalog["providers"]}
    assert {"openrouter", "lmstudio", "anthropic"} <= ids
    assert sum(len(v) for v in catalog["models"].values()) > 1000
