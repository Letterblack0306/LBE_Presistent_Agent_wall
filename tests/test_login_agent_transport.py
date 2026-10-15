"""Login-based platforms are reached through their installed CLI, tools off."""
import json
import sys
from pathlib import Path

import pytest

from lbe_guard_inspector import login_agent_transport as lat
from lbe_guard_inspector.provider_registry import default_provider_registry
from lbe_guard_inspector.reasoning_provider import ProviderConfig, ProviderError
from lbe_guard_inspector.runtime.provider_event_adapters import build_native_provider_event_adapter
from lbe_guard_inspector.professional_provider_events import ModelEventType


def _fake_cli(tmp_path: Path, body: str) -> str:
    script = tmp_path / "fakecli.py"
    script.write_text(body, encoding="utf-8")
    launcher = tmp_path / ("fakecli.cmd" if sys.platform == "win32" else "fakecli")
    if sys.platform == "win32":
        launcher.write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)
    return str(launcher)


_PAYLOAD = {
    "model": "default",
    "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
    "response_format": {"type": "json_schema", "json_schema": {"schema": {"type": "object"}}},
}


def test_registry_binds_login_platforms_to_native_engine() -> None:
    registry = default_provider_registry()
    for provider_id in lat.LOGIN_AGENT_SPECS:
        handle = registry.build(
            provider_id=provider_id,
            config=ProviderConfig(endpoint=lat.ENDPOINT_SCHEME + provider_id, model="default",
                                  timeout_seconds=5, provider_id=provider_id),
        )
        assert handle.descriptor.provider_id == provider_id
        assert handle.engine_id == "native-lbe"


def test_cli_answer_is_returned_as_chat_completion(monkeypatch, tmp_path) -> None:
    cli = _fake_cli(tmp_path, "import sys; sys.stdin.read(); print('{\"ok\": true}')")
    monkeypatch.setattr(lat.shutil, "which", lambda name: cli)
    reply = lat.LoginAgentTransport("claude-code").post_json(
        endpoint="login-agent://claude-code", payload=_PAYLOAD, headers={}, timeout_seconds=30)
    assert json.loads(reply["choices"][0]["message"]["content"]) == {"ok": True}


def test_cli_runs_in_empty_scratch_directory_not_the_workspace(monkeypatch, tmp_path) -> None:
    cli = _fake_cli(tmp_path, "import os,sys; sys.stdin.read(); print(os.getcwd()); print(os.listdir('.'))")
    monkeypatch.setattr(lat.shutil, "which", lambda name: cli)
    reply = lat.LoginAgentTransport("gemini-cli").post_json(
        endpoint="x", payload=_PAYLOAD, headers={}, timeout_seconds=30)
    text = reply["choices"][0]["message"]["content"]
    assert "lbe-login-agent-" in text and text.rstrip().endswith("[]")


def test_missing_cli_reports_login_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(lat.shutil, "which", lambda name: None)
    with pytest.raises(ProviderError) as err:
        lat.LoginAgentTransport("openai-codex-cli").post_json(
            endpoint="x", payload=_PAYLOAD, headers={}, timeout_seconds=5)
    assert err.value.code == "PROVIDER_LOGIN_UNAVAILABLE"


def test_logged_out_cli_reports_login_required(monkeypatch, tmp_path) -> None:
    cli = _fake_cli(tmp_path, "import sys; sys.stdin.read(); sys.stderr.write('Not logged in'); sys.exit(1)")
    monkeypatch.setattr(lat.shutil, "which", lambda name: cli)
    with pytest.raises(ProviderError) as err:
        lat.LoginAgentTransport("claude-code").post_json(
            endpoint="x", payload=_PAYLOAD, headers={}, timeout_seconds=30)
    assert err.value.code == "PROVIDER_LOGIN_REQUIRED"


def test_tools_are_disabled_in_every_binding() -> None:
    assert "--tools" in lat._claude_args("", "s", "o") and "-s" in lat._codex_args("", "s", "o")
    assert "read-only" in lat._codex_args("", "s", "o")
    assert "yolo" not in " ".join(lat._gemini_args("", "s", "o"))


def test_new_platform_is_added_from_json_without_code(monkeypatch, tmp_path) -> None:
    cli = _fake_cli(tmp_path, "import sys; print('args=' + ' '.join(sys.argv[1:])); sys.stdin.read()")
    monkeypatch.setattr(lat.shutil, "which", lambda name: cli)
    monkeypatch.setitem(lat.LOGIN_AGENT_SPECS, "x", lat.LOGIN_AGENT_SPECS["claude-code"])
    lat.LOGIN_AGENT_SPECS.pop("x")
    path = tmp_path / "agents.json"
    path.write_text(json.dumps({"acme-cli": {
        "executable": "acme", "args": ["run", "--quiet"], "model_args": ["-m", "{model}"]}}))
    monkeypatch.setattr(lat, "LOGIN_AGENT_SPECS", dict(lat.LOGIN_AGENT_SPECS))
    added = lat.load_extra_login_agents(path)
    assert set(added) == {"acme-cli"}
    reply = lat.LoginAgentTransport("acme-cli").post_json(
        endpoint="x", payload={**_PAYLOAD, "model": "big"}, headers={}, timeout_seconds=30)
    assert "args=run --quiet -m big" in reply["choices"][0]["message"]["content"]


def test_bad_spec_is_rejected() -> None:
    with pytest.raises(ValueError):
        lat.spec_from_mapping("p", {"args": ["x"]})


def test_login_cli_proposes_only_offered_lbe_tool(monkeypatch, tmp_path) -> None:
    cli = _fake_cli(tmp_path, "import sys; sys.stdin.read(); print('{\"tool_calls\": [{\"name\": \"workspace_read\", \"arguments\": {\"path\": \"notes.txt\"}}]}')")
    monkeypatch.setattr(lat.shutil, "which", lambda name: cli)
    config = ProviderConfig(endpoint="login-agent://claude-code", model="default",
                            timeout_seconds=30, provider_id="claude-code")
    adapter = build_native_provider_event_adapter(provider_id="claude-code", config=config)
    events = adapter.complete(
        messages=({"role": "user", "content": "Read notes"},), provider_id="claude-code",
        lbe_call_id_for_provider_tool_call=lambda call_id: "lbe-child-1",
        tools=({"type": "function", "function": {"name": "workspace_read", "parameters": {"type": "object"}}},),
    )
    call = next(event for event in events if event.event_type is ModelEventType.TOOL_CALL_COMPLETED)
    assert call.tool_name == "workspace_read"
    assert call.tool_arguments == {"path": "notes.txt"}
    assert call.lbe_call_id == "lbe-child-1"


def test_login_cli_rejects_unoffered_tool(monkeypatch, tmp_path) -> None:
    cli = _fake_cli(tmp_path, "import sys; sys.stdin.read(); print('{\"tool_calls\": [{\"name\": \"unsafe\", \"arguments\": {}}]}')")
    monkeypatch.setattr(lat.shutil, "which", lambda name: cli)
    with pytest.raises(ProviderError) as err:
        lat.LoginAgentTransport("claude-code").post_json(
            endpoint="login-agent://claude-code",
            payload={**_PAYLOAD, "tools": [{"type": "function", "function": {"name": "workspace_read"}}]},
            headers={}, timeout_seconds=30,
        )
    assert err.value.code == "PROVIDER_TOOL_RESPONSE_INVALID"
