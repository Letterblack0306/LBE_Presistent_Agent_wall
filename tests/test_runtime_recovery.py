from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.invocation_adapter import InvocationAdapterError
from lbe_guard_inspector.recovery import (
    FailureClass,
    RecoveryStoppedError,
    RetryPolicy,
)
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


def _runtime(tmp_path: Path) -> SessionMemoryRuntimeBridge:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite3",
        project_workspace_id="workspace-1",
        workspace_root=workspace,
        session_id="session-1",
        mode="coding",
    )


def test_transient_failure_recovers_within_policy_and_persists_attempts(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise InvocationAdapterError(
                "transport_failure",
                "temporary transport failure",
                retryable=True,
            )
        return "ok"

    result = runtime.run_recoverable(
        task_id="task-1",
        operation_id="provider-call",
        operation=operation,
        policy=RetryPolicy(
            max_attempts=3,
            retryable_failure_classes=frozenset(
                {FailureClass.TEMPORARY_TOOL_FAILURE}
            ),
        ),
        idempotent=True,
    )

    assert result == "ok"
    assert calls == 2
    state = runtime.load_recovery_state(
        task_id="task-1", operation_id="provider-call"
    )
    assert state is not None
    assert state.attempt_count == 2
    assert state.terminal is True
    assert state.succeeded is True


def test_retry_count_survives_runtime_restart(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    with pytest.raises(InvocationAdapterError):
        runtime.run_recoverable(
            task_id="task-1",
            operation_id="provider-call",
            operation=lambda: (_ for _ in ()).throw(
                InvocationAdapterError(
                    "transport_failure",
                    "temporary",
                    retryable=True,
                )
            ),
            policy=RetryPolicy(
                max_attempts=1,
                retryable_failure_classes=frozenset(
                    {FailureClass.TEMPORARY_TOOL_FAILURE}
                ),
            ),
            idempotent=True,
        )

    restarted = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "memory.sqlite3",
        project_workspace_id="workspace-1",
        workspace_root=tmp_path / "workspace",
        session_id="session-1",
    )
    state = restarted.load_recovery_state(
        task_id="task-1", operation_id="provider-call"
    )
    assert state is not None
    assert state.attempt_count == 1
    assert state.last_failure_class is FailureClass.TEMPORARY_TOOL_FAILURE
    assert state.terminal is True


def test_permission_denial_is_never_retried(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1
        raise PermissionError("denied")

    with pytest.raises(PermissionError):
        runtime.run_recoverable(
            task_id="task-1",
            operation_id="write",
            operation=operation,
            policy=RetryPolicy(
                max_attempts=4,
                retryable_failure_classes=frozenset({FailureClass.TIMEOUT}),
            ),
            idempotent=True,
        )

    assert calls == 1
    state = runtime.load_recovery_state(task_id="task-1", operation_id="write")
    assert state is not None
    assert state.last_failure_class is FailureClass.PERMISSION_DENIAL
    assert state.terminal is True


def test_non_idempotent_operation_cannot_enable_retries(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    with pytest.raises(ValueError, match="idempotency"):
        runtime.run_recoverable(
            task_id="task-1",
            operation_id="write",
            operation=lambda: None,
            policy=RetryPolicy(
                max_attempts=2,
                retryable_failure_classes=frozenset({FailureClass.TIMEOUT}),
            ),
            idempotent=False,
        )


def test_required_evidence_blocks_second_attempt_when_missing(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1
        raise TimeoutError("slow")

    with pytest.raises(RecoveryStoppedError, match="evidence required"):
        runtime.run_recoverable(
            task_id="task-1",
            operation_id="provider-call",
            operation=operation,
            policy=RetryPolicy(
                max_attempts=3,
                retryable_failure_classes=frozenset({FailureClass.TIMEOUT}),
                require_evidence_between_attempts=True,
            ),
            idempotent=True,
        )

    assert calls == 1
    state = runtime.load_recovery_state(
        task_id="task-1", operation_id="provider-call"
    )
    assert state is not None
    assert state.attempt_count == 1
    assert state.terminal is True
    assert state.succeeded is False


def test_completed_operation_is_not_executed_twice(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        return "done"

    policy = RetryPolicy(max_attempts=1)
    assert runtime.run_recoverable(
        task_id="task-1",
        operation_id="write",
        operation=operation,
        policy=policy,
        idempotent=True,
    ) == "done"

    with pytest.raises(RecoveryStoppedError, match="already completed"):
        runtime.run_recoverable(
            task_id="task-1",
            operation_id="write",
            operation=operation,
            policy=policy,
            idempotent=True,
        )

    assert calls == 1


def test_retry_policy_rejects_deterministic_retry_classes() -> None:
    with pytest.raises(ValueError, match="cannot be retryable"):
        RetryPolicy(
            max_attempts=2,
            retryable_failure_classes=frozenset(
                {FailureClass.PERMISSION_DENIAL, FailureClass.SCOPE_CONFLICT}
            ),
        )
