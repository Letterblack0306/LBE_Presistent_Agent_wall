from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.runtime.external_capabilities import (
    ExternalCapabilityKind,
    ExternalCapabilityRegistration,
    register_external_capabilities,
)
from lbe_guard_inspector.runtime.governed_coding import (
    _provider_tool_definition,
    _tool_id_for_provider_name,
)
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import (
    GovernedToolOrchestrator,
    ToolAccessClass,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolNetworkBehavior,
    ToolReceiptStatus,
    ToolRegistry,
    ToolRequest,
    ToolRiskClass,
)


def _context(tmp_path: Path, *capabilities: str) -> ToolExecutionContext:
    return ToolExecutionContext(
        mode_decision=ModeDecision(
            mode="coding",
            allowed_behaviors=("development_mode_capabilities",),
            capabilities=capabilities or ("inspect", "modify"),
            rationale="test",
        ),
        workspace_id="project-1",
        workspace_root=tmp_path,
        configured_root_id="project-1",
    )


def _handler(calls: list[str], name: str):
    def execute(request: ToolRequest) -> ToolExecutionResult:
        calls.append(name)
        return ToolExecutionResult(
            output={"adapter": name, "ok": True},
            evidence=({
                "ref": f"external:{name}:{request.operation_id}",
                "source_type": "runtime",
                "verified": True,
                "metadata": {
                    "operation_id": request.operation_id,
                    "tool_id": request.tool_id,
                },
            },),
        )

    return execute


@pytest.mark.parametrize(
    ("kind", "tool_id", "network_behavior"),
    [
        (ExternalCapabilityKind.MCP, "mcp.read_resource", ToolNetworkBehavior.NONE),
        (ExternalCapabilityKind.PLUGIN, "plugin.inspect_asset", ToolNetworkBehavior.NONE),
        (ExternalCapabilityKind.SUBAGENT, "subagent.review", ToolNetworkBehavior.OPTIONAL),
        (ExternalCapabilityKind.NETWORK, "network.lookup", ToolNetworkBehavior.REQUIRED),
        (ExternalCapabilityKind.HOSTED_SERVICE, "hosted.issue_read", ToolNetworkBehavior.REQUIRED),
    ],
)
def test_all_external_capability_kinds_register_behind_tool_registry(
    kind: ExternalCapabilityKind,
    tool_id: str,
    network_behavior: ToolNetworkBehavior,
) -> None:
    calls: list[str] = []
    registration = ExternalCapabilityRegistration(
        adapter_id=f"adapter-{kind.value}",
        kind=kind,
        tool_id=tool_id,
        description="bounded external capability",
        handler=_handler(calls, kind.value),
        required_arguments=("query",),
        network_behavior=network_behavior,
    )
    registry = ToolRegistry()
    registered = register_external_capabilities(registry, (registration,))
    assert registered == (registration,)
    stored = registry.get(tool_id)
    assert stored is not None
    assert stored.spec.network_behavior is network_behavior
    assert stored.spec.capability == "inspect"
    assert calls == []


def test_network_and_hosted_service_require_explicit_network_metadata() -> None:
    for kind, tool_id in (
        (ExternalCapabilityKind.NETWORK, "network.lookup"),
        (ExternalCapabilityKind.HOSTED_SERVICE, "hosted.issue_read"),
    ):
        with pytest.raises(ValueError, match="network_behavior=REQUIRED"):
            ExternalCapabilityRegistration(
                adapter_id=f"adapter-{kind.value}",
                kind=kind,
                tool_id=tool_id,
                description="networked",
                handler=_handler([], kind.value),
            )


@pytest.mark.parametrize(
    "argument_name",
    ["endpoint", "base_url", "url", "transport", "executable", "command", "argv", "shell"],
)
def test_provider_cannot_control_external_transport(argument_name: str) -> None:
    with pytest.raises(ValueError, match="provider-controlled transport selection is forbidden"):
        ExternalCapabilityRegistration(
            adapter_id="hosted-github",
            kind=ExternalCapabilityKind.HOSTED_SERVICE,
            tool_id="hosted.issue_read",
            description="read issue",
            handler=_handler([], "hosted"),
            required_arguments=(argument_name,),
            network_behavior=ToolNetworkBehavior.REQUIRED,
        )


