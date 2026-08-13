"""P4 persistent Session/Turn/Item/Event operational history.

This module composes with ``WorkspaceMemoryStore`` and writes into the same
SQLite database that already owns session/workspace identity. It is deliberately
not an independent EventRecorder or JSONL authority.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .models import utc_now
from .store import WorkspaceMemoryStore


class OperationalHistoryError(RuntimeError):
    """Raised when operational history ordering or finalization is violated."""


class TurnStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    REFUSED = "refused"
    CANCELLED = "cancelled"
    FAILED = "failed"
    ESCALATED = "escalated"


class ItemStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DENIED = "denied"
    ESCALATED = "escalated"


@dataclass(frozen=True)
class OperationalTurn:
    turn_id: str
    session_id: str
    ordinal: int
    status: TurnStatus
    created_at: str
    finalized_at: str | None = None


@dataclass(frozen=True)
class OperationalItem:
    item_id: str
    session_id: str
    turn_id: str
    ordinal: int
    kind: str
    status: ItemStatus
    created_at: str
    finalized_at: str | None = None


@dataclass(frozen=True)
class OperationalEvent:
    session_id: str
    turn_id: str
    event_type: str
    payload: Mapping[str, Any]
    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex}")
    item_id: str | None = None
    session_sequence: int = 0
    turn_sequence: int = 0
    provider_id: str | None = None
    model_id: str | None = None
    provider_request_id: str | None = None
    provider_item_id: str | None = None
    provider_tool_call_id: str | None = None
    lbe_call_id: str | None = None
    runtime_operation_id: str | None = None
    tool_receipt_id: str | None = None
    provider_state_metadata_ref: str | None = None
    raw_diagnostic_ref: str | None = None
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for name in ("session_id", "turn_id", "event_type", "event_id"):
            _require_text(getattr(self, name), name)
        if self.item_id is not None:
            _require_text(self.item_id, "item_id")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")
        for name in (
            "provider_id",
            "model_id",
            "provider_request_id",
            "provider_item_id",
            "provider_tool_call_id",
            "lbe_call_id",
            "runtime_operation_id",
            "tool_receipt_id",
            "provider_state_metadata_ref",
            "raw_diagnostic_ref",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_text(value, name)
        if self.session_sequence < 0 or self.turn_sequence < 0:
            raise ValueError("event sequences cannot be negative")


class SessionOperationalHistory:
    """Append-only operational history inside the authoritative session DB."""

    def __init__(self, *, store: WorkspaceMemoryStore) -> None:
        if not isinstance(store, WorkspaceMemoryStore):
            raise TypeError("store must be WorkspaceMemoryStore")
        self.store = store

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.store.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def start_turn(self, *, session_id: str, turn_id: str | None = None) -> OperationalTurn:
        clean_session = _require_text(session_id, "session_id")
        if self.store.load_session_state(session_id=clean_session) is None:
            raise OperationalHistoryError("cannot create runtime turn for unknown session")
        clean_turn = _optional_id(turn_id, "turn_id") or f"turn-{uuid.uuid4().hex}"
        created_at = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            ordinal = int(connection.execute(
                "SELECT COALESCE(MAX(ordinal), 0) + 1 FROM runtime_turns WHERE session_id=?",
                (clean_session,),
            ).fetchone()[0])
            connection.execute(
                "INSERT INTO runtime_turns (turn_id, session_id, ordinal, status, created_at, finalized_at) VALUES (?, ?, ?, ?, ?, NULL)",
                (clean_turn, clean_session, ordinal, TurnStatus.IN_PROGRESS.value, created_at),
            )
        return OperationalTurn(
            turn_id=clean_turn,
            session_id=clean_session,
            ordinal=ordinal,
            status=TurnStatus.IN_PROGRESS,
            created_at=created_at,
        )

    def start_item(self, *, turn_id: str, kind: str, item_id: str | None = None) -> OperationalItem:
        clean_turn = _require_text(turn_id, "turn_id")
        clean_kind = _require_text(kind, "kind")
        clean_item = _optional_id(item_id, "item_id") or f"item-{uuid.uuid4().hex}"
        created_at = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            turn = connection.execute(
                "SELECT session_id, status FROM runtime_turns WHERE turn_id=?",
                (clean_turn,),
            ).fetchone()
            if turn is None:
                raise OperationalHistoryError("cannot create item for unknown runtime turn")
            if str(turn["status"]) != TurnStatus.IN_PROGRESS.value:
                raise OperationalHistoryError("cannot create item for finalized runtime turn")
            session_id = str(turn["session_id"])
            ordinal = int(connection.execute(
                "SELECT COALESCE(MAX(ordinal), 0) + 1 FROM runtime_items WHERE turn_id=?",
                (clean_turn,),
            ).fetchone()[0])
            connection.execute(
                "INSERT INTO runtime_items (item_id, session_id, turn_id, ordinal, kind, status, created_at, finalized_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                (clean_item, session_id, clean_turn, ordinal, clean_kind, ItemStatus.IN_PROGRESS.value, created_at),
            )
        return OperationalItem(
            item_id=clean_item,
            session_id=session_id,
            turn_id=clean_turn,
            ordinal=ordinal,
            kind=clean_kind,
            status=ItemStatus.IN_PROGRESS,
            created_at=created_at,
        )

    def append_event(self, event: OperationalEvent) -> OperationalEvent:
        if not isinstance(event, OperationalEvent):
            raise TypeError("event must be OperationalEvent")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            turn = connection.execute(
                "SELECT session_id, status FROM runtime_turns WHERE turn_id=?",
                (event.turn_id,),
            ).fetchone()
            if turn is None:
                raise OperationalHistoryError("runtime event references unknown turn")
            if str(turn["session_id"]) != event.session_id:
                raise OperationalHistoryError("runtime event session does not match turn session")
            if str(turn["status"]) != TurnStatus.IN_PROGRESS.value:
                raise OperationalHistoryError("cannot append event to finalized runtime turn")
            if event.item_id is not None:
                item = connection.execute(
                    "SELECT session_id, turn_id, status FROM runtime_items WHERE item_id=?",
                    (event.item_id,),
                ).fetchone()
                if item is None:
                    raise OperationalHistoryError("runtime event references unknown item")
                if str(item["session_id"]) != event.session_id or str(item["turn_id"]) != event.turn_id:
                    raise OperationalHistoryError("runtime event item does not belong to the event turn/session")
                if str(item["status"]) != ItemStatus.IN_PROGRESS.value:
                    raise OperationalHistoryError("cannot append event to finalized runtime item")

            session_sequence = int(connection.execute(
                "SELECT COALESCE(MAX(session_sequence), 0) + 1 FROM runtime_events WHERE session_id=?",
                (event.session_id,),
            ).fetchone()[0])
            turn_sequence = int(connection.execute(
                "SELECT COALESCE(MAX(turn_sequence), 0) + 1 FROM runtime_events WHERE turn_id=?",
                (event.turn_id,),
            ).fetchone()[0])
            connection.execute(
                """
                INSERT INTO runtime_events (
                    event_id, session_id, turn_id, item_id, session_sequence, turn_sequence,
                    event_type, payload_json, provider_id, model_id, provider_request_id,
                    provider_item_id, provider_tool_call_id, lbe_call_id,
                    runtime_operation_id, tool_receipt_id, provider_state_metadata_ref,
                    raw_diagnostic_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.session_id,
                    event.turn_id,
                    event.item_id,
                    session_sequence,
                    turn_sequence,
                    event.event_type,
                    json.dumps(dict(event.payload), ensure_ascii=False, sort_keys=True),
                    event.provider_id,
                    event.model_id,
                    event.provider_request_id,
                    event.provider_item_id,
                    event.provider_tool_call_id,
                    event.lbe_call_id,
                    event.runtime_operation_id,
                    event.tool_receipt_id,
                    event.provider_state_metadata_ref,
                    event.raw_diagnostic_ref,
                    event.created_at,
                ),
            )
        return OperationalEvent(
            event_id=event.event_id,
            session_id=event.session_id,
            turn_id=event.turn_id,
            item_id=event.item_id,
            session_sequence=session_sequence,
            turn_sequence=turn_sequence,
            event_type=event.event_type,
            payload=dict(event.payload),
            provider_id=event.provider_id,
            model_id=event.model_id,
            provider_request_id=event.provider_request_id,
            provider_item_id=event.provider_item_id,
            provider_tool_call_id=event.provider_tool_call_id,
            lbe_call_id=event.lbe_call_id,
            runtime_operation_id=event.runtime_operation_id,
            tool_receipt_id=event.tool_receipt_id,
            provider_state_metadata_ref=event.provider_state_metadata_ref,
            raw_diagnostic_ref=event.raw_diagnostic_ref,
            created_at=event.created_at,
        )

    def finalize_item(self, *, item_id: str, status: ItemStatus) -> OperationalItem:
        clean_item = _require_text(item_id, "item_id")
        if not isinstance(status, ItemStatus) or status is ItemStatus.IN_PROGRESS:
            raise ValueError("final item status must be a terminal ItemStatus")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM runtime_items WHERE item_id=?", (clean_item,)).fetchone()
            if row is None:
                raise OperationalHistoryError("unknown runtime item")
            current = ItemStatus(str(row["status"]))
            if current is not ItemStatus.IN_PROGRESS:
                if current is status:
                    return _row_to_item(row)
                raise OperationalHistoryError("finalized runtime item outcome is immutable")
            finalized_at = utc_now()
            connection.execute(
                "UPDATE runtime_items SET status=?, finalized_at=? WHERE item_id=?",
                (status.value, finalized_at, clean_item),
            )
            row = connection.execute("SELECT * FROM runtime_items WHERE item_id=?", (clean_item,)).fetchone()
        assert row is not None
        return _row_to_item(row)

    def finalize_turn(self, *, turn_id: str, status: TurnStatus) -> OperationalTurn:
        clean_turn = _require_text(turn_id, "turn_id")
        if not isinstance(status, TurnStatus) or status is TurnStatus.IN_PROGRESS:
            raise ValueError("final turn status must be a terminal TurnStatus")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM runtime_turns WHERE turn_id=?", (clean_turn,)).fetchone()
            if row is None:
                raise OperationalHistoryError("unknown runtime turn")
            current = TurnStatus(str(row["status"]))
            if current is not TurnStatus.IN_PROGRESS:
                if current is status:
                    return _row_to_turn(row)
                raise OperationalHistoryError("finalized runtime turn outcome is immutable")
            in_flight = int(connection.execute(
                "SELECT COUNT(*) FROM runtime_items WHERE turn_id=? AND status=?",
                (clean_turn, ItemStatus.IN_PROGRESS.value),
            ).fetchone()[0])
            if in_flight:
                raise OperationalHistoryError("cannot finalize runtime turn while items remain in progress")
            finalized_at = utc_now()
            connection.execute(
                "UPDATE runtime_turns SET status=?, finalized_at=? WHERE turn_id=?",
                (status.value, finalized_at, clean_turn),
            )
            row = connection.execute("SELECT * FROM runtime_turns WHERE turn_id=?", (clean_turn,)).fetchone()
        assert row is not None
        return _row_to_turn(row)

    def get_turn(self, *, turn_id: str) -> OperationalTurn | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runtime_turns WHERE turn_id=?", (turn_id,)).fetchone()
        return _row_to_turn(row) if row is not None else None

    def get_item(self, *, item_id: str) -> OperationalItem | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runtime_items WHERE item_id=?", (item_id,)).fetchone()
        return _row_to_item(row) if row is not None else None

    def events_for_turn(self, *, turn_id: str) -> tuple[OperationalEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runtime_events WHERE turn_id=? ORDER BY turn_sequence ASC",
                (turn_id,),
            ).fetchall()
        return tuple(_row_to_event(row) for row in rows)

    def events_for_session(self, *, session_id: str) -> tuple[OperationalEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runtime_events WHERE session_id=? ORDER BY session_sequence ASC",
                (session_id,),
            ).fetchall()
        return tuple(_row_to_event(row) for row in rows)


