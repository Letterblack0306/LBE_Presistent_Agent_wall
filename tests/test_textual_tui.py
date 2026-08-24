import asyncio
from pathlib import Path

from textual.widgets import Input, Static

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import OperationalEvent, SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.persistent_turn_control import PersistentTurnControl
from lbe_guard_inspector.provider_health import ProviderHealthResult
from lbe_guard_inspector.provider_registry import ProviderCapabilities, ProviderRegistry
from lbe_guard_inspector.reasoning_provider import ProviderConfig
from lbe_guard_inspector.runtime.tool_orchestration import ToolRegistry, workspace_read_spec
from lbe_guard_inspector.textual_tui import build_textual_tui


def _app(tmp_path: Path):
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    store.save_session_state(SessionState(
        "s", "w", tmp_path, "coding", "read_only", "development",
        "openai-compatible", "m",
    ))
    history = SessionOperationalHistory(store=store)
    app = build_textual_tui(
        history=history,
        session_id="s",
        control=PersistentTurnControl(history=history),
    )
    return app, history


def test_stable_workspace_regions_focus_and_progressive_details(tmp_path: Path) -> None:
    app, history = _app(tmp_path)

    async def exercise() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            for selector in (
                "#workspace", "#header", "#objective", "#columns",
                "#activity", "#composer", "#status", "#details",
            ):
                assert app.query_one(selector) is not None
            assert app.size.width == 80
            assert app.size.height == 24
            assert app.focused is app.query_one("#composer", Input)
            assert app.title == "LBE | w | coding | session:s | IDLE"
            assert "No objective submitted" in str(app.query_one("#objective", Static).render())
            details = app.query_one("#details", Static)
            assert details.display is False
            await pilot.press("ctrl+p")
            assert details.display is True
            assert str(details.render()).startswith("HELP")
            await pilot.press("ctrl+p")
            assert details.display is False

    asyncio.run(exercise())
    assert history.events_for_session(session_id="s") == ()


def test_composer_refreshes_objective_activity_and_control_state(tmp_path: Path) -> None:
    app, history = _app(tmp_path)

    async def exercise() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("b", "e", "g", "i", "n", "enter")
            assert "> begin" in str(app.query_one("#objective", Static).render())
            assert "objective" in str(app.query_one("#activity", Static).render())
            assert "ACTIVE" in str(app.query_one("#status", Static).render())
            assert app.title == "LBE | w | coding | session:s | ACTIVE"
            await pilot.press("ctrl+i", "ctrl+x")
            assert app.title == "LBE | w | coding | session:s | IDLE"

    asyncio.run(exercise())
    assert [event.event_type for event in history.events_for_session(session_id="s")] == [
        "user.message", "turn.interrupt.requested", "turn.cancelled",
    ]


def test_existing_persisted_failure_and_completion_render_truthfully(tmp_path: Path) -> None:
    app, history = _app(tmp_path)
    turn = history.start_turn(session_id="s")
    history.append_event(OperationalEvent(
        session_id="s", turn_id=turn.turn_id, event_type="model.error",
        payload={"error_code": "PROVIDER_FAILED", "error_message": "unavailable"},
    ))
    history.append_event(OperationalEvent(
        session_id="s", turn_id=turn.turn_id, event_type="model.turn.completed",
        payload={"task_id": "task-1", "outcome": "COMPLETED"},
    ))
    events = history.events_for_session(session_id="s")
    failure_sequence = events[-2].session_sequence
    completion_sequence = events[-1].session_sequence

    async def submit_detail(pilot, sequence: int) -> str:
        composer = app.query_one("#composer", Input)
        composer.value = f"/detail {sequence}"
        await pilot.press("enter")
        await pilot.pause()
        return str(app.query_one("#details", Static).render())

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            activity = str(app.query_one("#activity", Static).render())
            assert "failure" in activity
            assert "Runtime error" in activity
            assert "failed" in activity
            assert "completion" in activity
            assert "Validated result" in activity
            assert "completed" in activity

            failure_detail = await submit_detail(pilot, failure_sequence)
            assert f"DETAIL event={failure_sequence} type=model.error" in failure_detail
            assert "text=unavailable" in failure_detail

            completion_detail = await submit_detail(pilot, completion_sequence)
            assert f"DETAIL event={completion_sequence} type=model.turn.completed" in completion_detail
            assert "validation=completed task=task-1 outcome=COMPLETED" in completion_detail

    asyncio.run(exercise())


