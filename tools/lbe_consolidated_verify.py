"""Single-command, evidence-scoped LBE machine verification. No acceptance fabrication."""
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools"))
from lbe_test_console import collect

def now():
    return datetime.now(timezone.utc).isoformat()

def run(output=None):
    root = output or Path(tempfile.gettempdir()) / "agent-validation" / uuid.uuid4().hex / "consolidated"
    root.mkdir(parents=True, exist_ok=True)
    child_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CARGO_TARGET_DIR=str(root / "cargo-target"))
    results = []
    def record(name, status, detail, blocking=True):
        entry = {"name": name, "status": status, "blocking": blocking, "detail": detail}
        results.append(entry)
        (root / "result.json").write_text(json.dumps({"status": "RUNNING", "checks": results}, indent=2), encoding="utf-8")
        print(name + ": " + status, flush=True)
    def command(name, argv, timeout=120, structural=False, blocking=True):
        logfile = root / (name + ".log")
        try:
            with logfile.open("w", encoding="utf-8") as log:
                proc = subprocess.run(argv, cwd=str(ROOT), env=child_env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            status = ("STRUCTURAL_PASS_ONLY" if structural else "PASS") if proc.returncode == 0 else "FAILED"
            record(name, status, {"exit": proc.returncode, "log": str(logfile)}, blocking)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logfile.write_text(type(exc).__name__ + ": " + str(exc), encoding="utf-8")
            record(name, "ERROR", {"log": str(logfile), "error": str(exc)}, blocking)
    for name in ("governance", "source_contract"):
        logfile = root / (name + ".log")
        try:
            passed, report = collect(name)
            logfile.write_text(report, encoding="utf-8")
            record(name, "PASS" if passed else "FAILED", {"log": str(logfile)})
        except Exception as exc:
            logfile.write_text(str(exc), encoding="utf-8")
            record(name, "ERROR", {"log": str(logfile)})
    command("rust_format", ["cargo", "fmt", "--manifest-path", "apps/lbe-terminal/Cargo.toml", "--", "--check"], 60, blocking=False)
    command("rust_tests", ["cargo", "test", "--manifest-path", "apps/lbe-terminal/Cargo.toml", "--locked", "--", "--quiet"], 150, blocking=False)
    command("rust_build", ["cargo", "check", "--manifest-path", "apps/lbe-terminal/Cargo.toml", "--locked"], 100, blocking=False)
    command("integration", ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools/lbe_product_integration.ps1"), "check", "-NoFetch", "-OutputRoot", str(root / "integration")], 180, structural=True)
    # Check exact installed product-owned paths, not an unrelated executable on PATH.
    install = Path.home() / "AppData" / "Local" / "LetterBlack" / "LBE"
    expected = [install / "venv" / "Scripts" / "lbe.exe", install / "lbe-launch.ps1", install / "bin" / "lbe.cmd"]
    missing = [str(item) for item in expected if not item.is_file()]
    installed_log = root / "installed_launcher.log"
    if missing:
        installed_log.write_text("PRODUCT_NOT_INSTALLED\n" + "\n".join(missing), encoding="utf-8")
        record("installed_launcher", "FAILED", {"log": str(installed_log), "reason": "PRODUCT_NOT_INSTALLED", "missing": missing})
    else:
        command("installed_launcher", [str(expected[2]), "--version"], 60)
    record("installed_tui_pty_visual", "UNVERIFIED", "Exact installed artifact + PTY/ConPTY keyboard, mouse, resize and screenshot observation not executed", True)
    record("provider_tool_end_to_end", "UNVERIFIED", "No authorized installed provider/tool effect-to-receipt-to-continuation acceptance recorded by this runner", True)
    gate = json.loads((ROOT / ".lbe/governance/implementation-gates.json").read_text("utf-8-sig"))
    pending = [{"slice": key, "status": value.get("status"), "blocking": value.get("blocking", True)}
               for key, value in gate.get("active_execution_plan", {}).get("ordered_slices", {}).items()
               if value.get("status") != "PASS"]
    blocking = any(item["status"] not in ("PASS", "STRUCTURAL_PASS_ONLY") for item in results if item["blocking"])
    payload = {"schema_version": 1, "created_at": now(), "kind": "LBE_CONSOLIDATED_MACHINE_VERIFICATION",
               "status": "BLOCKED" if blocking else "READY_FOR_PRODUCT_ACCEPTANCE",
               "release_ready": False, "checks": results, "gate_status": gate.get("status"),
               "pending_gate_slices": pending, "acceptance": "NOT_PROVEN"}
    (root / "result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("CONSOLIDATED_VERDICT=" + payload["status"], flush=True)
    print("RECEIPT=" + str(root / "result.json"), flush=True)
    return 2 if blocking else 0

if __name__ == "__main__":
    raise SystemExit(run())
