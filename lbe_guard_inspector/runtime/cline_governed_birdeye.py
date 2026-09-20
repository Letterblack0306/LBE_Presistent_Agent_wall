"""Thin governed BirdEye MCP add-on for the unmodified Cline product surface.

This add-on is the LBE-owned process boundary for Cline-driven governed tool
execution. It runs as a stdlib-only JSON-RPC MCP server over stdio and never
becomes a second session, provider, credential, tool, or completion authority:

* Read tools are delegated into the installed BirdEye package at the process
  boundary via the canonical ``build_birdeye_mcp_handler`` seam; they never
  write the Agent Wall database.
* Governed writes go through the exact ``product_entry._tool`` pathway:
  ``WorkspaceMemoryStore.save_governed_operation`` -> ``resolve_authorization``
  -> ``GovernedToolOrchestrator`` -> ``complete_governed_operation``, reusing
  ``_governed_operation_fingerprint``, ``_governed_operation_approval_id`` and
  ``_tool_receipt_payload`` from ``lbe_guard_inspector.product_entry``.

The server binds once at startup from environment and fails closed when the
session, wall database, or target workspace is missing or inconsistent.

Environment:
    LBE_SESSION_ID          required - governed session to bind
    LBE_WALL_DATABASE       required - Agent Wall database path
    LBE_TARGET_WORKSPACE    required - workspace root the add-on is attached to
    LBE_BIRDEYE_MCP_PYTHON  optional - python for the installed BirdEye server
    LBE_BIRDEYE_MCP_SERVER  optional - installed BirdEye mcp_server.py path
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from agent import Context

from lbe_guard_inspector import cli as _cli
from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.product_entry import (
    _governed_operation_approval_id,
    _governed_operation_fingerprint,
    _tool_receipt_payload,
)
from lbe_guard_inspector.runtime.authorization_resolver import (
    AuthorizationDecision,
    AuthorizationRequest,
    AuthorizationVerdict,
    resolve_authorization,
)
from lbe_guard_inspector.runtime.external_capabilities import (
    birdeye_mcp_tool_spec,
    build_birdeye_mcp_handler,
)
from lbe_guard_inspector.runtime.governed_coding import (
    build_process_run_registered_handler,
    build_workspace_patch_handler,
    process_run_registered_spec,
    workspace_patch_spec,
)
from lbe_guard_inspector.runtime.mode_controller import ModeRequest, resolve_mode
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolAccessClass,
    ToolExecutionContext,
    ToolReceipt,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
    build_workspace_glob_handler,
    build_workspace_list_handler,
    build_workspace_read_handler,
    build_workspace_search_handler,
    workspace_glob_spec,
    workspace_list_spec,
    workspace_read_spec,
    workspace_search_spec,
)

ADDON_NAME = "lbe-birdeye"
ADDON_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"

_ENV_SESSION = "LBE_SESSION_ID"
_ENV_DATABASE = "LBE_WALL_DATABASE"
_ENV_WORKSPACE = "LBE_TARGET_WORKSPACE"
_ENV_BIRDEYE_PYTHON = "LBE_BIRDEYE_MCP_PYTHON"
_ENV_BIRDEYE_SERVER = "LBE_BIRDEYE_MCP_SERVER"

DEFAULT_BIRDEYE_SERVER = r"C:\MCP Local\Letterblack_BirdEye\mcp_server.py"

GovernedExecuteHandler = Callable[[str], Callable[[ToolRequest], Any]]


class _McpError(Exception):
    """JSON-RPC error carrying an MCP error code."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def _required_string(values: Mapping[str, Any], key: str, *, tool_id: str = "") -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{tool_id} arguments must include a non-empty string '{key}'")
    return value


def _required_object(values: Mapping[str, Any], key: str, *, tool_id: str = "") -> Mapping[str, Any]:
    value = values.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{tool_id} arguments must include an object '{key}'")
    return value


def _request_message(identifier: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}


