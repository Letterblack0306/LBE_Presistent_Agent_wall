from __future__ import annotations

import sqlite3

import pytest

from lbe_guard_inspector.memory.models import SessionState
from lbe_guard_inspector.memory.operational_history import (
    ItemStatus,
    OperationalEvent,
    OperationalHistoryError,
    SessionOperationalHistory,
    TurnStatus,
)
from lbe_guard_inspector.memory.store import WorkspaceMemoryStore


def _history(tmp_path):
    store = WorkspaceMemoryStore(tmp_path / "memory.sqlite3")
    store.save_session_state(SessionState(
        session_id="session-1",
        project_workspace_id="workspace-1",
        canonical_workspace_root=tmp_path,
        mode="coding",
        permission="write_allowed",
        runtime_policy="development",
        provider_id="openai-compatible",
        provider_model="model-a",
    ))
    return store, SessionOperationalHistory(store=store)


def test_uses_same_authoritative_session_database(tmp_path) -> None:
    store, history = _history(tmp_path)
    turn = history.start_turn(session_id="session-1", turn_id="turn-1")
    assert turn.ordinal == 1
    with sqlite3.connect(store.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM runtime_turns").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM session_state").fetchone()[0] == 1


def test_unknown_session_cannot_create_turn(tmp_path) -> None:
    store = WorkspaceMemoryStore(tmp_path / "memory.sqlite3")
    history = SessionOperationalHistory(store=store)
    with pytest.raises(OperationalHistoryError, match="unknown session"):
        history.start_turn(session_id="missing")


def test_turn_and_item_ordinals_are_monotonic(tmp_path) -> None:
    _, history = _history(tmp_path)
    first = history.start_turn(session_id="session-1", turn_id="turn-1")
    second = history.start_turn(session_id="session-1", turn_id="turn-2")
    assert (first.ordinal, second.ordinal) == (1, 2)

    item1 = history.start_item(turn_id="turn-1", kind="model.message", item_id="item-1")
    item2 = history.start_item(turn_id="turn-1", kind="model.tool_call", item_id="item-2")
    assert (item1.ordinal, item2.ordinal) == (1, 2)


def test_event_sequences_are_monotonic_per_session_and_turn(tmp_path) -> None:
    _, history = _history(tmp_path)
    history.start_turn(session_id="session-1", turn_id="turn-1")
    history.start_turn(session_id="session-1", turn_id="turn-2")
    history.start_item(turn_id="turn-1", kind="model.message", item_id="item-1")

    first = history.append_event(OperationalEvent(
        session_id="session-1",
        turn_id="turn-1",
        item_id="item-1",
        event_type="model.turn.started",
        payload={},
    ))
    second = history.append_event(OperationalEvent(
        session_id="session-1",
        turn_id="turn-1",
        item_id="item-1",
        event_type="model.message.delta",
        payload={"text": "hi"},
    ))
    third = history.append_event(OperationalEvent(
        session_id="session-1",
        turn_id="turn-2",
        event_type="model.turn.started",
        payload={},
    ))

    assert (first.session_sequence, second.session_sequence, third.session_sequence) == (1, 2, 3)
    assert (first.turn_sequence, second.turn_sequence, third.turn_sequence) == (1, 2, 1)


def test_provider_and_runtime_identity_are_persisted_separately(tmp_path) -> None:
    _, history = _history(tmp_path)
    history.start_turn(session_id="session-1", turn_id="turn-1")
    history.start_item(turn_id="turn-1", kind="tool.execution", item_id="item-1")
    event = history.append_event(OperationalEvent(
        session_id="session-1",
        turn_id="turn-1",
        item_id="item-1",
        event_type="tool.completed",
        payload={"ok": True},
        provider_id="openai-compatible",
        model_id="model-a",
        provider_request_id="response-1",
        provider_item_id="provider-item-1",
        provider_tool_call_id="provider-call-1",
        lbe_call_id="lbe-call-1",
        runtime_operation_id="op-1",
        tool_receipt_id="receipt-1",
        provider_state_metadata_ref="state-ref-1",
        raw_diagnostic_ref="diag-ref-1",
    ))

    replayed = history.events_for_turn(turn_id="turn-1")
    assert replayed == (event,)
    assert replayed[0].provider_tool_call_id == "provider-call-1"
    assert replayed[0].lbe_call_id == "lbe-call-1"
    assert replayed[0].runtime_operation_id == "op-1"
    assert replayed[0].tool_receipt_id == "receipt-1"
    assert replayed[0].provider_state_metadata_ref == "state-ref-1"
    assert replayed[0].raw_diagnostic_ref == "diag-ref-1"


