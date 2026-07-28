from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from .invocation_adapter import (
    CancellationSignal,
    InvocationAdapterError,
    InvocationTransport,
    RuntimeNeutralInvocationAdapter,
)


_REQUEST_FIELDS = frozenset({"workspace_root", "workspace_id", "reason", "max_results"})
_PROFILE_FIELDS = frozenset(
    {
        "profile_id",
        "version",
        "transport_factory",
        "transport_config",
        "request_mapping",
        "capabilities",
        "timeout_seconds",
        "cancellation_supported",
    }
)
_REQUIRED_CAPABILITIES = frozenset({"callback_inspection"})
_FORBIDDEN_CAPABILITIES = frozenset(
    {"arbitrary_guard_selection", "workspace_mutation", "repair_execution"}
)
_MAX_TIMEOUT_SECONDS = 300.0


class TransportFactory(Protocol):
    def __call__(self, config: Mapping[str, Any]) -> InvocationTransport:
        """Create one configured transport from environment-supplied configuration."""


@dataclass(frozen=True)
class IntegrationProfileError(ValueError):
    code: str
    message: str
    details: Mapping[str, Any] | None = None

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.details is not None:
            result["details"] = dict(self.details)
        return result


@dataclass(frozen=True)
class RuntimeIntegrationProfile:
    profile_id: str
    version: str
    transport_factory: str
    transport_config: Mapping[str, Any]
    request_mapping: Mapping[str, str]
    capabilities: Mapping[str, bool]
    timeout_seconds: float = 30.0
    cancellation_supported: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RuntimeIntegrationProfile":
        if not isinstance(value, Mapping):
            raise IntegrationProfileError(
                "invalid_profile", "Integration profile must be an object"
            )
        unknown = sorted(set(value) - _PROFILE_FIELDS)
        if unknown:
            raise IntegrationProfileError(
                "invalid_profile",
                f"Unknown integration profile fields: {unknown}",
                {"unknown_fields": unknown},
            )

        profile_id = _required_text(value, "profile_id")
        version = _required_text(value, "version")
        factory_name = _required_text(value, "transport_factory")
        transport_config = _mapping(value.get("transport_config", {}), "transport_config")
        request_mapping = _request_mapping(value.get("request_mapping"))
        capabilities = _capabilities(value.get("capabilities"))
        timeout = _timeout(value.get("timeout_seconds", 30.0))
        cancellation_supported = value.get("cancellation_supported", True)
        if not isinstance(cancellation_supported, bool):
            raise IntegrationProfileError(
                "invalid_profile", "'cancellation_supported' must be boolean"
            )

        return cls(
            profile_id=profile_id,
            version=version,
            transport_factory=factory_name,
            transport_config=dict(transport_config),
            request_mapping=dict(request_mapping),
            capabilities=dict(capabilities),
            timeout_seconds=timeout,
            cancellation_supported=cancellation_supported,
        )

    def compile(
        self,
        transport_factories: Mapping[str, TransportFactory],
    ) -> "CompiledRuntimeIntegration":
        if not isinstance(transport_factories, Mapping):
            raise IntegrationProfileError(
                "invalid_factory_registry", "Transport factory registry must be an object"
            )
        factory = transport_factories.get(self.transport_factory)
        if factory is None or not callable(factory):
            raise IntegrationProfileError(
                "transport_factory_unavailable",
                f"Transport factory is not configured: {self.transport_factory}",
                {"transport_factory": self.transport_factory},
            )
        try:
            transport = factory(dict(self.transport_config))
        except IntegrationProfileError:
            raise
        except Exception as exc:
            raise IntegrationProfileError(
                "transport_configuration_rejected",
                str(exc) or type(exc).__name__,
                {"transport_factory": self.transport_factory},
            ) from exc
        if not callable(getattr(transport, "invoke", None)):
            raise IntegrationProfileError(
                "invalid_transport",
                "Configured transport does not implement invoke()",
                {"transport_factory": self.transport_factory},
            )
        return CompiledRuntimeIntegration(
            profile=self,
            adapter=RuntimeNeutralInvocationAdapter(
                transport, default_timeout_seconds=self.timeout_seconds
            ),
        )


