from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Protocol, TypeVar

from .invocation_adapter import InvocationAdapterError
from .memory import (
    CandidateClaim,
    MemoryPromoter,
    MemoryType,
    SourceType,
    ValidationStatus,
    WorkspaceMemoryStore,
)


T = TypeVar("T")


class FailureClass(StrEnum):
    PROVIDER_FAILURE = "provider_failure"
    TIMEOUT = "timeout"
    TEMPORARY_TOOL_FAILURE = "temporary_tool_failure"
    VALIDATION_FAILURE = "validation_failure"
    PERMISSION_DENIAL = "permission_denial"
    STALE_WORKSPACE = "stale_workspace"
    SCOPE_CONFLICT = "scope_conflict"
    MISSING_DEPENDENCY = "missing_dependency"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class CancellationSignal(Protocol):
    def is_cancelled(self) -> bool:
        """Return whether recovery should stop before another attempt."""


class RecoveryStoppedError(RuntimeError):
    """Raised when the persisted recovery contract has reached a terminal stop."""


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retryable_failure_classes: frozenset[FailureClass] = frozenset()
    delay_seconds: float = 0.0
    backoff_multiplier: float = 1.0
    require_idempotent: bool = True
    require_evidence_between_attempts: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.max_attempts, bool) or self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must not be negative")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")
        forbidden = {
            FailureClass.PERMISSION_DENIAL,
            FailureClass.SCOPE_CONFLICT,
            FailureClass.VALIDATION_FAILURE,
            FailureClass.CANCELLATION,
        }
        invalid = sorted(
            item.value for item in self.retryable_failure_classes if item in forbidden
        )
        if invalid:
            raise ValueError(
                "deterministic or terminal failure classes cannot be retryable: "
                + ", ".join(invalid)
            )


@dataclass(frozen=True)
class RecoveryState:
    operation_id: str
    attempt_count: int
    last_failure_class: FailureClass | None
    terminal: bool
    succeeded: bool
    last_error: str | None = None


EvidenceCallback = Callable[[int, FailureClass, BaseException], bool]
FailureClassifier = Callable[[BaseException], FailureClass]


def classify_failure(error: BaseException) -> FailureClass:
    if isinstance(error, KeyboardInterrupt):
        return FailureClass.CANCELLATION
    if isinstance(error, InvocationAdapterError):
        if error.code == "cancelled":
            return FailureClass.CANCELLATION
        if error.code == "timeout":
            return FailureClass.TIMEOUT
        if error.retryable or error.code in {"transport_failure", "endpoint_rejected"}:
            return FailureClass.TEMPORARY_TOOL_FAILURE
        if error.code in {"invalid_request", "invalid_transport_response"}:
            return FailureClass.VALIDATION_FAILURE
        return FailureClass.UNKNOWN
    if isinstance(error, TimeoutError):
        return FailureClass.TIMEOUT
    if isinstance(error, PermissionError):
        return FailureClass.PERMISSION_DENIAL
    if isinstance(error, FileNotFoundError):
        return FailureClass.MISSING_DEPENDENCY
    return FailureClass.UNKNOWN


def _subject(operation_id: str) -> str:
    return f"recovery:{operation_id}"


def load_recovery_state(
    *,
    store: WorkspaceMemoryStore,
    project_workspace_id: str,
    task_id: str,
    operation_id: str,
) -> RecoveryState | None:
    records = store.query(
        project_workspace_id=project_workspace_id,
        statuses=(ValidationStatus.VERIFIED,),
        task_id=task_id,
        memory_types=(MemoryType.VALIDATION_RESULT,),
        limit=500,
    )
    wanted = _subject(operation_id)
    for record in records:
        if record.subject != wanted or record.predicate != "recovery_state":
            continue
        value = record.value
        if not isinstance(value, dict):
            raise ValueError("corrupted recovery state: value must be an object")
        failure = value.get("last_failure_class")
        return RecoveryState(
            operation_id=operation_id,
            attempt_count=int(value.get("attempt_count", 0)),
            last_failure_class=(FailureClass(failure) if failure else None),
            terminal=bool(value.get("terminal", False)),
            succeeded=bool(value.get("succeeded", False)),
            last_error=value.get("last_error"),
        )
    return None