def test_event_item_must_belong_to_same_turn_and_session(tmp_path) -> None:
    _, history = _history(tmp_path)
    history.start_turn(session_id="session-1", turn_id="turn-1")
    history.start_turn(session_id="session-1", turn_id="turn-2")
    history.start_item(turn_id="turn-1", kind="message", item_id="item-1")
    with pytest.raises(OperationalHistoryError, match="does not belong"):
        history.append_event(OperationalEvent(
            session_id="session-1",
            turn_id="turn-2",
            item_id="item-1",
            event_type="model.message.delta",
            payload={"text": "wrong turn"},
        ))


def test_finalized_item_is_immutable_and_rejects_more_events(tmp_path) -> None:
    _, history = _history(tmp_path)
    history.start_turn(session_id="session-1", turn_id="turn-1")
    history.start_item(turn_id="turn-1", kind="message", item_id="item-1")
    history.append_event(OperationalEvent(
        session_id="session-1",
        turn_id="turn-1",
        item_id="item-1",
        event_type="model.message.completed",
        payload={"text": "done"},
    ))
    final = history.finalize_item(item_id="item-1", status=ItemStatus.COMPLETED)
    assert final.status is ItemStatus.COMPLETED
    assert history.finalize_item(item_id="item-1", status=ItemStatus.COMPLETED) == final
    with pytest.raises(OperationalHistoryError, match="immutable"):
        history.finalize_item(item_id="item-1", status=ItemStatus.FAILED)
    with pytest.raises(OperationalHistoryError, match="finalized runtime item"):
        history.append_event(OperationalEvent(
            session_id="session-1",
            turn_id="turn-1",
            item_id="item-1",
            event_type="model.message.delta",
            payload={"text": "late"},
        ))


def test_turn_cannot_finalize_with_inflight_items_and_final_outcome_is_immutable(tmp_path) -> None:
    _, history = _history(tmp_path)
    history.start_turn(session_id="session-1", turn_id="turn-1")
    history.start_item(turn_id="turn-1", kind="message", item_id="item-1")
    with pytest.raises(OperationalHistoryError, match="items remain in progress"):
        history.finalize_turn(turn_id="turn-1", status=TurnStatus.COMPLETED)
    history.finalize_item(item_id="item-1", status=ItemStatus.COMPLETED)
    final = history.finalize_turn(turn_id="turn-1", status=TurnStatus.COMPLETED)
    assert final.status is TurnStatus.COMPLETED
    assert history.finalize_turn(turn_id="turn-1", status=TurnStatus.COMPLETED) == final
    with pytest.raises(OperationalHistoryError, match="immutable"):
        history.finalize_turn(turn_id="turn-1", status=TurnStatus.FAILED)


def test_finalized_turn_rejects_new_items_and_events(tmp_path) -> None:
    _, history = _history(tmp_path)
    history.start_turn(session_id="session-1", turn_id="turn-1")
    history.finalize_turn(turn_id="turn-1", status=TurnStatus.CANCELLED)
    with pytest.raises(OperationalHistoryError, match="finalized runtime turn"):
        history.start_item(turn_id="turn-1", kind="message")
    with pytest.raises(OperationalHistoryError, match="finalized runtime turn"):
        history.append_event(OperationalEvent(
            session_id="session-1",
            turn_id="turn-1",
            event_type="model.cancelled",
            payload={},
        ))


def test_session_replay_preserves_append_order_across_turns(tmp_path) -> None:
    _, history = _history(tmp_path)
    history.start_turn(session_id="session-1", turn_id="turn-1")
    history.start_turn(session_id="session-1", turn_id="turn-2")
    history.append_event(OperationalEvent(
        session_id="session-1", turn_id="turn-1", event_type="a", payload={"n": 1}
    ))
    history.append_event(OperationalEvent(
        session_id="session-1", turn_id="turn-2", event_type="b", payload={"n": 2}
    ))
    history.append_event(OperationalEvent(
        session_id="session-1", turn_id="turn-1", event_type="c", payload={"n": 3}
    ))
    replay = history.events_for_session(session_id="session-1")
    assert [event.event_type for event in replay] == ["a", "b", "c"]
    assert [event.session_sequence for event in replay] == [1, 2, 3]
