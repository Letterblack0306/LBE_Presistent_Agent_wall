import asyncio
from pathlib import Path

from textual.widgets import Input, Static

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import OperationalEvent, SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.persistent_turn_control import PersistentTurnControl
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
            assert "OBJECTIVE" in str(app.query_one("#activity", Static).render())
            assert "ACTIVE" in str(app.query_one("#status", Static).render())
            await pilot.press("ctrl+i", "ctrl+x")

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

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)):
            activity = str(app.query_one("#activity", Static).render())
            assert "RUNTIME ERROR" in activity
            assert "unavailable" in activity
            assert "VALIDATED RESULT" in activity
            assert "COMPLETED" in activity

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

            await submit(pilot, "/session s")
            assert "session:s" in str(app.query_one("#header", Static).render())

    asyncio.run(exercise())


def test_no_color_build_keeps_ascii_text_contract(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    app, _ = _app(tmp_path)

    async def exercise() -> None:
        async with app.run_test(size=(80, 24)):
            header = str(app.query_one("#header", Static).render())
            status = str(app.query_one("#status", Static).render())
            assert header.startswith("LBE")
            assert "/status" in status and "/cancel" in status and "/sessions" in status
            assert "[|]" not in header

    asyncio.run(exercise())
