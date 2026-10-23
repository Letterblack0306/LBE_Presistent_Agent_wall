"""Validate durable UI proof bindings. Local frame comparison is separate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools/ui-proof/harness.py"
PLAN = ROOT / ".lbe/plan"
PROOFS = ROOT / ".lbe/proofs/ui"
RELEASE_EXE = ROOT / "apps/lbe-terminal/target/release/lbe-terminal.exe"
# Owner-maintained list of approved golden frame hashes. It lives under the
# protected .lbe/** path, so an agent cannot approve its own goldens.
APPROVED_GOLDENS = PROOFS / "approved-goldens.json"
MASK = re.compile(r"(?<!\w)(?:\d+(?:\.\d+)?\s*tok/s|\d+s ago|\d{4}-\d\d-\d\d(?:[T ][0-9:.+Z-]+)?|\d\d:\d\d(?::\d\d(?:\.\d+)?)?|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|(?:session|receipt|task|run)[-_][A-Za-z0-9-]+)(?!\w)", re.I)

def fail(message: str) -> None:
    raise SystemExit(f"LBE UI PROOF GATE: BLOCKED: {message}")

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        fail(f"cannot read {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"expected object in {path}")
    return value

def intent_id() -> str:
    value = read(ROOT / ".lbe/governance/implementation-gates.json").get("active_intent", {}).get("intent_id")
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        fail("active intent is missing or invalid")
    return value

def staged_tree(intent: str) -> str:
    # The two records are excluded to avoid a self-referential tree hash.
    result = subprocess.run(["git", "ls-files", "--stage", "-z"], cwd=ROOT, capture_output=True)
    if result.returncode:
        fail("cannot read Git index")
    excluded = {f".lbe/proofs/ui/{intent}.json", f".lbe/plan/{intent}.json"}
    entries = [entry for entry in result.stdout.split(b"\0") if entry and
               entry.split(b"\t", 1)[-1].decode(errors="replace") not in excluded]
    return digest(b"\0".join(entries) + b"\0")

def require_staged(path: Path) -> None:
    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(["git", "ls-files", "--error-unmatch", "--", relative],
                            cwd=ROOT, capture_output=True)
    if result.returncode:
        fail(f"durable record is not tracked by Git: {relative}")

def required(plan: dict, key: str) -> set[str]:
    values = plan.get(key)
    if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v for v in values) or len(values) != len(set(values)):
        fail(f"plan must declare unique {key}")
    return set(values)

def entries(manifest: dict, plan: dict, field: str, plan_field: str) -> list[dict]:
    actual = manifest.get(field)
    if not isinstance(actual, list) or any(not isinstance(v, dict) for v in actual):
        fail(f"{field} must be a list of objects")
    ids = [v.get("id") for v in actual]
    expected = required(plan, plan_field)
    if len(ids) != len(set(ids)) or set(ids) != expected:
        fail(f"{field} differ from plan: missing={sorted(expected - set(ids))}")
    if any(v.get("result") != "PASS" for v in actual):
        fail(f"{field} contain a non-PASS result")
    return actual

def masked(text: str, model: str) -> str:
    if model:
        text = text.replace(model, "<MODEL>")
    return MASK.sub("<DYNAMIC>", text)

def local_frames(manifest: dict, run_dir: Path, cases: list[dict]) -> None:
    base = run_dir.resolve()
    if not base.is_dir() or base == ROOT or ROOT in base.parents:
        fail("capture directory must exist outside repository")
    for case in cases:
        paths = {}
        for field in ("frame", "golden"):
            rel = case.get(field)
            if not isinstance(rel, str):
                fail(f"{case['id']} lacks {field}")
            path = (base / rel).resolve()
            if base not in path.parents or not path.is_file():
                fail(f"{case['id']} {field} missing or outside capture directory")
            if digest(path.read_bytes()) != str(case.get(f"{field}_sha256", "")).upper():
                fail(f"{case['id']} {field} hash mismatch")
            paths[field] = path
        model = str(manifest.get("model_name", ""))
        if masked(paths["frame"].read_text(encoding="utf-8"), model) != masked(paths["golden"].read_text(encoding="utf-8"), model):
            fail(f"{case['id']} differs from approved golden outside permitted masks")

def owner_goldens() -> set[str]:
    require_staged(APPROVED_GOLDENS)
    values = read(APPROVED_GOLDENS).get("approved_sha256")
    if not isinstance(values, list) or not values or any(
            not re.fullmatch(r"[0-9A-Fa-f]{64}", str(v)) for v in values):
        fail("owner-approved golden list is empty or invalid")
    return {str(v).upper() for v in values}

def validate(manifest: dict, plan: dict, intent: str, run_dir: Path | None,
             verify_only: bool = False) -> list[dict]:
    if manifest.get("intent_id") != intent or manifest.get("result") != "PASS":
        fail("manifest intent/result invalid")
    if manifest.get("staged_tree") != staged_tree(intent):
        fail("manifest staged_tree does not bind current Git index")
    if str(manifest.get("harness_sha256", "")).upper() != digest(HARNESS.read_bytes()):
        fail("manifest harness hash is stale")
    if not re.fullmatch(r"[0-9A-Fa-f]{64}", str(manifest.get("binary_sha256", ""))):
        fail("manifest binary_sha256 missing or invalid")
    if not verify_only:
        # CI cannot reproduce byte-identical builds; locally the proof must
        # describe the release binary that is actually on disk.
        if not RELEASE_EXE.is_file():
            fail("release binary missing; run cargo build --release in apps/lbe-terminal")
        if digest(RELEASE_EXE.read_bytes()) != str(manifest["binary_sha256"]).upper():
            fail("manifest binary_sha256 does not match the current release build")
    cases = entries(manifest, plan, "cases", "required_cases")
    entries(manifest, plan, "scenarios", "required_scenarios")
    for case in cases:
        if not all(re.fullmatch(r"[0-9A-Fa-f]{64}", str(case.get(f"{f}_sha256", ""))) for f in ("frame", "golden")):
            fail(f"{case['id']} lacks frame/golden hash")
    approved = owner_goldens()
    for case in cases:
        if str(case.get("golden_sha256", "")).upper() not in approved:
            fail(f"{case['id']} golden is not in the owner-approved golden list")
    if run_dir:
        local_frames(manifest, run_dir, cases)
    return cases

def write_plan(path: Path, plan: dict, manifest_path: Path, cases: list[dict]) -> None:
    decision = subprocess.run(["node", "scripts/action-preflight.mjs", "write",
                               path.relative_to(ROOT).as_posix()], cwd=ROOT, capture_output=True, text=True)
    if decision.returncode:
        fail(f"plan write denied: {decision.stdout.strip()} {decision.stderr.strip()}")
    items = plan.get("items")
    if not isinstance(items, list):
        fail("plan has no items")
    passed = {v["id"] for v in cases}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("proof_cases"), list):
            fail("plan item lacks proof_cases")
        if item["proof_cases"] and set(item["proof_cases"]) <= passed:
            item["state"] = "proved"
            item["proof_manifest"] = manifest_path.relative_to(ROOT).as_posix()
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, help="local capture with approved golden copies")
    parser.add_argument("--verify-only", action="store_true", help="CI binding check without local frames or plan write")
    args = parser.parse_args()
    intent = intent_id()
    manifest_path = PROOFS / f"{intent}.json"
    plan_path = PLAN / f"{intent}.json"
    require_staged(manifest_path)
    require_staged(plan_path)
    plan, manifest = read(plan_path), read(manifest_path)
    cases = validate(manifest, plan, intent, args.run_dir, verify_only=args.verify_only)
    if args.run_dir is not None and not args.verify_only:
        write_plan(plan_path, plan, manifest_path, cases)
    print("LBE UI PROOF GATE: MANIFEST_BINDING_VALID")

if __name__ == "__main__":
    main()