def test_external_write_uses_modify_authority_and_receipt(tmp_path: Path) -> None:
    calls: list[str] = []
    registration = ExternalCapabilityRegistration(
        adapter_id="plugin-write",
        kind=ExternalCapabilityKind.PLUGIN,
        tool_id="plugin.apply_change",
        description="preconfigured plugin mutation",
        handler=_handler(calls, "plugin-write"),
        required_arguments=("change_id",),
        access_class=ToolAccessClass.WRITE,
        risk_class=ToolRiskClass.HIGH,
    )
    registry = ToolRegistry()
    register_external_capabilities(registry, (registration,))
    orchestrator = GovernedToolOrchestrator(registry=registry)
    receipt = orchestrator.invoke(
        ToolRequest(
            operation_id="external-write-1",
            tool_id="plugin.apply_change",
            arguments={"change_id": "change-1"},
            context=_context(tmp_path, "modify"),
        )
    )
    assert calls == ["plugin-write"]
    assert receipt.status is ToolReceiptStatus.EXECUTED
    assert receipt.authorization is not None
    assert receipt.authorization.verdict.value == "ALLOW"
    assert receipt.operation_id == "external-write-1"
    assert receipt.tool_id == "plugin.apply_change"
    assert receipt.evidence[0]["metadata"]["operation_id"] == "external-write-1"


def test_authorization_denial_happens_before_external_adapter(tmp_path: Path) -> None:
    calls: list[str] = []
    registration = ExternalCapabilityRegistration(
        adapter_id="plugin-write",
        kind=ExternalCapabilityKind.PLUGIN,
        tool_id="plugin.apply_change",
        description="preconfigured plugin mutation",
        handler=_handler(calls, "plugin-write"),
        access_class=ToolAccessClass.WRITE,
    )
    registry = ToolRegistry()
    register_external_capabilities(registry, (registration,))
    receipt = GovernedToolOrchestrator(registry=registry).invoke(
        ToolRequest(
            operation_id="external-write-denied",
            tool_id="plugin.apply_change",
            arguments={},
            context=_context(tmp_path, "inspect"),
        )
    )
    assert calls == []
    assert receipt.status is ToolReceiptStatus.ESCALATED
    assert receipt.authorization is not None
    assert receipt.authorization.verdict.value == "ESCALATE"


def test_unregistered_external_tool_fails_closed(tmp_path: Path) -> None:
    receipt = GovernedToolOrchestrator(registry=ToolRegistry()).invoke(
        ToolRequest(
            operation_id="external-missing",
            tool_id="mcp.unregistered",
            arguments={},
            context=_context(tmp_path, "inspect"),
        )
    )
    assert receipt.status is ToolReceiptStatus.FAILED
    assert receipt.error_code == "UNREGISTERED_TOOL"
    assert receipt.authorization is None


def test_external_tool_is_projected_with_lbe_owned_provider_name() -> None:
    registration = ExternalCapabilityRegistration(
        adapter_id="mcp-memory",
        kind=ExternalCapabilityKind.MCP,
        tool_id="mcp.read_resource",
        description="read one registered MCP resource",
        handler=_handler([], "mcp"),
        required_arguments=("resource_id",),
    )
    spec = registration.tool_spec()
    definition = _provider_tool_definition(0, spec)
    provider_name = definition["function"]["name"]
    assert provider_name == "lbe_0_mcp_read_resource"
    assert provider_name != spec.tool_id
    assert _tool_id_for_provider_name(provider_name, (spec,)) == "mcp.read_resource"
    with pytest.raises(ValueError, match="unregistered tool"):
        _tool_id_for_provider_name("mcp.read_resource", (spec,))


def test_duplicate_external_adapter_and_tool_ids_are_rejected() -> None:
    first = ExternalCapabilityRegistration(
        adapter_id="same",
        kind=ExternalCapabilityKind.MCP,
        tool_id="mcp.one",
        description="one",
        handler=_handler([], "one"),
    )
    duplicate_adapter = ExternalCapabilityRegistration(
        adapter_id="same",
        kind=ExternalCapabilityKind.MCP,
        tool_id="mcp.two",
        description="two",
        handler=_handler([], "two"),
    )
    with pytest.raises(ValueError, match="duplicate external adapter_id"):
        register_external_capabilities(ToolRegistry(), (first, duplicate_adapter))

    duplicate_tool = ExternalCapabilityRegistration(
        adapter_id="other",
        kind=ExternalCapabilityKind.MCP,
        tool_id="mcp.one",
        description="duplicate tool",
        handler=_handler([], "other"),
    )
    with pytest.raises(ValueError, match="duplicate external tool_id"):
        register_external_capabilities(ToolRegistry(), (first, duplicate_tool))
