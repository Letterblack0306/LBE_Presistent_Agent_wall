from __future__ import annotations

from pathlib import Path

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import ItemStatus, SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.professional_history_runtime import ProfessionalTurnHistoryRecorder
from lbe_guard_inspector.professional_provider_events import ModelEventType, NormalizedModelEvent
from lbe_guard_inspector.provider_capabilities import ProviderProtocolFamily
from lbe_guard_inspector.runtime.professional_command_events import CommandEvent, CommandEventType
from lbe_guard_inspector.runtime.tool_orchestration import ToolReceipt, ToolReceiptStatus


FAMILY = ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT


def _history(tmp_path: Path) -> SessionOperationalHistory:
    store = WorkspaceMemoryStore(tmp_path / "memory.sqlite3")
    store.save_session_state(SessionState(
        session_id="session-1",
        project_workspace_id="workspace-1",
        canonical_workspace_root=tmp_path,
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
        provider_id="openai-compatible",
        provider_model="model-a",
    ))
    return SessionOperationalHistory(store=store)


def _event(event_type: ModelEventType, **kwargs) -> NormalizedModelEvent:
    return NormalizedModelEvent(
        event_type=event_type,
        provider_id="openai-compatible",
        model_id="model-a",
        protocol_family=FAMILY,
        **kwargs,
    )


def _proposal() -> NormalizedModelEvent:
    return _event(
        ModelEventType.TOOL_CALL_COMPLETED,
        provider_request_id="response-1",
        provider_item_id="item-1",
        provider_tool_call_id="provider-call-1",
        lbe_call_id="lbe-call-1",
        tool_name="terminal.exec",
        tool_arguments={"command_id": "test.live"},
    )


def _recorder(tmp_path: Path, operation_id: str) -> tuple[SessionOperationalHistory, ProfessionalTurnHistoryRecorder]:
    history = _history(tmp_path)
    recorder = ProfessionalTurnHistoryRecorder(history=history, session_id="session-1")
    recorder.observe_model_event(_event(ModelEventType.TURN_STARTED, provider_request_id="response-1"))
    proposal = _proposal()
    recorder.observe_model_event(proposal)
    recorder.observe_model_event(_event(
        ModelEventType.TURN_REQUIRES_TOOL,
        provider_request_id="response-1",
        provider_tool_call_id="provider-call-1",
        lbe_call_id="lbe-call-1",
        tool_name="terminal.exec",
    ))
    recorder.observe_tool_started(proposal, operation_id)
    return history, recorder


def test_real_command_deltas_project_to_generic_tool_output_and_progress(tmp_path: Path) -> None:
    history, recorder = _recorder(tmp_path, "runtime-op-1")
    recorder.observe_runtime_event(CommandEvent(
        event_type=CommandEventType.STDOUT_DELTA,
        operation_id="runtime-op-1",
        command_id="test.live",
        sequence=1,
        elapsed_seconds=0.1,
        text="hello\n",
    ))
    recorder.observe_runtime_event(CommandEvent(
        event_type=CommandEventType.STDERR_DELTA,
        operation_id="runtime-op-1",
        command_id="test.live",
        sequence=2,
        elapsed_seconds=0.2,
        text="warn\n",
    ))
    recorder.observe_runtime_event(CommandEvent(
        event_type=CommandEventType.PROGRESS,
        operation_id="runtime-op-1",
        command_id="test.live",
        sequence=3,
        elapsed_seconds=0.5,
        metadata={"running": True},
    ))
    receipt = ToolReceipt(
        operation_id="runtime-op-1",
        tool_id="terminal.exec",
        status=ToolReceiptStatus.EXECUTED,
        authorization=None,
        output={"exit_code": 0},
    )
    recorder.observe_tool_receipt(_proposal(), receipt)

    events = history.events_for_turn(turn_id=recorder.turn_id)
    event_types = [event.event_type for event in events]
    assert event_types.count("tool.output.delta") == 2
    assert event_types.count("tool.progress") == 1
    output_events = [event for event in events if event.event_type == "tool.output.delta"]
    assert [event.payload["stream"] for event in output_events] == ["stdout", "stderr"]
    assert [event.payload["text"] for event in output_events] == ["hello\n", "warn\n"]
    live_events = [event for event in events if event.event_type.startswith("command.") or event.event_type in {"tool.output.delta", "tool.progress", "tool.completed"}]
    assert {event.item_id for event in live_events} == {live_events[0].item_id}
    assert {event.runtime_operation_id for event in live_events} == {"runtime-op-1"}


def test_command_cancellation_projects_tool_cancelled_and_cancelled_item(tmp_path: Path) -> None:
    history, recorder = _recorder(tmp_path, "runtime-op-cancel")
    recorder.observe_runtime_event(CommandEvent(
        event_type=CommandEventType.CANCELLED,
        operation_id="runtime-op-cancel",
        command_id="test.live",
        sequence=1,
        elapsed_seconds=0.25,
        metadata={"exit_code": -15},
    ))
    receipt = ToolReceipt(
        operation_id="runtime-op-cancel",
        tool_id="terminal.exec",
        status=ToolReceiptStatus.FAILED,
        authorization=None,
        error_code="TOOL_EXECUTION_FAILED",
        error_message="RuntimeError: terminal command was cancelled",
    )
    recorder.observe_tool_receipt(_proposal(), receipt)

    events = history.events_for_turn(turn_id=recorder.turn_id)
    assert [event.event_type for event in events][-2:] == ["command.cancelled", "tool.cancelled"]
    terminal = events[-1]
    assert terminal.payload["cancelled_by_runtime_event"] is True
    assert terminal.runtime_operation_id == "runtime-op-cancel"
    assert terminal.tool_receipt_id == receipt.receipt_id
    assert history.get_item(item_id=terminal.item_id).status is ItemStatus.CANCELLED
