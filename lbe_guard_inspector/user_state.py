"""Versioned per-user LBE runtime state.

This module owns only local configuration references.  It deliberately never
serializes credentials; provider records contain a credential identifier or no
credential reference for local endpoints.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


STATE_SCHEMA_VERSION = 1


def default_state_root() -> Path:
    """Return the versioned user-state root, outside the current workspace."""
    configured = os.environ.get("LBE_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return (Path(appdata) / "LetterBlack" / "LBE" / "v1").resolve()
    return (Path.home() / ".lbe" / "v1").resolve()


@dataclass(frozen=True)
class ProviderProfile:
    provider_id: str
    model: str
    endpoint: str
    timeout_seconds: float
    credential_id: str | None = None

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (self.provider_id, self.model, self.endpoint)):
            raise ValueError("provider_id, model, and endpoint must be non-empty strings")
        if not isinstance(self.timeout_seconds, (int, float)) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.credential_id is not None and (not isinstance(self.credential_id, str) or not self.credential_id.strip()):
            raise ValueError("credential_id must be a non-empty string when supplied")


class UserStateStore:
    """Atomic JSON configuration store for profiles and selected profile only."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).expanduser().resolve() if root is not None else default_state_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "runtime-state.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": STATE_SCHEMA_VERSION, "profiles": {}, "active_profile": None}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid user runtime state: {self.path}: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema_version") != STATE_SCHEMA_VERSION:
            raise ValueError("unsupported user runtime state schema")
        if not isinstance(data.get("profiles"), dict):
            raise ValueError("invalid user runtime state profiles")
        return data

    def profiles(self) -> dict[str, ProviderProfile]:
        return {name: _profile_from_mapping(value) for name, value in self.load()["profiles"].items()}

    def active_profile_name(self) -> str | None:
        value = self.load().get("active_profile")
        return value if isinstance(value, str) and value else None

    def save_profile(self, name: str, profile: ProviderProfile, *, activate: bool = False) -> None:
        _profile_name(name)
        data = self.load()
        data["profiles"][name] = asdict(profile)
        if activate:
            data["active_profile"] = name
        self._write(data)

    def select_profile(self, name: str) -> ProviderProfile:
        profiles = self.profiles()
        if name not in profiles:
            raise ValueError(f"provider profile not found: {name}")
        data = self.load()
        data["active_profile"] = name
        self._write(data)
        return profiles[name]

    def remove_profile(self, name: str) -> ProviderProfile:
        data = self.load()
        raw = data["profiles"].pop(name, None)
        if raw is None:
            raise ValueError(f"provider profile not found: {name}")
        if data.get("active_profile") == name:
            data["active_profile"] = None
        self._write(data)
        return _profile_from_mapping(raw)

    def _write(self, data: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)


def _profile_name(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or any(char in value for char in "\\/\0"):
        raise ValueError("profile name must be a non-empty simple identifier")


def _profile_from_mapping(raw: Any) -> ProviderProfile:
    if not isinstance(raw, dict):
        raise ValueError("invalid provider profile record")
    unknown = set(raw) - {"provider_id", "model", "endpoint", "timeout_seconds", "credential_id"}
    if unknown:
        raise ValueError(f"invalid provider profile fields: {sorted(unknown)}")
    try:
        return ProviderProfile(**raw)
    except TypeError as exc:
        raise ValueError("invalid provider profile record") from exc
