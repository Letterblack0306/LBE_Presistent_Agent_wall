from __future__ import annotations

from lbe_guard_inspector.runtime.agent_guidance import build_agent_guidance
from lbe_guard_inspector.evidence_service import EvidenceService
from lbe_guard_inspector.runtime.governed_coding import workspace_create_candidate_text_spec
from lbe_guard_inspector.runtime.mode_controller import ModeDecision
from lbe_guard_inspector.runtime.tool_orchestration import workspace_read_spec
from lbe_guard_inspector.reasoning_contracts import LBERequest
from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.professional_provider_events import ModelEventType, NormalizedModelEvent, ProviderProtocolFamily
from lbe_guard_inspector.runtime.governed_coding import GovernedProviderReasoningController
from lbe_guard_inspector.runtime.tool_orchestration import ToolReceiptStatus
from lbe_guard_inspector.session_memory_runtime import SessionMemoryRuntimeBridge


def _decision(mode: str) -> ModeDecision:
    return ModeDecision(mode=mode, allowed_behaviors=(), capabilities=(), rationale="test")


def test_coding_guidance_loads_root_project_instruction_with_safe_provenance(tmp_path) -> None:
    (tmp_path / "AGENTS.md").write_text("Use project conventions.\n", encoding="utf-8")

    guidance = build_agent_guidance(
        mode_decision=_decision("coding"),
        workspace_root=tmp_path,
        tools=(workspace_read_spec(), workspace_create_candidate_text_spec()),
    )

    assert "ACTIVE DOCTRINE: ENGINEERING" in guidance.prompt
    assert "Use project conventions." in guidance.prompt
    assert "workspace.read" in guidance.prompt
    assert "workspace.create_candidate_text" in guidance.prompt
    payload = guidance.audit_payload()
    assert payload["instruction_sources"][0]["path"] == "AGENTS.md"
    assert "Use project conventions." not in str(payload)


def test_audit_and_investigation_guidance_prohibit_automatic_mutation(tmp_path) -> None:
    audit = build_agent_guidance(mode_decision=_decision("audit"), workspace_root=tmp_path, tools=())
    investigation = build_agent_guidance(mode_decision=_decision("investigation"), workspace_root=tmp_path, tools=())

    assert "Code modification is disabled." in audit.prompt
    assert "Automatic implementation is disabled." in investigation.prompt


def test_oversized_project_instruction_is_not_sent_to_provider(tmp_path) -> None:
    (tmp_path / "AGENTS.md").write_text("x" * (32 * 1024 + 1), encoding="utf-8")

    guidance = build_agent_guidance(mode_decision=_decision("coding"), workspace_root=tmp_path, tools=())

    assert "No root AGENTS.md was loaded." in guidance.prompt
    assert guidance.instruction_sources[0]["loaded"] is False


def test_governed_provider_turn_receives_guidance_and_persists_only_metadata(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("Follow this project's naming rules.\n", encoding="utf-8")
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "state.sqlite",
        project_workspace_id="project-1",
        workspace_root=workspace,
        session_id="session-1",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id="openai-compatible",
        provider_model="model-a",
    )
    captured: list[tuple[dict[str, object], ...]] = []

    class CaptureAdapter:
        def __init__(self, *, config) -> None:
            self.config = config

        def complete(self, *, messages, provider_id, lbe_call_id_for_provider_tool_call, tools):
            captured.append(messages)
            return (
                NormalizedModelEvent(
                    ModelEventType.MESSAGE_COMPLETED,
                    provider_id,
                    "model-a",
                    ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                    text="I inspected the objective.",
                ),
                NormalizedModelEvent(
                    ModelEventType.TURN_COMPLETED,
                    provider_id,
                    "model-a",
                    ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                ),
            )

    monkeypatch.setattr("lbe_guard_inspector.runtime.governed_coding.OpenAICompatibleEventAdapter", CaptureAdapter)
    controller = GovernedProviderReasoningController(
        runtime=runtime,
        provider_id="openai-compatible",
        provider_config=ProviderConfig("https://provider.invalid/v1/chat/completions", "model-a", 5),
    )

    result = controller.run(LBERequest("Inspect the workspace", workspace, (), "task-1", 10))

    assert "ACTIVE DOCTRINE: ENGINEERING" in str(captured[0][0]["content"])
    assert "Follow this project's naming rules." in str(captured[0][0]["content"])
    persisted = result.deterministic_result["agent_guidance"]
    assert persisted["instruction_sources"][0]["path"] == "AGENTS.md"
    assert "Follow this project's naming rules." not in str(persisted)


