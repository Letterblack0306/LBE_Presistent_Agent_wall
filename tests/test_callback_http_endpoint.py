from __future__ import annotations

import http.client
import json
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from typing import Any, Iterator

import pytest

import server
from agent import GovernanceError


@contextmanager
def _running_server() -> Iterator[tuple[str, int]]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = httpd.server_address
        yield str(host), int(port)
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def _post(host: str, port: int, path: str, payload: Any) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.request(
            "POST",
            path,
            body=body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
        )
        response = connection.getresponse()
        decoded = json.loads(response.read().decode("utf-8"))
        return response.status, decoded
    finally:
        connection.close()


def test_run_callback_inspection_invokes_only_fixed_vertical_slice(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class _FakeSlice:
        def run(self, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {"request": {"workspace_root": kwargs["workspace_root"]}}

    monkeypatch.setattr(server, "CallbackVerticalSlice", _FakeSlice)

    result = server.run_callback_inspection(
        {
            "workspace_root": "C:/workspace/project",
            "workspace_id": "project-a",
            "reason": "callback audit",
            "max_results": 7,
        }
    )

    assert result == {"request": {"workspace_root": "C:/workspace/project"}}
    assert captured == {
        "workspace_root": "C:/workspace/project",
        "workspace_id": "project-a",
        "reason": "callback audit",
        "max_results": 7,
    }


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "workspace_root"),
        ({"workspace_root": ""}, "workspace_root"),
        ({"workspace_root": "C:/ws", "workspace_id": 3}, "workspace_id"),
        ({"workspace_root": "C:/ws", "reason": ""}, "reason"),
        ({"workspace_root": "C:/ws", "max_results": True}, "max_results"),
        ({"workspace_root": "C:/ws", "max_results": 0}, "max_results"),
        ({"workspace_root": "C:/ws", "max_results": 51}, "max_results"),
        ({"workspace_root": "C:/ws", "pack_id": "other"}, "Unsupported"),
        ({"workspace_root": "C:/ws", "rule_id": "other"}, "Unsupported"),
    ],
)
def test_run_callback_inspection_rejects_invalid_or_arbitrary_guard_fields(
    payload: dict[str, Any], message: str
) -> None:
    with pytest.raises(GovernanceError, match=message):
        server.run_callback_inspection(payload)


@pytest.mark.parametrize(
    "verdict",
    ["PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"],
)
def test_callback_endpoint_returns_existing_vertical_slice_shape(
    monkeypatch, verdict: str
) -> None:
    expected = {
        "request": {"workspace_root": "C:/workspace/project"},
        "authorization": {"mode": "inspect", "write_allowed": False},
        "decision": {"guard_result": {"verdict": verdict}},
        "explanation": {"verdict": verdict, "citations": []},
        "decision_fingerprint": f"fingerprint-{verdict}",
        "workspace_unchanged": True,
    }

    def _fake(payload: dict[str, Any]) -> dict[str, Any]:
        assert payload == {
            "workspace_root": "C:/workspace/project",
            "max_results": 5,
        }
        return expected

    monkeypatch.setattr(server, "run_callback_inspection", _fake)

    with _running_server() as (host, port):
        status, body = _post(
            host,
            port,
            "/guard-inspector/callback",
            {"workspace_root": "C:/workspace/project", "max_results": 5},
        )

    assert status == 200
    assert body == expected


def test_callback_endpoint_maps_governance_failure_to_structured_error() -> None:
    with _running_server() as (host, port):
        status, body = _post(
            host,
            port,
            "/guard-inspector/callback",
            {"workspace_root": "C:/workspace/project", "pack_id": "arbitrary"},
        )

    assert status == 400
    assert body["error"] == "GovernanceError"
    assert "Unsupported callback inspection fields" in body["message"]


def test_callback_endpoint_does_not_load_generic_context(monkeypatch) -> None:
    class _NoContext:
        @classmethod
        def load(cls):
            raise AssertionError("generic Context.load must not precede callback invocation")

    monkeypatch.setattr(server, "Context", _NoContext)
    monkeypatch.setattr(
        server,
        "run_callback_inspection",
        lambda payload: {
            "request": payload,
            "authorization": {"write_allowed": False},
            "decision": {},
            "explanation": {},
            "decision_fingerprint": "fixed",
            "workspace_unchanged": True,
        },
    )

    with _running_server() as (host, port):
        status, body = _post(
            host,
            port,
            "/guard-inspector/callback",
            {"workspace_root": "C:/workspace/project"},
        )

    assert status == 200
    assert body["authorization"]["write_allowed"] is False
    assert body["workspace_unchanged"] is True
