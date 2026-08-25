from __future__ import annotations

import json
from pathlib import Path

import pytest

from lbe_guard_inspector.runtime.external_capabilities import ExternalCapabilityKind
from lbe_guard_inspector.runtime.installed_capability_registry import (
    InstalledCapabilityRecord,
    InstalledCapabilityRegistry,
    InstalledCapabilityRegistryStore,
)
from lbe_guard_inspector.runtime.tool_orchestration import (
    ToolAccessClass,
    ToolExecutionResult,
    ToolNetworkBehavior,
    ToolRequest,
    ToolRiskClass,
)


def _record(
    *,
    integration_id: str = "mcp-files",
    adapter_id: str = "mcp.files.local",
    kind: ExternalCapabilityKind = ExternalCapabilityKind.MCP,
    tool_id: str = "mcp.files.read",
    network_behavior: ToolNetworkBehavior = ToolNetworkBehavior.NONE,
    access_class: ToolAccessClass = ToolAccessClass.READ,
    credential_ref: str | None = None,
) -> InstalledCapabilityRecord:
    return InstalledCapabilityRecord(
        integration_id=integration_id,
        adapter_id=adapter_id,
        kind=kind,
        tool_id=tool_id,
        description=f"{kind.value} test capability",
        enabled=True,
        credential_ref=credential_ref,
        required_arguments=("query",),
        access_class=access_class,
        network_behavior=network_behavior,
        risk_class=ToolRiskClass.MEDIUM,
    )


def test_missing_registry_loads_empty(tmp_path: Path) -> None:
    store = InstalledCapabilityRegistryStore(tmp_path / "capabilities.json")
    registry = store.load()
    assert registry.schema_version == 1
    assert registry.records == ()


def test_registry_round_trip_persists_metadata_and_opaque_credential_ref(tmp_path: Path) -> None:
    path = tmp_path / "capabilities.json"
    store = InstalledCapabilityRegistryStore(path)
    original = InstalledCapabilityRegistry(records=(_record(credential_ref="wincred://lbe/github-primary"),))
    store.save(original)
    text = path.read_text(encoding="utf-8")
    assert "wincred://lbe/github-primary" in text
    assert "credential_ref_configured" not in text
    loaded = store.load()
    assert loaded == original
    assert loaded.records[0].public_payload()["credential_ref_configured"] is True


def test_all_five_external_kinds_are_valid_registry_records() -> None:
    records = (
        _record(),
        _record(integration_id="plugin-x", adapter_id="plugin.x", kind=ExternalCapabilityKind.PLUGIN, tool_id="plugin.x.inspect"),
        _record(integration_id="subagent-x", adapter_id="subagent.x", kind=ExternalCapabilityKind.SUBAGENT, tool_id="subagent.x.run"),
        _record(integration_id="network-x", adapter_id="network.x", kind=ExternalCapabilityKind.NETWORK, tool_id="network.x.query", network_behavior=ToolNetworkBehavior.REQUIRED),
        _record(integration_id="hosted-x", adapter_id="hosted.x", kind=ExternalCapabilityKind.HOSTED_SERVICE, tool_id="hosted.x.query", network_behavior=ToolNetworkBehavior.REQUIRED),
    )
    registry = InstalledCapabilityRegistry(records=records)
    assert {item.kind for item in registry.records} == set(ExternalCapabilityKind)


def test_duplicate_integration_adapter_or_tool_identity_is_denied() -> None:
    first = _record()
    with pytest.raises(ValueError, match="duplicate installed capability integration_id"):
        InstalledCapabilityRegistry(records=(first, _record(adapter_id="mcp.other", tool_id="mcp.other.read")))
    with pytest.raises(ValueError, match="duplicate installed capability adapter_id"):
        InstalledCapabilityRegistry(records=(first, _record(integration_id="other", tool_id="mcp.other.read")))
    with pytest.raises(ValueError, match="duplicate installed capability tool_id"):
        InstalledCapabilityRegistry(records=(first, _record(integration_id="other", adapter_id="mcp.other")))


