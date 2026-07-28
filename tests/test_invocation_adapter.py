from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

import pytest

from lbe_guard_inspector.invocation_adapter import (
    CancellationToken,
    InProcessTransport,
    InvocationAdapterError,
    LocalHttpTransport,
    RuntimeNeutralInvocationAdapter,
)


class _Transport:
    def __init__(self, result: Mapping[str, Any]) -> None:
        self.result = result
        self.calls: list[tuple[dict[str, Any], float]] = []

    def invoke(self, payload, *, timeout_seconds, cancellation):
        self.calls.append((dict(payload), timeout_seconds))
        return self.result


class _BlockingTransport:
    def __init__(self, release: threading.Event) -> None:
        self.release = release

    def invoke(self, payload, *, timeout_seconds, cancellation):
        del payload, timeout_seconds, cancellation
        self.release.wait(5)
        return {"late": True}


def test_in_process_preserves_response_without_verdict_reinterpretation() -> None:
    response = {
        "request": {"request_id": "req-1"},
        "authorization": {"write_allowed": False},
        "decision": {
            "verdict": "FAIL",
            "evidence_refs": ["workspace:file.js:1"],
            "validation_refs": ["validation:file.js:1"],
        },
        "decision_fingerprint": "sha256:fixed",
        "workspace_unchanged": True,
    }
    adapter = RuntimeNeutralInvocationAdapter(
        InProcessTransport(lambda payload: response)
    )

    result = adapter.invoke({"workspace_root": "C:/workspace/project"})

    assert result is response
    assert result["decision"]["verdict"] == "FAIL"
    assert result["decision"]["evidence_refs"] == ["workspace:file.js:1"]
    assert result["decision"]["validation_refs"] == ["validation:file.js:1"]
    assert result["request"]["request_id"] == "req-1"


def test_adapter_forwards_only_narrow_configurable_request() -> None:
    response = {"decision": {"verdict": "PASS"}}
    transport = _Transport(response)
    adapter = RuntimeNeutralInvocationAdapter(transport, default_timeout_seconds=4.5)
    payload = {
        "workspace_root": "D:/dynamic/workspace",
        "workspace_id": "workspace-7",
        "reason": "Inspect callback failure",
        "max_results": 7,
    }

    assert adapter.invoke(payload) is response
    assert transport.calls == [(payload, 4.5)]


@pytest.mark.parametrize("field", ["pack_id", "rule_id", "port", "runtime"])
def test_adapter_rejects_arbitrary_selection_and_fixed_runtime_fields(field: str) -> None:
    adapter = RuntimeNeutralInvocationAdapter(_Transport({}))

    with pytest.raises(InvocationAdapterError) as captured:
        adapter.invoke({"workspace_root": "C:/workspace", field: "forbidden"})

    assert captured.value.code == "invalid_request"
    assert captured.value.retryable is False
    assert captured.value.details == {"unsupported_fields": [field]}


def test_structured_transport_failure_is_preserved() -> None:
    failure = InvocationAdapterError(
        "endpoint_rejected",
        "Workspace is outside configured roots",
        details={
            "status": 400,
            "response": {
                "error": "GovernanceError",
                "message": "Workspace is outside configured roots",
            },
        },
    )

    class RejectingTransport:
        def invoke(self, payload, *, timeout_seconds, cancellation):
            del payload, timeout_seconds, cancellation
            raise failure

    adapter = RuntimeNeutralInvocationAdapter(RejectingTransport())

    with pytest.raises(InvocationAdapterError) as captured:
        adapter.invoke({"workspace_root": "C:/outside"})

    assert captured.value is failure
    assert captured.value.to_dict() == {
        "error": "endpoint_rejected",
        "message": "Workspace is outside configured roots",
        "retryable": False,
        "details": {
            "status": 400,
            "response": {
                "error": "GovernanceError",
                "message": "Workspace is outside configured roots",
            },
        },
    }


def test_timeout_is_bounded_without_retry() -> None:
    release = threading.Event()
    transport = _BlockingTransport(release)
    adapter = RuntimeNeutralInvocationAdapter(transport)
    started = time.monotonic()

    try:
        with pytest.raises(InvocationAdapterError) as captured:
            adapter.invoke(
                {"workspace_root": "C:/workspace"}, timeout_seconds=0.05
            )
    finally:
        release.set()

    assert captured.value.code == "timeout"
    assert captured.value.retryable is False
    assert time.monotonic() - started < 0.5


def test_cancellation_is_deterministic() -> None:
    release = threading.Event()
    token = CancellationToken()
    adapter = RuntimeNeutralInvocationAdapter(_BlockingTransport(release))

    timer = threading.Timer(0.03, token.cancel)
    timer.start()
    try:
        with pytest.raises(InvocationAdapterError) as captured:
            adapter.invoke(
                {"workspace_root": "C:/workspace"},
                timeout_seconds=1,
                cancellation=token,
            )
    finally:
        release.set()
        timer.cancel()

    assert captured.value.code == "cancelled"
    assert captured.value.retryable is False


def test_pre_cancelled_request_never_invokes_transport() -> None:
    transport = _Transport({})
    token = CancellationToken()
    token.cancel()
    adapter = RuntimeNeutralInvocationAdapter(transport)

    with pytest.raises(InvocationAdapterError) as captured:
        adapter.invoke({"workspace_root": "C:/workspace"}, cancellation=token)

    assert captured.value.code == "cancelled"
    assert transport.calls == []


def test_local_http_transport_uses_ephemeral_port_and_preserves_json() -> None:
    expected = {
        "request": {"request_id": "req-http"},
        "authorization": {"write_allowed": False},
        "decision": {"verdict": "NOT_APPLICABLE"},
        "decision_fingerprint": "sha256:http",
        "workspace_unchanged": True,
    }
    received: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.append(json.loads(self.rfile.read(length).decode("utf-8")))
            body = json.dumps(expected).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        adapter = RuntimeNeutralInvocationAdapter(
            LocalHttpTransport(f"http://{host}:{port}/guard-inspector/callback")
        )
        payload = {"workspace_root": "C:/workspace/project", "max_results": 3}
        result = adapter.invoke(payload, timeout_seconds=2)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result == expected
    assert received == [payload]


def test_local_http_transport_preserves_structured_endpoint_error() -> None:
    error_response = {
        "error": "GovernanceError",
        "message": "Workspace root is outside configured roots",
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            self.rfile.read(length)
            body = json.dumps(error_response).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        adapter = RuntimeNeutralInvocationAdapter(
            LocalHttpTransport(f"http://{host}:{port}/guard-inspector/callback")
        )
        with pytest.raises(InvocationAdapterError) as captured:
            adapter.invoke({"workspace_root": "C:/outside"}, timeout_seconds=2)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert captured.value.code == "endpoint_rejected"
    assert captured.value.details == {"status": 400, "response": error_response}


def test_http_transport_rejects_non_local_endpoint() -> None:
    with pytest.raises(ValueError, match="local-only HTTP"):
        LocalHttpTransport("https://example.com/guard-inspector/callback")
