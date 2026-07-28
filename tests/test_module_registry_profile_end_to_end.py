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
from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.invocation_adapter import (
    CancellationToken,
    InProcessTransport,
    InvocationAdapterError,
    LocalHttpTransport,
)
from lbe_guard_inspector.module_registry_vertical_slice import (
    ModuleRegistryGuardRunner,
    ModuleRegistryVerticalSlice,
)
from lbe_guard_inspector.runtime_integration_profile import (
    IntegrationProfileError,
    RuntimeIntegrationProfile,
)

# Importing the pack performs deterministic programmatic registration.
import rules.module_registry  # noqa: F401


def _context(root: Path) -> Context:
    return Context(
        config={"max_file_bytes": 1_000_000, "exclude_patterns": []},
        governance={},
        roots=(KnowledgeRoot("workspace", root),),
    )


def _service(root: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleRegistryVerticalSlice:
    ctx = _context(root)

    class _BoundContext:
        @classmethod
        def load(cls) -> Context:
            return ctx

    monkeypatch.setattr("lbe_guard_inspector.evidence_service.Context", _BoundContext)
    return ModuleRegistryVerticalSlice(
        runner=ModuleRegistryGuardRunner(
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


def _write_registry(
    root: Path,
    *,
    declarations: list[dict[str, Any]] | None = None,
    receipts: list[dict[str, Any]] | None = None,
) -> None:
    target = root / ".lbe" / "module-registry.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "declarations": declarations if declarations is not None else [],
                "receipts": receipts if receipts is not None else [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _profile(
    factory: str,
    *,
    timeout: float = 5.0,
    config: Mapping[str, Any] | None = None,
) -> RuntimeIntegrationProfile:
    return RuntimeIntegrationProfile.from_mapping(
        {
            "profile_id": "generic-module-registry-runtime",
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
                "module_registry_inspection": True,
                "callback_inspection": False,
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
        "reason": "module registry profile proof",
        "limit": 10,
    }


def test_module_registry_profile_is_explicit_and_callback_profile_remains_valid() -> None:
    module_profile = _profile("in_process")
    assert module_profile.inspection_capability == "module_registry_inspection"

    callback_profile = RuntimeIntegrationProfile.from_mapping(
        {
            "profile_id": "callback-runtime",
            "version": "1",
            "transport_factory": "in_process",
            "transport_config": {},
            "request_mapping": {"workspace_root": "root"},
            "capabilities": {"callback_inspection": True},
        }
    )
    assert callback_profile.inspection_capability == "callback_inspection"


def test_profile_rejects_multiple_fixed_inspection_capabilities() -> None:
    with pytest.raises(IntegrationProfileError) as captured:
        RuntimeIntegrationProfile.from_mapping(
            {
                "profile_id": "ambiguous-runtime",
                "version": "1",
                "transport_factory": "in_process",
                "transport_config": {},
                "request_mapping": {"workspace_root": "root"},
                "capabilities": {
                    "callback_inspection": True,
                    "module_registry_inspection": True,
                },
            }
        )
    assert captured.value.code == "contradictory_profile"
    assert captured.value.details == {
        "enabled_inspection_capabilities": [
            "callback_inspection",
            "module_registry_inspection",
        ]
    }


@pytest.mark.parametrize(
    ("declarations", "receipts", "create_registry", "verdict"),
    [
        (
            [{"id": "app.launcher"}],
            [{"type": "loaded", "module_id": "hidden.runtime", "instance_id": "hidden-1"}],
            True,
            "FAIL",
        ),
        (
            [{"id": "app.launcher"}],
            [{"type": "loaded", "module_id": "app.launcher", "instance_id": "app-1"}],
            True,
            "PASS",
        ),
        ([{"id": "app.launcher"}], [], True, "INSUFFICIENT_EVIDENCE"),
        ([], [], False, "NOT_APPLICABLE"),
    ],
)
def test_in_process_module_registry_profile_preserves_all_verdicts_and_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declarations: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    create_registry: bool,
    verdict: str,
) -> None:
    project = tmp_path / verdict.lower()
    project.mkdir()
    if create_registry:
        _write_registry(project, declarations=declarations, receipts=receipts)
    service = _service(project, monkeypatch)
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
    assert result["explanation"]["verdict"] == verdict
    assert result["decision_fingerprint"]
    assert result["workspace_unchanged"] is True
    assert _tree_hash(project) == before


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


def test_temporary_http_module_registry_profile_preserves_complete_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "http-project"
    project.mkdir()
    _write_registry(
        project,
        declarations=[{"id": "app.launcher"}],
        receipts=[{"type": "loaded", "module_id": "app.launcher", "instance_id": "app-1"}],
    )
    service = _service(project, monkeypatch)
    before = _tree_hash(project)
    endpoint_results: list[Mapping[str, Any]] = []

    def run(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        result = service.run(**dict(payload))
        endpoint_results.append(result)
        return result

    monkeypatch.setattr(server, "run_module_registry_inspection", run)
    with _running_server() as (host, port):
        endpoint = f"http://{host}:{port}/guard-inspector/module-registry"
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


def test_module_registry_endpoint_rejects_arbitrary_guard_selection() -> None:
    payload = {
        "workspace_root": "C:/workspace/project",
        "pack_id": "caller-selected",
    }
    with pytest.raises(Exception, match="Unsupported module registry inspection fields"):
        server.run_module_registry_inspection(payload)


def test_module_registry_profile_missing_factory_is_structured() -> None:
    with pytest.raises(IntegrationProfileError) as captured:
        _profile("missing").compile({})
    assert captured.value.code == "transport_factory_unavailable"
    assert captured.value.details == {"transport_factory": "missing"}


def test_module_registry_endpoint_rejection_is_structured() -> None:
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
            config={"endpoint": f"http://{host}:{port}/guard-inspector/module-registry"},
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


def test_module_registry_timeout_and_cancellation_are_deterministic() -> None:
    class SlowTransport:
        def invoke(self, payload, *, timeout_seconds, cancellation):
            del payload, timeout_seconds, cancellation
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


def test_module_registry_transport_failure_is_not_retried() -> None:
    calls = 0

    class FailingTransport:
        def invoke(self, payload, *, timeout_seconds, cancellation):
            nonlocal calls
            del payload, timeout_seconds, cancellation
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
