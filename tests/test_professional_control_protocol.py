from __future__ import annotations

import pytest

from lbe_guard_inspector.professional_control_protocol import (
    CONTROL_PROTOCOL_VERSION,
    ClientKind,
    ControlClientMetadata,
    ControlError,
    ControlMethod,
    ControlNotification,
    ControlNotificationType,
    ControlProtocolError,
    ControlRequest,
    ControlResponse,
    InitializeParams,
    InitializeResult,
    canonical_control_methods,
    canonical_control_notifications,
    require_supported_protocol_version,
)


def test_canonical_methods_cover_required_first_control_surface() -> None:
    assert {item.value for item in canonical_control_methods()} == {
        "initialize",
        "session.create",
        "session.resume",
        "session.read",
        "session.status",
        "session.events.list",
        "session.events.subscribe",
        "turn.start",
        "turn.steer",
        "turn.interrupt",
        "turn.cancel",
        "provider.list",
        "provider.check",
        "provider.select",
        "capabilities.list",
        "permissions.get",
        "approval.respond",
        "evidence.get",
        "validation.get",
    }


def test_canonical_notifications_cover_required_async_surface() -> None:
    values = {item.value for item in canonical_control_notifications()}
    assert {
        "session.started",
        "session.updated",
        "turn.started",
        "turn.steering.received",
        "turn.steering.applied",
        "turn.steering.queued",
        "turn.steering.rejected",
        "turn.interrupted",
        "turn.completed",
        "item.started",
        "item.delta",
        "item.progress",
        "item.completed",
        "item.failed",
        "item.cancelled",
        "item.declined",
        "item.escalated",
        "approval.requested",
        "capabilities.changed",
        "permissions.changed",
        "provider.changed",
    } <= values


def test_initialize_metadata_and_result_are_typed() -> None:
    client = ControlClientMetadata(
        client_name="lbe-test",
        client_version="0.1.0",
        client_kind=ClientKind.TEST,
        supported_protocol_version=CONTROL_PROTOCOL_VERSION,
        supported_event_capabilities=("item.delta", "item.progress"),
    )
    params = InitializeParams(client=client)
    result = InitializeResult(
        protocol_version=CONTROL_PROTOCOL_VERSION,
        runtime_name="lbe",
        runtime_version="0.2.1",
        supported_methods=canonical_control_methods(),
        supported_notifications=canonical_control_notifications(),
    )
    assert params.client is client
    assert ControlMethod.TURN_STEER in result.supported_methods
    assert ControlNotificationType.ITEM_DELTA in result.supported_notifications


def test_request_response_and_notification_envelopes_preserve_identity() -> None:
    request = ControlRequest(
        request_id="request-1",
        method=ControlMethod.SESSION_STATUS,
        params={"session_id": "session-1"},
    )
    response = ControlResponse(request_id=request.request_id, result={"status": "active"})
    notification = ControlNotification(
        notification_type=ControlNotificationType.SESSION_UPDATED,
        payload={"session_id": "session-1"},
    )
    assert request.protocol_version == CONTROL_PROTOCOL_VERSION
    assert response.request_id == request.request_id
    assert notification.payload["session_id"] == "session-1"


def test_response_requires_exactly_one_result_or_error() -> None:
    with pytest.raises(ControlProtocolError, match="exactly one"):
        ControlResponse(request_id="request-1")
    with pytest.raises(ControlProtocolError, match="exactly one"):
        ControlResponse(
            request_id="request-1",
            result={"ok": True},
            error=ControlError(code="ERR", message="no"),
        )


def test_initialize_capabilities_are_unique_and_nonempty() -> None:
    with pytest.raises(ControlProtocolError, match="duplicates"):
        ControlClientMetadata(
            client_name="client",
            client_version="1",
            client_kind=ClientKind.CLI,
            supported_protocol_version=CONTROL_PROTOCOL_VERSION,
            supported_event_capabilities=("item.delta", "item.delta"),
        )
    with pytest.raises(ControlProtocolError, match="non-empty"):
        ControlClientMetadata(
            client_name="client",
            client_version="1",
            client_kind=ClientKind.CLI,
            supported_protocol_version=CONTROL_PROTOCOL_VERSION,
            supported_event_capabilities=("",),
        )


def test_protocol_version_fails_closed() -> None:
    assert require_supported_protocol_version(CONTROL_PROTOCOL_VERSION) == CONTROL_PROTOCOL_VERSION
    with pytest.raises(ControlProtocolError, match="unsupported control protocol version"):
        require_supported_protocol_version("2.0")


def test_contract_rejects_untyped_method_notification_and_payloads() -> None:
    with pytest.raises(TypeError, match="method"):
        ControlRequest(request_id="request-1", method="session.read")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="notification_type"):
        ControlNotification(notification_type="turn.started", payload={})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="params"):
        ControlRequest(request_id="request-1", method=ControlMethod.SESSION_READ, params=())  # type: ignore[arg-type]
