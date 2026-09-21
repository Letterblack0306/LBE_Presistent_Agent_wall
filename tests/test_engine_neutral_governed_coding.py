from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.reasoning_contracts import LBERequest
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
        ("anthropic", "https://api.anthropic.com/v1/messages"),
        (
            "gemini",
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent",
        ),
        ("openai", "https://api.openai.com/v1/responses"),
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
        ("openai-compatible", "http://127.0.0.1:1234/v1/chat/completions"),
        ("lmstudio", "http://127.0.0.1:1234/v1/chat/completions"),
        ("ollama", "http://127.0.0.1:11434/v1/chat/completions"),
        ("openrouter", "https://openrouter.ai/api/v1/chat/completions"),
    ],
)
def test_native_lbe_governed_coding_accepts_proven_chat_completions_transport(
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
            api_key="test-key" if provider_id == "openrouter" else None,
        ),
        engine_id="native-lbe",
    )

    assert controller.engine_id == "native-lbe"
