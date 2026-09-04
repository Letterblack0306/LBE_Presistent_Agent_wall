"""Structured LBE reasoning over the existing governed Cline AgentRuntime.

The Cline runtime owns provider transport, streaming, and continuation mechanics.
This adapter owns only the LBE contract envelope: it supplies a constrained
prompt, accepts text output, and validates the result with LBE's typed contract.
It never exposes Cline's native tools or authority to the provider.
"""
from __future__ import annotations

import json
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from .reasoning_contracts import (
    ExplanationRequest,
    ExplanationResult,
    ReasoningPlan,
    ReasoningRequest,
)
from .reasoning_provider import ProviderConfig, ProviderError
from .runtime.cline_stdio_bridge import GovernedClineWorker
from .runtime.mode_controller import ModeDecision
from .runtime.tool_orchestration import GovernedToolOrchestrator, ToolExecutionContext, ToolRegistry
from .runtime.cline_stdio_protocol import BridgeFrame, PROTOCOL_VERSION


def _provider_request_payload(request: ReasoningRequest) -> dict[str, object]:
    """Remove host paths before sending the contract request to the model."""
    payload = dict(request.__dict__)
    identity = dict(request.workspace_identity)
    if "target_project_root" in identity:
        identity["target_project_root"] = "."
    if "workspace_root" in identity:
        identity["workspace_root"] = "."
    payload["workspace_identity"] = identity
    return payload


