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
