"""The opened project must become the knowledge root for an installed terminal."""
import json
from pathlib import Path

import pytest

from lbe_guard_inspector import terminal_ui


_KEYS = (
    "LBE_GUARD_INSPECTOR_CONFIG_PATH",
    "LBE_GUARD_INSPECTOR_STATE_DIR",
    "LBE_GUARD_INSPECTOR_GOVERNANCE_PATH",
)


@pytest.fixture(autouse=True)
def _clean_env():
    """The helper writes os.environ directly; restore it so nothing leaks."""
    import os

    saved = {key: os.environ.pop(key, None) for key in _KEYS}
    yield
    for key, value in saved.items():
        os.environ.pop(key, None)
        if value is not None:
            os.environ[key] = value


def _shipped(monkeypatch, roots):
    monkeypatch.setattr(
        terminal_ui, "_shipped_runtime_config",
        lambda: {"knowledge_roots": roots, "max_file_bytes": 123, "write_enabled": False},
    )


def test_unconfigured_project_becomes_the_only_knowledge_root(tmp_path, monkeypatch) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _shipped(monkeypatch, [{"name": "dev", "path": str(tmp_path / "elsewhere")}])
    terminal_ui._ensure_workspace_runtime_config(project, tmp_path / "state" / "lbe.sqlite3")
    import os
    config_path = Path(os.environ["LBE_GUARD_INSPECTOR_CONFIG_PATH"])
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["knowledge_roots"] == [{"name": "project", "path": str(project)}]
    assert config["max_file_bytes"] == 123  # shipped defaults preserved
    assert config_path.is_relative_to(tmp_path / "state")
    assert Path(os.environ["LBE_GUARD_INSPECTOR_STATE_DIR"]).is_relative_to(tmp_path / "state")


def test_project_already_inside_a_configured_root_is_left_alone(tmp_path, monkeypatch) -> None:
    root = tmp_path / "root"
    project = root / "sub"
    project.mkdir(parents=True)
    _shipped(monkeypatch, [{"name": "dev", "path": str(root)}])
    terminal_ui._ensure_workspace_runtime_config(project, tmp_path / "state" / "lbe.sqlite3")
    import os
    assert "LBE_GUARD_INSPECTOR_CONFIG_PATH" not in os.environ


def test_explicit_config_path_always_wins(tmp_path, monkeypatch) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    monkeypatch.setenv("LBE_GUARD_INSPECTOR_CONFIG_PATH", "C:/explicit.json")
    _shipped(monkeypatch, [])
    terminal_ui._ensure_workspace_runtime_config(project, tmp_path / "state" / "lbe.sqlite3")
    import os
    assert os.environ["LBE_GUARD_INSPECTOR_CONFIG_PATH"] == "C:/explicit.json"


def test_generated_config_is_stable_across_launches(tmp_path, monkeypatch) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _shipped(monkeypatch, [])
    database = tmp_path / "state" / "lbe.sqlite3"
    terminal_ui._ensure_workspace_runtime_config(project, database)
    import os
    first = os.environ.pop("LBE_GUARD_INSPECTOR_CONFIG_PATH")
    os.environ.pop("LBE_GUARD_INSPECTOR_STATE_DIR")
    terminal_ui._ensure_workspace_runtime_config(project, database)
    assert os.environ["LBE_GUARD_INSPECTOR_CONFIG_PATH"] == first


def test_user_authored_workspace_policy_outside_project_is_honored(tmp_path, monkeypatch) -> None:
    import hashlib, os
    project = tmp_path / "proj"
    project.mkdir()
    _shipped(monkeypatch, [])
    database = tmp_path / "state" / "lbe.sqlite3"
    identity = hashlib.sha256(str(project).lower().encode("utf-8")).hexdigest()[:16]
    policy = database.parent / "workspaces" / identity / "governance.json"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"allowed_write_paths": ["hello.txt"]}), encoding="utf-8")
    monkeypatch.delenv("LBE_GUARD_INSPECTOR_GOVERNANCE_PATH", raising=False)
    terminal_ui._ensure_workspace_runtime_config(project, database)
    assert os.environ["LBE_GUARD_INSPECTOR_GOVERNANCE_PATH"] == str(policy)
    monkeypatch.delenv("LBE_GUARD_INSPECTOR_GOVERNANCE_PATH", raising=False)


def test_no_workspace_policy_leaves_shipped_fail_closed_governance(tmp_path, monkeypatch) -> None:
    import os
    project = tmp_path / "proj"
    project.mkdir()
    _shipped(monkeypatch, [])
    monkeypatch.delenv("LBE_GUARD_INSPECTOR_GOVERNANCE_PATH", raising=False)
    terminal_ui._ensure_workspace_runtime_config(project, tmp_path / "state" / "lbe.sqlite3")
    assert "LBE_GUARD_INSPECTOR_GOVERNANCE_PATH" not in os.environ
