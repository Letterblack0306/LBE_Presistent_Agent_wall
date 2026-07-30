from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from typing import Any

from lbe_guard_inspector.reasoning_contracts import LBERequest, LBEResponse
from server import Handler, make_handler


class FakeController:
    def __init__(self) -> None:
        self.requests: list[LBERequest] = []

    def run(self, request: LBERequest) -> LBEResponse:
        self.requests.append(request)
        return LBEResponse(
            task_id=request.task_id or "task-generated",
            workspace_identity={"workspace_id": "workspace-1"},
            workspace_profile={"project_type": "test"},
            plan=None,
            deterministic_result={"verdict": "PASS"},
            explanation=None,
            outcome="COMPLETED",
        )


def _start(handler: type[Handler]) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post(server: ThreadingHTTPServer, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    host, port = server.server_address
    body = json.dumps(payload).encode("utf-8")
    connection = HTTPConnection(host, port, timeout=3)
    try:
        connection.request(
            "POST",
            "/reasoning/run",
            body=body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()


def test_bound_handler_routes_exact_request_to_controller() -> None:
    controller = FakeController()
    server, thread = _start(make_handler(controller))
    try:
        status, payload = _post(server, {
            "problem": "Inspect the configured workspace",
            "workspace_root": ".",
            "reference_context": [{"source": "test"}],
            "task_id": "task-1",
            "max_results": 7,
        })
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    assert status == 200
    assert payload["task_id"] == "task-1"
    assert payload["outcome"] == "COMPLETED"
    assert payload["read_only"] is True
    assert len(controller.requests) == 1
    request = controller.requests[0]
    assert request.problem == "Inspect the configured workspace"
    assert request.workspace_root == "."
    assert request.reference_context == ({"source": "test"},)
    assert request.max_results == 7


def test_unbound_root_handler_rejects_reasoning_route() -> None:
    server, thread = _start(Handler)
    try:
        status, payload = _post(server, {
            "problem": "Inspect",
            "workspace_root": ".",
        })
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    assert status == 400
    assert payload["error"] == "GovernanceError"
    assert "not configured" in payload["message"]


def test_unknown_reasoning_fields_fail_before_controller_call() -> None:
    controller = FakeController()
    server, thread = _start(make_handler(controller))
    try:
        status, payload = _post(server, {
            "problem": "Inspect",
            "workspace_root": ".",
            "backend": "forbidden",
        })
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    assert status == 400
    assert payload["error"] == "GovernanceError"
    assert "Unsupported reasoning fields" in payload["message"]
    assert controller.requests == []


def test_make_handler_requires_explicit_controller() -> None:
    try:
        make_handler(None)  # type: ignore[arg-type]
    except TypeError as exc:
        assert "reasoning_controller is required" in str(exc)
    else:
        raise AssertionError("make_handler accepted a missing controller")
