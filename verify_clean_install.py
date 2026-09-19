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

    # Check textual_tui absence
    print("\n=== Checking textual_tui absence ===")
    check_tui = """
try:
    import lbe_guard_inspector.cli.textual_tui
    print("ERROR: textual_tui.py IS present in installed wheel!")
except ImportError:
    print("OK: textual_tui.py is NOT in installed wheel")
"""
    result = run([venv_python, "-c", check_tui])

    if "ERROR" in result.stdout:
        print("FAILED: textual_tui.py should not be present")
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
