"""Unattended real ConPTY LBE keyboard/mouse smoke acceptance.

Requires pywinpty (install outside the worktree if desired). Runs the built
release TUI; makes no project modifications and records trace evidence in TEMP.
A source/unit PASS must never substitute for these observed PTY actions.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXE = ROOT / "apps" / "lbe-terminal" / "target" / "release" / "lbe.exe"


def run_case(name: str, exe: Path, steps: list[tuple[str, float]], required: list[str]) -> dict:
    from winpty import PtyProcess

    trace = Path(tempfile.gettempdir()) / f"lbe-real-pty-{os.getpid()}-{name}.jsonl"
    trace.unlink(missing_ok=True)
    env = dict(os.environ)
    env.update(LBE_INPUT_TRACE_FILE=str(trace), LBE_NO_ANIMATION="1")
    proc = PtyProcess.spawn(str(exe), cwd=str(ROOT), env=env, dimensions=(35, 110))
    captured: list[str] = []

    def read_output() -> None:
        try:
            while proc.isalive():
                chunk = proc.read(8192)
                if chunk:
                    captured.append(chunk)
        except (OSError, EOFError):
            pass

    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()
    # ConPTY does not emulate the DA/window-state responses supplied by a
    # real terminal. Without them the event reader may start after input
    # injection, silently losing the first mouse-down packet.
    time.sleep(0.3)
    proc.write("\x1b[2t\x1b[?1;2c")
    deadline = time.monotonic() + 5.0
    while "?1002h" not in "".join(captured) and proc.isalive() and time.monotonic() < deadline:
        time.sleep(0.05)
    capture_ready = "?1002h" in "".join(captured)
    started = proc.isalive() and capture_ready
    try:
        for payload, pause in steps:
            if not proc.isalive():
                break
            proc.write(payload)
            time.sleep(pause)
        if proc.isalive():
            proc.write("q")
        time.sleep(0.9)
        clean_exit = not proc.isalive()
    finally:
        if proc.isalive():
            proc.terminate(force=True)
    terminal_output = "".join(captured)
    restore_emitted = "?1049l" in terminal_output and "?1002l" in terminal_output
    observed = trace.read_text(encoding="utf-8", errors="replace").splitlines() if trace.exists() else []
    actions = [line.split("action=", 1)[1] for line in observed if "action=" in line]
    missing = [needle for needle in required if not any(needle in action for action in actions)]
    return {
        "case": name,
        "status": "PASS" if started and clean_exit and restore_emitted and not missing else "FAIL",
        "started": started,
        "mouse_capture_ready": capture_ready,
        "clean_exit": clean_exit,
        "terminal_restore_emitted": restore_emitted,
        "missing_actions": missing,
        "actions": actions,
        "trace": str(trace),
        "trace_rows": len(observed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--deps", type=Path, default=Path(tempfile.gettempdir()) / "lbe-pty-test-deps")
    options = parser.parse_args()
    if options.deps.exists():
        sys.path.insert(0, str(options.deps))
    try:
        import winpty  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "BLOCKED_DEPENDENCY", "need": "pywinpty", "temp_deps": str(options.deps)}))
        return 2
    exe = options.exe.resolve()
    if not exe.is_file():
        print(json.dumps({"status": "BLOCKED_BUILD", "exe": str(exe)}))
        return 2

    cases = [
        (
            "keyboard",
            [("\r", .45), ("?", .45), ("\x10", .45), ("\x1b[B", .45),
             ("\r", .45), ("\x1bOQ", .45), ("\x1bOR", .45), ("\t", .45)],
            ["enter_landing", "toggle_shortcuts", "toggle_command_palette",
             "command_palette_execute", "open_provider_panel",
             "open_model_panel", "set_mode"],
        ),
        (
            "mouse_landing",
            [("\x1b[<0;20;10M", .5), ("\x1b[<0;20;10m", .5)],
            ["mouse_enter_landing"],
        ),
        (
            "keyboard_palette_escape",
            [("\r", .45), ("\x10", .45), ("\x1b", .75)],
            ["enter_landing", "toggle_command_palette", "close_command_palette"],
        ),
        (
            "mouse_shortcuts_dismiss",
            [("\r", .45), ("?", .45),
             ("\x1b[<0;20;10M", .45), ("\x1b[<0;20;10m", .45)],
            ["enter_landing", "toggle_shortcuts", "mouse_close_shortcuts"],
        ),
        (
            "mouse_palette_scroll",
            [("\r", .45), ("\x10", .45),
             ("\x1b[<0;16;8M", .45), ("\x1b[<0;16;8m", .45),
             ("\x1b[<65;30;14M", .45), ("\x1b[<64;30;14M", .45)],
            ["enter_landing", "toggle_command_palette",
             "mouse_command_palette_select index=0",
             "mouse_scroll delta=3", "mouse_scroll delta=-3"],
        ),
    ]
    results = [run_case(name, exe, steps, wanted) for name, steps, wanted in cases]
    status = "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"
    print(json.dumps({"status": status, "exe": str(exe), "cases": results}, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
