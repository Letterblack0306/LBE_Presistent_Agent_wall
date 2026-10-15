"""Catalog and read-only discovery of external coding-agent platforms.

This module describes agent platforms (CLIs) that can sit on the agent side of
the LBE boundary: the agent reasons, LBE authorizes, executes and validates.
Discovery only resolves an executable and asks it for ``--version``. It never
sends a prompt, starts a model, grants permissions, or registers a tool.

Every flag below was observed in the platform's own ``--help`` output. An empty
tuple means "not observed", never "unsupported". A catalog entry is not an
adopted execution adapter: governed use of these agents goes through LBE's
existing external-capability and R6C/R6E paths.
"""
from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class AgentPlatform:
    platform_id: str
    display_name: str
    executables: tuple[str, ...]
    headless_args: tuple[str, ...] = ()
    structured_output_args: tuple[str, ...] = ()
    mcp_client: bool = False
    acp_args: tuple[str, ...] = ()
    # Harness-owned surfaces: loaded or run by the platform itself, not chosen
    # by the agent as a tool. Observed in --help only; empty/False = not observed.
    harness_instructions: tuple[str, ...] = ()
    hooks: bool = False

    def __post_init__(self) -> None:
        if not self.platform_id.strip() or not self.executables:
            raise ValueError("platform_id and at least one executable are required")


AGENT_PLATFORMS: tuple[AgentPlatform, ...] = (
    AgentPlatform("claude-code", "Claude Code", ("claude",),
                  headless_args=("-p",),
                  structured_output_args=("--output-format", "stream-json"),
                  mcp_client=True,
                  harness_instructions=("CLAUDE.md", "--append-system-prompt"),
                  hooks=True),
    AgentPlatform("codex", "OpenAI Codex CLI", ("codex",),
                  headless_args=("exec",),
                  mcp_client=True,
                  hooks=True),
    AgentPlatform("opencode", "OpenCode", ("opencode",),
                  headless_args=("run",),
                  structured_output_args=("--format", "json"),
                  mcp_client=True),
    AgentPlatform("antigravity", "Antigravity (agy)", ("agy",),
                  headless_args=("-p",),
                  structured_output_args=("--output-format", "json"),
                  mcp_client=True),
    AgentPlatform("gemini-cli", "Gemini CLI", ("gemini",),
                  headless_args=("-p",),
                  structured_output_args=("-o", "json"),
                  mcp_client=True,
                  acp_args=("--acp",),
                  hooks=True),
    AgentPlatform("copilot-cli", "GitHub Copilot CLI", ("copilot",),
                  headless_args=("-p",),
                  mcp_client=True,
                  acp_args=("--acp",),
                  harness_instructions=("AGENTS.md",)),
    AgentPlatform("cline", "Cline", ("cline",),
                  structured_output_args=("--json",),
                  mcp_client=True,
                  acp_args=("--acp",),
                  harness_instructions=("--system",),
                  hooks=True),
)

Which = Callable[[str], "str | None"]
Run = Callable[..., "subprocess.CompletedProcess[str]"]


def discover_agent_platforms(
    *,
    platforms: Sequence[AgentPlatform] = AGENT_PLATFORMS,
    which: Which = shutil.which,
    run: Run = subprocess.run,
    timeout_seconds: float = 15.0,
) -> list[dict[str, Any]]:
    """Return one read-only discovery record per platform."""
    records: list[dict[str, Any]] = []
    for platform in platforms:
        path = next((found for name in platform.executables if (found := which(name))), None)
        record: dict[str, Any] = {
            "platform_id": platform.platform_id,
            "display_name": platform.display_name,
            "installed": path is not None,
            "executable": path,
            "version": None,
            "headless_args": list(platform.headless_args),
            "structured_output_args": list(platform.structured_output_args),
            "mcp_client": platform.mcp_client,
            "acp_args": list(platform.acp_args),
            "harness_instructions": list(platform.harness_instructions),
            "hooks": platform.hooks,
            "adapter": "CATALOG_ONLY",
        }
        if path is not None:
            record["version"] = _probe_version(path, run=run, timeout_seconds=timeout_seconds)
        records.append(record)
    return records


def _probe_version(path: str, *, run: Run, timeout_seconds: float) -> str | None:
    try:
        completed = run(
            [path, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    lines = (completed.stdout or completed.stderr or "").strip().splitlines()
    return lines[0].strip()[:120] if lines else None


def platform_ids() -> tuple[str, ...]:
    return tuple(platform.platform_id for platform in AGENT_PLATFORMS)


def get_platform(platform_id: str) -> AgentPlatform:
    for platform in AGENT_PLATFORMS:
        if platform.platform_id == platform_id:
            return platform
    raise KeyError(f"unknown agent platform: {platform_id}")


def platforms_payload(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    return {
        "action": "agents.list",
        "platforms": rows,
        "installed": [row["platform_id"] for row in rows if row.get("installed")],
        "note": (
            "CATALOG_ONLY: discovery does not run a model or grant authority. "
            "Governed execution uses LBE's R6C/R6E and external-capability paths."
        ),
    }