def _birdeye_round_trip(python: str, server: Path, messages: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run one framed message batch against the installed BirdEye stdio server."""
    if not Path(server).is_file():
        raise FileNotFoundError(f"BirdEye MCP server is unavailable: {server}")
    encoded = "\n".join(json.dumps(message, ensure_ascii=False) for message in messages) + "\n"
    completed = subprocess.run(
        [python, str(server), "--stdio"],
        cwd=str(Path(server).parent),
        input=encoded,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"BirdEye MCP exited unsuccessfully: {completed.returncode}")
    responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    initialize = next((item for item in responses if item.get("id") == 1), None)
    if initialize is None or initialize.get("result", {}).get("serverInfo", {}).get("name") != "birdeye":
        raise ValueError("BirdEye MCP server identity mismatch")
    return responses


def probe_birdeye_read_tools(
    *, python: str | None = None, server: str | None = None,
) -> list[dict[str, Any]]:
    """Return the installed BirdEye read-tool catalog via a tools/list probe."""
    python_value = python or os.environ.get(_ENV_BIRDEYE_PYTHON, "python")
    server_value = server or os.environ.get(_ENV_BIRDEYE_SERVER, DEFAULT_BIRDEYE_SERVER)
    messages = [
        _request_message(1, "initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": ADDON_NAME, "version": ADDON_VERSION},
        }),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        _request_message(2, "tools/list", {}),
        _request_message(4, "shutdown", {}),
    ]
    responses = _birdeye_round_trip(python_value, Path(server_value), messages)
    tools = next(
        (item for item in responses if item.get("id") == 2),
        {},
    ).get("result", {}).get("tools", [])
    if not isinstance(tools, list):
        raise ValueError("BirdEye MCP tools/list omitted a tools array")
    return [dict(item) for item in tools]


class GovernedBirdeyeAddon:
    """MCP stdio server binding one governed LBE session to Cline-side tool calls."""

    def __init__(
        self,
        *,
        store: Any,
        session: Any,
        workspace_root: str | Path,
        context_loader: Callable[[], Context] | None = None,
        read_tools: Optional[Sequence[Mapping[str, Any]]] = None,
        governed_handler_builder: GovernedExecuteHandler = build_birdeye_mcp_handler,
    ) -> None:
        self._store = store
        self._session = session
        self._workspace_root = Path(workspace_root).expanduser().resolve()
        persisted_root = Path(session.canonical_workspace_root).expanduser().resolve()
        if persisted_root != self._workspace_root:
            raise ValueError("workspace root does not match persisted session")
        self._context_loader = context_loader or Context.load
        self._read_tools = list(read_tools) if read_tools is not None else None
        self._governed_handler_builder = governed_handler_builder
        self._probe_error: str | None = None
        self._read_tool_names: set[str] = set()

    # -- MCP surface ---------------------------------------------------------

    def serve_stdio(self, *, stdin: Any = None, stdout: Any = None) -> int:
        reader = stdin or sys.stdin
        writer = stdout or sys.stdout
        flush = getattr(writer, "flush", lambda: None)
        for line in reader:
            if not line.strip():
                continue
            try:
                message = _parse_message(line)
            except _McpError as exc:
                writer.write(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": exc.code, "message": str(exc)},
                }, ensure_ascii=False) + "\n")
                flush()
                continue
            response = self._dispatch(message)
            if response is not None:
                writer.write(json.dumps(response, ensure_ascii=False) + "\n")
                flush()
        return 0

    def _dispatch(self, message: dict[str, Any]) -> dict[str, Any] | None:
        try:
            method = str(message.get("method", ""))
            request_id = message.get("id")
            params = message.get("params") or {}
            if method == "notifications/initialized":
                return None
            result = self._handle(method, params if isinstance(params, Mapping) else {})
            if request_id is None:
                return None
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except _McpError as exc:
            if message.get("id") is None:
                return None
            return {"jsonrpc": "2.0", "id": message.get("id"), "error": {
                "code": exc.code, "message": str(exc),
            }}
        except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError) as exc:
            if message.get("id") is None:
                return None
            return {"jsonrpc": "2.0", "id": message.get("id"), "error": {
                "code": -32603, "message": f"{type(exc).__name__}: {exc}",
            }}

    def _handle(self, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            return {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": ADDON_NAME, "version": ADDON_VERSION},
            }
        if method == "shutdown":
            return {}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": self._tools()}
        if method == "tools/call":
            return self._call_tool(params)
        raise _McpError(-32601, f"method not found: {method}")

    # -- tools/list ----------------------------------------------------------

    def _tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        if self._read_tools is None:
            try:
                self._read_tools = probe_birdeye_read_tools()
            except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError) as exc:
                self._probe_error = f"{type(exc).__name__}: {exc}"
                self._read_tools = []
        for definition in self._read_tools:
            name = str(definition.get("name", ""))
            description = str(definition.get("description", ""))
            tools.append({
                "name": name,
                "description": f"Read-only BirdEye tool delegated to the installed BirdEye server by LBE. {description}".strip(),
                "inputSchema": definition.get("inputSchema") or {"type": "object", "properties": {}},
            })
            self._read_tool_names.add(name)
        tools.append({
            "name": "lbe_session_status",
            "description": "Read-only projection of the LBE-governed session the add-on is bound to.",
            "inputSchema": {"type": "object", "properties": {}},
        })
        tools.append({
            "name": "lbe_governed_execute",
            "description": "Execute one LBE-governed tool against the bound session. Writes require explicit Agent Wall approval; reads are traced as receipts without mutation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tool_id": {
                        "type": "string",
                        "description": "Registered governed tool id: workspace.read, workspace.list, workspace.glob, workspace.search, workspace.patch, process.run_registered, or mcp.birdeye.<read-tool>.",
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Tool-specific arguments for the target tool.",
                    },
                    "operation_id": {
                        "type": "string",
                        "description": "Caller-chosen operation id. Omitted ids are generated as op-<uuid4.hex>.",
                    },
                },
                "required": ["tool_id", "arguments"],
            },
        })
        return tools

    # -- tools/call ----------------------------------------------------------

    def _call_tool(self, params: Mapping[str, Any]) -> dict[str, Any]:
        name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, Mapping):
            raise _McpError(-32602, "tools/call arguments must be an object")
        if name == "lbe_governed_execute":
            payload = self._governed_execute(arguments)
            return self._text_result(payload)
        if name == "lbe_session_status":
            return self._text_result(self._session_status())
        if name in self._read_tool_names:
            payload = self._read_tool(name, arguments)
            return self._text_result(payload)
        self._ensure_read_catalog()
        if name in self._read_tool_names:
            payload = self._read_tool(name, arguments)
            return self._text_result(payload)
        raise _McpError(-32602, f"tool is not registered: {name}")

    def _ensure_read_catalog(self) -> None:
        if self._read_tools is None:
            try:
                self._read_tools = probe_birdeye_read_tools()
            except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError) as exc:
                raise _McpError(-32602, f"BirdEye read tools are unavailable: {exc}") from exc
        for definition in self._read_tools:
            self._read_tool_names.add(str(definition.get("name", "")))

    @staticmethod
    def _text_result(payload: Mapping[str, Any]) -> dict[str, Any]:
        return {"content": [{
            "type": "text",
            "text": json.dumps(dict(payload), ensure_ascii=False, sort_keys=True),
        }]}

    def _session_status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "name": ADDON_NAME,
            "version": ADDON_VERSION,
            "session_id": self._session.session_id,
            "workspace_id": self._session.project_workspace_id,
            "workspace_root": str(self._workspace_root),
            "mode": self._session.mode,
            "permission": self._session.permission,
            "runtime_policy": self._session.runtime_policy,
            "database": str(self._store.database_path),
        }

    def _read_tool(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        session = self._session
        mode_decision = resolve_mode(ModeRequest(
            intent="inspect_workspace",
            permission=session.permission or "read_only",
            runtime_policy=session.runtime_policy or "audit",
            workspace_root=str(self._workspace_root),
        ))
        context = ToolExecutionContext(
            mode_decision=mode_decision,
            workspace_id=session.project_workspace_id,
            workspace_root=self._workspace_root,
            configured_root_id="lbe-governed",
            explicitly_forbidden=False,
            approval_granted=False,
        )
        operation_id = f"read-{uuid.uuid4().hex}"
        handler = self._governed_handler_builder(name)
        result = handler(ToolRequest(
            operation_id=operation_id,
            tool_id=f"mcp.birdeye.{name}",
            arguments={"arguments": dict(arguments)},
            context=context,
        ))
        payload = dict(result.output or {})
        payload.setdefault("governed", False)
        payload["read_only"] = True
        return payload

    def _governed_execute(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        tool_id = _required_string(arguments, "tool_id")
        tool_arguments = _required_object(arguments, "arguments", tool_id=tool_id)
        operation_id = arguments.get("operation_id")
        if operation_id is None or not isinstance(operation_id, str) or not operation_id.strip():
            operation_id = f"op-{uuid.uuid4().hex}"
        store = self._store
        session = self._session
        requested_root = self._workspace_root
        persisted_root = Path(session.canonical_workspace_root).expanduser().resolve()
        if requested_root != persisted_root:
            raise ValueError("workspace root does not match persisted session")

        context_config = self._context_loader()
        configured_root = next(
            (root for root in self._configured_roots(context_config) if self._root_path(root) == requested_root),
            None,
        )
        if configured_root is None:
            raise ValueError(f"workspace root is not configured for Agent Wall: {requested_root}")

        mode_decision = resolve_mode(ModeRequest(
            intent="fix_issue" if tool_id == "workspace.patch" else "inspect_workspace",
            permission=session.permission or "read_only",
            runtime_policy=session.runtime_policy or "audit",
            workspace_root=str(requested_root),
        ))
        explicitly_forbidden = (
            tool_id in {"workspace.patch", "process.run_registered"}
            and (session.permission or "read_only") in {"read_only", "audit_only"}
        )

        registry = ToolRegistry()
        registry.register(workspace_read_spec(), build_workspace_read_handler(EvidenceService()))
        registry.register(workspace_list_spec(), build_workspace_list_handler())
        registry.register(workspace_glob_spec(), build_workspace_glob_handler())
        registry.register(workspace_search_spec(), build_workspace_search_handler(EvidenceService()))
        registry.register(workspace_patch_spec(), build_workspace_patch_handler())
        registry.register(process_run_registered_spec(), build_process_run_registered_handler())
        if tool_id.startswith("mcp.birdeye."):
            birdeye_tool = tool_id.removeprefix("mcp.birdeye.")
            registry.register(
                birdeye_mcp_tool_spec(birdeye_tool),
                self._governed_handler_builder(birdeye_tool),
            )

        if tool_id.startswith("mcp.birdeye."):
            normalized = {"arguments": dict(_required_object(tool_arguments, "arguments", tool_id=tool_id))}
        elif tool_id == "workspace.glob":
            normalized = {"pattern": _required_string(tool_arguments, "pattern", tool_id=tool_id)}
        elif tool_id == "workspace.search":
            normalized = {"query": _required_string(tool_arguments, "query", tool_id=tool_id)}
        elif tool_id == "workspace.patch":
            normalized = {
                "path": _required_string(tool_arguments, "path", tool_id=tool_id),
                "content": _required_string(tool_arguments, "content", tool_id=tool_id),
                "expected_sha256": _required_string(tool_arguments, "expected_sha256", tool_id=tool_id),
            }
        elif tool_id == "process.run_registered":
            normalized = {"command_id": _required_string(tool_arguments, "command_id", tool_id=tool_id)}
        else:
            normalized = {"path": _required_string(tool_arguments, "path", tool_id=tool_id)}

        registered = registry.get(tool_id)
        if registered is None:
            raise ValueError(f"tool is not registered: {tool_id}")
        capability = registered.spec.capability
        fingerprint, request_binding = _governed_operation_fingerprint(
            session_id=session.session_id,
            workspace_id=session.project_workspace_id,
            workspace_root=requested_root,
            tool_id=tool_id,
            arguments=normalized,
        )
        approval_id = _governed_operation_approval_id(
            operation_id=operation_id,
            capability=capability,
            workspace_id=session.project_workspace_id,
        )
        persisted_operation = store.load_governed_operation(operation_id=operation_id)

        if persisted_operation is not None:
            persisted_operation = store.save_governed_operation(
                operation_id=operation_id,
                session_id=session.session_id,
                project_workspace_id=session.project_workspace_id,
                canonical_workspace_root=str(requested_root),
                tool_id=tool_id,
                capability=capability,
                request_fingerprint=fingerprint,
                request=request_binding,
                approval_id=approval_id,
            )
            decision = str(persisted_operation["decision"])
            if decision in {"executed", "failed"}:
                persisted_receipt = persisted_operation.get("receipt")
                if not isinstance(persisted_receipt, dict):
                    raise ValueError("terminal governed operation is missing its persisted receipt")
                return dict(persisted_receipt)
            if decision == "rejected":
                receipt = ToolReceipt(
                    operation_id=operation_id,
                    tool_id=tool_id,
                    status=ToolReceiptStatus.DENIED,
                    authorization=AuthorizationDecision(
                        verdict=AuthorizationVerdict.DENY,
                        capability=capability,
                        rationale="User rejected the Agent Wall approval request.",
                    ),
                    error_code="AUTHORIZATION_DENIED",
                    error_message="User rejected the Agent Wall approval request.",
                )
                return _tool_receipt_payload(receipt, approval_id=approval_id)
            approval_granted = decision == "approved"
        else:
            approval_granted = False

        context = ToolExecutionContext(
            mode_decision=mode_decision,
            workspace_id=session.project_workspace_id,
            workspace_root=requested_root,
            configured_root_id=configured_root.name if configured_root.name else "lbe-governed",
            explicitly_forbidden=explicitly_forbidden,
            approval_granted=approval_granted,
        )

        if registered.spec.access_class is ToolAccessClass.WRITE and not approval_granted:
            baseline = resolve_authorization(AuthorizationRequest(
                mode_decision=mode_decision,
                capability=capability,
                explicitly_forbidden=explicitly_forbidden,
            ))
            if baseline.verdict is AuthorizationVerdict.DENY:
                receipt = ToolReceipt(
                    operation_id=operation_id,
                    tool_id=tool_id,
                    status=ToolReceiptStatus.DENIED,
                    authorization=baseline,
                    error_code="AUTHORIZATION_DENIED",
                    error_message=baseline.rationale,
                )
                return _tool_receipt_payload(receipt)

            store.save_governed_operation(
                operation_id=operation_id,
                session_id=session.session_id,
                project_workspace_id=session.project_workspace_id,
                canonical_workspace_root=str(requested_root),
                tool_id=tool_id,
                capability=capability,
                request_fingerprint=fingerprint,
                request=request_binding,
                approval_id=approval_id,
            )
            rationale = (
                baseline.rationale
                if baseline.verdict is AuthorizationVerdict.ESCALATE
                else "Writable operation requires explicit Agent Wall approval."
            )
            receipt = ToolReceipt(
                operation_id=operation_id,
                tool_id=tool_id,
                status=ToolReceiptStatus.ESCALATED,
                authorization=AuthorizationDecision(
                    verdict=AuthorizationVerdict.ESCALATE,
                    capability=capability,
                    rationale=rationale,
                ),
                error_code="AUTHORIZATION_REQUIRED",
                error_message=rationale,
            )
            return _tool_receipt_payload(receipt, approval_id=approval_id)

        receipt = GovernedToolOrchestrator(registry=registry).invoke(
            ToolRequest(
                operation_id=operation_id,
                tool_id=tool_id,
                arguments=normalized,
                context=context,
            )
        )
        payload = _tool_receipt_payload(
            receipt,
            approval_id=approval_id if persisted_operation is not None else None,
        )
        if persisted_operation is not None and approval_granted and receipt.status in {
            ToolReceiptStatus.EXECUTED,
            ToolReceiptStatus.FAILED,
        }:
            store.complete_governed_operation(
                operation_id=operation_id,
                receipt=payload,
                failed=receipt.status is ToolReceiptStatus.FAILED,
            )
        return payload

    @staticmethod
    def _configured_roots(context_config: Any):
        return context_config.roots if context_config is not None else ()

    @staticmethod
    def _root_path(root: Any) -> Path:
        path = root.path
        return Path(path).expanduser().resolve()


def _parse_message(line: str) -> dict[str, Any]:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        raise _McpError(-32700, f"parse error: {exc}") from exc
    if not isinstance(message, dict):
        raise _McpError(-32600, "invalid request: expected a JSON object")
    return message


def build_addon_from_environment(*, environ: Mapping[str, str] | None = None) -> GovernedBirdeyeAddon:
    env = environ or os.environ
    session_id = env.get(_ENV_SESSION)
    database = env.get(_ENV_DATABASE)
    workspace = env.get(_ENV_WORKSPACE)
    if not session_id:
        raise ValueError(f"{_ENV_SESSION} is required and was not set")
    if not database:
        raise ValueError(f"{_ENV_DATABASE} is required and was not set")
    if not workspace:
        raise ValueError(f"{_ENV_WORKSPACE} is required and was not set")
    store = _cli.WorkspaceMemoryStore(database)
    session = _cli._require_session(store, session_id)
    return GovernedBirdeyeAddon(
        store=store,
        session=session,
        workspace_root=workspace,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lbe-birdeye-addon",
        description="LBE governed BirdEye MCP add-on (stdio).",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        default=True,
        help="Serve MCP over standard input/output (default).",
    )
    parser.parse_args(argv)
    try:
        addon = build_addon_from_environment()
    except (ValueError, TypeError, FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"lbe-birdeye add-on failed to start: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return addon.serve_stdio()


if __name__ == "__main__":
    raise SystemExit(main())