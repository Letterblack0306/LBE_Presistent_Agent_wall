from __future__ import annotations

from pathlib import Path

from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolRegistry,
    ToolRequest,
    workspace_read_spec,
)


def test_receipt_identity_is_distinct_and_stable_across_idempotent_replay(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register(workspace_read_spec(), lambda request: ToolExecutionResult(output={"ok": True}))
    orchestrator = GovernedToolOrchestrator(registry=registry)
    context = ToolExecutionContext(
        mode_decision=ModeDecision(
            mode="coding",
            allowed_behaviors=("development_mode_capabilities",),
            capabilities=("inspect",),
            rationale="test",
        ),
        workspace_id="workspace-1",
        workspace_root=tmp_path,
        configured_root_id="dev",
    )
    request = ToolRequest(
        operation_id="runtime-op-1",
        tool_id="workspace.read",
        arguments={"path": "README.md"},
        context=context,
    )

    first = orchestrator.invoke(request)
    second = orchestrator.invoke(request)

    assert first is second
    assert first.receipt_id
    assert first.receipt_id != first.operation_id
    assert second.receipt_id == first.receipt_id