def test_governed_provider_tool_call_round_trips_through_receipt(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("governed evidence\n", encoding="utf-8")
    runtime = SessionMemoryRuntimeBridge(
        database_path=tmp_path / "state.sqlite",
        project_workspace_id="project-1",
        workspace_root=workspace,
        session_id="session-1",
        mode="coding",
        permission="write_allowed",
        runtime_policy="permissive",
        provider_id="openai-compatible",
        provider_model="model-a",
    )

    class FakeEvidenceService(EvidenceService):
        def build_evidence_package(self, **kwargs):
            assert kwargs["rule_id"] == "workspace.read"
            return {
                "current_workspace_evidence": [
                    {
                        "ref": "workspace:project-1:README.md",
                        "verified": True,
                    }
                ],
                "missing_evidence": [],
            }

    monkeypatch.setattr(
        "lbe_guard_inspector.runtime.governed_coding.EvidenceService",
        FakeEvidenceService,
    )
    captured_messages = []

    class ToolCallingAdapter:
        def __init__(self, *, config) -> None:
            self.config = config
            self.calls = 0

        def complete(self, *, messages, provider_id, lbe_call_id_for_provider_tool_call, tools):
            captured_messages.append(messages)
            self.calls += 1
            if self.calls == 1:
                tool_name = next(
                    item["function"]["name"]
                    for item in tools
                    if item["function"]["name"].endswith("workspace_read")
                )
                provider_call_id = "provider-call-1"
                return (
                    NormalizedModelEvent(
                        ModelEventType.TOOL_CALL_STARTED,
                        provider_id,
                        "model-a",
                        ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                        provider_tool_call_id=provider_call_id,
                        lbe_call_id=lbe_call_id_for_provider_tool_call(provider_call_id),
                    ),
                    NormalizedModelEvent(
                        ModelEventType.TOOL_CALL_COMPLETED,
                        provider_id,
                        "model-a",
                        ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                        provider_tool_call_id=provider_call_id,
                        lbe_call_id=lbe_call_id_for_provider_tool_call(provider_call_id),
                        tool_name=tool_name,
                        tool_arguments={"path": "README.md"},
                    ),
                )
            tool_messages = [item for item in messages if item.get("role") == "tool"]
            assert len(tool_messages) == 1
            assert '"status": "EXECUTED"' in tool_messages[0]["content"]
            assert '"tool_id": "workspace.read"' in tool_messages[0]["content"]
            return (
                NormalizedModelEvent(
                    ModelEventType.MESSAGE_COMPLETED,
                    provider_id,
                    "model-a",
                    ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                    text="Receipt-backed result received.",
                ),
                NormalizedModelEvent(
                    ModelEventType.TURN_COMPLETED,
                    provider_id,
                    "model-a",
                    ProviderProtocolFamily.OPENAI_COMPATIBLE_CHAT,
                ),
            )

    monkeypatch.setattr(
        "lbe_guard_inspector.runtime.governed_coding.OpenAICompatibleEventAdapter",
        ToolCallingAdapter,
    )
    controller = GovernedProviderReasoningController(
        runtime=runtime,
        provider_id="openai-compatible",
        provider_config=ProviderConfig("https://provider.invalid/v1/chat/completions", "model-a", 5),
    )

    result = controller.run(LBERequest("Inspect README.md", workspace, (), "task-1", 10))

    assert result.outcome == "COMPLETED"
    receipts = result.deterministic_result["governed_tool_receipts"]
    assert len(receipts) == 1
    assert receipts[0]["tool_id"] == "workspace.read"
    assert receipts[0]["status"] == ToolReceiptStatus.EXECUTED.value
    assert len(captured_messages) == 2
