"""Tool-aware extension of the existing bounded OpenAI-compatible reasoning backend.

This module adds one optional model request shape for governed coding actions.
It does not execute tools or grant write authority. The runtime gateway and R6C
remain the only execution/authorization owners.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from .reasoning_contracts import ReasoningPlan, ReasoningRequest
from .reasoning_provider import (
    OpenAICompatibleReasoningBackend,
    ProviderError,
    _PLANNING_JSON_SCHEMA,
    _PLANNING_OUTPUT_CONTRACT,
    _require_relative_evidence_paths,
)


@dataclass(frozen=True)
class PlannedToolRequest:
    tool_id: str
    path: str
    old_text: str
    new_text: str
    reason: str

    @property
    def arguments(self) -> Mapping[str, Any]:
        return {
            "path": self.path,
            "old_text": self.old_text,
            "new_text": self.new_text,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannedToolRequest":
        expected = {"tool_id", "path", "old_text", "new_text", "reason"}
        if set(value) != expected:
            missing = sorted(expected - set(value))
            extra = sorted(set(value) - expected)
            parts: list[str] = []
            if missing:
                parts.append("missing " + ", ".join(missing))
            if extra:
                parts.append("unsupported " + ", ".join(extra))
            raise ValueError("tool request fields are invalid: " + "; ".join(parts))
        tool_id = _required_text(value.get("tool_id"), "tool_request.tool_id")
        path = _required_text(value.get("path"), "tool_request.path")
        old_text = _required_text(value.get("old_text"), "tool_request.old_text")
        new_text = value.get("new_text")
        if not isinstance(new_text, str):
            raise ValueError("tool_request.new_text must be a string")
        reason = _required_text(value.get("reason"), "tool_request.reason")
        _require_relative_path(path)
        return cls(
            tool_id=tool_id,
            path=path,
            old_text=old_text,
            new_text=new_text,
            reason=reason,
        )


@dataclass(frozen=True)
class ToolAwareReasoningPlan(ReasoningPlan):
    tool_requests: tuple[PlannedToolRequest, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ToolAwareReasoningPlan":
        raw = dict(value)
        requests = raw.pop("tool_requests", [])
        if not isinstance(requests, list) or not all(isinstance(item, Mapping) for item in requests):
            raise ValueError("reasoning_plan.tool_requests must be an array of objects")
        if len(requests) > 1:
            raise ValueError("reasoning_plan.tool_requests supports at most one action")
        base = ReasoningPlan.from_mapping(raw)
        return cls(
            interpreted_problem=base.interpreted_problem,
            ambiguities=base.ambiguities,
            candidate_guard_ids=base.candidate_guard_ids,
            evidence_requests=base.evidence_requests,
            validation_requests=base.validation_requests,
            explanation_focus=base.explanation_focus,
            proposal_candidate=base.proposal_candidate,
            tool_requests=tuple(PlannedToolRequest.from_mapping(item) for item in requests),
        )


class ToolAwareOpenAICompatibleReasoningBackend(OpenAICompatibleReasoningBackend):
    """Use the existing provider transport while allowing bounded tool requests."""

    def plan(self, request: ReasoningRequest) -> ToolAwareReasoningPlan:
        result = self._complete(
            "planning",
            _TOOL_AWARE_PLANNING_SYSTEM_PROMPT,
            _tool_aware_output_contract(),
            _tool_aware_schema(),
            _planning_input_payload(request),
        )
        try:
            plan = ToolAwareReasoningPlan.from_mapping(result)
            _require_relative_evidence_paths(plan)
            approved = set(request.approved_tools)
            for item in plan.tool_requests:
                if item.tool_id not in approved:
                    raise ValueError(f"tool request is not approved for this runtime: {item.tool_id}")
            return plan
        except (TypeError, ValueError) as exc:
            raise ProviderError("PROVIDER_SCHEMA_ERROR", f"invalid planning response: {exc}") from exc


def _planning_input_payload(request: ReasoningRequest) -> Mapping[str, Any]:
    # Keep the same privacy boundary as reasoning_provider._planning_input_payload.
    from dataclasses import asdict

    payload = asdict(request)
    identity = dict(payload.get("workspace_identity", {}))
    identity.pop("target_project_root", None)
    payload["workspace_identity"] = identity
    return payload


def _tool_aware_output_contract() -> Mapping[str, Any]:
    return {
        **dict(_PLANNING_OUTPUT_CONTRACT),
        "tool_requests": [
            {
                "tool_id": "approved tool ID string",
                "path": "workspace-relative path",
                "old_text": "exact non-empty text expected once in the target file",
                "new_text": "replacement text; may be empty",
                "reason": "non-empty string",
            }
        ],
    }


def _tool_aware_schema() -> Mapping[str, Any]:
    schema = deepcopy(_PLANNING_JSON_SCHEMA)
    properties = schema["properties"]
    properties["tool_requests"] = {
        "type": "array",
        "maxItems": 1,
        "items": {
            "type": "object",
            "properties": {
                "tool_id": {"type": "string", "minLength": 1},
                "path": {
                    "type": "string",
                    "minLength": 1,
                    "pattern": "^[^/\\\\:][^:]*$",
                },
                "old_text": {"type": "string", "minLength": 1},
                "new_text": {"type": "string"},
                "reason": {"type": "string", "minLength": 1},
            },
            "required": ["tool_id", "path", "old_text", "new_text", "reason"],
            "additionalProperties": False,
        },
    }
    return schema


def _require_relative_path(path: str) -> None:
    if (
        PureWindowsPath(path).is_absolute()
        or PurePosixPath(path).is_absolute()
        or path.startswith(("/", "\\"))
        or (len(path) >= 2 and path[1] == ":")
        or ".." in PurePosixPath(path.replace("\\", "/")).parts
    ):
        raise ValueError(f"tool request path must be workspace-relative: {path}")


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


_TOOL_AWARE_PLANNING_SYSTEM_PROMPT = """You are the bounded planning stage inside LBE. Return exactly one top-level JSON object with these six required keys: interpreted_problem, ambiguities, candidate_guard_ids, evidence_requests, validation_requests, explanation_focus. You may optionally include proposal_candidate using the existing governed rule-candidate contract. You may also optionally include tool_requests only when the input approved_tools contains workspace.replace_text and the user's requested coding change can be represented as one exact bounded text replacement. tool_requests must contain at most one object with exactly tool_id, path, old_text, new_text, reason. The path must be workspace-relative. old_text must be exact non-empty text expected once in the target file. Use only approved guard IDs and approved tool IDs supplied in the input. validation_requests must remain an empty array because validation is owned by LBE. Do not return shell commands, authorization decisions, verdicts, memory promotion, unrestricted writes, destructive operations, or paths outside the workspace. Do not include Markdown or prose outside the JSON object."""
