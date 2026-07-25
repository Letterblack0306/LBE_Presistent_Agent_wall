from __future__ import annotations

import argparse
import json
import traceback
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from agent import GovernanceError

from .contracts import ContractValidationError, validate_contract
from .evidence_service import EvidenceService
from .guard_inspector import GuardInspector
from .guard_runner import GuardRunner


def make_handler(
    service: EvidenceService,
    inspector: GuardInspector | None = None,
    runner: GuardRunner | None = None,
):
    guard_inspector = inspector or GuardInspector()
    guard_runner = runner or GuardRunner(
        evidence_service=service, inspector=guard_inspector
    )

    class Handler(BaseHTTPRequestHandler):
        server_version = "LBEGuardInspectorPhase1/1.3"

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "service": "lbe-guard-inspector-phase1",
                        "search_backend": "agent.search_workspace",
                        "workspace_evidence": True,
                        "contradictions": True,
                        "guard_evaluation": True,
                    },
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:
            try:
                if self.path == "/evidence-package":
                    self._handle_evidence_package()
                elif self.path == "/guard-result":
                    self._handle_guard_result()
                elif self.path == "/guard-run":
                    self._handle_guard_run()
                else:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            except ContractValidationError as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "error": "contract_validation_failed",
                        "contract": exc.contract_name,
                        "details": exc.errors,
                    },
                )
            except (GovernanceError, ValueError, FileNotFoundError, RuntimeError) as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "error": type(exc).__name__,
                        "message": str(exc),
                    },
                )
            except Exception as exc:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": "internal_error",
                        "message": str(exc),
                        "trace": traceback.format_exc(limit=3),
                    },
                )

        def _handle_evidence_package(self) -> None:
            payload = self._read_json_body()

            task = {
                "task_id": payload.get("task_id") or f"task-{uuid.uuid4()}",
                "problem": payload.get("problem", ""),
                "workspace_id": payload.get("workspace_id"),
                "workspace_root": payload.get("workspace_root"),
                "mode": payload.get("mode", "inspect"),
                "write_allowed": False,
                "constraints": payload.get("constraints", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            validate_contract("task_record", task)

            extensions = payload.get("extensions")
            roots = payload.get("roots")

            if extensions is not None and not isinstance(extensions, list):
                raise ValueError("'extensions' must be an array")
            if roots is not None and not isinstance(roots, list):
                raise ValueError("'roots' must be an array")

            package = service.build_evidence_package(
                task_id=task["task_id"],
                query=task["problem"],
                workspace_id=task["workspace_id"],
                workspace_root=task["workspace_root"],
                max_results=int(payload.get("max_results", 10)),
                extensions=extensions,
                roots=roots,
                include_excluded=bool(
                    payload.get("include_excluded", False)
                ),
            )

            self._send_json(
                HTTPStatus.OK,
                {
                    "task": task,
                    "evidence_package": package,
                },
            )

        def _handle_guard_result(self) -> None:
            payload = self._read_json_body()

            rule_result = payload.get("rule_result")
            evidence_package = payload.get("evidence_package")
            if not isinstance(rule_result, dict):
                raise ValueError("'rule_result' must be an object")
            if not isinstance(evidence_package, dict):
                raise ValueError("'evidence_package' must be an object")

            task = payload.get("task")
            workspace_id = None
            reason = ""
            if isinstance(task, dict):
                workspace_id = task.get("workspace_id")
                reason = task.get("reason", "") or ""

            result = guard_inspector.evaluate(
                rule_result=rule_result,
                evidence_package=evidence_package,
                guard_id=payload.get("guard_id"),
                guard_version=payload.get("guard_version"),
                workspace_id=workspace_id or payload.get("workspace_id"),
                reason=reason or payload.get("reason", ""),
            )

            self._send_json(
                HTTPStatus.OK,
                {
                    "task": task if isinstance(task, dict) else {},
                    "evidence_package": evidence_package,
                    "guard_result": result,
                },
            )

        def _handle_guard_run(self) -> None:
            payload = self._read_json_body()

            problem = payload.get("problem")
            if not isinstance(problem, str) or not problem.strip():
                raise ValueError("'problem' must be a non-empty string")
            pack_id = payload.get("pack_id")
            rule_id = payload.get("rule_id")
            if not isinstance(pack_id, str) or not pack_id.strip():
                raise ValueError("'pack_id' must be a non-empty string")
            if not isinstance(rule_id, str) or not rule_id.strip():
                raise ValueError("'rule_id' must be a non-empty string")

            extensions = payload.get("extensions")
            roots = payload.get("roots")
            if extensions is not None and not isinstance(extensions, list):
                raise ValueError("'extensions' must be an array")
            if roots is not None and not isinstance(roots, list):
                raise ValueError("'roots' must be an array")

            result = guard_runner.run(
                problem=problem,
                workspace_root=payload.get("workspace_root"),
                pack_id=pack_id,
                rule_id=rule_id,
                workspace_id=payload.get("workspace_id"),
                guard_id=payload.get("guard_id"),
                guard_version=payload.get("guard_version"),
                extensions=extensions,
                roots=roots,
                max_results=int(payload.get("max_results", 10)),
                reason=payload.get("reason", ""),
            )

            self._send_json(HTTPStatus.OK, result)


        def _read_json_body(self) -> dict[str, Any]:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("Content-Length is required")

            length = int(raw_length)
            if length < 1 or length > 1_000_000:
                raise ValueError("Request body size is invalid")

            raw = self.rfile.read(length)
            parsed = json.loads(raw.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("JSON body must be an object")
            return parsed

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format_string: str, *args: Any) -> None:
            print(f"[HTTP] {self.address_string()} - {format_string % args}")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="LBE Phase 1 evidence endpoint")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    service = EvidenceService()
    inspector = GuardInspector()
    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_handler(service, inspector, GuardRunner(evidence_service=service, inspector=inspector)),
    )

    print(f"LBE Phase 1 endpoint: http://{args.host}:{args.port}")
    print("Search backend: agent.search_workspace")
    print("Workspace evidence: bounded read-only scan")
    print("Guard evaluation: evidence-bound verdict mapping")
    print("POST /evidence-package")
    print("POST /guard-result  (supplied rule_result -> guard_result)")
    print("POST /guard-run     (problem -> select+execute guard -> verdict)")
    print("GET  /health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
