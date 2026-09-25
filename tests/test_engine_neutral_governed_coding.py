from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.reasoning_contracts import LBERequest
from lbe_guard_inspector.professional_provider_events import (
    ModelEventType,
    NormalizedModelEvent,
    ProviderProtocolFamily,
)
from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.runtime.cline_stdio_protocol import BridgeFrame, PROTOCOL_VERSION
from lbe_guard_inspector.runtime.governed_coding import build_governed_coding_controller
from lbe_guard_inspector.runtime.tool_orchestration import ToolRequest, ToolReceiptStatus
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


class _FakeEvidenceService(EvidenceService):
    def build_evidence_package(self, **kwargs):
        return {
            "current_workspace_evidence": [
                {
                    "ref": "workspace:project-1:README.md",
                    "verified": True,
                }
            ],
            "missing_evidence": [],
        }


class _FakeGovernedClineWorker:
    last_start: BridgeFrame | None = None

    def __init__(self, **_kwargs) -> None:
        self.is_running = False

    def start(self, frame: BridgeFrame) -> BridgeFrame:
        self.is_running = True
        type(self).last_start = frame
        allowed = frame.payload["allowed_tools"]
        assert any(item["tool_id"] == "workspace.read" for item in allowed)
        return BridgeFrame(
            protocol_version=PROTOCOL_VERSION,
            message_id="node-ready",
            message_type="runtime.ready",
            session_id=frame.session_id,
            turn_id=frame.turn_id,
            payload={
                "provider_configured": True,
                "allowed_tool_ids": [item["tool_id"] for item in allowed],
            },
        )

    def execute_turn(
        self,
        frame: BridgeFrame,
        *,
        orchestrator,
        context,
        timeout_seconds,
        on_provider_event=None,
        on_tool_receipt=None,
    ) -> BridgeFrame:
        assert timeout_seconds >= 60.0
        receipt = orchestrator.invoke(
            ToolRequest(
                operation_id=f"{frame.turn_id}:tool:test",
                tool_id="workspace.read",
                arguments={"path": "README.md"},
                context=context,
            )
        )
        assert receipt.status is ToolReceiptStatus.EXECUTED
        if on_tool_receipt is not None:
            on_tool_receipt(frame, receipt)
        if on_provider_event is not None:
            on_provider_event(
                BridgeFrame(
                    protocol_version=PROTOCOL_VERSION,
                    message_id="node-event",
                    message_type="provider.event",
                    session_id=frame.session_id,
                    turn_id=frame.turn_id,
                    payload={"event_type": "turn-finished"},
                )
            )
        return BridgeFrame(
            protocol_version=PROTOCOL_VERSION,
            message_id="node-complete",
            message_type="turn.completed",
            session_id=frame.session_id,
            turn_id=frame.turn_id,
            payload={
                "status": "completed",
                "output_text": "Cline received the governed receipt.",
                "lbe_completion_truth": False,
            },
        )

    def shutdown(self, frame: BridgeFrame, *, timeout_seconds: float = 5.0) -> BridgeFrame:
        self.is_running = False
        return BridgeFrame(
            protocol_version=PROTOCOL_VERSION,
            message_id="node-shutdown",
            message_type="turn.completed",
            session_id=frame.session_id,
            turn_id=frame.turn_id,
            payload={"shutdown": True},
        )

    def terminate(self) -> None:
        self.is_running = False


def test_cline_and_native_engines_share_lbe_governed_coding_owner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("governed evidence\n", encoding="utf-8")
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "state.sqlite",
        project_workspace_id="project-1",
        workspace_root=workspace,
        session_id="session-cline",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id="openrouter",
        provider_model="model-a",
        reasoning_engine="cline",
    )

    monkeypatch.setattr(
        "lbe_guard_inspector.runtime.governed_coding.EvidenceService",
        _FakeEvidenceService,
    )
    monkeypatch.setattr(
        "lbe_guard_inspector.runtime.cline_stdio_bridge.GovernedClineWorker",
        _FakeGovernedClineWorker,
    )

    controller = build_governed_coding_controller(
        runtime=runtime,
        provider_id="openrouter",
        provider_config=ProviderConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            model="model-a",
            timeout_seconds=5,
            api_key="test-key",
        ),
        engine_id="cline",
    )

    result = controller.run(
        LBERequest(
            "Inspect README.md through the governed tool loop",
            workspace,
            (),
            "task-1",
            10,
        )
    )

    assert result.outcome == "COMPLETED"
    assert result.workspace_profile["reasoning_engine"] == "cline"
    assert result.deterministic_result["reasoning_engine"] == "cline"
    assert result.deterministic_result["provider_output"] == (
        "Cline received the governed receipt."
    )
    receipts = result.deterministic_result["governed_tool_receipts"]
    assert len(receipts) == 1
    assert receipts[0]["tool_id"] == "workspace.read"
    assert receipts[0]["status"] == "EXECUTED"

    projection = result.deterministic_result["governed_tool_projection"]
    assert projection == [
        {
            "tool_id": "workspace.read",
            "capability": "inspect",
            "access_class": "read",
            "network_behavior": "none",
            "risk_class": "low",
            "authorization_verdict": "ALLOW",
            "authorization_rationale": projection[0]["authorization_rationale"],
        }
    ]
    assert projection[0]["authorization_rationale"]
    assert result.deterministic_result["direct_native_mutation_tools_exposed"] is False
    start = _FakeGovernedClineWorker.last_start
    assert start is not None
    assert start.payload["provider"]["provider_id"] == "openrouter"
    assert start.payload["system_prompt"]