def test_six_commands_route_to_distinct_truthful_behavior(tmp_path: Path) -> None:
    app, history = _app(tmp_path)

    async def submit(pilot, command: str) -> str:
        composer = app.query_one("#composer", Input)
        composer.value = command
        await pilot.press("enter")
        await pilot.pause()
        return str(app.query_one("#details", Static).render())

    async def exercise() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            status = await submit(pilot, "/status")
            provider = await submit(pilot, "/provider")
            evidence = await submit(pilot, "/evidence")
            help_text = await submit(pilot, "/help")
            assert status.startswith("STATUS")
            assert provider.startswith("PROVIDER")
            assert evidence.startswith("EVIDENCE")
            assert help_text.startswith("HELP")
            assert len({status, provider, evidence, help_text}) == 4

            composer = app.query_one("#composer", Input)
            composer.value = "begin"
            await pilot.press("enter")
            composer.value = "/interrupt"
            await pilot.press("enter")
            composer.value = "/cancel"
            await pilot.press("enter")

    asyncio.run(exercise())
    assert [event.event_type for event in history.events_for_session(session_id="s")] == [
        "user.message", "turn.interrupt.requested", "turn.cancelled",
    ]


def test_unknown_command_does_not_create_runtime_event(tmp_path: Path) -> None:
    app, history = _app(tmp_path)

    async def exercise() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            composer = app.query_one("#composer", Input)
            composer.value = "/unknown"
            await pilot.press("enter")
            assert composer.value == ""

    asyncio.run(exercise())
    assert history.events_for_session(session_id="s") == ()


def test_session_list_create_resume_and_active_turn_boundary(tmp_path: Path) -> None:
    app, history = _app(tmp_path)
    history.store.save_session_state(SessionState(
        "s2", "w", tmp_path, "audit", "read_only", "audit",
        "openai-compatible", "m2",
    ))

    async def submit(pilot, text: str) -> None:
        composer = app.query_one("#composer", Input)
        composer.value = text
        await pilot.press("enter")
        await pilot.pause()

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            await submit(pilot, "/sessions")
            sessions = str(app.query_one("#details", Static).render())
            assert sessions.startswith("SESSIONS")
            assert "* s " in sessions
            assert "s2" in sessions

            await submit(pilot, "/session s2")
            assert "session:s2" in str(app.query_one("#header", Static).render())
            assert app.title == "LBE | w | audit | session:s2 | IDLE"
            assert history.events_for_session(session_id="s2") == ()

            await submit(pilot, "active objective")
            await submit(pilot, "/new blocked")
            assert history.store.load_session_state(session_id="blocked") is None

            await submit(pilot, "/cancel")
            await submit(pilot, "/new s3")
            created = history.store.load_session_state(session_id="s3")
            assert created is not None
            assert created.project_workspace_id == "w"
            assert created.mode == "audit"
            assert "session:s3" in str(app.query_one("#header", Static).render())
            assert app.title == "LBE | w | audit | session:s3 | IDLE"

            await submit(pilot, "/session s")
            assert "session:s" in str(app.query_one("#header", Static).render())
            assert app.title == "LBE | w | coding | session:s | IDLE"

    asyncio.run(exercise())


