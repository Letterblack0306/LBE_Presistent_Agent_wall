from __future__ import annotations

import sys
from pathlib import Path

from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.professional_terminal_backend import (
    TerminalCommandPolicy,
    TerminalCommandPolicyCatalog,
    register_terminal_exec_backend,
)
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
)


def _context(root: Path, *, mode: str = "coding") -> ToolExecutionContext:
    capabilities = ("test_candidate",) if mode == "coding" else ("inspect",)
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode=mode,
            allowed_behaviors=("development_mode_capabilities",) if mode == "coding" else ("audit_mode_constraints",),
            capabilities=capabilities,
            rationale="test",
        ),
        workspace_id="workspace-1",
        workspace_root=root,
        configured_root_id="dev",
    )


def _runtime(root: Path):
    catalog = TerminalCommandPolicyCatalog((
        TerminalCommandPolicy(
            command_id="python.version",
            argv=(sys.executable, "--version"),
            timeout_seconds=15.0,
        ),
        TerminalCommandPolicy(
            command_id="python.cwd",
            argv=(sys.executable, "-c", "import os; print(os.getcwd())"),
            timeout_seconds=15.0,
        ),
    ))
    registry = ToolRegistry()
    spec = register_terminal_exec_backend(registry=registry, catalog=catalog)
    return catalog, GovernedToolOrchestrator(registry=registry), spec


def test_executes_only_registered_fixed_command_in_workspace(tmp_path: Path) -> None:
    _, orchestrator, spec = _runtime(tmp_path)
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-terminal",
        tool_id="terminal.exec",
        arguments={"command_id": "python.cwd"},
        context=_context(tmp_path),
    ))

    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.output is not None
    assert receipt.output["command_id"] == "python.cwd"
    assert Path(receipt.output["stdout"].strip()).resolve() == tmp_path.resolve()
    assert receipt.output["cwd"] == str(tmp_path.resolve())
    assert receipt.output["exit_code"] == 0
    assert spec.access_class.value == "write"
    assert spec.capability == "test_candidate"


def test_unknown_command_id_fails_closed_without_execution(tmp_path: Path) -> None:
    _, orchestrator, _ = _runtime(tmp_path)
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-unknown",
        tool_id="terminal.exec",
        arguments={"command_id": "shell.anything"},
        context=_context(tmp_path),
    ))
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "TOOL_EXECUTION_FAILED"
    assert "not registered" in (receipt.error_message or "")


def test_provider_cannot_supply_argv_cwd_or_shell_fields(tmp_path: Path) -> None:
    _, orchestrator, _ = _runtime(tmp_path)
    for index, arguments in enumerate((
        {"command_id": "python.version", "argv": ["cmd", "/c", "echo", "x"]},
        {"command_id": "python.version", "cwd": ".."},
        {"command_id": "python.version", "shell": True},
    )):
        receipt = orchestrator.invoke(ToolRequest(
            operation_id=f"op-extra-{index}",
            tool_id="terminal.exec",
            arguments=arguments,
            context=_context(tmp_path),
        ))
        assert receipt.status is ToolReceiptStatus.FAILED
        assert receipt.error_code == "INVALID_TOOL_ARGUMENTS"


def test_terminal_exec_escalates_outside_coding_delegation(tmp_path: Path) -> None:
    _, orchestrator, _ = _runtime(tmp_path)
    receipt = orchestrator.invoke(ToolRequest(
        operation_id="op-audit",
        tool_id="terminal.exec",
        arguments={"command_id": "python.version"},
        context=_context(tmp_path, mode="audit"),
    ))
    assert receipt.status is ToolReceiptStatus.ESCALATED


def test_catalog_rejects_duplicate_command_ids() -> None:
    policy = TerminalCommandPolicy(command_id="same", argv=(sys.executable, "--version"))
    try:
        TerminalCommandPolicyCatalog((policy, policy))
    except ValueError as exc:
        assert "duplicate terminal command policy" in str(exc)
    else:
        raise AssertionError("duplicate command IDs must fail closed")


def test_policy_rejects_empty_or_invalid_commands() -> None:
    for kwargs in (
        {"command_id": "", "argv": (sys.executable,)},
        {"command_id": "ok", "argv": ()},
        {"command_id": "ok", "argv": ("",)},
        {"command_id": "ok", "argv": (sys.executable,), "timeout_seconds": 0},
    ):
        try:
            TerminalCommandPolicy(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid terminal policy should fail: {kwargs}")
