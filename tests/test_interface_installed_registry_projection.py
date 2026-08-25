import asyncio
import json
import os
from pathlib import Path

from textual.widgets import Input, Static

from lbe_guard_inspector import product_entry
from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import SessionOperationalHistory
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore
from lbe_guard_inspector.persistent_turn_control import PersistentTurnControl
from lbe_guard_inspector.runtime.external_capabilities import ExternalCapabilityKind
from lbe_guard_inspector.runtime.installed_capability_registry import (
    InstalledCapabilityRecord,
    InstalledCapabilityRegistry,
    InstalledCapabilityRegistryStore,
)
from lbe_guard_inspector.textual_tui import build_textual_tui


def _history(tmp_path: Path) -> SessionOperationalHistory:
    store = WorkspaceMemoryStore(tmp_path / "state.sqlite3")
    store.save_session_state(SessionState(
        "s", "w", tmp_path, "coding", "read_only", "development",
        "openai-compatible", "m",
    ))
    return SessionOperationalHistory(store=store)


def _registry() -> InstalledCapabilityRegistry:
    return InstalledCapabilityRegistry(records=(
        InstalledCapabilityRecord(
            integration_id="mcp.files",
            adapter_id="mcp-files-adapter",
            kind=ExternalCapabilityKind.MCP,
            tool_id="mcp.files.read",
            description="Configured MCP file capability",
            credential_ref="credential://mcp-files",
        ),
        InstalledCapabilityRecord(
            integration_id="plugin.notes",
            adapter_id="notes-adapter",
            kind=ExternalCapabilityKind.PLUGIN,
            tool_id="plugin.notes.search",
            description="Configured notes plugin",
        ),
        InstalledCapabilityRecord(
            integration_id="plugin.disabled",
            adapter_id="disabled-adapter",
            kind=ExternalCapabilityKind.PLUGIN,
            tool_id="plugin.disabled.read",
            description="Disabled plugin",
            enabled=False,
        ),
    ))


def test_tui_projects_integrations_and_filters_mcp_without_execution(tmp_path: Path) -> None:
    history = _history(tmp_path)
    app = build_textual_tui(
        history=history,
        session_id="s",
        control=PersistentTurnControl(history=history),
        installed_capability_registry=_registry(),
    )

    async def submit(pilot, command: str) -> str:
        composer = app.query_one("#composer", Input)
        composer.value = command
        await pilot.press("enter")
        await pilot.pause()
        return str(app.query_one("#details", Static).render())

    async def exercise() -> None:
        async with app.run_test(size=(120, 34)) as pilot:
            integrations = await submit(pilot, "/integrations")
            assert integrations.startswith("INTEGRATIONS")
            assert "mcp.files kind=mcp tool=mcp.files.read state=configured" in integrations
            assert "plugin.notes kind=plugin tool=plugin.notes.search state=configured" in integrations
            assert "plugin.disabled kind=plugin tool=plugin.disabled.read state=disabled" in integrations
            assert "credential://mcp-files" not in integrations
            assert "credential_ref=configured" in integrations
            assert "projection_only=true execution_attempted=false" in integrations

            mcp = await submit(pilot, "/mcp")
            assert mcp.startswith("MCP")
            assert "mcp.files kind=mcp tool=mcp.files.read state=configured" in mcp
            assert "plugin.notes" not in mcp
            assert "plugin.disabled" not in mcp
            assert "projection_only=true execution_attempted=false" in mcp

    asyncio.run(exercise())
    assert history.events_for_session(session_id="s") == ()


def test_tui_empty_installed_registry_is_truthful_and_nonexecuting(tmp_path: Path) -> None:
    history = _history(tmp_path)
    app = build_textual_tui(
        history=history,
        session_id="s",
        control=PersistentTurnControl(history=history),
        installed_capability_registry=InstalledCapabilityRegistry(records=()),
    )

    async def exercise() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            composer = app.query_one("#composer", Input)
            composer.value = "/integrations"
            await pilot.press("enter")
            await pilot.pause()
            integrations = str(app.query_one("#details", Static).render())
            assert integrations == "INTEGRATIONS\nempty: no installed integrations configured\nprojection_only=true execution_attempted=false"

            composer.value = "/mcp"
            await pilot.press("enter")
            await pilot.pause()
            mcp = str(app.query_one("#details", Static).render())
            assert mcp == "MCP\nempty: no MCP integrations configured\nprojection_only=true execution_attempted=false"

    asyncio.run(exercise())
    assert history.events_for_session(session_id="s") == ()


def test_start_scopes_capability_registry_handoff_and_restores_environment(tmp_path: Path, monkeypatch, capsys) -> None:
    registry_path = tmp_path / "capabilities.json"
    InstalledCapabilityRegistryStore(registry_path).save(_registry())
    seen = {}

    def fake_tui(args):
        seen["registry_env"] = os.environ.get("LBE_CAPABILITY_REGISTRY")
        seen["argument"] = args.capability_registry
        return {"action": "tui", "session_id": "s"}

    monkeypatch.setattr(product_entry._cli, "_tui", fake_tui)
    monkeypatch.setattr(product_entry._cli, "_validate_provider_selection", lambda *args, **kwargs: None)
    monkeypatch.setenv("LBE_CAPABILITY_REGISTRY", "previous-registry-value")

    rc = product_entry.main([
        "start",
        "--database", str(tmp_path / "state.sqlite3"),
        "--workspace", str(tmp_path),
        "--project-workspace-id", "w",
        "--mode", "coding",
        "--capability-registry", str(registry_path),
    ])

    assert rc == 0
    assert seen["registry_env"] == str(registry_path.resolve())
    assert seen["argument"] == str(registry_path)
    assert os.environ["LBE_CAPABILITY_REGISTRY"] == "previous-registry-value"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["entry"] == "start"