def test_no_color_build_keeps_ascii_text_contract(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    app, _ = _app(tmp_path)

    async def exercise() -> None:
        async with app.run_test(size=(80, 24)):
            header = str(app.query_one("#header", Static).render())
            status = str(app.query_one("#status", Static).render())
            assert header.startswith("LBE")
            assert "IDLE" in status and "/help" in status and "session:s" in status
            assert "Ctrl+I interrupt" in status and "Ctrl+X cancel" in status
            assert "[|]" not in header

    asyncio.run(exercise())


def test_wide_statusline_exposes_primary_controls(tmp_path: Path) -> None:
    app, history = _app(tmp_path)

    async def exercise() -> None:
        async with app.run_test(size=(140, 30)):
            status = str(app.query_one("#status", Static).render())
            assert status.startswith("IDLE  coding  openai-compatible/m  session:s")
            for command in (
                "/status", "/provider", "/evidence", "/tools",
                "/sessions", "/help", "/interrupt", "/cancel",
            ):
                assert command in status

    asyncio.run(exercise())
    assert history.events_for_session(session_id="s") == ()


def test_provider_selection_and_health_delegate_without_exposing_config(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    store.save_session_state(SessionState(
        "provider-session", "w", tmp_path, "coding", "read_only", "development",
        "openai-compatible", "old-model",
    ))
    history = SessionOperationalHistory(store=store)
    registry = ProviderRegistry({"test-provider": lambda config: None})
    config = ProviderConfig(
        endpoint="http://provider.invalid/v1",
        model="new-model",
        timeout_seconds=5,
        api_key="top-secret-provider-key",
    )
    calls = []

    def health_checker(**kwargs):
        calls.append(kwargs)
        return ProviderHealthResult(
            provider_id=kwargs["provider_id"],
            model_id=kwargs["provider_config"].model,
            status="READY",
            capabilities=ProviderCapabilities(structured_output=True),
        )

    app = build_textual_tui(
        history=history,
        session_id="provider-session",
        control=PersistentTurnControl(history=history),
        provider_config=config,
        provider_registry=registry,
        provider_health_checker=health_checker,
    )

    async def submit(pilot, text: str) -> str:
        composer = app.query_one("#composer", Input)
        composer.value = text
        await pilot.press("enter")
        await pilot.pause()
        return str(app.query_one("#details", Static).render())

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            selected = await submit(pilot, "/provider use test-provider new-model")
            assert "id=test-provider model=new-model" in selected
            persisted = history.store.load_session_state(session_id="provider-session")
            assert persisted is not None
            assert persisted.provider_id == "test-provider"
            assert persisted.provider_model == "new-model"

            checked = await submit(pilot, "/provider check")
            assert "health=READY" in checked
            assert "top-secret-provider-key" not in checked
            assert "provider.invalid" not in checked

    asyncio.run(exercise())
    assert len(calls) == 1
    assert calls[0]["provider_id"] == "test-provider"
    assert calls[0]["provider_config"] is config
    assert calls[0]["provider_registry"] is registry
    assert history.events_for_session(session_id="provider-session") == ()


def test_provider_health_without_explicit_config_is_truthful_and_non_mutating(tmp_path: Path) -> None:
    app, history = _app(tmp_path)
    before = history.store.load_session_state(session_id="s")

    async def exercise() -> None:
        async with app.run_test(size=(80, 24)) as pilot:
            composer = app.query_one("#composer", Input)
            composer.value = "/provider check"
            await pilot.press("enter")
            await pilot.pause()
            details = str(app.query_one("#details", Static).render())
            assert "health=unavailable (no explicit provider config)" in details

    asyncio.run(exercise())
    assert history.store.load_session_state(session_id="s") == before
    assert history.events_for_session(session_id="s") == ()


def test_detail_command_discloses_selected_persisted_event(tmp_path: Path) -> None:
    app, history = _app(tmp_path)
    turn = history.start_turn(session_id="s")
    history.append_event(OperationalEvent(
        session_id="s",
        turn_id=turn.turn_id,
        event_type="tool.denied",
        payload={
            "tool_id": "workspace.write",
            "authorization": {"verdict": "DENY", "rationale": "read-only session"},
            "error_code": "POLICY_DENIED",
        },
        runtime_operation_id="operation-denied",
    ))
    sequence = history.events_for_session(session_id="s")[-1].session_sequence

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            composer = app.query_one("#composer", Input)
            composer.value = f"/detail {sequence}"
            await pilot.press("enter")
            await pilot.pause()
            detail = str(app.query_one("#details", Static).render())
            assert f"DETAIL event={sequence} type=tool.denied" in detail
            assert "authorization=DENY rationale=read-only session" in detail
            assert "error=POLICY_DENIED" in detail

    asyncio.run(exercise())


def test_capability_inspection_uses_registered_governed_tool_specs(tmp_path: Path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    store.save_session_state(SessionState(
        "cap-session", "w", tmp_path, "coding", "read_only", "development",
        "openai-compatible", "m",
    ))
    history = SessionOperationalHistory(store=store)
    tool_registry = ToolRegistry()
    tool_registry.register(workspace_read_spec(), lambda request: None)
    app = build_textual_tui(
        history=history,
        session_id="cap-session",
        control=PersistentTurnControl(history=history),
        tool_registry=tool_registry,
    )

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            composer = app.query_one("#composer", Input)
            composer.value = "/tools"
            await pilot.press("enter")
            await pilot.pause()
            details = str(app.query_one("#details", Static).render())
            assert details.startswith("CAPABILITIES")
            assert "workspace.read capability=inspect" in details
            assert "access=read" in details
            assert "network=none" in details
            assert "risk=low" in details
            assert "state=available" in details

    asyncio.run(exercise())
    assert history.events_for_session(session_id="cap-session") == ()


def test_capability_and_integration_unavailable_states_are_truthful(tmp_path: Path) -> None:
    app, history = _app(tmp_path)

    async def submit(pilot, text: str) -> str:
        composer = app.query_one("#composer", Input)
        composer.value = text
        await pilot.press("enter")
        await pilot.pause()
        return str(app.query_one("#details", Static).render())

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            tools = await submit(pilot, "/tools")
            integrations = await submit(pilot, "/integrations")
            assert tools == "CAPABILITIES\nunavailable: no governed tool registry configured"
            assert integrations == (
                "INTEGRATIONS\n"
                "unavailable: no runtime integration registry owner is configured"
            )

    asyncio.run(exercise())
    assert history.events_for_session(session_id="s") == ()