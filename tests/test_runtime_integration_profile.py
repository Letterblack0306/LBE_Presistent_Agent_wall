from __future__ import annotations

import time
from typing import Any, Mapping

import pytest

from lbe_guard_inspector.invocation_adapter import (
    CancellationToken,
    InvocationAdapterError,
    InProcessTransport,
)
from lbe_guard_inspector.runtime_integration_profile import (
    IntegrationProfileError,
    RuntimeIntegrationProfile,
)


def profile(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "profile_id": "sample.runtime",
        "version": "1.0",
        "transport_factory": "in_process",
        "transport_config": {"target": "callback"},
        "request_mapping": {
            "workspace_root": "root",
            "workspace_id": "project_id",
            "reason": "diagnostic_reason",
            "max_results": "limit",
        },
        "capabilities": {
            "callback_inspection": True,
            "workspace_mutation": False,
            "repair_execution": False,
            "arbitrary_guard_selection": False,
        },
        "timeout_seconds": 1.0,
        "cancellation_supported": True,
    }
    value.update(overrides)
    return value


def factories(target):
    def build(config: Mapping[str, Any]):
        assert config == {"target": "callback"}
        return InProcessTransport(target)

    return {"in_process": build}


def test_profile_maps_runtime_input_and_preserves_adapter_response_exactly() -> None:
    response = {
        "request": {"request_id": "req-1"},
        "authorization": {"write_allowed": False},
        "decision": {
            "guard_result": {
                "verdict": "FAIL",
                "evidence_refs": ["ev-1"],
                "validation_refs": ["val-1"],
            }
        },
        "decision_fingerprint": "sha256:fixed",
        "workspace_unchanged": True,
    }
    seen: list[Mapping[str, Any]] = []

    def target(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        seen.append(payload)
        return response

    compiled = RuntimeIntegrationProfile.from_mapping(profile()).compile(factories(target))
    result = compiled.invoke(
        {
            "root": "C:/configured/project",
            "project_id": "project-1",
            "diagnostic_reason": "callback failure",
            "limit": 7,
            "ignored_runtime_metadata": "not forwarded",
        }
    )

    assert seen == [
        {
            "workspace_root": "C:/configured/project",
            "workspace_id": "project-1",
            "reason": "callback failure",
            "max_results": 7,
        }
    ]
    assert result is response


def test_profile_uses_environment_supplied_transport_factory() -> None:
    created: list[Mapping[str, Any]] = []

    def factory(config: Mapping[str, Any]):
        created.append(config)
        return InProcessTransport(lambda payload: {"request": dict(payload)})

    compiled = RuntimeIntegrationProfile.from_mapping(profile()).compile(
        {"in_process": factory}
    )
    result = compiled.invoke({"root": "D:/workspace"})

    assert created == [{"target": "callback"}]
    assert result == {"request": {"workspace_root": "D:/workspace"}}


def test_unknown_profile_fields_fail_deterministically() -> None:
    with pytest.raises(IntegrationProfileError) as caught:
        RuntimeIntegrationProfile.from_mapping(profile(vendor="fixed-product"))
    assert caught.value.code == "invalid_profile"
    assert caught.value.details == {"unknown_fields": ["vendor"]}


def test_unknown_request_mapping_target_is_rejected() -> None:
    value = profile(
        request_mapping={"workspace_root": "root", "pack_id": "pack"}
    )
    with pytest.raises(IntegrationProfileError) as caught:
        RuntimeIntegrationProfile.from_mapping(value)
    assert caught.value.details == {"unsupported_fields": ["pack_id"]}


def test_duplicate_runtime_source_fields_are_rejected() -> None:
    value = profile(
        request_mapping={"workspace_root": "value", "workspace_id": "value"}
    )
    with pytest.raises(IntegrationProfileError, match="distinct source fields"):
        RuntimeIntegrationProfile.from_mapping(value)


@pytest.mark.parametrize(
    "capabilities, prohibited",
    [
        ({"callback_inspection": True, "workspace_mutation": True}, "workspace_mutation"),
        ({"callback_inspection": True, "repair_execution": True}, "repair_execution"),
        (
            {"callback_inspection": True, "arbitrary_guard_selection": True},
            "arbitrary_guard_selection",
        ),
    ],
)
def test_contradictory_authority_capabilities_are_rejected(
    capabilities: Mapping[str, bool], prohibited: str
) -> None:
    with pytest.raises(IntegrationProfileError) as caught:
        RuntimeIntegrationProfile.from_mapping(profile(capabilities=capabilities))
    assert caught.value.code == "contradictory_profile"
    assert prohibited in caught.value.details["prohibited_capabilities"]


def test_callback_capability_must_be_explicitly_enabled() -> None:
    with pytest.raises(IntegrationProfileError) as caught:
        RuntimeIntegrationProfile.from_mapping(profile(capabilities={}))
    assert caught.value.code == "contradictory_profile"


def test_missing_factory_is_structured() -> None:
    parsed = RuntimeIntegrationProfile.from_mapping(profile())
    with pytest.raises(IntegrationProfileError) as caught:
        parsed.compile({})
    assert caught.value.code == "transport_factory_unavailable"


def test_invalid_transport_factory_result_is_rejected() -> None:
    parsed = RuntimeIntegrationProfile.from_mapping(profile())
    with pytest.raises(IntegrationProfileError) as caught:
        parsed.compile({"in_process": lambda config: object()})
    assert caught.value.code == "invalid_transport"


def test_runtime_input_must_supply_mapped_workspace_root() -> None:
    compiled = RuntimeIntegrationProfile.from_mapping(profile()).compile(
        factories(lambda payload: payload)
    )
    with pytest.raises(IntegrationProfileError) as caught:
        compiled.invoke({"project_id": "missing-root"})
    assert caught.value.code == "invalid_runtime_input"
    assert caught.value.details == {"source_field": "root"}


def test_adapter_error_is_preserved_without_reinterpretation() -> None:
    error = InvocationAdapterError(
        "endpoint_rejected",
        "governance rejected request",
        {"status": 400, "response": {"error": "GovernanceError"}},
    )

    def target(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        raise error

    compiled = RuntimeIntegrationProfile.from_mapping(profile()).compile(factories(target))
    with pytest.raises(InvocationAdapterError) as caught:
        compiled.invoke({"root": "C:/project"})
    assert caught.value is error


def test_timeout_is_bounded_by_profile_contract() -> None:
    with pytest.raises(IntegrationProfileError, match="at most 300"):
        RuntimeIntegrationProfile.from_mapping(profile(timeout_seconds=301))

    def slow(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        time.sleep(0.05)
        return payload

    compiled = RuntimeIntegrationProfile.from_mapping(
        profile(timeout_seconds=0.01)
    ).compile(factories(slow))
    with pytest.raises(InvocationAdapterError) as caught:
        compiled.invoke({"root": "C:/project"})
    assert caught.value.code == "timeout"


def test_cancellation_support_is_explicit() -> None:
    compiled = RuntimeIntegrationProfile.from_mapping(
        profile(cancellation_supported=False)
    ).compile(factories(lambda payload: payload))
    token = CancellationToken()

    with pytest.raises(IntegrationProfileError) as caught:
        compiled.invoke({"root": "C:/project"}, cancellation=token)
    assert caught.value.code == "unsupported_capability"


def test_enabled_cancellation_flows_to_adapter() -> None:
    compiled = RuntimeIntegrationProfile.from_mapping(profile()).compile(
        factories(lambda payload: payload)
    )
    token = CancellationToken()
    token.cancel()

    with pytest.raises(InvocationAdapterError) as caught:
        compiled.invoke({"root": "C:/project"}, cancellation=token)
    assert caught.value.code == "cancelled"
