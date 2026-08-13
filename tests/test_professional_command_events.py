from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from lbe_guard_inspector.runtime.professional_command_events import (
    CommandCancellation,
    CommandEventType,
    stream_registered_command,
)
from lbe_guard_inspector.runtime.professional_terminal_backend import TerminalCommandPolicy


def _policy(code: str, *, timeout: float = 5.0) -> TerminalCommandPolicy:
    return TerminalCommandPolicy(
        command_id="python.stream",
        argv=(sys.executable, "-u", "-c", code),
        timeout_seconds=timeout,
    )


def test_streams_stdout_stderr_before_completion(tmp_path: Path) -> None:
    policy = _policy(
        "import sys,time; print('out-1', flush=True); "
        "print('err-1', file=sys.stderr, flush=True); time.sleep(0.15); print('out-2', flush=True)"
    )
    events = list(stream_registered_command(
        operation_id="op-stream",
        policy=policy,
        workspace_root=tmp_path,
        progress_interval_seconds=0.05,
    ))

    types = [event.event_type for event in events]
    assert types[0] is CommandEventType.STARTED
    assert types[-1] is CommandEventType.COMPLETED
    assert CommandEventType.STDOUT_DELTA in types
    assert CommandEventType.STDERR_DELTA in types
    assert CommandEventType.PROGRESS in types
    assert "out-1" in "".join(event.text or "" for event in events if event.event_type is CommandEventType.STDOUT_DELTA)
    assert "out-2" in "".join(event.text or "" for event in events if event.event_type is CommandEventType.STDOUT_DELTA)
    assert "err-1" in "".join(event.text or "" for event in events if event.event_type is CommandEventType.STDERR_DELTA)
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert events[-1].exit_code == 0


def test_nonzero_exit_emits_failed_after_observed_output(tmp_path: Path) -> None:
    events = list(stream_registered_command(
        operation_id="op-fail",
        policy=_policy("import sys; print('before-fail', flush=True); sys.exit(7)"),
        workspace_root=tmp_path,
    ))
    assert events[0].event_type is CommandEventType.STARTED
    assert any(event.event_type is CommandEventType.STDOUT_DELTA for event in events)
    assert events[-1].event_type is CommandEventType.FAILED
    assert events[-1].exit_code == 7
    assert events[-1].metadata["reason"] == "nonzero_exit"


def test_timeout_emits_failed_timeout_without_completed(tmp_path: Path) -> None:
    events = list(stream_registered_command(
        operation_id="op-timeout",
        policy=_policy("import time; print('started', flush=True); time.sleep(5)", timeout=0.15),
        workspace_root=tmp_path,
        progress_interval_seconds=0.05,
    ))
    assert events[0].event_type is CommandEventType.STARTED
    assert events[-1].event_type is CommandEventType.FAILED
    assert events[-1].metadata["reason"] == "timeout"
    assert CommandEventType.COMPLETED not in [event.event_type for event in events]


def test_external_cancellation_emits_cancelled(tmp_path: Path) -> None:
    cancellation = CommandCancellation()

    def cancel_soon() -> None:
        time.sleep(0.12)
        cancellation.cancel()

    thread = threading.Thread(target=cancel_soon)
    thread.start()
    events = list(stream_registered_command(
        operation_id="op-cancel",
        policy=_policy("import time; print('running', flush=True); time.sleep(5)"),
        workspace_root=tmp_path,
        cancellation=cancellation,
        progress_interval_seconds=0.05,
    ))
    thread.join(timeout=1.0)
    assert events[0].event_type is CommandEventType.STARTED
    assert events[-1].event_type is CommandEventType.CANCELLED
    assert CommandEventType.COMPLETED not in [event.event_type for event in events]


def test_launch_failure_is_structured_failed_event(tmp_path: Path) -> None:
    policy = TerminalCommandPolicy(
        command_id="missing",
        argv=(str(tmp_path / "definitely-missing-executable"),),
        timeout_seconds=1.0,
    )
    events = list(stream_registered_command(
        operation_id="op-launch",
        policy=policy,
        workspace_root=tmp_path,
    ))
    assert len(events) == 1
    assert events[0].event_type is CommandEventType.FAILED
    assert events[0].exit_code == -1
    assert events[0].metadata["phase"] == "launch"


def test_event_contract_rejects_invalid_operation_and_workspace(tmp_path: Path) -> None:
    policy = _policy("print('ok')")
    try:
        list(stream_registered_command(operation_id="", policy=policy, workspace_root=tmp_path))
    except ValueError as exc:
        assert "operation_id" in str(exc)
    else:
        raise AssertionError("empty operation ID must fail")

    missing = tmp_path / "missing"
    try:
        list(stream_registered_command(operation_id="op", policy=policy, workspace_root=missing))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing workspace must fail")