def test_engine_neutral_coding_factory_rejects_unknown_engine(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "state.sqlite",
        project_workspace_id="project-1",
        workspace_root=workspace,
        session_id="session-unknown",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id="openai-compatible",
        provider_model="model-a",
        reasoning_engine="future-engine",
    )

    try:
        build_governed_coding_controller(
            runtime=runtime,
            provider_id="openai-compatible",
            provider_config=ProviderConfig(
                endpoint="http://127.0.0.1:1234/v1/chat/completions",
                model="model-a",
                timeout_seconds=5,
            ),
            engine_id="future-engine",
        )
    except ValueError as exc:
        assert "unsupported governed coding reasoning engine" in str(exc)
    else:
        raise AssertionError("unknown reasoning engine must fail explicitly")


@pytest.mark.parametrize(
    ("provider_id", "endpoint"),
    [
        ("gemini", "https://generativelanguage.googleapis.com/v1beta/interactions"),
        ("openai-compatible", "https://router.example/custom/inference"),
    ],
)
def test_native_lbe_governed_coding_fails_closed_for_unimplemented_protocols(
    tmp_path: Path,
    provider_id: str,
    endpoint: str,
) -> None:
    workspace = tmp_path / provider_id
    workspace.mkdir()
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / f"{provider_id}.sqlite",
        project_workspace_id=f"project-{provider_id}",
        workspace_root=workspace,
        session_id=f"session-{provider_id}",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id=provider_id,
        provider_model="model-a",
        reasoning_engine="native-lbe",
    )

    with pytest.raises(
        ValueError,
        match="native-lbe governed coding transport is not implemented",
    ):
        build_governed_coding_controller(
            runtime=runtime,
            provider_id=provider_id,
            provider_config=ProviderConfig(
                endpoint=endpoint,
                model="model-a",
                timeout_seconds=5,
                api_key="test-key",
            ),
            engine_id="native-lbe",
        )


@pytest.mark.parametrize(
    ("provider_id", "endpoint"),
    [
        ("anthropic", "https://api.anthropic.com/v1/messages"),
        (
            "gemini",
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent",
        ),
        ("openai", "https://api.openai.com/v1/responses"),
        ("openai-compatible", "http://127.0.0.1:1234/v1/chat/completions"),
        ("lmstudio", "http://127.0.0.1:1234/v1/chat/completions"),
        ("ollama", "http://127.0.0.1:11434/v1/chat/completions"),
        ("openrouter", "https://openrouter.ai/api/v1/chat/completions"),
    ],
)
def test_native_lbe_governed_coding_accepts_implemented_provider_transports(
    tmp_path: Path,
    provider_id: str,
    endpoint: str,
) -> None:
    workspace = tmp_path / provider_id
    workspace.mkdir()
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / f"{provider_id}.sqlite",
        project_workspace_id=f"project-{provider_id}",
        workspace_root=workspace,
        session_id=f"session-{provider_id}",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id=provider_id,
        provider_model="model-a",
        reasoning_engine="native-lbe",
    )

    controller = build_governed_coding_controller(
        runtime=runtime,
        provider_id=provider_id,
        provider_config=ProviderConfig(
            endpoint=endpoint,
            model="model-a",
            timeout_seconds=5,
            api_key="test-key" if provider_id in {"anthropic", "gemini", "openai", "openrouter"} else None,
        ),
        engine_id="native-lbe",
    )

    assert controller.engine_id == "native-lbe"