@dataclass(frozen=True)
class CompiledRuntimeIntegration:
    profile: RuntimeIntegrationProfile
    adapter: RuntimeNeutralInvocationAdapter

    def map_request(self, runtime_input: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(runtime_input, Mapping):
            raise IntegrationProfileError(
                "invalid_runtime_input", "Runtime input must be an object"
            )
        request: dict[str, Any] = {}
        for target, source in self.profile.request_mapping.items():
            if source in runtime_input:
                request[target] = runtime_input[source]
        if "workspace_root" not in request:
            raise IntegrationProfileError(
                "invalid_runtime_input",
                "Runtime input does not supply the mapped workspace_root field",
                {"source_field": self.profile.request_mapping["workspace_root"]},
            )
        return request

    def invoke(
        self,
        runtime_input: Mapping[str, Any],
        *,
        cancellation: CancellationSignal | None = None,
    ) -> Mapping[str, Any]:
        if cancellation is not None and not self.profile.cancellation_supported:
            raise IntegrationProfileError(
                "unsupported_capability",
                "This integration profile does not support cancellation",
                {"capability": "cancellation"},
            )
        request = self.map_request(runtime_input)
        try:
            return self.adapter.invoke(
                request,
                timeout_seconds=self.profile.timeout_seconds,
                cancellation=cancellation,
            )
        except InvocationAdapterError:
            raise


def _required_text(value: Mapping[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise IntegrationProfileError(
            "invalid_profile", f"'{field}' must be a non-empty string"
        )
    return item.strip()


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise IntegrationProfileError(
            "invalid_profile", f"'{field}' must be an object"
        )
    return value


def _request_mapping(value: Any) -> Mapping[str, str]:
    mapping = _mapping(value, "request_mapping")
    unknown = sorted(set(mapping) - _REQUEST_FIELDS)
    if unknown:
        raise IntegrationProfileError(
            "invalid_profile",
            f"Unsupported callback request mappings: {unknown}",
            {"unsupported_fields": unknown},
        )
    if "workspace_root" not in mapping:
        raise IntegrationProfileError(
            "invalid_profile", "'request_mapping.workspace_root' is required"
        )
    result: dict[str, str] = {}
    for target, source in mapping.items():
        if not isinstance(source, str) or not source.strip():
            raise IntegrationProfileError(
                "invalid_profile",
                f"Request mapping for '{target}' must name a non-empty source field",
            )
        result[target] = source.strip()
    if len(set(result.values())) != len(result):
        raise IntegrationProfileError(
            "invalid_profile", "Request mappings must use distinct source fields"
        )
    return result


def _capabilities(value: Any) -> Mapping[str, bool]:
    capabilities = _mapping(value, "capabilities")
    for name, enabled in capabilities.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(enabled, bool):
            raise IntegrationProfileError(
                "invalid_profile", "Capabilities must map non-empty names to booleans"
            )
    missing = sorted(name for name in _REQUIRED_CAPABILITIES if capabilities.get(name) is not True)
    if missing:
        raise IntegrationProfileError(
            "contradictory_profile",
            "Callback inspection capability must be enabled",
            {"required_capabilities": missing},
        )
    forbidden = sorted(name for name in _FORBIDDEN_CAPABILITIES if capabilities.get(name) is True)
    if forbidden:
        raise IntegrationProfileError(
            "contradictory_profile",
            "Read-only integration profile enables prohibited capabilities",
            {"prohibited_capabilities": forbidden},
        )
    result = dict(capabilities)
    for name in _FORBIDDEN_CAPABILITIES:
        result.setdefault(name, False)
    return result


def _timeout(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IntegrationProfileError(
            "invalid_profile", "'timeout_seconds' must be numeric"
        )
    timeout = float(value)
    if timeout <= 0 or timeout > _MAX_TIMEOUT_SECONDS:
        raise IntegrationProfileError(
            "invalid_profile",
            f"'timeout_seconds' must be greater than zero and at most {_MAX_TIMEOUT_SECONDS:g}",
        )
    return timeout
