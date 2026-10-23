"""Provider-neutral OpenAI-compatible backend for bounded LBE reasoning."""
from __future__ import annotations

import json
import re
import copy
import http.client
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath, PureWindowsPath
from collections.abc import Iterator
from typing import Any, Mapping, Protocol

import jsonschema

from .reasoning_contracts import (
    ExplanationRequest,
    ExplanationResult,
    ReasoningPlan,
    ReasoningRequest,
)


# Bounded need of one structured planning/explanation step. Reasoning models spend
# hidden thinking tokens inside this budget; 512 truncated them to content=null.
_REASONING_MAX_TOKENS = 2048

# Output-token bounding. A provider will happily default an omitted `max_tokens` to the
# model's full output ceiling (for example 131072 on OpenRouter), which is neither the
# model's context window nor what a bounded governed step needs, and it turns a normal
# call into a provider rejection. LBE therefore always sends an explicit, bounded value.
#
#   actual max_tokens = min(configured or advertised limit, LBE ceiling, request need)
#
# This is a static, LBE-owned bound. It is deliberately not credit-aware: provider
# billing state is not a runtime policy owner, and shrinking a request because an
# account balance changed would be a silent substitution.
LBE_MAX_REQUESTED_OUTPUT_TOKENS = 8192
LBE_DEFAULT_REQUESTED_OUTPUT_TOKENS = 4096


def resolve_max_output_tokens(
    *,
    configured: int | None = None,
    requirement: int | None = None,
) -> int:
    """Resolve one bounded output-token limit for a governed provider call.

    `configured` is the explicit user/provider cap (ProviderConfig.max_output_tokens).
    `requirement` is the request-specific bounded need of the step being executed.
    """
    if configured is not None:
        if isinstance(configured, bool) or not isinstance(configured, int):
            raise ValueError("configured max_output_tokens must be an integer")
        if configured <= 0:
            raise ValueError("configured max_output_tokens must be positive")
        if configured > LBE_MAX_REQUESTED_OUTPUT_TOKENS:
            raise ValueError(
                "configured max_output_tokens exceeds the LBE request-policy maximum of "
                f"{LBE_MAX_REQUESTED_OUTPUT_TOKENS}"
            )
        limit = configured
    else:
        limit = LBE_DEFAULT_REQUESTED_OUTPUT_TOKENS

    if requirement is not None:
        if isinstance(requirement, bool) or not isinstance(requirement, int):
            raise ValueError("max_output_tokens requirement must be an integer")
        if requirement <= 0:
            raise ValueError("max_output_tokens requirement must be positive")
        limit = min(limit, requirement)
    return limit


@dataclass(frozen=True)
class ProviderConfig:
    endpoint: str
    model: str
    timeout_seconds: float
    api_key: str | None = None
    reasoning_effort: str | None = None
    provider_id: str | None = None
    # Optional explicit output cap. `None` means "no user/provider cap", and the
    # resolver applies the LBE default and ceiling. It is never the context window.
    max_output_tokens: int | None = None
    # Extra request headers for custom providers (e.g. gateways needing x-api-key).
    headers: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, str) or not self.endpoint.strip():
            raise ValueError("provider endpoint must be a non-empty string")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("provider model must be a non-empty string")
        if not isinstance(self.timeout_seconds, (int, float)) or self.timeout_seconds <= 0:
            raise ValueError("provider timeout_seconds must be greater than zero")
        if self.reasoning_effort is not None and (
            not isinstance(self.reasoning_effort, str) or not self.reasoning_effort.strip()
        ):
            raise ValueError("provider reasoning_effort must be a non-empty string when supplied")
        if self.provider_id is not None and (
            not isinstance(self.provider_id, str) or not self.provider_id.strip()
        ):
            raise ValueError("provider_id must be a non-empty string when supplied")