def _row_to_turn(row: sqlite3.Row) -> OperationalTurn:
    return OperationalTurn(
        turn_id=str(row["turn_id"]),
        session_id=str(row["session_id"]),
        ordinal=int(row["ordinal"]),
        status=TurnStatus(str(row["status"])),
        created_at=str(row["created_at"]),
        finalized_at=row["finalized_at"],
    )


def _row_to_item(row: sqlite3.Row) -> OperationalItem:
    return OperationalItem(
        item_id=str(row["item_id"]),
        session_id=str(row["session_id"]),
        turn_id=str(row["turn_id"]),
        ordinal=int(row["ordinal"]),
        kind=str(row["kind"]),
        status=ItemStatus(str(row["status"])),
        created_at=str(row["created_at"]),
        finalized_at=row["finalized_at"],
    )


def _row_to_event(row: sqlite3.Row) -> OperationalEvent:
    return OperationalEvent(
        event_id=str(row["event_id"]),
        session_id=str(row["session_id"]),
        turn_id=str(row["turn_id"]),
        item_id=row["item_id"],
        session_sequence=int(row["session_sequence"]),
        turn_sequence=int(row["turn_sequence"]),
        event_type=str(row["event_type"]),
        payload=json.loads(str(row["payload_json"])),
        provider_id=row["provider_id"],
        model_id=row["model_id"],
        provider_request_id=row["provider_request_id"],
        provider_item_id=row["provider_item_id"],
        provider_tool_call_id=row["provider_tool_call_id"],
        lbe_call_id=row["lbe_call_id"],
        runtime_operation_id=row["runtime_operation_id"],
        tool_receipt_id=row["tool_receipt_id"],
        provider_state_metadata_ref=row["provider_state_metadata_ref"],
        raw_diagnostic_ref=row["raw_diagnostic_ref"],
        created_at=str(row["created_at"]),
    )


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_id(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, name)
