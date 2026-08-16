"""Python-owned lifecycle for the governed Cline Node stdio worker."""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import TextIO

from .cline_stdio_protocol import BridgeFrame, ProtocolError, parse_frame


class BridgeProcessError(RuntimeError):
    """Raised when the bounded worker lifecycle fails closed."""


class GovernedClineWorker:
    """Own one bounded long-lived Node child and fail closed on protocol defects."""

    def __init__(
        self,
        *,
        node_executable: str = "node",
        worker_path: str | Path | None = None,
        startup_timeout_seconds: float = 10.0,
    ) -> None:
        default_worker = Path(__file__).with_name("cline_worker") / "worker.mjs"
        self.node_executable = node_executable
        self.worker_path = (
            Path(worker_path) if worker_path is not None else default_worker
        )
        self.startup_timeout_seconds = startup_timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._seen_message_ids: set[str] = set()
        self._stderr_lines: list[str] = []
        self._stderr_thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def stderr_text(self) -> str:
        return "".join(self._stderr_lines)

    def start(self, frame: BridgeFrame) -> BridgeFrame:
        if self.is_running:
            raise BridgeProcessError("worker already running")
        if frame.message_type != "runtime.start":
            raise ValueError("start requires runtime.start frame")
        if not self.worker_path.is_file():
            raise FileNotFoundError(f"worker not found: {self.worker_path}")

        self._process = subprocess.Popen(
            [self.node_executable, str(self.worker_path)],
            cwd=self.worker_path.parent,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        assert self._process.stdin is not None
        assert self._process.stdout is not None
        assert self._process.stderr is not None
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            args=(self._process.stderr,),
            daemon=True,
        )
        self._stderr_thread.start()
        self.send(frame)
        ready = self.read(timeout_seconds=self.startup_timeout_seconds)
        if ready.message_type != "runtime.ready":
            self.terminate()
            raise BridgeProcessError(
                f"expected runtime.ready, got {ready.message_type}"
            )
        return ready

    def send(self, frame: BridgeFrame) -> None:
        if (
            not self.is_running
            or self._process is None
            or self._process.stdin is None
        ):
            raise BridgeProcessError("worker is not running")
        self._process.stdin.write(frame.to_json_line())
        self._process.stdin.flush()

    def read(self, *, timeout_seconds: float = 10.0) -> BridgeFrame:
        if (
            not self.is_running
            or self._process is None
            or self._process.stdout is None
        ):
            raise BridgeProcessError("worker is not running")

        holder: list[str] = []
        done = threading.Event()

        def _reader() -> None:
            assert self._process is not None
            assert self._process.stdout is not None
            holder.append(self._process.stdout.readline())
            done.set()

        threading.Thread(target=_reader, daemon=True).start()
        if not done.wait(timeout_seconds):
            self.terminate()
            raise BridgeProcessError("worker response timeout")
        raw = holder[0]
        if raw == "":
            code = self._process.poll()
            raise BridgeProcessError(
                f"worker exited before protocol response: {code}"
            )

        try:
            frame = parse_frame(raw, expected_direction="node_to_python")
        except ProtocolError:
            self.terminate()
            raise

        if frame.message_id in self._seen_message_ids:
            self.terminate()
            raise ProtocolError(f"duplicate message_id: {frame.message_id}")
        self._seen_message_ids.add(frame.message_id)
        return frame

    def shutdown(
        self, frame: BridgeFrame, *, timeout_seconds: float = 5.0
    ) -> BridgeFrame:
        if frame.message_type != "runtime.shutdown":
            raise ValueError("shutdown requires runtime.shutdown frame")
        self.send(frame)
        result = self.read(timeout_seconds=timeout_seconds)
        process = self._process
        if process is not None:
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                self.terminate()
                raise BridgeProcessError(
                    "worker did not exit after shutdown"
                ) from exc
        return result

    def terminate(self) -> None:
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)

    def _drain_stderr(self, stream: TextIO) -> None:
        for line in stream:
            self._stderr_lines.append(line)
