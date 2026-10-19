from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".lbe" / "governance" / "implementation-gates.json"

DOC_ALLOW_PREFIXES = (".agent/", "docs/")
DOC_ALLOW_SUFFIXES = (".md", ".mdx", ".rst", ".txt")


def fail(message: str) -> None:
    print(f"LBE IMPLEMENTATION GATE: BLOCKED: {message}", file=sys.stderr)
    raise SystemExit(1)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail(f"cannot inspect staged changes: {exc}")


# Set by `--proposed PATH...`: validate paths that are about to be written, before any
# staging. Same checks as the commit-time run, except the two that only make sense
# against a staged change set (the staged diff check and "new file needs an index update").
PROPOSED: tuple[str, ...] | None = None


def _staged_paths() -> tuple[str, ...]:
    if PROPOSED is not None:
        return PROPOSED
    result = _git("diff", "--cached", "--name-only", "--diff-filter=ACMRD")
    if result.returncode != 0:
        fail(f"cannot enumerate staged paths: {result.stderr.strip() or 'git diff failed'}")
    return tuple(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())


def _documentation_only_commit_allowed() -> bool:
    staged = _staged_paths()
    if not staged:
        fail("implementation is locked and no staged documentation paths were found")

    disallowed = tuple(
        path
        for path in staged
        if not path.startswith(DOC_ALLOW_PREFIXES)
        or not path.lower().endswith(DOC_ALLOW_SUFFIXES)
    )
    if disallowed:
        fail(
            "implementation is locked; documentation-only allowance rejected staged path(s): "
            + ", ".join(disallowed)
        )

    diff_check = _git("diff", "--cached", "--check") if PROPOSED is None else None
    if diff_check is not None and diff_check.returncode != 0:
        detail = (diff_check.stdout + diff_check.stderr).strip()
        fail(f"documentation-only staged diff failed git diff --cached --check: {detail}")

    return True


def _structure_for(path: str) -> str:
    if "/" in path:
        return path.split("/", 1)[0] + "/"
    return path