def apply_credentials(config: "ProviderConfig", headers: dict[str, str]) -> dict[str, str]:
    """Add bearer auth and any custom headers; custom headers win on conflict."""
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    for name, value in (config.headers or {}).items():
        headers[str(name)] = str(value)
    return headers


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _openai_compatible_catalog(config: ProviderConfig) -> list[dict[str, Any]]:
    """GET the /models catalog beside the completion route, without inference."""
    if not isinstance(config, ProviderConfig):
        raise TypeError("config must be a ProviderConfig")
    parsed = urllib.parse.urlsplit(config.endpoint)
    path = parsed.path.rstrip("/")
    suffix = next(
        (item for item in ("/chat/completions", "/completions") if path.endswith(item)),
        None,
    )
    if suffix is None or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProviderError(
            "MODEL_DISCOVERY_UNSUPPORTED",
            "provider endpoint does not identify an OpenAI-compatible completion route",
        )
    models_path = path[: -len(suffix)] + "/models"
    models_url = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, models_path, "", "")
    )
    headers = apply_credentials(config, {"Accept": "application/json"})
    request = urllib.request.Request(models_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(
            request, timeout=min(float(config.timeout_seconds), 5.0)
        ) as response:
            payload = json.loads(response.read())
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(
            "MODEL_DISCOVERY_FAILED", "provider model catalog request failed"
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ProviderError(
            "MODEL_DISCOVERY_INVALID_RESPONSE",
            "provider model catalog response did not contain a data array",
        )
    return [item for item in payload["data"] if isinstance(item, dict)]


def discover_openai_compatible_model_ids(config: ProviderConfig) -> tuple[str, ...]:
    """Read IDs from /v1/models without prompting or performing inference."""
    model_ids: list[str] = []
    for item in _openai_compatible_catalog(config):
        model_id = item.get("id")
        if isinstance(model_id, str) and model_id.strip():
            clean_id = model_id.strip()
            if clean_id not in model_ids:
                model_ids.append(clean_id)
    return tuple(model_ids)


# Field names providers use for a model's context size in their /models entry.
_CONTEXT_WINDOW_FIELDS = (
    "context_window", "context_length", "loaded_context_length",
    "max_context_length", "max_model_len",
)


def discover_openai_compatible_context_window(config: ProviderConfig, model_id: str) -> int | None:
    """Context size the provider itself reports for ``model_id`` in its catalog.

    Only a positive integer from that model's own entry counts. ``None`` means
    the provider did not report one; callers must show nothing rather than guess.
    """
    for item in _openai_compatible_catalog(config):
        if item.get("id") != model_id:
            continue
        for field in _CONTEXT_WINDOW_FIELDS:
            value = item.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                return value
        return None
    return None


class JsonTransport(Protocol):
    supports_cancellation: bool

    def post_json(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]: ...

    def cancel(self) -> None: ...

    def stream_json(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Iterator[Mapping[str, Any]]: ...


class UrllibJsonTransport:
    supports_cancellation = False  # http.client/urlib cannot be reliably cancelled from another thread

    def __init__(self) -> None:
        pass

    def cancel(self) -> None:
        """Request cancellation - not supported by urllib transport."""
        raise ProviderError("PROVIDER_CANCELLED", "live provider cancellation is not available for this transport")

    def post_json(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            raise ProviderError("PROVIDER_HTTP_ERROR", f"HTTP {exc.code}: {detail}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ProviderError("PROVIDER_TIMEOUT", str(exc) or "provider request timed out") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, (TimeoutError, socket.timeout)):
                raise ProviderError("PROVIDER_TIMEOUT", str(reason) or "provider request timed out") from exc
            raise ProviderError("PROVIDER_TRANSPORT_ERROR", str(reason)) from exc
        except OSError as exc:
            raise ProviderError("PROVIDER_TRANSPORT_ERROR", str(exc)) from exc

        if not raw:
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider returned an empty response body")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider returned invalid JSON") from exc
        if not isinstance(decoded, Mapping):
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider response must be a JSON object")
        return decoded

    def stream_json(
        self,
        *,
        endpoint: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Iterator[Mapping[str, Any]]:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={**dict(headers), "Accept": "text/event-stream"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    data = line[5:].strip() if line.startswith("data:") else line
                    if data == "[DONE]":
                        return
                    try:
                        decoded = json.loads(data)
                    except json.JSONDecodeError as exc:
                        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider returned invalid stream JSON") from exc
                    if not isinstance(decoded, Mapping):
                        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider stream event must be a JSON object")
                    yield decoded
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            raise ProviderError("PROVIDER_HTTP_ERROR", f"HTTP {exc.code}: {detail}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ProviderError("PROVIDER_TIMEOUT", str(exc) or "provider request timed out") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise ProviderError("PROVIDER_TRANSPORT_ERROR", str(reason)) from exc
        except OSError as exc:
            raise ProviderError("PROVIDER_TRANSPORT_ERROR", str(exc)) from exc


class OpenAICompatibleReasoningBackend:
    def __init__(self, *, config: ProviderConfig, transport: JsonTransport | None = None) -> None:
        self._config = config
        self._transport = transport or UrllibJsonTransport()

    def plan(self, request: ReasoningRequest) -> ReasoningPlan:
        # Concrete runtime options, not example strings that smaller models
        # can copy as literal guard/tool IDs. Controller still validates every
        # returned ID; this changes guidance, never authority.
        contract = dict(_PLANNING_OUTPUT_CONTRACT)
        contract["candidate_guard_ids"] = list(request.approved_guard_ids)
        contract["evidence_requests"] = [
            {"tool_id": tool_id, "path": "workspace-relative evidence path",
             "reason": "why this evidence is needed"}
            for tool_id in request.approved_tools
        ]
        # Also constrain the provider's structured-output schema to runtime
        # approved names. This does not authorize a tool or normalize unknown
        # IDs: the controller remains the independent fail-closed authority.
        schema = copy.deepcopy(_PLANNING_JSON_SCHEMA)
        # An empty enum is an invalid schema for most providers. With nothing
        # approved, keep the plain string type; the controller still rejects
        # any returned ID.
        if request.approved_guard_ids:
            schema["properties"]["candidate_guard_ids"]["items"] = {
                "type": "string", "enum": list(request.approved_guard_ids),
            }
        if request.approved_tools:
            schema["properties"]["evidence_requests"]["items"]["properties"]["tool_id"] = {
                "type": "string", "enum": list(request.approved_tools),
            }
        result = self._complete(
            "planning",
            _PLANNING_SYSTEM_PROMPT,
            contract,
            schema,
            _planning_input_payload(request),
        )
        try:
            plan = ReasoningPlan.from_mapping(result)
            _require_relative_evidence_paths(plan)
            jsonschema.validate(result, _PLANNING_JSON_SCHEMA)
            return plan
        except (TypeError, ValueError, jsonschema.ValidationError) as exc:
            detail = exc.message if isinstance(exc, jsonschema.ValidationError) else str(exc)
            raise ProviderError("PROVIDER_SCHEMA_ERROR", f"invalid planning response: {detail}") from exc

    def explain(self, request: ExplanationRequest) -> ExplanationResult:
        result = self._complete(
            "explanation",
            _EXPLANATION_SYSTEM_PROMPT,
            _EXPLANATION_OUTPUT_CONTRACT,
            _EXPLANATION_JSON_SCHEMA,
            asdict(request),
        )
        try:
            return ExplanationResult.from_mapping(result)
        except (TypeError, ValueError) as exc:
            raise ProviderError("PROVIDER_SCHEMA_ERROR", f"invalid explanation response: {exc}") from exc

    def _complete(
        self,
        stage: str,
        system_prompt: str,
        output_contract: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        input_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        payload = {
            "model": self._config.model.strip(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "stage": stage,
                            "output_contract": output_contract,
                            "input": input_payload,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": resolve_max_output_tokens(
                configured=self._config.max_output_tokens,
                requirement=_REASONING_MAX_TOKENS,
            ),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": f"lbe_{stage}_response",
                    "strict": True,
                    "schema": _provider_wire_schema(output_schema, self._config.provider_id),
                },
            },
        }
        if self._config.reasoning_effort is not None:
            payload["reasoning_effort"] = self._config.reasoning_effort.strip()
        headers = apply_credentials(self._config, {"Content-Type": "application/json"})
        response = self._transport.post_json(
            endpoint=self._config.endpoint.strip(),
            payload=payload,
            headers=headers,
            timeout_seconds=float(self._config.timeout_seconds),
        )
        content = _extract_message_content(response)
        try:
            decoded = decode_structured_reply(content)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                "PROVIDER_RESPONSE_ERROR",
                "provider message content is not valid JSON: " + repr(content[:120]),
            ) from exc
        if not isinstance(decoded, Mapping):
            raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider message content must decode to an object")
        return decoded


def _provider_wire_schema(schema: Mapping[str, Any], provider_id: str | None) -> Mapping[str, Any]:
    # OpenAI-compatible endpoints can expose a local grammar engine under a
    # generic provider identity. Schema wire compatibility must not depend on
    # a provider label: retain LBE's complete canonical schema for validation
    # after the model responds, while omitting known unsupported grammar bounds.
    wire_schema = copy.deepcopy(schema)

    def remove_max_items(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("maxItems", None)
            for child in value.values():
                remove_max_items(child)
        elif isinstance(value, list):
            for child in value:
                remove_max_items(child)

    remove_max_items(wire_schema)
    return wire_schema


def _planning_input_payload(request: ReasoningRequest) -> Mapping[str, Any]:
    payload = asdict(request)
    identity = dict(payload.get("workspace_identity", {}))
    identity.pop("target_project_root", None)
    payload["workspace_identity"] = identity
    return payload


def _require_relative_evidence_paths(plan: ReasoningPlan) -> None:
    for item in plan.evidence_requests:
        path = item.path.strip()
        if (
            not path
            or PureWindowsPath(path).is_absolute()
            or PurePosixPath(path).is_absolute()
            or path.startswith(("/", "\\"))
            or (len(path) >= 2 and path[1] == ":")
        ):
            raise ValueError(f"evidence path must be workspace-relative: {item.path}")


_FENCED_OBJECT = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def decode_structured_reply(content: str) -> Any:
    """Decode a model's structured reply.

    Models routinely wrap the one JSON object in a markdown fence or a sentence
    of prose. Accept the first complete top-level object and nothing else; the
    caller still validates it against the schema, so a non-conforming object is
    rejected exactly as before. Raises json.JSONDecodeError when no object is
    present.
    """
    text = content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as original:
        fenced = _FENCED_OBJECT.search(text)
        candidates = [fenced.group(1)] if fenced else []
        start = text.find("{")
        if start >= 0:
            candidates.append(text[start:])
        decoder = json.JSONDecoder()
        for candidate in candidates:
            try:
                value, _ = decoder.raw_decode(candidate.strip())
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise original


def _extract_message_content(response: Mapping[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider response must contain exactly one choice")
    choice = choices[0]
    if not isinstance(choice, Mapping):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider choice must be an object")
    message = choice.get("message")
    if not isinstance(message, Mapping):
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider choice must contain a message object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        finish_reason = choice.get("finish_reason")
        if finish_reason == "length":
            raise ProviderError(
                "PROVIDER_OUTPUT_TRUNCATED",
                "provider stopped at its output limit (finish_reason=length) before producing "
                "content; the model likely spent the budget on hidden reasoning. Raise "
                "max_output_tokens or lower reasoning_effort in the provider config.",
            )
        raise ProviderError("PROVIDER_RESPONSE_ERROR", "provider message content must be a non-empty string")
    return content.strip()


_PLANNING_OUTPUT_CONTRACT = {
    "interpreted_problem": "non-empty string",
    "ambiguities": ["string"],
    "candidate_guard_ids": ["approved guard ID string"],
    "evidence_requests": [
        {
            "tool_id": "approved tool ID string",
            "path": "workspace-relative path without a leading slash, backslash, or drive prefix",
            "reason": "non-empty string",
        }
    ],
    "validation_requests": [],
    "explanation_focus": ["string"],
    "proposal_candidate": "optional governed rule candidate object",
}

_EXPLANATION_OUTPUT_CONTRACT = {"explanation": "non-empty string"}

_PLANNING_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "interpreted_problem": {"type": "string", "minLength": 1},
        "ambiguities": {"type": "array", "items": {"type": "string"}},
        "candidate_guard_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 1},
        "evidence_requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool_id": {"type": "string", "minLength": 1},
                    "path": {
                        "type": "string",
                        "minLength": 1,
                        "pattern": "^[^/\\\\:][^:]*$",
                    },
                    "reason": {"type": "string", "minLength": 1},
                },
                "required": ["tool_id", "path", "reason"],
                "additionalProperties": False,
            },
        },
        "validation_requests": {"type": "array", "items": {"type": "string"}, "maxItems": 0},
        "explanation_focus": {"type": "array", "items": {"type": "string"}},
        "proposal_candidate": {
            "type": ["object", "null"],
            "properties": {
                "target_profile_path": {"type": "string", "minLength": 1},
                "trigger": {"type": "string", "minLength": 1},
                "rationale": {"type": "string", "minLength": 1},
                "scope": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
                "required_action": {"type": "string", "minLength": 1},
                "severity": {"type": "string", "enum": ["info", "warning", "error", "blocking"]},
                "exceptions": {"type": "array", "items": {"type": "string"}},
                "validation_plan": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
                "rollback_plan": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
            },
            "required": [
                "target_profile_path", "trigger", "rationale", "scope",
                "required_action", "severity", "exceptions",
                "validation_plan", "rollback_plan",
            ],
            "additionalProperties": False,
        },
    },
    "required": [
        "interpreted_problem",
        "ambiguities",
        "candidate_guard_ids",
        "evidence_requests",
        "validation_requests",
        "explanation_focus",
    ],
    "additionalProperties": False,
}

_EXPLANATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string", "minLength": 1},
    },
    "required": ["explanation"],
    "additionalProperties": False,
}

_PLANNING_SYSTEM_PROMPT = """You are the bounded planning stage inside LBE. Return exactly one top-level JSON object with exactly these six required keys: interpreted_problem, ambiguities, candidate_guard_ids, evidence_requests, validation_requests, explanation_focus. You may optionally include a seventh key, proposal_candidate, only when the deterministic result warrants a governed workspace rule; it must be an object with exactly these keys: target_profile_path, trigger, rationale, scope, required_action, severity, exceptions, validation_plan, rollback_plan, and must be omitted otherwise. Do not wrap the object in planning_contract, result, output, data, or any other key. interpreted_problem must be a non-empty string. ambiguities, candidate_guard_ids, and explanation_focus must be JSON arrays of strings and may be empty. validation_requests must be an empty JSON array because deterministic validation is owned by LBE. evidence_requests must be a JSON array of objects with exactly tool_id, path, and reason. Every evidence path must be workspace-relative and must not begin with a slash or backslash, contain a drive prefix, use a UNC prefix, or reconstruct an absolute workspace root. Use only approved guard IDs, approved tool IDs, and workspace-relative paths supplied in the input. Do not select validation IDs. CRITICAL CONSISTENCY RULE: candidate_guard_ids may contain a guard only when evidence_requests contains the bounded evidence request needed to evaluate that same guard; when no evidence is needed, candidate_guard_ids MUST be an empty array. Do not return verdicts, authorization, commands, writes, repairs, mutations, policy decisions, or memory-promotion instructions. Do not include Markdown or prose outside the JSON object."""

_EXPLANATION_SYSTEM_PROMPT = """You are the bounded explanation stage inside LBE. The deterministic result is final. Return exactly one top-level JSON object with exactly one key: explanation. Do not wrap it in result, output, data, or any other key. explanation must be a non-empty string that concisely explains only the supplied result and evidence. Do not add or alter verdicts, authority, evidence, governance state, commands, writes, repairs, or policy decisions. Do not include Markdown or prose outside the JSON object."""
