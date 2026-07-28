from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .models import LifecycleReceipt, ModuleDeclaration, ReceiptType


@dataclass(frozen=True, slots=True)
class WatcherEvent:
    sequence: int
    event_type: ReceiptType
    module_id: str
    payload: ModuleDeclaration | LifecycleReceipt


@dataclass(frozen=True, slots=True)
class WatcherFailure:
    sequence: int
    module_id: str
    event_type: ReceiptType
    subscriber_name: str
    error_type: str
    error: str


@dataclass(frozen=True, slots=True)
class WatchSubscription:
    on_registered: Callable[[ModuleDeclaration], Any] | None = None
    on_loaded: Callable[[LifecycleReceipt], Any] | None = None
    on_started: Callable[[LifecycleReceipt], Any] | None = None
    on_activity: Callable[[LifecycleReceipt], Any] | None = None
    on_stopped: Callable[[LifecycleReceipt], Any] | None = None
    on_failed: Callable[[LifecycleReceipt], Any] | None = None
    name: str = "anonymous"

    def callback_for(
        self, event_type: ReceiptType
    ) -> Callable[[ModuleDeclaration | LifecycleReceipt], Any] | None:
        callbacks = {
            ReceiptType.REGISTERED: self.on_registered,
            ReceiptType.LOADED: self.on_loaded,
            ReceiptType.STARTED: self.on_started,
            ReceiptType.ACTIVITY: self.on_activity,
            ReceiptType.STOPPED: self.on_stopped,
            ReceiptType.FAILED: self.on_failed,
        }
        return callbacks[event_type]


class ModuleWatcher:
    def __init__(self, *, history_limit: int = 100, failure_limit: int = 100) -> None:
        if history_limit < 1:
            raise ValueError("history_limit must be at least 1")
        if failure_limit < 1:
            raise ValueError("failure_limit must be at least 1")
        self._history_limit = history_limit
        self._failure_limit = failure_limit
        self._subscriptions: list[WatchSubscription] = []
        self._history: list[WatcherEvent] = []
        self._failures: list[WatcherFailure] = []
        self._sequence = 0

    def watch(self, subscription: WatchSubscription) -> WatchSubscription:
        self._subscriptions.append(subscription)
        return subscription

    @property
    def history(self) -> tuple[WatcherEvent, ...]:
        return tuple(self._history)

    @property
    def failures(self) -> tuple[WatcherFailure, ...]:
        return tuple(self._failures)

    def publish_registered(self, declaration: ModuleDeclaration) -> WatcherEvent:
        return self._publish(ReceiptType.REGISTERED, declaration.id, declaration)

    def publish_receipt(self, receipt: LifecycleReceipt) -> WatcherEvent:
        return self._publish(receipt.type, receipt.module_id, receipt)

    def _publish(
        self,
        event_type: ReceiptType,
        module_id: str,
        payload: ModuleDeclaration | LifecycleReceipt,
    ) -> WatcherEvent:
        self._sequence += 1
        event = WatcherEvent(
            sequence=self._sequence,
            event_type=event_type,
            module_id=module_id,
            payload=payload,
        )
        self._history.append(event)
        self._history[:] = self._history[-self._history_limit :]

        for subscription in tuple(self._subscriptions):
            callback = subscription.callback_for(event_type)
            if callback is None:
                continue
            try:
                callback(payload)
            except Exception as exc:
                failure = WatcherFailure(
                    sequence=event.sequence,
                    module_id=module_id,
                    event_type=event_type,
                    subscriber_name=subscription.name,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                self._failures.append(failure)
                self._failures[:] = self._failures[-self._failure_limit :]
        return event
