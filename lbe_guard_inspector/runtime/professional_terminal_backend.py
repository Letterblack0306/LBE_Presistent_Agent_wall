"""P5 synchronous terminal.exec backend with explicit fixed-command authority.

This backend deliberately does not accept free-form shell commands or arbitrary
argv. Host code must register exact command vectors under stable command IDs.
That preserves the active-workspace boundary until a stronger sandbox/process
backend exists.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .tool_orchestration import (
    ToolAccessClass,
    ToolExecutionResult,
    ToolNetworkBehavior,
    ToolRegistry,
    ToolRequest,
    ToolRiskClass,
    ToolSpec,
)


@dataclass(frozen=True)
class TerminalCommandPolicy:
    command_id: str
    argv: tuple[str, ...]
    timeout_seconds: float = 120.0
    network_behavior: ToolNetworkBehavior = ToolNetworkBehavior.NONE

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, str) or not self.command_id.strip():
            raise ValueError("command_id must be a non-empty string")
        if not self.argv or not all(isinstance(arg, str) and arg for arg in self.argv):
            raise ValueError("argv must contain non-empty strings")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class TerminalCommandPolicyCatalog:
    def __init__(self, policies: tuple[TerminalCommandPolicy, ...]) -> None:
        by_id: dict[str, TerminalCommandPolicy] = {}
        for policy in policies:
            if not isinstance(policy, TerminalCommandPolicy):
                raise TypeError("policies must contain TerminalCommandPolicy")
            key = policy.command_id.strip()
            if key in by_id:
                raise ValueError(f"duplicate terminal command policy: {key}")
            by_id[key] = policy
        self._by_id = by_id

    def get(self, command_id: str) -> TerminalCommandPolicy | None:
        return self._by_id.get(command_id.strip())

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id))


def terminal_exec_spec(*, network_behavior: ToolNetworkBehavior = ToolNetworkBehavior.NONE) -> ToolSpec:
    return ToolSpec(
        tool_id="terminal.exec",
        capability="test_candidate",
        required_arguments=("command_id",),
        optional_arguments=(),
        access_class=ToolAccessClass.WRITE,
        network_behavior=network_behavior,
        risk_class=ToolRiskClass.MEDIUM,
        timeout_seconds=300.0,
        retry_policy="none",
        preconditions=(
            "coding mode delegates test_candidate",
            "command_id is registered by host policy",
            "cwd is fixed to active workspace root",
        ),
        expected_evidence=("exit code", "stdout", "stderr", "registered command identity"),
        failure_modes=("unknown command policy", "timeout", "process launch failure", "authorization failure"),
    )


def register_terminal_exec_backend(*, registry: ToolRegistry, catalog: TerminalCommandPolicyCatalog) -> ToolSpec:
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be ToolRegistry")
    if not isinstance(catalog, TerminalCommandPolicyCatalog):
        raise TypeError("catalog must be TerminalCommandPolicyCatalog")

    spec = terminal_exec_spec(network_behavior=_catalog_network_behavior(catalog))
    registry.register(spec, build_terminal_exec_handler(catalog))
    return spec


def build_terminal_exec_handler(catalog: TerminalCommandPolicyCatalog):
    def handler(request: ToolRequest) -> ToolExecutionResult:
        command_id = request.arguments["command_id"]
        if not isinstance(command_id, str) or not command_id.strip():
            raise ValueError("command_id must be a non-empty string")
        policy = catalog.get(command_id)
        if policy is None:
            raise ValueError("terminal command is not registered by host policy")

        root = Path(request.context.workspace_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError("active workspace root does not exist")

        try:
            completed = subprocess.run(
                policy.argv,
                cwd=root,
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=policy.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"terminal command timed out: {policy.command_id}") from exc

        output = {
            "command_id": policy.command_id,
            "argv": list(policy.argv),
            "cwd": str(root),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        evidence = ({
            "source_class": "terminal_exec_receipt",
            "command_id": policy.command_id,
            "exit_code": completed.returncode,
            "cwd": str(root),
        },)
        return ToolExecutionResult(output=output, evidence=evidence)

    return handler


def _catalog_network_behavior(catalog: TerminalCommandPolicyCatalog) -> ToolNetworkBehavior:
    behaviors = {policy.network_behavior for policy in catalog._by_id.values()}
    if ToolNetworkBehavior.REQUIRED in behaviors:
        return ToolNetworkBehavior.REQUIRED
    if ToolNetworkBehavior.OPTIONAL in behaviors:
        return ToolNetworkBehavior.OPTIONAL
    return ToolNetworkBehavior.NONE
