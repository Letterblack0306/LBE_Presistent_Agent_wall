from __future__ import annotations

import json

import pytest

from lbe_guard_inspector.cli import main
from lbe_guard_inspector.user_state import ProviderProfile, UserStateStore


def test_provider_profile_persists_reference_not_secret(tmp_path) -> None:
    state = UserStateStore(tmp_path / "user-state")
    profile = ProviderProfile("local", "model-a", "http://127.0.0.1:1234/v1", 10, None)

    state.save_profile("local", profile, activate=True)

    raw = json.loads(state.path.read_text(encoding="utf-8"))
    assert raw["active_profile"] == "local"
    assert raw["profiles"]["local"] == {
        "credential_id": None,
        "endpoint": "http://127.0.0.1:1234/v1",
        "model": "model-a",
        "provider_id": "local",
        "timeout_seconds": 10,
    }


def test_provider_profile_rejects_api_key_field(tmp_path) -> None:
    state = UserStateStore(tmp_path / "user-state")
    state.path.write_text('{"schema_version": 1, "profiles": {"bad": {"provider_id": "local", "model": "m", "endpoint": "http://x", "timeout_seconds": 1, "api_key": "secret"}}, "active_profile": null}', encoding="utf-8")

    with pytest.raises(ValueError, match="invalid provider profile fields"):
        state.profiles()


def test_cli_provider_add_and_use_local_profile_without_credential(tmp_path, capsys) -> None:
    root = tmp_path / "user-state"

    assert main(["provider", "add", "--state-root", str(root), "--name", "local", "--provider", "local", "--model", "model-a", "--endpoint", "http://127.0.0.1:1234/v1", "--use"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["profile"]["credential_id"] is None
    assert "api_key" not in json.dumps(added)

    assert main(["provider", "use", "--state-root", str(root), "--name", "local"]) == 0
    selected = json.loads(capsys.readouterr().out)
    assert selected["action"] == "provider.use"
    assert UserStateStore(root).active_profile_name() == "local"


def test_cli_provider_migrate_uses_explicit_config_and_never_emits_secret(tmp_path, capsys, monkeypatch) -> None:
    root = tmp_path / "user-state"
    legacy = tmp_path / "provider.json"
    legacy.write_text(
        json.dumps({
            "endpoint": "https://provider.example/v1/chat/completions",
            "model": "model-a",
            "timeout_seconds": 10,
            "api_key": "legacy-secret",
        }),
        encoding="utf-8",
    )
    stored: dict[str, str] = {}

    class FakeCredentialStore:
        def put(self, credential_id: str, secret: str) -> None:
            stored[credential_id] = secret

    monkeypatch.setattr("lbe_guard_inspector.cli.WindowsCredentialStore", FakeCredentialStore)

    assert main([
        "provider", "migrate", "--state-root", str(root), "--name", "cloud",
        "--provider", "openai-compatible", "--provider-config", str(legacy),
        "--credential-id", "cloud-key", "--use",
    ]) == 0
    result = json.loads(capsys.readouterr().out)

    assert stored == {"cloud-key": "legacy-secret"}
    assert result["profile"]["credential_id"] == "cloud-key"
    assert result["legacy_config_removal_required"] is True
    assert "legacy-secret" not in json.dumps(result)
    assert str(legacy) not in json.dumps(result)
    persisted = UserStateStore(root).profiles()["cloud"]
    assert persisted.credential_id == "cloud-key"
    assert "legacy-secret" not in (root / "runtime-state.json").read_text(encoding="utf-8")
