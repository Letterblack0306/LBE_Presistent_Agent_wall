"""Keyboard-first Textual projection over persisted LBE runtime owners."""
from __future__ import annotations

import os
from typing import Callable
from uuid import uuid4

from .control_protocol import ControlMethod, ControlOutcome, ControlRequest
from .memory.operational_history import SessionOperationalHistory
from .persistent_turn_control import PersistentTurnControl
from .provider_health import ProviderHealthResult, check_provider_health
from .provider_registry import ProviderRegistry, default_provider_registry
from .reasoning_provider import ProviderConfig
from .runtime.tool_orchestration import ToolRegistry
from .session_memory_runtime import SessionMemoryRuntimeBridge
from .terminal_projection import render_terminal_activity, render_terminal_event_detail
from .tui_view_models import project_tui_capabilities


def build_textual_tui(
    *,
    history: SessionOperationalHistory,
    session_id: str,
    control: PersistentTurnControl,
    provider_config: ProviderConfig | None = None,
    provider_registry: ProviderRegistry | None = None,
    provider_health_checker: Callable[..., ProviderHealthResult] = check_provider_health,
    tool_registry: ToolRegistry | None = None,
):
    """Build one stable workspace without creating a second runtime authority."""
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Vertical
        from textual.widgets import Input, Static
    except ImportError as exc:
        raise RuntimeError("Textual UI is unavailable; install lbe-guard-inspector[tui]") from exc

    current_session_id = session_id
    state = history.store.load_session_state(session_id=current_session_id)
    if state is None:
        raise ValueError(f"session not found: {current_session_id}")

    registry = provider_registry or default_provider_registry()
    provider_health = "unknown"

    no_color = "NO_COLOR" in os.environ
    accent = "#d0d0d0" if no_color else "#ef4b4b"
    muted = "#b8b8b8" if no_color else "#a1a1aa"

    class LbeTextualApp(App[None]):
        """Stable header, objective, activity, composer, status, and details regions."""

        TITLE = "LBE"
        CSS = f"""
        Screen {{ background: #000000; color: #e9e9ef; }}
        #workspace {{ height: 100%; background: #000000; }}
        #header {{ height: 1; padding: 0 1; color: #e9e9ef; background: #0b0c15; }}
        #objective {{ height: 2; padding: 0 1; color: #e9e9ef; background: #0b0c15; }}
        #columns {{ height: 1; padding: 0 1; color: {muted}; background: #0b0c15; }}
        #activity {{ height: 1fr; min-height: 4; padding: 0 1; color: #e9e9ef; background: #000000; overflow-y: auto; }}
        #composer {{ height: 3; margin: 0; border-top: solid {accent}; border-bottom: none; background: #000000; color: #e9e9ef; }}
        #status {{ height: 1; padding: 0 1; color: {muted}; background: #0b0c15; }}
        #details {{ height: auto; max-height: 7; padding: 0 1; color: #e9e9ef; background: #0b0c15; }}
        """
        BINDINGS = [
            Binding("ctrl+p", "details", "Details", priority=True),
            Binding("ctrl+h", "details", "Details", priority=True),
            Binding("ctrl+i", "interrupt", "Interrupt", priority=True),
            Binding("ctrl+c", "interrupt", "Interrupt", priority=True),
            Binding("ctrl+x", "cancel", "Cancel", priority=True),
        ]

        def compose(self) -> ComposeResult:
            with Vertical(id="workspace"):
                yield Static(_header_text(), id="header")
                yield Static(_objective_text(), id="objective")
                yield Static("event      target                                     receipt        state", id="columns")
                yield Static(_activity_text(), id="activity")
                yield Input(
                    placeholder="Enter an objective, steer an active turn, or type /help",
                    id="composer",
                )
                yield Static(_status_text(), id="status")
                details = Static(_details_text(), id="details")
                details.display = False
                yield details

        def on_mount(self) -> None:
            self.query_one("#composer", Input).focus()

        def on_input_submitted(self, event: Input.Submitted) -> None:
            text = event.value.strip()
            if not text:
                return
            if text.startswith("/"):
                self._command(text)
                event.input.value = ""
                return
            active = history.latest_running_turn(session_id=current_session_id)
            method = ControlMethod.TURN_STEER if active is not None else ControlMethod.TURN_START
            params = {"session_id": current_session_id, "text": text}
            if active is not None:
                params["turn_id"] = active.turn_id
            self._handle(ControlRequest(f"tui-{uuid4()}", method, params))
            event.input.value = ""

        def action_details(self) -> None:
            details = self.query_one("#details", Static)
            if details.display:
                details.display = False
            else:
                self._show_details(_help_text())

        def _show_details(self, text: str) -> None:
            details = self.query_one("#details", Static)
            details.update(text)
            details.display = True

        def _command(self, text: str) -> None:
            command = text.split(maxsplit=1)[0].lower()
            if command == "/status":
                self._show_details(_status_details_text())
                return
            if command == "/provider":
                parts = text.split()
                if len(parts) == 1:
                    self._show_details(_provider_details_text())
                    return
                if len(parts) == 2 and parts[1].lower() == "check":
                    self._check_provider_health()
                    return
                if len(parts) == 4 and parts[1].lower() == "use":
                    self._select_provider(parts[2], parts[3])
                    return
                self.notify(
                    "Usage: /provider | /provider use <provider> <model> | /provider check",
                    severity="warning",
                )
                return
            if command == "/evidence":
                self._show_details(_evidence_details_text())
                return
            if command in {"/tools", "/capabilities"}:
                self._show_details(_capabilities_text())
                return
            if command == "/integrations":
                self._show_details(_integrations_text())
                return
            if command == "/detail":
                parts = text.split()
                if len(parts) > 2 or (len(parts) == 2 and not parts[1].isdigit()):
                    self.notify("Usage: /detail [event-sequence]", severity="warning")
                    return
                sequence = int(parts[1]) if len(parts) == 2 else None
                self._show_details(render_terminal_event_detail(
                    history=history,
                    session_id=current_session_id,
                    sequence=sequence,
                ))
                return
            if command in {"/help", "/commands"}:
                self._show_details(_help_text())
                return
            if command == "/sessions":
                self._show_details(_sessions_text())
                return
            if command == "/session":
                parts = text.split(maxsplit=1)
                if len(parts) != 2:
                    self.notify("Usage: /session <session-id>", severity="warning")
                    return
                self._switch_session(parts[1])
                return
            if command == "/new":
                parts = text.split(maxsplit=1)
                if len(parts) != 2:
                    self.notify("Usage: /new <session-id>", severity="warning")
                    return
                self._create_session(parts[1])
                return
            if command == "/interrupt":
                self.action_interrupt()
                return
            if command == "/cancel":
                self.action_cancel()
                return
            self.notify(f"Unsupported command: {command}. Use /help.", severity="warning")

        def _select_provider(self, provider_id: str, model_id: str) -> None:
            nonlocal state, provider_health
            clean_provider = provider_id.strip()
            clean_model = model_id.strip()
            if history.latest_running_turn(session_id=current_session_id) is not None:
                self.notify("Cancel or complete the active turn before changing provider.", severity="warning")
                return
            if clean_provider not in registry.provider_ids():
                self.notify(f"Provider is not registered: {clean_provider}", severity="warning")
                return
            runtime = _runtime_for_state(state)
            state = runtime.configure_session(
                provider_id=clean_provider,
                provider_model=clean_model,
            )
            provider_health = "unknown"
            self._refresh_projection()
            self._show_details(_provider_details_text())
            self.notify(f"Selected provider {clean_provider}/{clean_model}", severity="information")

        def _check_provider_health(self) -> None:
            nonlocal provider_health
            if not state.provider_id or not state.provider_model:
                provider_health = "unconfigured"
                self._show_details(_provider_details_text())
                return
            if provider_config is None:
                provider_health = "unavailable (no explicit provider config)"
                self._show_details(_provider_details_text())
                return
            if provider_config.model.strip() != state.provider_model:
                provider_health = "unavailable (config model does not match selected model)"
                self._show_details(_provider_details_text())
                return
            try:
                result = provider_health_checker(
                    provider_id=state.provider_id,
                    provider_config=provider_config,
                    provider_registry=registry,
                )
            except Exception as exc:
                provider_health = f"failed ({type(exc).__name__})"
                self._show_details(_provider_details_text())
                return
            provider_health = result.status
            self._show_details(_provider_details_text())

        def _switch_session(self, target_session_id: str) -> None:
            nonlocal current_session_id, state
            clean_id = target_session_id.strip()
            if history.latest_running_turn(session_id=current_session_id) is not None:
                self.notify("Cancel or complete the active turn before switching sessions.", severity="warning")
                return
            target = history.store.load_session_state(session_id=clean_id)
            if target is None:
                self.notify(f"Session not found: {clean_id}", severity="warning")
                return
            current_session_id = target.session_id
            state = target
            self._refresh_projection()
            self.notify(f"Resumed session {clean_id}", severity="information")

        def _create_session(self, requested_session_id: str) -> None:
            nonlocal current_session_id, state
            clean_id = requested_session_id.strip()
            if not clean_id:
                self.notify("Session id must not be empty.", severity="warning")
                return
            if history.latest_running_turn(session_id=current_session_id) is not None:
                self.notify("Cancel or complete the active turn before creating a session.", severity="warning")
                return
            if history.store.load_session_state(session_id=clean_id) is not None:
                self.notify(f"Session already exists: {clean_id}", severity="warning")
                return
            runtime = _runtime_for_state(state, session_id=clean_id)
            current_session_id = runtime.session_state.session_id
            state = runtime.session_state
            self._refresh_projection()
            self.notify(f"Created session {clean_id}", severity="information")

        def _refresh_projection(self) -> None:
            self.query_one("#activity", Static).update(_activity_text())
            self.query_one("#header", Static).update(_header_text())
            self.query_one("#objective", Static).update(_objective_text())
            self.query_one("#status", Static).update(_status_text())
            details = self.query_one("#details", Static)
            if details.display:
                details.update(_status_details_text())

        def action_interrupt(self) -> None:
            active = history.latest_running_turn(session_id=current_session_id)
            if active is None:
                self.notify("No active turn to interrupt", severity="warning")
                return
            self._handle(ControlRequest(
                f"tui-{uuid4()}",
                ControlMethod.TURN_INTERRUPT,
                {"session_id": current_session_id, "turn_id": active.turn_id},
            ))

        def action_cancel(self) -> None:
            active = history.latest_running_turn(session_id=current_session_id)
            if active is None:
                self.notify("No active turn to cancel", severity="warning")
                return
            self._handle(ControlRequest(
                f"tui-{uuid4()}",
                ControlMethod.TURN_CANCEL,
                {"session_id": current_session_id, "turn_id": active.turn_id},
            ))

        def _handle(self, request: ControlRequest) -> None:
            outcome: ControlOutcome = control.handle(request)
            self.query_one("#activity", Static).update(_activity_text())
            self.query_one("#header", Static).update(_header_text())
            self.query_one("#objective", Static).update(_objective_text())
            self.query_one("#status", Static).update(_status_text())
            self.notify(
                outcome.reason if not outcome.accepted else f"Control {outcome.state}",
                severity="error" if not outcome.accepted else "information",
            )

    def _header_text() -> str:
        active = history.latest_running_turn(session_id=current_session_id)
        runtime_state = "active" if active is not None else "idle"
        workspace = state.project_workspace_id or state.canonical_workspace_root.name
        provider = f"{state.provider_id or 'unconfigured'}/{state.provider_model or 'unconfigured'}"
        return f"LBE  {workspace}  session:{state.session_id}  {state.mode}  {provider}  {runtime_state}"

    def _objective_text() -> str:
        events = history.events_for_session(session_id=current_session_id)
        latest = next((event for event in reversed(events) if event.event_type == "user.message"), None)
        if latest is None:
            return "> No objective submitted"
        text = latest.payload.get("text") if isinstance(latest.payload, dict) else None
        return f"> {text.strip() if isinstance(text, str) and text.strip() else '(no persisted objective text)'}"

    def _activity_text() -> str:
        return render_terminal_activity(history=history, session_id=current_session_id)

    def _status_text() -> str:
        active = history.latest_running_turn(session_id=current_session_id)
        state_text = "ACTIVE" if active is not None else "IDLE"
        return f"{state_text}  /status /provider /evidence /tools /integrations /detail /help /sessions /session /new /interrupt /cancel"

    def _details_text() -> str:
        return _help_text()

    def _status_details_text() -> str:
        active = history.latest_running_turn(session_id=current_session_id)
        runtime_state = "ACTIVE" if active is not None else "IDLE"
        return (
            f"STATUS\n"
            f"runtime={runtime_state} session={state.session_id} mode={state.mode}\n"
            f"workspace={state.canonical_workspace_root}\n"
            f"permission={state.permission or 'unknown'} policy={state.runtime_policy or 'unknown'}"
        )

    def _provider_details_text() -> str:
        return (
            f"PROVIDER\n"
            f"id={state.provider_id or 'unconfigured'} model={state.provider_model or 'unconfigured'}\n"
            f"profile={state.active_profile_id or 'unconfigured'}\n"
            f"health={provider_health}"
        )

    def _evidence_details_text() -> str:
        events = history.events_for_session(session_id=current_session_id)
        receipts = tuple(event.tool_receipt_id for event in events if event.tool_receipt_id)
        recent = ", ".join(receipts[-3:]) if receipts else "none"
        return (
            f"EVIDENCE\n"
            f"persisted_events={len(events)} persisted_receipts={len(receipts)}\n"
            f"recent_receipts={recent}"
        )

    def _capabilities_text() -> str:
        if tool_registry is None:
            return "CAPABILITIES\nunavailable: no governed tool registry configured"
        views = project_tui_capabilities(tool_registry.specs())
        if not views:
            return "CAPABILITIES\nempty: no registered governed tools"
        lines = ["CAPABILITIES"]
        for view in views:
            lines.append(
                f"{view.tool_id} capability={view.capability} access={view.access_class} "
                f"network={view.network_behavior} risk={view.risk_class} "
                f"state={'available' if view.available else 'unavailable'}"
            )
        return "\n".join(lines)

    def _integrations_text() -> str:
        return (
            "INTEGRATIONS\n"
            "unavailable: no runtime integration registry owner is configured"
        )

    def _sessions_text() -> str:
        sessions = history.store.list_session_states(
            project_workspace_id=state.project_workspace_id,
            limit=50,
        )
        lines = ["SESSIONS"]
        for item in sessions:
            marker = "*" if item.session_id == current_session_id else " "
            lines.append(f"{marker} {item.session_id}  {item.mode}  {item.updated_at}")
        return "\n".join(lines) if len(lines) > 1 else "SESSIONS\nnone"

    def _help_text() -> str:
        return (
            "HELP\n"
            "/status runtime and policy  /provider selected provider metadata\n"
            "/provider use <provider> <model>  /provider check explicit-config health\n"
            "/evidence persisted event and receipt counts  /detail [sequence] event facts\n"
            "/tools registered governed capabilities  /integrations integration availability\n"
            "/sessions list workspace sessions\n"
            "/session <id> resume  /new <id> create  /help this reference\n"
            "/interrupt request interruption  /cancel cancel the active turn"
        )

    def _runtime_for_state(source_state, *, session_id: str | None = None) -> SessionMemoryRuntimeBridge:
        return SessionMemoryRuntimeBridge(
            database_path=history.store.database_path,
            project_workspace_id=source_state.project_workspace_id,
            workspace_root=source_state.canonical_workspace_root,
            session_id=session_id or source_state.session_id,
            mode=source_state.mode,
            permission=source_state.permission,
            runtime_policy=source_state.runtime_policy,
            provider_id=source_state.provider_id,
            provider_model=source_state.provider_model,
            active_profile_id=source_state.active_profile_id,
            permission_policy_id=source_state.permission_policy_id,
            evidence_policy_id=source_state.evidence_policy_id,
        )

    return LbeTextualApp()


def run_textual_tui(
    *,
    history: SessionOperationalHistory,
    session_id: str,
    control: PersistentTurnControl,
    provider_config: ProviderConfig | None = None,
    tool_registry: ToolRegistry | None = None,
) -> None:
    build_textual_tui(
        history=history,
        session_id=session_id,
        control=control,
        provider_config=provider_config,
        tool_registry=tool_registry,
    ).run()