def persist_recovery_state(
    *,
    promoter: MemoryPromoter,
    project_workspace_id: str,
    canonical_workspace_root: str,
    task_id: str,
    state: RecoveryState,
) -> RecoveryState:
    promoter.promote(
        CandidateClaim(
            project_workspace_id=project_workspace_id,
            canonical_workspace_root=canonical_workspace_root,
            task_id=task_id,
            memory_type=MemoryType.VALIDATION_RESULT,
            subject=_subject(state.operation_id),
            predicate="recovery_state",
            value={
                "operation_id": state.operation_id,
                "attempt_count": state.attempt_count,
                "last_failure_class": (
                    state.last_failure_class.value if state.last_failure_class else None
                ),
                "terminal": state.terminal,
                "succeeded": state.succeeded,
                "last_error": state.last_error,
            },
            source_type=SourceType.COMMAND_RESULT,
            authority=9,
            validation_method="bounded-runtime-recovery",
            validated=True,
        )
    )
    return state


def run_with_recovery(
    *,
    operation: Callable[[], T],
    policy: RetryPolicy,
    store: WorkspaceMemoryStore,
    promoter: MemoryPromoter,
    project_workspace_id: str,
    canonical_workspace_root: str,
    task_id: str,
    operation_id: str,
    idempotent: bool,
    cancellation: CancellationSignal | None = None,
    evidence_between_attempts: EvidenceCallback | None = None,
    classify: FailureClassifier = classify_failure,
) -> T:
    clean_task = task_id.strip()
    clean_operation = operation_id.strip()
    if not clean_task:
        raise ValueError("task_id must not be empty")
    if not clean_operation:
        raise ValueError("operation_id must not be empty")
    if policy.max_attempts > 1 and policy.require_idempotent and not idempotent:
        raise ValueError("retryable operations must declare idempotency")

    previous = load_recovery_state(
        store=store,
        project_workspace_id=project_workspace_id,
        task_id=clean_task,
        operation_id=clean_operation,
    )
    if previous is not None and previous.terminal:
        if previous.succeeded:
            raise RecoveryStoppedError(
                "operation already completed; duplicate execution is blocked"
            )
        raise RecoveryStoppedError("recovery policy already reached a terminal stop")

    attempts = previous.attempt_count if previous is not None else 0
    while attempts < policy.max_attempts:
        if cancellation is not None and cancellation.is_cancelled():
            state = RecoveryState(
                operation_id=clean_operation,
                attempt_count=attempts,
                last_failure_class=FailureClass.CANCELLATION,
                terminal=True,
                succeeded=False,
                last_error="cancelled before attempt",
            )
            persist_recovery_state(
                promoter=promoter,
                project_workspace_id=project_workspace_id,
                canonical_workspace_root=canonical_workspace_root,
                task_id=clean_task,
                state=state,
            )
            raise RecoveryStoppedError("recovery cancelled")

        attempts += 1
        try:
            result = operation()
        except BaseException as error:
            failure = classify(error)
            retryable = failure in policy.retryable_failure_classes
            terminal = not retryable or attempts >= policy.max_attempts
            state = RecoveryState(
                operation_id=clean_operation,
                attempt_count=attempts,
                last_failure_class=failure,
                terminal=terminal,
                succeeded=False,
                last_error=str(error) or type(error).__name__,
            )
            persist_recovery_state(
                promoter=promoter,
                project_workspace_id=project_workspace_id,
                canonical_workspace_root=canonical_workspace_root,
                task_id=clean_task,
                state=state,
            )
            if terminal:
                raise
            if policy.require_evidence_between_attempts:
                if evidence_between_attempts is None or not evidence_between_attempts(
                    attempts, failure, error
                ):
                    stopped = RecoveryState(
                        operation_id=clean_operation,
                        attempt_count=attempts,
                        last_failure_class=failure,
                        terminal=True,
                        succeeded=False,
                        last_error="required recovery evidence was not supplied",
                    )
                    persist_recovery_state(
                        promoter=promoter,
                        project_workspace_id=project_workspace_id,
                        canonical_workspace_root=canonical_workspace_root,
                        task_id=clean_task,
                        state=stopped,
                    )
                    raise RecoveryStoppedError(
                        "recovery evidence required before another attempt"
                    ) from error
            delay = policy.delay_seconds * (
                policy.backoff_multiplier ** max(0, attempts - 1)
            )
            if delay:
                time.sleep(delay)
            continue

        success = RecoveryState(
            operation_id=clean_operation,
            attempt_count=attempts,
            last_failure_class=None,
            terminal=True,
            succeeded=True,
            last_error=None,
        )
        persist_recovery_state(
            promoter=promoter,
            project_workspace_id=project_workspace_id,
            canonical_workspace_root=canonical_workspace_root,
            task_id=clean_task,
            state=success,
        )
        return result

    raise RecoveryStoppedError("maximum recovery attempts exhausted")
