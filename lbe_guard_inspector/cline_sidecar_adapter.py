"""Python-owned process adapter for the optional Cline ``@cline/llms`` sidecar.

The sidecar is provider transport only. This module owns process lifecycle,
truthful P0 normalization, pending tool-call correlation, and continuation
serialization. It never receives a workspace root or a governed tool executor.
"""
from __future__ import annotations

import json
import subprocess
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

from .cline_llms_compat import normalize_cline_stream_chunk
from .professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProfessionalProviderAdapter,
    ProviderToolResultContinuation,
    ProviderTurnRequest,
)


class ClineSidecarProcessError(RuntimeError):
    """Raised when the transport sidecar itself cannot complete its contract."""


@dataclass(frozen=True)
class PendingProviderToolCall:
    provider_tool_call_id: str
    lbe_call_id: str
    tool_name: str
    tool_arguments: Mapping[str, Any]


BridgeRunner = Callable[[Mapping[str, Any]], Iterable[Mapping[str, Any]]]
CallIdFactory = Callable[[], str]


class ClineSidecarProviderAdapter(ProfessionalProviderAdapter):
    """ProfessionalProviderAdapter backed by one-shot Cline sidecar processes."""

    def __init__(
        self,
        *,
        provider_config: Mapping[str, Any],
        node_executable: str = "node",
        bridge_path: str | Path | None = None,
        bridge_runner: BridgeRunner | None = None,
        call_id_factory: CallIdFactory | None = None,
        reasoning_is_summary: bool = False,
    ) -> None:
        if not isinstance(provider_config, Mapping):
            raise TypeError("provider_config must be a mapping")
        if not isinstance(node_executable, str) or not node_executable.strip():
            raise ValueError("node_executable must be a non-empty string")

        self._provider_config = dict(provider_config)
        self._node_executable = node_executable.strip()
        self._bridge_path = Path(bridge_path) if bridge_path is not None else _default_bridge_path()
        self._bridge_runner = bridge_runner or self._run_bridge_process
        self._call_id_factory = call_id_factory or (lambda: f"lbe-call-{uuid.uuid4().hex}")
        self._reasoning_is_summary = reasoning_is_summary
        self._pending_tool_call: PendingProviderToolCall | None = None
        self._active_process: subprocess.Popen[str] | None = None
        self._process_lock = threading.Lock()

    @property
    def pending_tool_call(self) -> PendingProviderToolCall | None:
        return self._pending_tool_call

    def stream_turn(self, request: ProviderTurnRequest) -> Iterable[NormalizedModelEvent]:
        self._require_request_matches_config(request)
        if self._pending_tool_call is not None:
            raise ClineSidecarProcessError("cannot start a new provider turn while a tool result continuation is pending")
        return tuple(self._stream_request(request, messages=request.messages))

    def continue_with_tool_result(
        self,
        request: ProviderTurnRequest,
        result: ProviderToolResultContinuation,
    ) -> Iterable[NormalizedModelEvent]:
        self._require_request_matches_config(request)
        pending = self._pending_tool_call
        if pending is None:
            raise ClineSidecarProcessError("no provider tool call is awaiting continuation")
        if result.provider_tool_call_id != pending.provider_tool_call_id:
            raise ClineSidecarProcessError("tool result provider_tool_call_id does not match the pending provider call")
        if result.lbe_call_id != pending.lbe_call_id:
            raise ClineSidecarProcessError("tool result lbe_call_id does not match the pending LBE call")
        if result.tool_name != pending.tool_name:
            raise ClineSidecarProcessError("tool result tool_name does not match the pending provider call")

        continuation_messages = tuple(request.messages) + (
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": pending.provider_tool_call_id,
                        "call_id": pending.provider_tool_call_id,
                        "name": pending.tool_name,
                        "input": dict(pending.tool_arguments),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": pending.provider_tool_call_id,
                        "name": pending.tool_name,
                        "content": _serialize_tool_output(result.output),
                        "is_error": result.is_error,
                    }
                ],
            },
        )
        self._pending_tool_call = None
        return tuple(self._stream_request(request, messages=continuation_messages))

    def cancel(self) -> None:
        with self._process_lock:
            process = self._active_process
        if process is not None and process.poll() is None:
            process.terminate()

    def _stream_request(
        self,
        request: ProviderTurnRequest,
        *,
        messages: Sequence[Mapping[str, Any]],
    ) -> Iterator[NormalizedModelEvent]:
        yield NormalizedModelEvent(
            event_type=ModelEventType.TURN_STARTED,
            provider_id=request.provider_id,
            model_id=request.model_id,
            protocol_family=request.protocol_family,
            metadata={"backend": "@cline/llms-sidecar"},
        )

        payload = {
            "provider_config": dict(self._provider_config),
            "system_prompt": request.system_prompt,
            "messages": [dict(item) for item in messages],
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": dict(tool.input_schema),
                }
                for tool in request.tool_definitions
            ],
        }
        saw_tool_call = False
        terminal_seen = False

        for envelope in self._bridge_runner(payload):
            if not isinstance(envelope, Mapping):
                raise ClineSidecarProcessError("Cline bridge emitted a non-object envelope")
            kind = envelope.get("kind")
            if kind == "chunk":
                chunk = envelope.get("chunk")
                if not isinstance(chunk, Mapping):
                    raise ClineSidecarProcessError("Cline bridge chunk envelope requires a chunk object")

                chunk_type = chunk.get("type")
                if chunk_type == "tool_calls":
                    lbe_call_id = self._call_id_factory()
                    events = normalize_cline_stream_chunk(
                        chunk,
                        provider_id=request.provider_id,
                        model_id=request.model_id,
                        protocol_family=request.protocol_family,
                        lbe_call_id=lbe_call_id,
                        reasoning_is_summary=self._reasoning_is_summary,
                    )
                    if len(events) != 1 or events[0].event_type is not ModelEventType.TOOL_CALL_COMPLETED:
                        raise ClineSidecarProcessError("Cline tool call did not normalize to one completed proposal")
                    event = events[0]
                    self._pending_tool_call = PendingProviderToolCall(
                        provider_tool_call_id=event.provider_tool_call_id or "",
                        lbe_call_id=event.lbe_call_id or "",
                        tool_name=event.tool_name or "",
                        tool_arguments=dict(event.tool_arguments or {}),
                    )
                    saw_tool_call = True
                    yield event
                    continue

                if chunk_type == "done" and saw_tool_call and chunk.get("success") is True:
                    pending = self._pending_tool_call
                    if pending is None:
                        raise ClineSidecarProcessError("Cline tool call state was lost before continuation gate")
                    terminal_seen = True
                    yield NormalizedModelEvent(
                        event_type=ModelEventType.TURN_REQUIRES_TOOL,
                        provider_id=request.provider_id,
                        model_id=request.model_id,
                        protocol_family=request.protocol_family,
                        provider_request_id=_optional_text(chunk.get("id")),
                        provider_tool_call_id=pending.provider_tool_call_id,
                        lbe_call_id=pending.lbe_call_id,
                        tool_name=pending.tool_name,
                        metadata={"backend": "@cline/llms-sidecar"},
                    )
                    continue

                events = normalize_cline_stream_chunk(
                    chunk,
                    provider_id=request.provider_id,
                    model_id=request.model_id,
                    protocol_family=request.protocol_family,
                    reasoning_is_summary=self._reasoning_is_summary,
                )
                for event in events:
                    if event.event_type in {
                        ModelEventType.TURN_COMPLETED,
                        ModelEventType.TURN_INCOMPLETE,
                        ModelEventType.ERROR,
                    }:
                        terminal_seen = True
                    yield event
                continue

            if kind == "error":
                terminal_seen = True
                code = envelope.get("code")
                message = envelope.get("message")
                yield NormalizedModelEvent(
                    event_type=ModelEventType.ERROR,
                    provider_id=request.provider_id,
                    model_id=request.model_id,
                    protocol_family=request.protocol_family,
                    error_code=code.strip() if isinstance(code, str) and code.strip() else "CLINE_BRIDGE_ERROR",
                    text=message.strip() if isinstance(message, str) and message.strip() else "Cline bridge failed",
                    metadata={"backend": "@cline/llms-sidecar"},
                )
                continue

            if kind == "end":
                continue
            raise ClineSidecarProcessError(f"unsupported Cline bridge envelope kind: {kind!r}")

        if not terminal_seen:
            raise ClineSidecarProcessError("Cline bridge ended without a terminal provider event")

    def _run_bridge_process(self, payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
        bridge_path = self._bridge_path.resolve()
        if not bridge_path.is_file():
            raise ClineSidecarProcessError(f"Cline bridge entrypoint not found: {bridge_path}")

        process = subprocess.Popen(
            [self._node_executable, str(bridge_path)],
            cwd=str(bridge_path.parent),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            shell=False,
        )
        with self._process_lock:
            self._active_process = process
        try:
            assert process.stdin is not None
            assert process.stdout is not None
            process.stdin.write(json.dumps(payload, ensure_ascii=False))
            process.stdin.close()

            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    envelope = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ClineSidecarProcessError("Cline bridge emitted invalid JSONL") from exc
                if not isinstance(envelope, Mapping):
                    raise ClineSidecarProcessError("Cline bridge JSONL envelope must be an object")
                yield envelope

            return_code = process.wait()
            stderr = process.stderr.read().strip() if process.stderr is not None else ""
            if return_code != 0:
                detail = f": {stderr}" if stderr else ""
                raise ClineSidecarProcessError(f"Cline bridge exited with code {return_code}{detail}")
        finally:
            with self._process_lock:
                if self._active_process is process:
                    self._active_process = None

    def _require_request_matches_config(self, request: ProviderTurnRequest) -> None:
        configured_provider = self._provider_config.get("providerId")
        configured_model = self._provider_config.get("modelId")
        if configured_provider != request.provider_id:
            raise ClineSidecarProcessError("ProviderTurnRequest provider_id does not match sidecar provider_config")
        if configured_model != request.model_id:
            raise ClineSidecarProcessError("ProviderTurnRequest model_id does not match sidecar provider_config")


def _serialize_tool_output(output: Any) -> str:
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ClineSidecarProcessError("tool result output must be JSON-serializable or a string") from exc


def _optional_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _default_bridge_path() -> Path:
    return Path(__file__).resolve().parents[1] / "provider_bridge" / "cline_llms" / "bridge.mjs"
