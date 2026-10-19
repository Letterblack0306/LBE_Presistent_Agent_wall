"""Drive the real lbe-terminal.exe in a headless ConPTY and record every frame.

usage: python harness.py spec.json out_dir
"""
import html
import json
import os
import re
import sys
import threading
import time

import pyte
from winpty import PtyProcess

KEYS = {
    "Enter": "\r", "Esc": "\x1b", "Tab": "\t", "BackTab": "\x1b[Z",
    "Up": "\x1b[A", "Down": "\x1b[B", "PageUp": "\x1b[5~", "PageDown": "\x1b[6~",
    "F1": "\x1bOP", "F2": "\x1bOQ", "F3": "\x1bOR", "F4": "\x1bOS",
    "F5": "\x1b[15~", "F6": "\x1b[17~", "F7": "\x1b[18~", "F8": "\x1b[19~",
    "CtrlK": "\x0b", "CtrlC": "\x03", "Backspace": "\x7f",
}
NAMED = {
    "black": "#000000", "red": "#cd3131", "green": "#0dbc79", "yellow": "#e5e510",
    "blue": "#2472c8", "magenta": "#bc3fbc", "cyan": "#11a8cd", "white": "#e5e5e5",
    "brightblack": "#666666", "brightred": "#f14c4c", "brightgreen": "#23d18b",
    "brightyellow": "#f5f543", "brightblue": "#3b8eea", "brightmagenta": "#d670d6",
    "brightcyan": "#29b8db", "brightwhite": "#ffffff",
}


def colour(value, default):
    if not value or value == "default":
        return default
    if value in NAMED:
        return NAMED[value]
    if re.fullmatch(r"[0-9a-fA-F]{6}", value):
        return "#" + value
    return default


def main() -> None:
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cols, rows = spec.get("cols", 130), spec.get("rows", 38)
    env = dict(os.environ)
    env.update(spec.get("env", {}))
    log = open(os.path.join(out, "log.txt"), "w", encoding="utf-8", buffering=1)

    def note(msg):
        log.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

    proc = PtyProcess.spawn(spec["argv"], cwd=spec.get("cwd"), env=env, dimensions=(rows, cols))
    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream(screen)
    lock = threading.Lock()

    def reader():
        while True:
            try:
                data = proc.read(65536)
            except EOFError:
                note("pty closed")
                return
            except Exception as exc:  # noqa: BLE001
                note(f"read error {exc!r}")
                return
            if data:
                with lock:
                    stream.feed(data)

    threading.Thread(target=reader, daemon=True).start()

    def text():
        with lock:
            return "\n".join(screen.display)

    def snap(name):
        with lock:
            lines = list(screen.display)
            body = []
            for y in range(rows):
                row = screen.buffer[y]
                runs = []
                for x in range(cols):
                    ch = row[x]
                    fg = colour(ch.fg, "#cccccc")
                    bg = colour(ch.bg, "#0c0c0c")
                    if ch.reverse:
                        fg, bg = bg, fg
                    style = f"color:{fg};background:{bg}"
                    if ch.bold:
                        style += ";font-weight:700"
                    if ch.underscore:
                        style += ";text-decoration:underline"
                    if runs and runs[-1][0] == style:
                        runs[-1][1].append(ch.data or " ")
                    else:
                        runs.append((style, [ch.data or " "]))
                body.append("".join(
                    f'<span style="{s}">{html.escape("".join(t))}</span>' for s, t in runs))
        with open(os.path.join(out, name + ".txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        page = (
            "<!doctype html><meta charset=utf-8><body style='margin:0;background:#0c0c0c'>"
            "<pre style=\"margin:0;padding:8px;font:14px/1.25 'Cascadia Mono','DejaVu Sans Mono',monospace\">"
            + "\n".join(body) + "</pre>"
        )
        with open(os.path.join(out, name + ".html"), "w", encoding="utf-8") as fh:
            fh.write(page)
        note(f"snap {name}")

    def last_line():
        with lock:
            return screen.display[rows - 1]

    for step in spec["steps"]:
        if "key" in step:
            proc.write(KEYS[step["key"]])
            time.sleep(step.get("pause", 0.6))
        elif "type" in step:
            for c in step["type"]:
                proc.write(c)
                time.sleep(0.02)
            time.sleep(0.3)
        elif "sleep" in step:
            time.sleep(step["sleep"])
        elif "snap" in step:
            snap(step["snap"])
        elif "wait" in step:
            pat = re.compile(step["wait"])
            where = step.get("where", "screen")
            deadline = time.time() + step.get("timeout", 30)
            hit = False
            while time.time() < deadline:
                hay = last_line() if where == "status" else text()
                if pat.search(hay):
                    hit = True
                    break
                time.sleep(0.5)
            note(f"wait {step['wait']!r} -> {'hit' if hit else 'TIMEOUT'}")
        elif "if" in step:
            if re.search(step["if"], text()):
                note(f"if {step['if']!r} matched -> {step['then']}")
                proc.write(KEYS.get(step["then"], step["then"]))
                time.sleep(1)
            else:
                note(f"if {step['if']!r} no match")
    note("done")
    try:
        proc.terminate(force=True)
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
