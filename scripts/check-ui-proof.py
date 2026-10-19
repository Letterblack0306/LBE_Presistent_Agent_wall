from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HARNESS = ROOT / "tools" / "ui-proof" / "harness.py"
GOLDEN_DIR = ROOT / "apps" / "lbe-terminal" / "tests" / "golden"
PROOF_DIR = ROOT / ".lbe" / "proofs" / "ui"
RELEASE_EXE = ROOT / "apps" / "lbe-terminal" / "target" / "release" / "lbe-terminal.exe"

INTENT_ID = "LBE-INTENT-TUI-V4-LIVE-HEADER-RAIL-PLAN-20261019"


def fail(message: str) -> None:
    print(f"LBE UI PROOF GATE: BLOCKED: {message}", file=sys.stderr)
    raise SystemExit(1)


def _check(path: Path, label: str) -> None:
    if not path.exists():
        fail(f"missing required UI proof artifact: {label} ({path})")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest().upper()


def _validate_manifest(manifest_path: Path) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = [
        "intent_id",
        "binary_sha256",
        "gate_version",
        "cases",
        "result",
    ]
    for key in required:
        if key not in data:
            fail(f"proof manifest missing required key: {key}")
    if data["intent_id"] != INTENT_ID:
        fail(f"proof manifest intent_id mismatch: {data['intent_id']} != {INTENT_ID}")
    exe = Path(data.get("binary_path", ""))
    if exe.exists():
        actual = _sha256_file(exe)
        if data["binary_sha256"] != actual:
            fail(
                f"proof manifest binary sha256 mismatch: "
                f"manifest={data['binary_sha256']} actual={actual}"
            )


def main() -> None:
    # Gate §6: the UI proof infrastructure must exist before any UI change can be committed.
    _check(HARNESS, "UI proof harness (tools/ui-proof/harness.py)")
    _check(GOLDEN_DIR, "golden frames directory (apps/lbe-terminal/tests/golden/)")

    # Gate §6a: if a proof manifest exists for this intent, it must be valid and current.
    manifest = PROOF_DIR / f"{INTENT_ID}.json"
    if manifest.exists():
        _validate_manifest(manifest)
        exe = RELEASE_EXE
        if not exe.exists():
            fail("proof manifest exists but release binary is missing; rebuild with cargo build --release")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        actual_sha = _sha256_file(exe)
        if data.get("binary_sha256") != actual_sha:
            fail(
                f"proof manifest is stale: binary changed since proof was produced "
                f"(manifest={data.get('binary_sha256')} actual={actual_sha}); "
                f"re-run proof and regenerate manifest"
            )
        if data.get("result") != "PASS":
            fail(f"proof manifest result is {data.get('result')!r}, expected PASS")

    print(
        "LBE UI PROOF GATE: PASS — "
        f"harness={HARNESS} goldens={GOLDEN_DIR} manifest={'present' if manifest.exists() else 'pending'}"
    )


if __name__ == "__main__":
    if "--print-index-revision" in sys.argv:
        # Not applicable to UI proof gate; kept for interface symmetry.
        print("n/a")
        raise SystemExit(0)
    main()
