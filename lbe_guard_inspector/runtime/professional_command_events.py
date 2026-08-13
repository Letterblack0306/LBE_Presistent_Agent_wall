"""P6 live execution events for host-registered fixed terminal commands.

This extends the accepted P5 terminal policy boundary without replacing the
synchronous ``terminal.exec`` compatibility path. Commands remain host-selected,
workspace-root scoped and ``shell=False``. This module owns process observation,
not authorization or provider continuation.
"""
from __future__ import annotations

import codecs
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterator, Mapping

from .professional_terminal_backend import TerminalCommandPolicy


class CommandEventType(StrEnum):
    STARTED = "command.started"
    STDOUT_DELTA = "command.stdout.delta"
    STDERR_DELTA = "command.stderr.delta"
    PROGRESS = "command.progress"
    COMPLETED = "command.completed"
    FAILED = "command.failed"
    CANCELLED = "command.cancelled"


@dataclass(frozen=True)
class CommandEvent:
    event_type: CommandEventType
    operation_id: str
    command_id: str
    sequence: int
    elapsed_seconds: float
    text: str | None = None
    exit_code: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, CommandEventType):
            raise TypeError("event_type must be CommandEventType")
        for name in ("operation_id", "command_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.sequence < 1:
            raise ValueError("sequence must be positive")
        if self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be non-negative")
        if self.event_type in {CommandEventType.STDOUT_DELTA, CommandEventType.STDERR_DELTA}:
            if not isinstance(self.text, str) or not self.text:
                raise ValueError("stream delta events require non-empty text")
        if self.event_type in {CommandEventType.COMPLETED, CommandEventType.FAILED} and self.exit_code is None:
            raise ValueError("terminal command event requires exit_code")
        object.__setattr__(self, "metadata", dict(self.metadata))


class CommandCancellation:
    """Thread-safe cancellation signal for one live command operation."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class _StreamChunk:
    stream: str
    text: str


@dataclass(frozen=True)
class _StreamClosed:
    stream: str


def stream_registered_command(
    *,
    operation_id: str,
    policy: TerminalCommandPolicy,
    workspace_root: str | Path,
    cancellation: CommandCancellation | None = None,
    progress_interval_seconds: float = 0.5,
) -> Iterator[CommandEvent]:
    """Yield truthful lifecycle events from one registered fixed command.

    ``policy`` is the same immutable host authority used by P5 ``terminal.exec``.
    No provider-controlled argv, cwd or shell flag is accepted here.
    """
    clean_operation = operation_id.strip() if isinstance(operation_id, str) else ""
    if not clean_operation:
        raise ValueError("operation_id must be a non-empty string")
    if not isinstance(policy, TerminalCommandPolicy):
        raise TypeError("policy must be TerminalCommandPolicy")
    if progress_interval_seconds <= 0:
        raise ValueError("progress_interval_seconds must be positive")
    root = Path(workspace_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError("active workspace root does not exist")
    cancellation = cancellation or CommandCancellation()

    started = time.monotonic()
    sequence = 0

    def event(
        event_type: CommandEventType,
        *,
        text: str | None = None,
        exit_code: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CommandEvent:
        nonlocal sequence
        sequence += 1
        return CommandEvent(
            event_type=event_type,
            operation_id=clean_operation,
            command_id=policy.command_id,
            sequence=sequence,
            elapsed_seconds=max(0.0, time.monotonic() - started),
            text=text,
            exit_code=exit_code,
            metadata={} if metadata is None else metadata,
        )

    try:
        process = subprocess.Popen(
            policy.argv,
            cwd=root,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
    except OSError as exc:
        yield event(
            CommandEventType.FAILED,
            exit_code=-1,
            metadata={"phase": "launch", "error_type": type(exc).__name__, "error_message": str(exc)},
        )
        return

    yield event(CommandEventType.STARTED, metadata={"pid": process.pid, "cwd": str(root), "argv": list(policy.argv)})

    observations: queue.Queue[_StreamChunk | _StreamClosed] = queue.Queue()

    def read_stream(name: str, pipe) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            while True:
                chunk = pipe.read(4096)
                if not chunk:
                    break
                text = decoder.decode(chunk)
                if text:
                    observations.put(_StreamChunk(name, text))
            tail = decoder.decode(b"", final=True)
            if tail:
                observations.put(_StreamChunk(name, tail))
        finally:
            try:
                pipe.close()
            finally:
                observations.put(_StreamClosed(name))

    assert process.stdout is not None
    assert process.stderr is not None
    threads = (
        threading.Thread(target=read_stream, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=read_stream, args=("stderr", process.stderr), daemon=True),
    )
    for thread in threads:
        thread.start()

    closed: set[str] = set()
    next_progress = started + progress_interval_seconds
    termination_reason: str | None = None

    while True:
        now = time.monotonic()
        if cancellation.cancelled and process.poll() is None:
            termination_reason = "cancelled"
            _terminate_process(process)
        elif now - started >= policy.timeout_seconds and process.poll() is None:
            termination_reason = "timeout"
            _terminate_process(process)

        wait_for = max(0.01, min(0.1, next_progress - now))
        try:
            observation = observations.get(timeout=wait_for)
        except queue.Empty:
            observation = None

        if isinstance(observation, _StreamChunk):
            stream_type = (
                CommandEventType.STDOUT_DELTA if observation.stream == "stdout" else CommandEventType.STDERR_DELTA
            )
            yield event(stream_type, text=observation.text)
        elif isinstance(observation, _StreamClosed):
            closed.add(observation.stream)

        now = time.monotonic()
        if process.poll() is None and now >= next_progress:
            yield event(CommandEventType.PROGRESS, metadata={"pid": process.pid, "running": True})
            while next_progress <= now:
                next_progress += progress_interval_seconds

        if process.poll() is not None and closed == {"stdout", "stderr"} and observations.empty():
            break

    for thread in threads:
        thread.join(timeout=1.0)
    exit_code = int(process.returncode if process.returncode is not None else -1)

    if termination_reason == "cancelled":
        yield event(CommandEventType.CANCELLED, metadata={"pid": process.pid, "exit_code": exit_code})
    elif termination_reason == "timeout":
        yield event(
            CommandEventType.FAILED,
            exit_code=exit_code,
            metadata={"pid": process.pid, "reason": "timeout", "timeout_seconds": policy.timeout_seconds},
        )
    elif exit_code == 0:
        yield event(CommandEventType.COMPLETED, exit_code=exit_code, metadata={"pid": process.pid})
    else:
        yield event(CommandEventType.FAILED, exit_code=exit_code, metadata={"pid": process.pid, "reason": "nonzero_exit"})


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    try:
        process.terminate()
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2.0)
    except ProcessLookupError:
        return