def _staged_index_revision() -> str:
    """The revision `active_intent.index_revision` must equal: SHA-256 (upper-case hex) of the RAW BYTES of the
    STAGED PROJECT_INDEX.md blob, i.e. `git show :PROJECT_INDEX.md | sha256sum`. No text decoding or newline
    translation is applied. This is the only definition; the validator and --print-index-revision share it."""
    try:
        staged_index = subprocess.run(
            ["git", "show", ":PROJECT_INDEX.md"],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail(f"cannot inspect staged changes: {exc}")
    if staged_index.returncode != 0:
        fail("BLOCKED_STRUCTURE_DRIFT: PROJECT_INDEX.md must be staged before mutation")
    return hashlib.sha256(staged_index.stdout).hexdigest().upper()


def _intent_block(ledger: str, intent_id: str) -> str:
    match = re.search(
        rf"^## INTENT {re.escape(intent_id)}\s*$([\s\S]*?)(?=^## INTENT |\Z)",
        ledger,
        re.MULTILINE,
    )
    return match.group(1) if match else ""


def _field(block: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:[ \t]*(.+)$", block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _validate_intent_and_structure(data: dict[str, object], staged: tuple[str, ...]) -> None:
    policy = data.get("intent_and_structure_governance") or {}
    if policy.get("required") is not True:
        fail("intent_and_structure_governance.required must be true")

    index_path = ROOT / str(policy.get("root_index", ""))
    ledger_path = ROOT / str(policy.get("intent_ledger", ""))
    if not index_path.is_file():
        fail("BLOCKED_MISSING_PROJECT_INDEX")
    if not ledger_path.is_file():
        fail("BLOCKED_MISSING_INTENT")

    active = data.get("active_intent") or {}
    intent_id = str(active.get("intent_id", "")).strip()
    if not intent_id:
        fail("BLOCKED_INTENT_GATE_MISMATCH: active_intent.intent_id is missing")

    ledger = ledger_path.read_text(encoding="utf-8")
    block = _intent_block(ledger, intent_id)
    if not block:
        fail(f"BLOCKED_INTENT: {intent_id} is not registered")
    if _field(block, "STATUS") not in {"ACTIVE", "AUTHORIZED"}:
        fail(f"BLOCKED_INTENT: {intent_id} is not active or authorized")
    if _field(block, "MACHINE_SLICE") != str(data.get("active_slice")):
        fail("BLOCKED_INTENT_GATE_MISMATCH: intent machine slice does not match active_slice")
    if not _field(block, "EXISTING_OWNER"):
        fail("BLOCKED_OWNER_UNDECLARED")

    expected = tuple(
        item.strip()
        for item in _field(block, "EXPECTED_PATH_PREFIXES").split(",")
        if item.strip()
    )
    if not expected:
        fail("BLOCKED_INTENT_SCOPE_MISMATCH: expected path scope is empty")

    index = index_path.read_text(encoding="utf-8")
    revision = _staged_index_revision()
    declared_revision = str(active.get("index_revision", "")).strip().upper()
    if declared_revision != revision:
        fail("BLOCKED_STRUCTURE_DRIFT: active_intent.index_revision does not match PROJECT_INDEX.md")

    for path in staged:
        if not any(prefix == "*" or path == prefix or path.startswith(prefix) for prefix in expected):
            fail(f"BLOCKED_INTENT_SCOPE_MISMATCH: staged path is outside intent: {path}")
        head_check = _git("cat-file", "-e", f"HEAD:{path}")
        structure = _structure_for(path)
        if head_check.returncode != 0 and f"`{structure}`" not in index and f"`{path}`" not in index:
            fail(f"BLOCKED_UNINDEXED_STRUCTURE: {structure}")

        head_check = _git("cat-file", "-e", f"HEAD:{path}")
        if PROPOSED is None and head_check.returncode != 0 and "PROJECT_INDEX.md" not in staged:
            fail(f"BLOCKED_STRUCTURE_DRIFT: new structure requires PROJECT_INDEX.md update: {path}")


def main() -> None:
    if not GATE.is_file():
        fail(f"missing gate file: {GATE.relative_to(ROOT)}")

    try:
        data = json.loads(GATE.read_text(encoding="utf-8"))
    except Exception as exc:  # fail closed on malformed governance state
        fail(f"cannot parse gate file: {exc}")

    if not data.get("active_plan"):
        fail("active_plan is not declared")
    status = str(data.get("status", "")).upper()
    if not data.get("active_phase") or not data.get("active_slice"):
        fail("active phase/slice is not declared")

    if status in {"PASS", "CLOSED"} and PROPOSED is not None:
        fail("BLOCKED_GATE_CLOSED: no open implementation slice covers a write to " + ", ".join(PROPOSED))

    if status in {"PASS", "CLOSED"}:
        active = data.get("active_intent") or {}
        intent_id = str(active.get("intent_id", "")).strip()
        ledger_path = ROOT / str((data.get("intent_and_structure_governance") or {}).get("intent_ledger", ""))
        if not intent_id or not ledger_path.is_file():
            fail("BLOCKED_CLOSURE: completed gate must retain a registered active_intent and intent ledger")
        block = _intent_block(ledger_path.read_text(encoding="utf-8"), intent_id)
        if not block:
            fail(f"BLOCKED_CLOSURE: completed intent {intent_id} is not registered")
        if _field(block, "STATUS") != "COMPLETED" or _field(block, "RESULT") != "PASS":
            fail(f"BLOCKED_CLOSURE: intent {intent_id} must be COMPLETED with RESULT PASS")
        checkpoint = _field(block, "COMPLETION_CHECKPOINT")
        if not checkpoint or not (ROOT / checkpoint).is_file():
            fail(f"BLOCKED_CLOSURE: completion checkpoint is missing for {intent_id}")
        if str(data.get("active_slice", "")).upper() not in {"NONE", "COMPLETED"}:
            fail("BLOCKED_CLOSURE: closed gate must not retain an executable active slice")
        print(
            "LBE IMPLEMENTATION GATE: PASS — closed gate; "
            f"last_intent={intent_id} checkpoint={checkpoint}"
        )
        return

    if status != "OPEN":
        fail(f"current gate status is {data.get('status')!r}, expected 'OPEN', 'PASS', or 'CLOSED'")

    staged = _staged_paths()
    if data.get("intent_and_structure_governance", {}).get("intent_required_before_mutation") is True:
        if not staged:
            print("LBE IMPLEMENTATION GATE: NO_STAGED_CHANGES; no commit validation required")
            return
        _validate_intent_and_structure(data, staged)

    if data.get("implementation_allowed") is not True:
        if _documentation_only_commit_allowed():
            print(
                "LBE IMPLEMENTATION GATE: PASS — documentation-only exception; "
                f"phase={data['active_phase']} slice={data['active_slice']} implementation_allowed=false"
            )
            return
        fail("implementation_allowed is not true")

    if data.get("next_phase_locked") is not True:
        fail("next_phase_locked must remain true while the current slice is active")

    blocking = set(data.get("blocking_statuses", []))
    required = {"FAIL", "UNVERIFIED", "DOCUMENT_CONFLICT", "MISSING_EVIDENCE"}
    if not required.issubset(blocking):
        fail("blocking_statuses does not contain all mandatory fail-closed states")

    rules = data.get("rules") or {}
    for key in (
        "one_active_slice",
        "no_next_phase_without_pass",
        "no_parallel_architecture",
        "existing_owner_audit_required",
        "reuse_evaluation_required",
        "architecture_change_requires_user_authorization",
        "checkpoint_required_before_advance",
        "fail_closed",
    ):
        if rules.get(key) is not True:
            fail(f"mandatory rule disabled: {key}")

    print(
        "LBE IMPLEMENTATION GATE: PASS — "
        f"phase={data['active_phase']} slice={data['active_slice']} next_phase_locked=true"
    )


if __name__ == "__main__":
    if "--print-index-revision" in sys.argv:
        # Read-only: prints the value the gate file's active_intent.index_revision must hold for the
        # index as currently staged. It changes nothing; the owner records it.
        print(_staged_index_revision())
        raise SystemExit(0)
    if "--proposed" in sys.argv:
        import posixpath

        _paths = []
        for item in sys.argv[sys.argv.index("--proposed") + 1:]:
            if not item.strip():
                continue
            _norm = posixpath.normpath(item.replace("\\", "/").strip())
            if (
                _norm in {".", ".."}
                or _norm.startswith(("../", "/"))
                or re.match(r"^[A-Za-z]:", _norm)
                or any(not ch.isprintable() for ch in _norm)
            ):
                fail(f"BLOCKED_PATH_ESCAPE: not a plain workspace-relative path: {item!r}")
            _paths.append(_norm)
        _paths = tuple(_paths)
        if not _paths:
            fail("--proposed needs at least one path")
        PROPOSED = _paths
    main()
