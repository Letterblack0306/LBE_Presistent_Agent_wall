"""Typed P8 bidirectional agent-control protocol contract.

This module defines the public request/response/notification vocabulary only.
It owns no session state, provider state, authorization, tool execution, event
persistence, or transport process. Future control handlers must delegate those
responsibilities to their existing LBE runtime owners.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


CONTROL_PROTOCOL_VERSION = "1.0"


class ControlProtocolError(ValueError):
    """Raised when a control-protocol message violates the frozen contract."""


class ControlMethod(StrEnum):
    INITIALIZE = "initialize"

    SESSION_CREATE = "session.create"
    SESSION_RESUME = "session.resume"
    SESSION_READ = "session.read"
    SESSION_STATUS = "session.status"
    SESSION_EVENTS_LIST = "session.events.list"
    SESSION_EVENTS_SUBSCRIBE = "session.events.subscribe"

    TURN_START = "turn.start"
    TURN_STEER = "turn.steer"
    TURN_INTERRUPT = "turn.interrupt"
    TURN_CANCEL = "turn.cancel"

    PROVIDER_LIST = "provider.list"
    PROVIDER_CHECK = "provider.check"
    PROVIDER_SELECT = "provider.select"

    CAPABILITIES_LIST = "capabilities.list"
    PERMISSIONS_GET = "permissions.get"
    APPROVAL_RESPOND = "approval.respond"

    EVIDENCE_GET = "evidence.get"
    VALIDATION_GET = "validation.get"


class ControlNotificationType(StrEnum):
    SESSION_STARTED = "session.started"
    SESSION_UPDATED = "session.updated"

    TURN_STARTED = "turn.started"
    TURN_STEERING_RECEIVED = "turn.steering.received"
    TURN_STEERING_APPLIED = "turn.steering.applied"
    TURN_STEERING_QUEUED = "turn.steering.queued"
    TURN_STEERING_REJECTED = "turn.steering.rejected"
    TURN_INTERRUPTED = "turn.interrupted"
    TURN_COMPLETED = "turn.completed"

    ITEM_STARTED = "item.started"
    ITEM_DELTA = "item.delta"
    ITEM_PROGRESS = "item.progress"
    ITEM_COMPLETED = "item.completed"
    ITEM_FAILED = "item.failed"
    ITEM_CANCELLED = "item.cancelled"
    ITEM_DECLINED = "item.declined"
    ITEM_ESCALATED = "item.escalated"

    APPROVAL_REQUESTED = "approval.requested"
    CAPABILITIES_CHANGED = "capabilities.changed"
    PERMISSIONS_CHANGED = "permissions.changed"
    PROVIDER_CHANGED = "provider.changed"


class ClientKind(StrEnum):
    CLI = "cli"
    TUI = "tui"
    IDE = "ide"
    GUI = "gui"
    SDK = "sdk"
    AUTOMATION = "automation"
    TEST = "test"


@dataclass(frozen=True)
class ControlClientMetadata:
    client_name: str
    client_version: str
    client_kind: ClientKind
    supported_protocol_version: str
    supported_event_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.client_name, "client_name")
        _require_text(self.client_version, "client_version")
        if not isinstance(self.client_kind, ClientKind):
            raise TypeError("client_kind must be ClientKind")
        _require_text(self.supported_protocol_version, "supported_protocol_version")
        if not isinstance(self.supported_event_capabilities, tuple):
            raise TypeError("supported_event_capabilities must be a tuple")
        for capability in self.supported_event_capabilities:
            _require_text(capability, "supported event capability")
        if len(set(self.supported_event_capabilities)) != len(self.supported_event_capabilities):
            raise ControlProtocolError("supported_event_capabilities must not contain duplicates")


@dataclass(frozen=True)
class InitializeParams:
    client: ControlClientMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.client, ControlClientMetadata):
            raise TypeError("client must be ControlClientMetadata")


@dataclass(frozen=True)
class InitializeResult:
    protocol_version: str
    runtime_name: str
    runtime_version: str
    supported_methods: tuple[ControlMethod, ...]
    supported_notifications: tuple[ControlNotificationType, ...]

    def __post_init__(self) -> None:
        _require_text(self.protocol_version, "protocol_version")
        _require_text(self.runtime_name, "runtime_name")
        _require_text(self.runtime_version, "runtime_version")
        if not isinstance(self.supported_methods, tuple) or not all(
            isinstance(item, ControlMethod) for item in self.supported_methods
        ):
            raise TypeError("supported_methods must be a tuple of ControlMethod")
        if not isinstance(self.supported_notifications, tuple) or not all(
            isinstance(item, ControlNotificationType) for item in self.supported_notifications
        ):
            raise TypeError("supported_notifications must be a tuple of ControlNotificationType")
        if len(set(self.supported_methods)) != len(self.supported_methods):
            raise ControlProtocolError("supported_methods must not contain duplicates")
        if len(set(self.supported_notifications)) != len(self.supported_notifications):
            raise ControlProtocolError("supported_notifications must not contain duplicates")


@dataclass(frozen=True)
class ControlRequest:
    request_id: str
    method: ControlMethod
    params: Mapping[str, Any] = field(default_factory=dict)
    protocol_version: str = CONTROL_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        _require_text(self.request_id, "request_id")
        if not isinstance(self.method, ControlMethod):
            raise TypeError("method must be ControlMethod")
        if not isinstance(self.params, Mapping):
            raise TypeError("params must be a mapping")
        _require_text(self.protocol_version, "protocol_version")


@dataclass(frozen=True)
class ControlError:
    code: str
    message: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.code, "error code")
        _require_text(self.message, "error message")
        if not isinstance(self.data, Mapping):
            raise TypeError("error data must be a mapping")


@dataclass(frozen=True)
class ControlResponse:
    request_id: str
    result: Mapping[str, Any] | None = None
    error: ControlError | None = None
    protocol_version: str = CONTROL_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        _require_text(self.request_id, "request_id")
        _require_text(self.protocol_version, "protocol_version")
        if self.result is not None and not isinstance(self.result, Mapping):
            raise TypeError("result must be a mapping when supplied")
        if self.error is not None and not isinstance(self.error, ControlError):
            raise TypeError("error must be ControlError when supplied")
        if (self.result is None) == (self.error is None):
            raise ControlProtocolError("control response must contain exactly one of result or error")


@dataclass(frozen=True)
class ControlNotification:
    notification_type: ControlNotificationType
    payload: Mapping[str, Any]
    protocol_version: str = CONTROL_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.notification_type, ControlNotificationType):
            raise TypeError("notification_type must be ControlNotificationType")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")
        _require_text(self.protocol_version, "protocol_version")


def require_supported_protocol_version(version: str) -> str:
    """Fail closed until explicit version negotiation is implemented."""
    clean = _require_text(version, "protocol version")
    if clean != CONTROL_PROTOCOL_VERSION:
        raise ControlProtocolError(
            f"unsupported control protocol version: {clean}; supported={CONTROL_PROTOCOL_VERSION}"
        )
    return clean


def canonical_control_methods() -> tuple[ControlMethod, ...]:
    return tuple(ControlMethod)


def canonical_control_notifications() -> tuple[ControlNotificationType, ...]:
    return tuple(ControlNotificationType)


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ControlProtocolError(f"{name} must be a non-empty string")
    return value.strip()
