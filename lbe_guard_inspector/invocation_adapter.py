from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_ALLOWED_REQUEST_FIELDS = frozenset(
    {"workspace_root", "workspace_id", "reason", "max_results"}
)
_DEFAULT_TIMEOUT_SECONDS = 30.0
_POLL_INTERVAL_SECONDS = 0.01


class CancellationSignal(Protocol):
    def is_cancelled(self) -> bool:
        """Return whether the current invocation should stop waiting."""


class InvocationTransport(Protocol):
    def invoke(
        self,
        payload: Mapping[str, Any],
        *,
        timeout_seconds: float,
        cancellation: CancellationSignal | None,
    ) -> Mapping[str, Any]:
        """Invoke the fixed callback inspection contract without reinterpretation."""


@dataclass(frozen=True)
class InvocationAdapterError(RuntimeError):
    code: str
    message: str
    details: Mapping[str, Any] | None = None
    retryable: bool = False

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details is not None:
            payload["details"] = dict(self.details)
        return payload


class CancellationToken:
    """Small runtime-neutral cancellation token."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


class InProcessTransport:
    """Invoke a configured local callable through the common adapter contract."""

    def __init__(self, target: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        if not callable(target):
            raise TypeError("target must be callable")
        self._target = target

    def invoke(
        self,
        payload: Mapping[str, Any],
        *,
        timeout_seconds: float,
        cancellation: CancellationSignal | None,
    ) -> Mapping[str, Any]:
        del timeout_seconds, cancellation
        result = self._target(payload)
        if not isinstance(result, Mapping):
            raise InvocationAdapterError(
                "invalid_transport_response",
                "In-process callback returned a non-object response",
            )
        return result


class LocalHttpTransport:
    """POST the callback request to a configurable local HTTP endpoint."""

    def __init__(self, endpoint: str) -> None:
        endpoint = endpoint.strip() if isinstance(endpoint, str) else ""
        if not endpoint:
            raise ValueError("endpoint must be a non-empty string")
        if not endpoint.startswith(("http://127.0.0.1:", "http://localhost:")):
            raise ValueError("endpoint must use local-only HTTP")
        self._endpoint = endpoint

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def invoke(
        self,
        payload: Mapping[str, Any],
        *,
        timeout_seconds: float,
        cancellation: CancellationSignal | None,
    ) -> Mapping[str, Any]:
        if cancellation is not None and cancellation.is_cancelled():
            raise InvocationAdapterError("cancelled", "Invocation was cancelled")

        body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
        request = Request(
            self._endpoint,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            response = urlopen(request, timeout=timeout_seconds)
            return self._decode_response(response)
        except HTTPError as exc:
            error_payload = self._decode_error_payload(exc)
            raise InvocationAdapterError(
                "endpoint_rejected",
                str(error_payload.get("message") or f"Endpoint returned HTTP {exc.code}"),
                details={"status": exc.code, "response": error_payload},
            ) from exc
        except URLError as exc:
            raise InvocationAdapterError(
                "transport_failure",
                f"Local callback endpoint could not be reached: {exc.reason}",
            ) from exc
        except TimeoutError as exc:
            raise InvocationAdapterError(
                "timeout",
                f"Invocation exceeded {timeout_seconds:g} seconds",
            ) from exc

    @staticmethod
    def _decode_response(response: HTTPResponse) -> Mapping[str, Any]:
        try:
            payload = json.loads(response.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvocationAdapterError(
                "invalid_transport_response",
                "Endpoint returned invalid UTF-8 JSON",
            ) from exc
        if not isinstance(payload, Mapping):
            raise InvocationAdapterError(
                "invalid_transport_response",
                "Endpoint returned a non-object JSON response",
            )
        return payload

    @staticmethod
    def _decode_error_payload(exc: HTTPError) -> Mapping[str, Any]:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"error": "http_error", "message": str(exc)}
        if isinstance(payload, Mapping):
            return payload
        return {"error": "http_error", "message": str(exc)}


class RuntimeNeutralInvocationAdapter:
    """Bounded transport-neutral adapter for the fixed callback inspection request."""

    def __init__(
        self,
        transport: InvocationTransport,
        *,
        default_timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not isinstance(default_timeout_seconds, (int, float)) or isinstance(
            default_timeout_seconds, bool
        ):
            raise TypeError("default_timeout_seconds must be numeric")
        if default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be greater than zero")
        self._transport = transport
        self._default_timeout_seconds = float(default_timeout_seconds)

    def invoke(
        self,
        payload: Mapping[str, Any],
        *,
        timeout_seconds: float | None = None,
        cancellation: CancellationSignal | None = None,
    ) -> Mapping[str, Any]:
        request = self._validate_request(payload)
        timeout = self._resolve_timeout(timeout_seconds)
        if cancellation is not None and cancellation.is_cancelled():
            raise InvocationAdapterError("cancelled", "Invocation was cancelled")

        result: list[Mapping[str, Any]] = []
        failure: list[BaseException] = []

        def execute() -> None:
            try:
                result.append(
                    self._transport.invoke(
                        request,
                        timeout_seconds=timeout,
                        cancellation=cancellation,
                    )
                )
            except BaseException as exc:  # captured and re-raised on caller thread
                failure.append(exc)

        worker = threading.Thread(target=execute, daemon=True)
        worker.start()
        deadline = time.monotonic() + timeout

        while worker.is_alive():
            if cancellation is not None and cancellation.is_cancelled():
                raise InvocationAdapterError("cancelled", "Invocation was cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise InvocationAdapterError(
                    "timeout", f"Invocation exceeded {timeout:g} seconds"
                )
            worker.join(min(_POLL_INTERVAL_SECONDS, remaining))

        if failure:
            error = failure[0]
            if isinstance(error, InvocationAdapterError):
                raise error
            raise InvocationAdapterError(
                "transport_failure",
                str(error) or type(error).__name__,
                details={"exception": type(error).__name__},
            ) from error
        if not result or not isinstance(result[0], Mapping):
            raise InvocationAdapterError(
                "invalid_transport_response",
                "Transport returned a non-object response",
            )
        return result[0]

    def _resolve_timeout(self, value: float | None) -> float:
        timeout = self._default_timeout_seconds if value is None else value
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
            raise TypeError("timeout_seconds must be numeric")
        if timeout <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        return float(timeout)

    @staticmethod
    def _validate_request(payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise InvocationAdapterError(
                "invalid_request", "Callback invocation payload must be an object"
            )
        unknown = sorted(set(payload) - _ALLOWED_REQUEST_FIELDS)
        if unknown:
            raise InvocationAdapterError(
                "invalid_request",
                f"Unsupported callback inspection fields: {unknown}",
                details={"unsupported_fields": unknown},
            )
        workspace_root = payload.get("workspace_root")
        if not isinstance(workspace_root, str) or not workspace_root.strip():
            raise InvocationAdapterError(
                "invalid_request", "'workspace_root' must be a non-empty string"
            )
        return dict(payload)