def test_native_and_cline_project_the_same_lbe_read_authority(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "shared"
    workspace.mkdir()
    (workspace / "README.md").write_text("same authority\n", encoding="utf-8")

    monkeypatch.setattr(
        "lbe_guard_inspector.runtime.governed_coding.EvidenceService",
        _FakeEvidenceService,
    )

    class _NativeAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def complete(
            self,
            *,
            messages,
            provider_id,
            lbe_call_id_for_provider_tool_call,
            tools,
            max_output_tokens=None,
        ):
            self.calls += 1
            if self.calls == 1:
                provider_call_id = "native-call-1"
                lbe_call_id = lbe_call_id_for_provider_tool_call(provider_call_id)
                tool_name = next(
                    item["function"]["name"]
                    for item in tools
                    if "workspace_read" in item["function"]["name"]
                )
                return (
                    NormalizedModelEvent(
                        ModelEventType.TOOL_CALL_COMPLETED,
                        provider_id,
                        "model-a",
                        ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                        provider_tool_call_id=provider_call_id,
                        lbe_call_id=lbe_call_id,
                        tool_name=tool_name,
                        tool_arguments={"path": "README.md"},
                    ),
                    NormalizedModelEvent(
                        ModelEventType.TURN_REQUIRES_TOOL,
                        provider_id,
                        "model-a",
                        ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                    ),
                )
            tool_messages = [item for item in messages if item.get("role") == "tool"]
            assert len(tool_messages) == 1
            assert '"status": "EXECUTED"' in tool_messages[0]["content"]
            return (
                NormalizedModelEvent(
                    ModelEventType.MESSAGE_COMPLETED,
                    provider_id,
                    "model-a",
                    ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                    text="native complete",
                ),
                NormalizedModelEvent(
                    ModelEventType.TURN_COMPLETED,
                    provider_id,
                    "model-a",
                    ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                ),
            )

    native_adapter = _NativeAdapter()
    monkeypatch.setattr(
        "lbe_guard_inspector.runtime.governed_coding.build_native_provider_event_adapter",
        lambda **_kwargs: native_adapter,
    )

    native_runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "native.sqlite",
        project_workspace_id="project-1",
        workspace_root=workspace,
        session_id="native-session",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id="openai-compatible",
        provider_model="model-a",
        reasoning_engine="native-lbe",
    )
    native = build_governed_coding_controller(
        runtime=native_runtime,
        provider_id="openai-compatible",
        provider_config=ProviderConfig(
            endpoint="http://127.0.0.1:1234/v1/chat/completions",
            model="model-a",
            timeout_seconds=5,
        ),
        engine_id="native-lbe",
    )
    native_result = native.run(
        LBERequest("Inspect README.md", workspace, (), "native-task", 10)
    )

    monkeypatch.setattr(
        "lbe_guard_inspector.runtime.cline_stdio_bridge.GovernedClineWorker",
        _FakeGovernedClineWorker,
    )
    cline_runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "cline.sqlite",
        project_workspace_id="project-1",
        workspace_root=workspace,
        session_id="cline-session",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id="openrouter",
        provider_model="model-a",
        reasoning_engine="cline",
    )
    cline = build_governed_coding_controller(
        runtime=cline_runtime,
        provider_id="openrouter",
        provider_config=ProviderConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            model="model-a",
            timeout_seconds=5,
            api_key="test-key",
        ),
        engine_id="cline",
    )
    cline_result = cline.run(
        LBERequest("Inspect README.md", workspace, (), "cline-task", 10)
    )

    native_receipt = native_result.deterministic_result["governed_tool_receipts"][0]
    cline_receipt = cline_result.deterministic_result["governed_tool_receipts"][0]
    assert native_receipt["tool_id"] == cline_receipt["tool_id"] == "workspace.read"
    assert native_receipt["status"] == cline_receipt["status"] == "EXECUTED"

    native_projection = native_result.deterministic_result["governed_tool_projection"][0]
    cline_projection = cline_result.deterministic_result["governed_tool_projection"][0]
    for key in (
        "tool_id",
        "capability",
        "access_class",
        "network_behavior",
        "risk_class",
        "authorization_verdict",
    ):
        assert native_projection[key] == cline_projection[key]

    assert native_result.workspace_profile["reasoning_engine"] == "native-lbe"
    assert cline_result.workspace_profile["reasoning_engine"] == "cline"
    assert native_result.deterministic_result["direct_native_mutation_tools_exposed"] is False
    assert cline_result.deterministic_result["direct_native_mutation_tools_exposed"] is False