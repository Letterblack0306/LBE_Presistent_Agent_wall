"""Keyboard-first Textual projection over persisted LBE runtime owners."""
from __future__ import annotations

import os
from uuid import uuid4

from .control_protocol import ControlMethod, ControlOutcome, ControlRequest
from .memory.operational_history import SessionOperationalHistory
from .persistent_turn_control import PersistentTurnControl
from .terminal_projection import render_terminal_timeline


def build_textual_tui(*, history: SessionOperationalHistory, session_id: str, control: PersistentTurnControl):
    """Build one stable workspace without creating a second runtime authority."""
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Vertical
        from textual.widgets import Input, Static
    except ImportError as exc:
        raise RuntimeError("Textual UI is unavailable; install lbe-guard-inspector[tui]") from exc

    state = history.store.load_session_state(session_id=session_id)
    if state is None:
        raise ValueError(f"session not found: {session_id}")

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
                self.notify("Command routing opens in the next gated slice.", severity="warning")
                event.input.value = ""
                return
            active = history.latest_running_turn(session_id=session_id)
            method = ControlMethod.TURN_STEER if active is not None else ControlMethod.TURN_START
            params = {"session_id": session_id, "text": text}
            if active is not None:
                params["turn_id"] = active.turn_id
            self._handle(ControlRequest(f"tui-{uuid4()}", method, params))
            event.input.value = ""

        def action_details(self) -> None:
            details = self.query_one("#details", Static)
            details.update(_details_text())
            details.display = not details.display

        def action_interrupt(self) -> None:
            active = history.latest_running_turn(session_id=session_id)
            if active is None:
                self.notify("No active turn to interrupt", severity="warning")
                return
            self._handle(ControlRequest(
                f"tui-{uuid4()}",
                ControlMethod.TURN_INTERRUPT,
                {"session_id": session_id, "turn_id": active.turn_id},
            ))

        def action_cancel(self) -> None:
            active = history.latest_running_turn(session_id=session_id)
            if active is None:
                self.notify("No active turn to cancel", severity="warning")
                return
            self._handle(ControlRequest(
                f"tui-{uuid4()}",
                ControlMethod.TURN_CANCEL,
                {"session_id": session_id, "turn_id": active.turn_id},
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
        active = history.latest_running_turn(session_id=session_id)
        runtime_state = "active" if active is not None else "idle"
        workspace = state.project_workspace_id or state.canonical_workspace_root.name
        provider = f"{state.provider_id or 'unconfigured'}/{state.provider_model or 'unconfigured'}"
        return f"LBE  {workspace}  session:{state.session_id}  {state.mode}  {provider}  {runtime_state}"

    def _objective_text() -> str:
        events = history.events_for_session(session_id=session_id)
        latest = next((event for event in reversed(events) if event.event_type == "user.message"), None)
        if latest is None:
            return "> No objective submitted"
        text = latest.payload.get("text") if isinstance(latest.payload, dict) else None
        return f"> {text.strip() if isinstance(text, str) and text.strip() else '(no persisted objective text)'}"

    def _activity_text() -> str:
        return render_terminal_timeline(history=history, session_id=session_id)

    def _status_text() -> str:
        active = history.latest_running_turn(session_id=session_id)
        state_text = "ACTIVE" if active is not None else "IDLE"
        return f"{state_text}  Ctrl+P details  Ctrl+I interrupt  Ctrl+X cancel"

    def _details_text() -> str:
        events = history.events_for_session(session_id=session_id)
        receipts = [event.tool_receipt_id for event in events if event.tool_receipt_id]
        return (
            f"SESSION: {state.session_id}  WORKSPACE: {state.canonical_workspace_root}\n"
            f"PROVIDER: {state.provider_id or 'unconfigured'} / {state.provider_model or 'unconfigured'}\n"
            f"POLICY: mode={state.mode} permission={state.permission or 'unknown'} profile={state.runtime_policy or 'unknown'}\n"
            f"EVIDENCE: persisted receipts={len(receipts)}"
        )

    return LbeTextualApp()


def run_textual_tui(*, history: SessionOperationalHistory, session_id: str, control: PersistentTurnControl) -> None:
    build_textual_tui(history=history, session_id=session_id, control=control).run()
