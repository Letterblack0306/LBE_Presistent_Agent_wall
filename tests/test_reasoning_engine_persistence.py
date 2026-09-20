from __future__ import annotations

from pathlib import Path

import pytest

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.provider_registry import (
    CLINE_ENGINE_ID,
    NATIVE_LBE_ENGINE_ID,
    ProviderCapabilities,
    ProviderDescriptor,
    ProviderHandle,
    ProviderRegistry,
    default_provider_registry,
)
from lbe_guard_inspector.reasoning_contracts import ExplanationResult, ReasoningPlan
from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.session_lifecycle import LbeSessionService, SessionLifecycleError


class _Backend:
    def plan(self, request):
        return ReasoningPlan(
            interpreted_problem="ok",
            ambiguities=(),
            candidate_guard_ids=(),
            evidence_requests=(),
            validation_requests=(),
            explanation_focus=(),
        )

    def explain(self, request):
        return ExplanationResult(explanation="ok")


def _config(model: str = "m") -> ProviderConfig:
    return ProviderConfig(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model=model,
        timeout_seconds=30,
    )


def test_reasoning_engine_persists_with_session_state(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    state = SessionState(
        session_id="s",
        project_workspace_id="w",
        canonical_workspace_root=tmp_path,
        mode="coding",
        provider_id="lmstudio",
        provider_model="m",
        reasoning_engine=NATIVE_LBE_ENGINE_ID,
    )
    store.save_session_state(state)

    reopened = WorkspaceMemoryStore(tmp_path / "state.sqlite3").load_session_state(
        session_id="s"
    )

    assert reopened is not None
    assert reopened.reasoning_engine == NATIVE_LBE_ENGINE_ID
    assert reopened.as_dict()["reasoning_engine"] == NATIVE_LBE_ENGINE_ID


@pytest.mark.parametrize("provider_id", ["lmstudio", "ollama", "openrouter"])
def test_openai_compatible_routes_are_native_without_cline_by_default(provider_id) -> None:
    registry = default_provider_registry()

    assert registry.default_engine_for_provider(provider_id) == NATIVE_LBE_ENGINE_ID
    assert registry.engines_for_provider(provider_id) == (
        CLINE_ENGINE_ID,
        NATIVE_LBE_ENGINE_ID,
    )
    handle = registry.build(provider_id=provider_id, config=_config())
    assert handle.engine_id == NATIVE_LBE_ENGINE_ID


def test_session_provider_selection_persists_explicit_engine(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    state = SessionState("s", "w", tmp_path, "audit")
    store.save_session_state(state)
    registry = ProviderRegistry()

    def factory(config: ProviderConfig) -> ProviderHandle:
        return ProviderHandle(
            descriptor=ProviderDescriptor(
                provider_id="fake",
                model_id=config.model,
                capabilities=ProviderCapabilities(),
            ),
            backend=_Backend(),
            engine_id="engine-a",
        )

    registry.register_binding(
        engine_id="engine-a",
        provider_id="fake",
        factory=factory,
        default=True,
    )
    service = LbeSessionService(
        history=SessionOperationalHistory(store=store),
        provider_registry=registry,
    )

    updated = service.configure_provider(
        state=state,
        provider_id="fake",
        model_id="m",
        engine_id="engine-a",
    )

    assert updated.provider_id == "fake"
    assert updated.provider_model == "m"
    assert updated.reasoning_engine == "engine-a"
    reopened = store.load_session_state(session_id="s")
    assert reopened is not None
    assert reopened.reasoning_engine == "engine-a"


def test_session_provider_selection_rejects_unregistered_engine(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    state = SessionState("s", "w", tmp_path, "audit")
    store.save_session_state(state)
    registry = ProviderRegistry()

    registry.register_binding(
        engine_id="engine-a",
        provider_id="fake",
        factory=lambda config: ProviderHandle(
            descriptor=ProviderDescriptor(
                provider_id="fake",
                model_id=config.model,
                capabilities=ProviderCapabilities(),
            ),
            backend=_Backend(),
            engine_id="engine-a",
        ),
        default=True,
    )
    service = LbeSessionService(
        history=SessionOperationalHistory(store=store),
        provider_registry=registry,
    )

    with pytest.raises(SessionLifecycleError, match="not registered"):
        service.configure_provider(
            state=state,
            provider_id="fake",
            model_id="m",
            engine_id="engine-b",
        )
