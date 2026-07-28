from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from typing import Any, cast
from urllib.request import urlopen

from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.module_registry import ModuleState
from lbe_guard_inspector.runtime_slice import RuntimeSlice
from lbe_guard_inspector.server import make_handler


def _start_server(runtime: RuntimeSlice) -> tuple[ThreadingHTTPServer, threading.Thread]:
    service = cast(EvidenceService, object())
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(service, runtime=runtime),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _get_json(server: ThreadingHTTPServer, path: str) -> dict[str, Any]:
    host, port = server.server_address
    with urlopen(f"http://{host}:{port}{path}", timeout=3) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def test_health_reports_registry_availability() -> None:
    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()
    server, thread = _start_server(runtime)
    try:
        payload = _get_json(server, "/health")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    assert payload["ok"] is True
    assert payload["module_registry"] is True
    assert runtime.state("agent.http-server") is ModuleState.IDLE


def test_registry_endpoint_returns_live_read_only_snapshot() -> None:
    runtime = RuntimeSlice(active_profile="test")
    runtime.startup()
    server, thread = _start_server(runtime)
    try:
        payload = _get_json(server, "/module-registry")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    assert payload["profile"] == "test"
    assert payload["defects"] == []
    modules = {item["id"]: item for item in payload["modules"]}
    assert modules["module.registry"]["loaded"] is True
    assert modules["agent.http-server"]["current_activity"]["detail"] == (
        "GET /module-registry"
    )
    assert runtime.state("agent.http-server") is ModuleState.IDLE
    assert runtime.watcher.history[-1].module_id == "agent.http-server"
