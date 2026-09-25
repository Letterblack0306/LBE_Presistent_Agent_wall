from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _runtime_env(tmp_path: Path, roots: list[dict[str, str]]) -> dict[str, str]:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"knowledge_roots": roots}), encoding="utf-8")
    governance = tmp_path / "governance.json"
    governance.write_text(
        json.dumps({"allowed_read_paths": ["."], "forbidden_globs": []}),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["LBE_GUARD_INSPECTOR_CONFIG_PATH"] = str(config)
    env["LBE_GUARD_INSPECTOR_GOVERNANCE_PATH"] = str(governance)
    return env


def _roots(tmp_path: Path, roots: list[dict[str, str]]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "agent.py", "roots"],
        cwd=REPOSITORY_ROOT,
        env=_runtime_env(tmp_path, roots),
        capture_output=True,
        text=True,
    )


def test_absent_configured_root_is_reported_instead_of_failing_the_run(tmp_path: Path) -> None:
    """A configured root that is not present (for example an unmounted drive) must not
    abort every run: it stays visible as missing so reduced knowledge scope is never
    reported as full coverage."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    absent = tmp_path / "unmounted" / "developments"

    result = _roots(
        tmp_path,
        [
            {"name": "workspace", "path": str(workspace)},
            {"name": "offline-drive", "path": str(absent)},
        ],
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [item["name"] for item in payload["knowledge_roots"]] == ["workspace"]
    assert payload["missing_knowledge_roots"] == [
        {
            "name": "offline-drive",
            "path": str(absent.resolve()),
            "reason": "configured path is not present on this machine",
        }
    ]


def test_no_present_root_still_fails_closed(tmp_path: Path) -> None:
    """Degrading per root must not degrade to zero-evidence runs: when nothing is
    present the context refuses to load instead of pretending to have a knowledge scope."""
    result = _roots(
        tmp_path,
        [{"name": "offline-drive", "path": str(tmp_path / "missing")}],
    )

    assert result.returncode != 0
    assert "No configured knowledge root is present on this machine" in (
        result.stdout + result.stderr
    )