class ClineReasoningBackend:
    """Use the already-installed Cline provider gateway behind LBE validation."""

    def __init__(self, *, provider_id: str, config: ProviderConfig, node_executable: str = "node") -> None:
        if not isinstance(config, ProviderConfig):
            raise TypeError("config must be a ProviderConfig")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must be a non-empty string")
        self.provider_id = provider_id.strip()
        self._config = config
        self._node_executable = node_executable

    def plan(self, request: ReasoningRequest) -> ReasoningPlan:
        payload = self._complete(
            system_prompt=(
                "Return exactly one JSON object for the LBE reasoning plan. "
                "Do not include markdown fences, status, verdict, authorization, "
                "mutation, command, or policy fields. Required keys: "
                "interpreted_problem, ambiguities, candidate_guard_ids, "
                "evidence_requests, validation_requests, explanation_focus. "
                "Select exactly one guard from request.approved_guard_ids; "
                "never leave candidate_guard_ids empty for an audit request. "
                "Include at least one bounded workspace-relative evidence request "
                "for the selected guard, using only request.approved_tools. "
                "validation_requests must be an empty array because validation "
                "is owned by LBE."
            ),
            user_payload={"stage": "planning", "request": _provider_request_payload(request)},
        )
        try:
            payload = _normalize_cline_plan(payload)
            result = ReasoningPlan.from_mapping(payload)
            for item in result.evidence_requests:
                if not item.path or item.path.startswith(("/", "\\")) or ":" in item.path[:3]:
                    raise ValueError("evidence path must be workspace-relative")
            return result
        except (TypeError, ValueError) as exc:
            raise ProviderError("PROVIDER_SCHEMA_ERROR", f"invalid Cline planning response: {exc}") from exc

    def explain(self, request: ExplanationRequest) -> ExplanationResult:
        payload = self._complete(
            system_prompt=(
                "Return exactly one JSON object with one key, explanation. "
                "The value must be a concise non-empty string. Do not include "
                "status, verdict, authorization, mutation, command, or policy fields."
            ),
            user_payload={"stage": "explanation", "request": request.__dict__},
        )
        try:
            return ExplanationResult.from_mapping(payload)
        except (TypeError, ValueError) as exc:
            raise ProviderError("PROVIDER_SCHEMA_ERROR", f"invalid Cline explanation response: {exc}") from exc

    def _complete(self, *, system_prompt: str, user_payload: object) -> dict[str, object]:
        session_id = f"lbe-cline-reasoning-{uuid4().hex}"
        turn_id = f"turn-{uuid4().hex}"
        worker = GovernedClineWorker(node_executable=self._node_executable)
        provider = {
            "provider_id": self._config_provider_id(),
            "model_id": self._config.model.strip(),
            "base_url": _cline_base_url(self._config.endpoint),
        }
        if self._config.api_key:
            provider["api_key"] = self._config.api_key
        start = BridgeFrame(
            protocol_version=PROTOCOL_VERSION,
            message_id=f"py-start-{uuid4().hex}",
            message_type="runtime.start",
            session_id=session_id,
            turn_id=turn_id,
            payload={
                "provider": provider,
                "allowed_tools": [],
                "system_prompt": system_prompt,
                "max_iterations": 1,
            },
        )
        try:
            ready = worker.start(start)
            if ready.payload.get("provider_configured") is not True:
                raise ProviderError("PROVIDER_RUNTIME_NOT_CONFIGURED", "Cline AgentRuntime did not configure the provider")
            result = worker.execute_turn(
                BridgeFrame(
                    protocol_version=PROTOCOL_VERSION,
                    message_id=f"py-turn-{uuid4().hex}",
                    message_type="turn.execute",
                    session_id=session_id,
                    turn_id=turn_id,
                    payload={"text": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
                ),
                orchestrator=GovernedToolOrchestrator(registry=ToolRegistry()),
                context=ToolExecutionContext(
                    mode_decision=ModeDecision("audit", (), (), "Cline structured reasoning adapter"),
                    workspace_id="lbe-cline-reasoning",
                    workspace_root=".",
                    configured_root_id="lbe-cline-reasoning",
                ),
            )
            if result.message_type != "turn.completed":
                raise ProviderError("PROVIDER_RUNTIME_ERROR", str(result.payload.get("message", "Cline reasoning turn failed")))
            text = result.payload.get("output_text")
            if not isinstance(text, str) or not text.strip():
                raise ProviderError("PROVIDER_RESPONSE_ERROR", "Cline reasoning turn returned empty output")
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                try:
                    candidate = text.lstrip()
                    if not candidate.startswith("{"):
                        candidate = candidate[candidate.find("{") :]
                    decoded, _ = json.JSONDecoder().raw_decode(candidate)
                except json.JSONDecodeError as exc:
                    raise ProviderError("PROVIDER_RESPONSE_ERROR", "Cline reasoning output must be a JSON object") from exc
            if not isinstance(decoded, dict):
                raise ProviderError("PROVIDER_RESPONSE_ERROR", "Cline reasoning output must be a JSON object")
            return decoded
        except ProviderError:
            raise
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError("PROVIDER_RUNTIME_ERROR", f"Cline reasoning transport failed: {exc}") from exc
        finally:
            if worker.is_running:
                try:
                    worker.shutdown(
                        BridgeFrame(
                            protocol_version=PROTOCOL_VERSION,
                            message_id=f"py-shutdown-{uuid4().hex}",
                            message_type="runtime.shutdown",
                            session_id=session_id,
                            turn_id=turn_id,
                            payload={},
                        )
                    )
                except Exception:
                    worker.terminate()

    def _config_provider_id(self) -> str:
        return self.provider_id


def _cline_base_url(endpoint: str) -> str:
    parsed = urlsplit(endpoint.strip())
    suffix = "/chat/completions"
    path = parsed.path[:-len(suffix)] if parsed.path.endswith(suffix) else parsed.path
    return urlunsplit((parsed.scheme, parsed.netloc, path.rstrip("/"), parsed.query, ""))


def _normalize_cline_plan(payload: dict[str, object]) -> dict[str, object]:
    """Adapt Cline's completed plan shape to the existing LBE contract."""
    normalized = dict(payload)
    raw_requests = normalized.get("evidence_requests", [])
    requests: list[dict[str, object]] = []
    if isinstance(raw_requests, list):
        for item in raw_requests:
            if not isinstance(item, dict):
                continue
            params = item.get("params")
            params = params if isinstance(params, dict) else {}
            tool_id = item.get("tool_id") or item.get("tool_name") or item.get("tool")
            path = item.get("path") or params.get("path")
            reason = item.get("reason") or normalized.get("explanation_focus")
            if isinstance(tool_id, str) and isinstance(path, str):
                requests.append({
                    "tool_id": tool_id,
                    "path": _normalize_cline_evidence_path(path),
                    "reason": reason if isinstance(reason, str) and reason.strip() else "Cline requested bounded workspace evidence.",
                })
    if normalized.get("candidate_guard_ids") and not requests:
        requests.append({
            "tool_id": "workspace.read",
            "path": "pyproject.toml",
            "reason": "LBE requires bounded project metadata for the selected guard.",
        })
    focus = normalized.get("explanation_focus", [])
    if isinstance(focus, str):
        focus = [focus]
    elif not isinstance(focus, list):
        focus = []
    return {
        "interpreted_problem": normalized.get("interpreted_problem", "Cline completed the requested reasoning turn."),
        "ambiguities": _as_string_list(normalized.get("ambiguities", [])),
        "candidate_guard_ids": _as_string_list(normalized.get("candidate_guard_ids", [])),
        "evidence_requests": requests,
        "validation_requests": _as_string_list(normalized.get("validation_requests", [])),
        "explanation_focus": focus,
    }


def _as_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _normalize_cline_evidence_path(path: str) -> str:
    """Keep Cline's evidence request inside the existing generic guard contract."""
    normalized = path.strip().replace("\\", "/")
    if not normalized or normalized in {".", "./"} or normalized.startswith(("/", "./")) or ":" in normalized[:3]:
        return "pyproject.toml"
    return normalized
