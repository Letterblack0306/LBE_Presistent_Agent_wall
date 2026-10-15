from __future__ import annotations

import subprocess

import pytest

from lbe_guard_inspector.agent_platforms import (
    AGENT_PLATFORMS,
    AgentPlatform,
    discover_agent_platforms,
    get_platform,
    platform_ids,
    platforms_payload,
)


def _completed(stdout: str = "", code: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


def test_catalog_covers_major_agent_platforms_with_unique_ids() -> None:
    ids = platform_ids()
    assert len(ids) == len(set(ids))
    for expected in ("claude-code", "codex", "opencode", "antigravity", "gemini-cli", "copilot-cli", "cline"):
        assert expected in ids


def test_discovery_reports_installed_and_missing_without_running_models() -> None:
    calls: list[list[str]] = []

    def which(name: str):
        return {"claude": "C:/bin/claude.exe", "codex": "C:/bin/codex.cmd"}.get(name)

    def run(argv, **kwargs):
        calls.append(list(argv))
        return _completed("tool 1.2.3\nsecond line")

    records = {r["platform_id"]: r for r in discover_agent_platforms(which=which, run=run)}
    assert records["claude-code"]["installed"] is True
    assert records["claude-code"]["version"] == "tool 1.2.3"
    assert records["opencode"]["installed"] is False
    assert records["opencode"]["version"] is None
    # only --version probes; never a prompt or headless invocation
    assert calls and all(argv[1:] == ["--version"] for argv in calls)
    assert all(r["adapter"] == "CATALOG_ONLY" for r in records.values())


def test_version_probe_failure_is_not_fatal() -> None:
    def run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 1)

    records = discover_agent_platforms(
        platforms=(AgentPlatform("x", "X", ("x",)),),
        which=lambda name: "C:/bin/x.exe",
        run=run,
    )
    assert records[0]["installed"] is True
    assert records[0]["version"] is None


def test_unknown_platform_and_invalid_definition_rejected() -> None:
    with pytest.raises(KeyError):
        get_platform("nope")
    with pytest.raises(ValueError):
        AgentPlatform("", "Blank", ("x",))
    assert get_platform("antigravity").executables == ("agy",)
    assert len(AGENT_PLATFORMS) >= 7


def test_payload_lists_installed_ids() -> None:
    payload = platforms_payload([{"platform_id": "a", "installed": True}, {"platform_id": "b", "installed": False}])
    assert payload["installed"] == ["a"]
    assert payload["action"] == "agents.list"


def test_catalog_records_harness_owned_surfaces_separately_from_tools() -> None:
    claude = get_platform("claude-code")
    assert claude.hooks is True and "CLAUDE.md" in claude.harness_instructions
    assert get_platform("gemini-cli").hooks is True
    # not observed means False/empty, never assumed
    assert get_platform("opencode").hooks is False
    assert get_platform("opencode").harness_instructions == ()
