import asyncio
from pathlib import Path

from textual.widgets import Input, Static

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory
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
    return build_textual_tui(
        history=history,
        session_id="s",
        control=PersistentTurnControl(history=history),
    ), history


def test_composer_exposes_prefix_grammar_and_palette(tmp_path: Path) -> None:
    app, history = _app(tmp_path)

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            hint = app.query_one("#composer_hint", Static)
            composer = app.query_one("#composer", Input)
            assert "/ commands" in str(hint.render())
            assert "@ context" in str(hint.render())
            assert "# skills" in str(hint.render())
            assert "+ attach" in str(hint.render())

            composer.value = "/"
            await pilot.pause()
            assert "settings" in str(hint.render()) and "mcp" in str(hint.render()) and "skills" in str(hint.render())

            composer.value = "@"
            await pilot.pause()
            assert "runtime resolution must be owned" in str(hint.render())

            composer.value = "#"
            await pilot.pause()
            assert "/skills" in str(hint.render())

            composer.value = "+"
            await pilot.pause()
            assert "/attach" in str(hint.render())

            await pilot.press("ctrl+k")
            palette = str(app.query_one("#details", Static).render())
            assert palette.startswith("COMMAND PALETTE")
            assert "/settings" in palette and "/mcp" in palette and "/skills" in palette and "/attach" in palette

    asyncio.run(exercise())
    assert history.events_for_session(session_id="s") == ()


def test_settings_mcp_skills_and_attachment_commands_are_truthful(tmp_path: Path) -> None:
    app, history = _app(tmp_path)

    async def submit(pilot, command: str) -> str:
        composer = app.query_one("#composer", Input)
        composer.value = command
        await pilot.press("enter")
        await pilot.pause()
        return str(app.query_one("#details", Static).render())

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            settings = await submit(pilot, "/settings")
            assert settings.startswith("SETTINGS")
            assert "mode=coding permission=read_only runtime_policy=development" in settings
            assert "view is read-only" in settings

            mcp = await submit(pilot, "/mcp")
            skills = await submit(pilot, "/skills")
            attachments = await submit(pilot, "/attach")
            mentions = await submit(pilot, "/mentions")

            assert mcp == "MCP\nunavailable: no runtime MCP registry owner is configured"
            assert skills == "SKILLS\nunavailable: no runtime skill registry owner is configured"
            assert "TUI will not read files directly" in attachments
            assert "no generic mention resolver owner is configured" in mentions

    asyncio.run(exercise())
    assert history.events_for_session(session_id="s") == ()