def test_network_and_hosted_records_require_required_network_behavior() -> None:
    with pytest.raises(ValueError, match="network requires network_behavior=required"):
        _record(kind=ExternalCapabilityKind.NETWORK, integration_id="n", adapter_id="network.n", tool_id="network.n.read")
    with pytest.raises(ValueError, match="hosted_service requires network_behavior=required"):
        _record(kind=ExternalCapabilityKind.HOSTED_SERVICE, integration_id="h", adapter_id="hosted.h", tool_id="hosted.h.read")


def test_provider_transport_arguments_are_denied() -> None:
    with pytest.raises(ValueError, match="provider-controlled transport arguments"):
        InstalledCapabilityRecord(
            integration_id="bad",
            adapter_id="mcp.bad",
            kind=ExternalCapabilityKind.MCP,
            tool_id="mcp.bad.read",
            description="bad",
            required_arguments=("endpoint",),
        )


@pytest.mark.parametrize("secret_field", ["api_key", "token", "secret", "password", "client_secret", "credentials"])
def test_plaintext_secret_fields_are_rejected(tmp_path: Path, secret_field: str) -> None:
    path = tmp_path / "capabilities.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "integrations": [
                    {
                        "integration_id": "bad",
                        "adapter_id": "mcp.bad",
                        "kind": "mcp",
                        "tool_id": "mcp.bad.read",
                        "description": "bad",
                        secret_field: "plaintext-secret",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="plaintext credential field is forbidden"):
        InstalledCapabilityRegistryStore(path).load()


def test_unknown_registry_fields_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "capabilities.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "integrations": [
                    {
                        "integration_id": "x",
                        "adapter_id": "mcp.x",
                        "kind": "mcp",
                        "tool_id": "mcp.x.read",
                        "description": "x",
                        "surprise": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported installed capability fields"):
        InstalledCapabilityRegistryStore(path).load()


def test_unavailable_and_disabled_integrations_are_projected_without_execution() -> None:
    called: list[str] = []

    def factory(record: InstalledCapabilityRecord):
        called.append(record.integration_id)
        def handler(request: ToolRequest) -> ToolExecutionResult:
            return ToolExecutionResult(output={"ok": True})
        return handler

    disabled = InstalledCapabilityRecord(
        integration_id="disabled",
        adapter_id="mcp.disabled",
        kind=ExternalCapabilityKind.MCP,
        tool_id="mcp.disabled.read",
        description="disabled",
        enabled=False,
    )
    unavailable = _record()
    registry = InstalledCapabilityRegistry(records=(disabled, unavailable))
    statuses = registry.statuses({"mcp.disabled": factory})
    assert [(item.record.integration_id, item.availability) for item in statuses] == [
        ("disabled", "DISABLED"),
        ("mcp-files", "UNAVAILABLE"),
    ]
    assert called == []
    assert registry.materialize({"mcp.disabled": factory}) == ()
    assert called == []


def test_available_record_materializes_to_external_registration_without_exposing_transport() -> None:
    calls: list[str] = []

    def factory(record: InstalledCapabilityRecord):
        calls.append(record.adapter_id)
        def handler(request: ToolRequest) -> ToolExecutionResult:
            return ToolExecutionResult(output={"query": request.arguments["query"]})
        return handler

    record = _record(credential_ref="hostcred://mcp-files")
    registry = InstalledCapabilityRegistry(records=(record,))
    registrations = registry.materialize({record.adapter_id: factory})
    assert calls == [record.adapter_id]
    assert len(registrations) == 1
    registration = registrations[0]
    assert registration.adapter_id == record.adapter_id
    assert registration.kind is ExternalCapabilityKind.MCP
    assert registration.tool_id == record.tool_id
    assert registration.required_arguments == ("query",)
    assert "endpoint" not in registration.required_arguments
    assert "credential_ref" not in registration.required_arguments
    assert registration.handler is not None


def test_write_record_materializes_with_modify_authority() -> None:
    record = _record(access_class=ToolAccessClass.WRITE)
    registry = InstalledCapabilityRegistry(records=(record,))
    registration = registry.materialize({record.adapter_id: lambda _record: (lambda _request: ToolExecutionResult(output={}))})[0]
    assert registration.access_class is ToolAccessClass.WRITE
    assert registration.capability == "modify"
