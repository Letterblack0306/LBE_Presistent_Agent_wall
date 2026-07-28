from __future__ import annotations

import hashlib
import json
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator, Mapping

import pytest

import server
from agent import Context, KnowledgeRoot
from lbe_guard_inspector.callback_vertical_slice import CallbackVerticalSlice
from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.guard_runner import GuardRunner
from lbe_guard_inspector.invocation_adapter import (
    CancellationToken,
    InProcessTransport,
    InvocationAdapterError,
    LocalHttpTransport,
)
from lbe_guard_inspector.runtime_integration_profile import (
    IntegrationProfileError,
    RuntimeIntegrationProfile,
)

# Importing the pack performs deterministic programmatic registration.
import rules.cep_callback  # noqa: F401


def _context(root: Path) -> Context:
    return Context(
        config={"max_file_bytes": 1_000_000, "exclude_patterns": []},
        governance={},
        roots=(KnowledgeRoot("workspace", root),),
    )


def _service(root: Path, monkeypatch: pytest.MonkeyPatch) -> CallbackVerticalSlice:
    ctx = _context(root)

    class _BoundContext:
        @classmethod
        def load(cls) -> Context:
            return ctx

    monkeypatch.setattr("lbe_guard_inspector.evidence_service.Context", _BoundContext)
    return CallbackVerticalSlice(
        runner=GuardRunner(
            evidence_service=EvidenceService(),
            context_loader=lambda: ctx,
        ),
        context_loader=lambda: ctx,
    )


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _write_case(root: Path, callback: str | None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    target = root / "panel.js"
    if callback is None:
        body = "// Provided callback is not a function\nconst value = 1;\n"
    else:
        body = (
            "// Provided callback is not a function\n"
            "const payload = 'work';\n"
            f"cs.evalScript(payload, {callback});\n"
        )
    target.write_text(body, encoding="utf-8")
    return target


def _profile(factory: str, *, timeout: float = 5.0, config: Mapping[str, Any] | None = None):
    return RuntimeIntegrationProfile.from_mapping(
        {
            "profile_id": "generic-runtime",
            "version": "1",
            "transport_factory": factory,
            "transport_config": dict(config or {}),
            "request_mapping": {
                "workspace_root": "root",
                "workspace_id": "workspace",
                "reason": "reason",
                "max_results": "limit",
            },
            "capabilities": {
                "callback_inspection": True,
                "arbitrary_guard_selection": False,
                "workspace_mutation": False,
                "repair_execution": False,
            },
            "timeout_seconds": timeout,
            "cancellation_supported": True,
        }
    )


def _runtime_input(root: Path) -> dict[str, Any]:
    return {
        "root": str(root),
        "workspace": "temporary-project",
        "reason": "profile-driven proof",
        "limit": 10,
    }


@pytest.mark.parametrize(
    ("callback", "verdict"),
    [
        ("function (result) { return result; }", "PASS"),
        ("null", "FAIL"),
        ("onResult", "INSUFFICIENT_EVIDENCE"),
        (None, "NOT_APPLICABLE"),
    ],
)
def test_in_process_profile_preserves_all_verdicts_and_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    callback: str | None,
    verdict: str,
) -> None:
    project = tmp_path / verdict.lower()
    _write_case(project, callback)
    service = _service(tmp_path, monkeypatch)
    before = _tree_hash(project)
    raw: list[Mapping[str, Any]] = []

    def target(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        result = service.run(**dict(payload))
        raw.append(result)
        return result

    compiled = _profile("in_process").compile(
        {"in_process": lambda config: InProcessTransport(target)}
    )
    result = compiled.invoke(_runtime_input(project))

    assert result is raw[0]
    assert result["decision"]["guard_result"]["verdict"] == verdict
    assert result["request"]["workspace_root"] == str(project.resolve())
    assert result["authorization"]["write_allowed"] is False
    assert result["decision"]["guard_result"].get("result_id")
    assert "evidence_refs" in result["decision"]["guard_result"]
    assert "validation_refs" in result["decision"]["guard_result"]
    assert "explanation" in result
    assert result["decision_fingerprint"]
    assert result["workspace_unchanged"] is True
    assert _tree_hash(project) == before


@contextmanager
def _running_callback_server() -> Iterator[tuple[str, int]]:
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


def test_temporary_http_profile_preserves_complete_endpoint_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "http-project"
    _write_case(project, "function (result) { return result; }")
    service = _service(tmp_path, monkeypatch)
    before = _tree_hash(project)
    endpoint_results: list[Mapping[str, Any]] = []

    def run(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        result = service.run(**dict(payload))
        endpoint_results.append(result)
        return result

    monkeypatch.setattr(server, "run_callback_inspection", run)
    with _running_callback_server() as (host, port):
        endpoint = f"http://{host}:{port}/guard-inspector/callback"
        compiled = _profile("local_http", config={"endpoint": endpoint}).compile(
            {
                "local_http": lambda config: LocalHttpTransport(
                    str(config["endpoint"])
                )
            }
        )
        result = compiled.invoke(_runtime_input(project))

    assert result == endpoint_results[0]
    assert result["decision"]["guard_result"]["verdict"] == "PASS"
    assert result["authorization"]["write_allowed"] is False
    assert result["workspace_unchanged"] is True
    assert result["decision_fingerprint"] == endpoint_results[0]["decision_fingerprint"]
    assert result["explanation"] == endpoint_results[0]["explanation"]
    assert _tree_hash(project) == before


def test_unknown_runtime_input_is_rejected_before_transport_invocation() -> None:
    calls = 0

    class CountingTransport:
        def invoke(self, payload, *, timeout_seconds, cancellation):
            nonlocal calls
            calls += 1
            return {"unexpected": True}

    compiled = _profile("counting").compile(
        {"counting": lambda config: CountingTransport()}
    )
    with pytest.raises(IntegrationProfileError) as captured:
        compiled.invoke({"unknown": "value"})

    assert captured.value.code == "invalid_runtime_input"
    assert calls == 0


def test_missing_factory_remains_structured() -> None:
    with pytest.raises(IntegrationProfileError) as captured:
        _profile("missing").compile({})

    assert captured.value.to_dict() == {
        "error": "transport_factory_unavailable",
        "message": "Transport factory is not configured: missing",
        "details": {"transport_factory": "missing"},
    }


def test_endpoint_rejection_remains_structured() -> None:
    response = {"error": "GovernanceError", "message": "rejected by governance"}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            self.rfile.read(length)
            body = json.dumps(response).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args) -> None:
            del format, args

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        compiled = _profile(
            "local_http",
            config={"endpoint": f"http://{host}:{port}/guard-inspector/callback"},
        ).compile(
            {
                "local_http": lambda config: LocalHttpTransport(
                    str(config["endpoint"])
                )
            }
        )
        with pytest.raises(InvocationAdapterError) as captured:
            compiled.invoke({"root": "C:/outside"})
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()

    assert captured.value.code == "endpoint_rejected"
    assert captured.value.details == {"status": 400, "response": response}
    assert captured.value.retryable is False


def test_timeout_and_cancellation_are_deterministic() -> None:
    class SlowTransport:
        def invoke(self, payload, *, timeout_seconds, cancellation):
            time.sleep(0.2)
            return {"late": True}

    timed = _profile("slow", timeout=0.02).compile(
        {"slow": lambda config: SlowTransport()}
    )
    with pytest.raises(InvocationAdapterError) as timeout_error:
        timed.invoke({"root": "C:/temporary"})
    assert timeout_error.value.code == "timeout"

    token = CancellationToken()
    token.cancel()
    cancellable = _profile("slow", timeout=1).compile(
        {"slow": lambda config: SlowTransport()}
    )
    with pytest.raises(InvocationAdapterError) as cancellation_error:
        cancellable.invoke({"root": "C:/temporary"}, cancellation=token)
    assert cancellation_error.value.code == "cancelled"


def test_transport_failure_is_not_retried() -> None:
    calls = 0

    class FailingTransport:
        def invoke(self, payload, *, timeout_seconds, cancellation):
            nonlocal calls
            calls += 1
            raise InvocationAdapterError(
                "transport_failure", "single deterministic failure", retryable=False
            )

    compiled = _profile("failing").compile(
        {"failing": lambda config: FailingTransport()}
    )
    with pytest.raises(InvocationAdapterError) as captured:
        compiled.invoke({"root": "C:/temporary"})

    assert captured.value.code == "transport_failure"
    assert captured.value.retryable is False
    assert calls == 1
