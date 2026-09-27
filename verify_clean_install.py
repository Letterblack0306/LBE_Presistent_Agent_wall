#!/usr/bin/env python3
"""Clean install and entrypoint verification script."""
import subprocess
import sys
import os
import tempfile
import shutil

def run(cmd, cwd=None):
    """Run a command and return result."""
    print(f"\n>>> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    print(f"Return code: {result.returncode}")
    return result

def main():
    repo_root = r"C:\Agents-Memory-Tool-v6-integration"
    dist_dir = os.path.join(repo_root, "dist")
    temp_dir = tempfile.mkdtemp(prefix="lbe-verify-")

    print(f"Working in temp dir: {temp_dir}")

    # Create venv
    print("\n=== Creating clean venv ===")
    venv_result = run([sys.executable, "-m", "venv", temp_dir])
    if venv_result.returncode != 0:
        print("FAILED: Could not create venv")
        return 1

    venv_python = os.path.join(temp_dir, "Scripts", "python.exe")
    venv_pip = os.path.join(temp_dir, "Scripts", "pip.exe")

    # Upgrade pip in venv
    print("\n=== Upgrading pip ===")
    run([venv_python, "-m", "pip", "install", "--upgrade", "pip"])

    # Install wheel
    print("\n=== Installing wheel ===")
    install_result = run([venv_pip, "install", "--no-index", f"--find-links={dist_dir}", "lbe-guard-inspector"])

    if install_result.returncode != 0:
        print("\n=== RETRYING with PyPI index for dependencies ===")
        install_result = run([
            venv_pip, "install", "--no-cache-dir",
            f"--find-links={dist_dir}",
            "lbe-guard-inspector"
        ])

    # Check entrypoints
    print("\n=== Checking installed entrypoints ===")
    check_code = """
from importlib.metadata import distribution
d = distribution('lbe-guard-inspector')
print("Installed entrypoints:")
for ep in d.entry_points:
    print(f"  '{ep.name}' -> '{ep.value}'")
"""
    result = run([venv_python, "-c", check_code])

    if result.returncode != 0:
        print("FAILED: Could not check entrypoints")
        return 1

    # The legacy Textual TUI is a tracked, deliberately retained diagnostic module.
    # Shipping it in the installed wheel is permitted; being reachable from the
    # supported installed product path is not. This probe therefore tests
    # reachability through the supported entrypoint instead of module absence.
    # It never imports the legacy module (that would require and execute the
    # optional Textual UI); it observes attempted imports instead. Import attempts
    # are recorded with a sys.meta_path hook, which is consulted for every import
    # including ones that fail resolution, so a legacy route cannot stay invisible.
    print("\n=== Checking legacy textual TUI reachability ===")
    check_tui = """
import importlib.metadata
import importlib.util
import sys

LEGACY = "lbe_guard_inspector.textual_tui"

if importlib.util.find_spec(LEGACY) is not None:
    print(f"shipped legacy module (permitted, must stay unreachable): {LEGACY}")
else:
    print(f"legacy module not shipped: {LEGACY}")

distribution = importlib.metadata.distribution("lbe-guard-inspector")
entrypoints = sorted(f"{ep.name}={ep.value}" for ep in distribution.entry_points)
legacy_entrypoints = [entry for entry in entrypoints if LEGACY in entry]
print(f"supported entrypoints: {entrypoints}")


class LegacyImportRecorder:
    def __init__(self):
        self.attempts = []

    def find_spec(self, fullname, path=None, target=None):
        if fullname == LEGACY or fullname.startswith(LEGACY + "."):
            self.attempts.append(fullname)
        return None


recorder = LegacyImportRecorder()
sys.meta_path.insert(0, recorder)

try:
    from lbe_guard_inspector.product_entry import main
except Exception as exc:
    main = None
    print(f"ERROR: supported product entrypoint did not import: {type(exc).__name__}: {exc}")

if main is not None:
    for label, argv in (
        ("delegated path lbe --help", ["--help"]),
        ("product command path lbe capabilities --help", ["capabilities", "--help"]),
    ):
        try:
            exit_code = main(argv)
        except SystemExit as exit_request:
            exit_code = 0 if exit_request.code is None else exit_request.code
        except Exception as exc:
            exit_code = f"ERROR {type(exc).__name__}: {exc}"
        print(f"{label} -> exit {exit_code}")

if legacy_entrypoints:
    print(f"ERROR: supported entrypoint routes into the legacy TUI: {legacy_entrypoints}")
elif recorder.attempts:
    print(f"ERROR: supported product path resolved the legacy TUI: {recorder.attempts}")
elif main is None:
    print("supported product path was not exercised; reachability not established")
else:
    print("OK: no supported installed entrypoint or invocation reaches the legacy textual TUI")
"""
    result = run([venv_python, "-c", check_tui])

    if "ERROR" in result.stdout:
        print("FAILED: legacy textual TUI is reachable from the supported product path")
        return 1

    # Check that lbe, lbe start work
    print("\n=== Checking 'lbe --help' ===")
    result = run([venv_python, "-c", "from lbe_guard_inspector.product_entry import main; print('product_entry.main importable')"])

    if result.returncode != 0:
        print("FAILED: product_entry.main not importable")
        return 1

    # Check that retired scripts are absent
    print("\n=== Checking retired scripts absent ===")
    check_retired = """
from importlib.metadata import distribution
d = distribution('lbe-guard-inspector')
names = {ep.name for ep in d.entry_points}
retired = {'lbe-guard-inspector', 'lbe-guard-audit'}
found_retired = names & retired
if found_retired:
    print(f"ERROR: Retired scripts still present: {found_retired}")
else:
    print("OK: No retired scripts in entrypoints")
    print(f"Current entrypoints: {sorted(names)}")
"""
    result = run([venv_python, "-c", check_retired])

    if "ERROR" in result.stdout:
        print("FAILED: Retired scripts still present")
        return 1

    # Cleanup
    print(f"\n=== Cleaning up temp dir {temp_dir} ===")
    shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n=== ALL CHECKS PASSED ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
