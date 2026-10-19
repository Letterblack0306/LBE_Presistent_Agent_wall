"""Pre-write intent check and proposed-intent recording over the EXISTING implementation gate.

No second validator and no second intent system:

* ``check_paths`` runs the workspace's own ``scripts/check-implementation-gate.py --proposed``
  (the same checks as the commit-time run) and translates its verdict into the shared
  response contract: reason, what was checked, what is missing, what can be investigated
  read-only, and the exact question.
* ``record_proposed_intent`` appends one ``STATUS: PROPOSED`` block, in the existing format,
  to the ledger the gate file already names. A PROPOSED intent never passes the gate and
  the gate file's ``active_intent`` is never changed here, so recording an answer cannot
  authorize a change: the owner decides.

Enforcement is opt-in per workspace: ``intent_and_structure_governance.enforce_before_write``
must be true in that workspace's own gate file. A workspace without the gate script (an
installed runtime workspace) is unaffected.
"""
from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

INTENT_GATE_BLOCKED = "INTENT_GATE_BLOCKED"
_GATE_REL = Path(".lbe") / "governance" / "implementation-gates.json"
_SCRIPT_REL = Path("scripts") / "check-implementation-gate.py"
_MAX_PATHS = 20
_MAX_REASON = 400


@dataclass(frozen=True)
class IntentBlock:
    code: str
    detail: str
    paths: tuple[str, ...]
    checked: str
    missing: str
    investigate: str
    ask: str
    next_step: str

    def message(self) -> str:
        return (
            f"{self.code}: {self.detail}. No valid intent covers {', '.join(self.paths)}. "
            f"Only the owner can authorize it. {self.ask}"
        )

    def output(self) -> dict[str, object]:
        return {
            "satisfiable_by": "owner",
            "next_step": self.next_step,
            "allowed_paths": [],
            "proposed_paths": list(self.paths),
            "checked": self.checked,
            "missing": self.missing,
            "investigate": self.investigate,
            "ask": self.ask,
        }


def _gate_data(root: Path) -> dict | None:
    try:
        data = json.loads((root / _GATE_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def enforced(root: Path) -> bool:
    """True only for a workspace whose own gate file asks for the check before a write.

    Once a workspace has opted in, a missing script or unreadable gate state blocks writes
    (fail closed); a workspace with no gate file at all is not covered."""
    if not (root / _GATE_REL).is_file():
        return False
    data = _gate_data(root)
    if data is None:
        return True
    section = data.get("intent_and_structure_governance")
    return isinstance(section, dict) and section.get("enforce_before_write") is True


def _normalize(raw: object) -> str | None:
    """A plain workspace-relative posix path, or None when it is not one (absolute, drive
    letter, traversal, control or line-break characters). Model-chosen paths reach here."""
    text = str(raw).replace("\\", "/").strip()
    if not text or any(not ch.isprintable() for ch in text):
        return None
    if text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return None
    norm = posixpath.normpath(text)
    if norm in {".", ".."} or norm.startswith("../"):
        return None
    return norm


def _shown(items: list[str]) -> tuple[str, ...]:
    return tuple("".join(ch if ch.isprintable() else "?" for ch in item)[:80] for item in items[:3])


def _ledger_path(root: Path, data: dict) -> Path | None:
    section = data.get("intent_and_structure_governance")
    rel = str(section.get("intent_ledger", "")).strip() if isinstance(section, dict) else ""
    if not rel:
        return None
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def _field(block: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:[ \t]*(.+)$", block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _active_summary(root: Path) -> tuple[str, str, list[str]]:
    data = _gate_data(root) or {}
    active = data.get("active_intent")
    intent_id = str(active.get("intent_id", "")).strip() if isinstance(active, dict) else ""
    ledger = _ledger_path(root, data)
    if not intent_id or ledger is None:
        return intent_id, "", []
    text = ledger.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"^## INTENT {re.escape(intent_id)}\s*$([\s\S]*?)(?=^## INTENT |\Z)", text, re.MULTILINE)
    if not match:
        return intent_id, "not registered", []
    prefixes = [p.strip() for p in _field(match.group(1), "EXPECTED_PATH_PREFIXES").split(",") if p.strip()]
    return intent_id, _field(match.group(1), "STATUS"), prefixes


def _block_from(root: Path, code: str, detail: str, paths: tuple[str, ...]) -> IntentBlock:
    intent_id, status, prefixes = _active_summary(root)
    target = ", ".join(paths)
    checked = (
        f"active intent {intent_id or 'none'} ({status or 'unknown'}) "
        f"covers {', '.join(prefixes) or 'no paths'}"
    )
    investigate = "docs/governance/PROJECT_INTENT_LEDGER.md and .lbe/governance/implementation-gates.json (read-only)"
    ask_record = f"Why change {target}? Answer with /intent <reason> (a proposal only; the owner decides)."
    if code == "BLOCKED_INTENT_SCOPE_MISMATCH":
        missing = f"an authorized intent that covers {target}"
        ask = ask_record
    elif code in {"BLOCKED_UNRESOLVED_TARGET", "BLOCKED_PATH_ESCAPE"}:
        missing = "a plain workspace-relative path for the write"
        ask = "Which file should be changed? Name one path inside the workspace."
    elif code == "BLOCKED_GATE_CLOSED":
        missing = "an open implementation slice with an authorized intent"
        ask = f"Should the owner open a slice for {target}? Only the owner can open one."
    elif code in {"BLOCKED_INTENT", "BLOCKED_INTENT_GATE_MISMATCH", "BLOCKED_MISSING_INTENT"}:
        missing = "an ACTIVE or AUTHORIZED intent registered in the ledger for the active slice"
        ask = f"Which intent authorizes changing {target}? The owner has to activate one. {ask_record}"
    elif code == "BLOCKED_OWNER_UNDECLARED":
        missing = f"an EXISTING_OWNER on intent {intent_id or 'none'}"
        ask = f"Who owns {target}? Only the owner can add EXISTING_OWNER to the intent."
    elif code in {"BLOCKED_STRUCTURE_DRIFT", "BLOCKED_UNINDEXED_STRUCTURE", "BLOCKED_MISSING_PROJECT_INDEX"}:
        missing = "the project index entry, or a matching index revision, for this structure"
        ask = f"Should {target} be added to PROJECT_INDEX.md? Only the owner can update the index revision."
    else:
        missing = detail or "a passing implementation gate"
        ask = f"What must change in the implementation gate before {target} can be written? Only the owner can change it."
    next_step = f"stop writing and ask the owner to authorize an intent that covers {target} (the owner can reply /intent <reason> to record one)"
    return IntentBlock(code, detail, paths, checked, missing, investigate, ask, next_step)


def check_paths(root: Path, paths: tuple[str, ...] | list[str]) -> IntentBlock | None:
    """The existing gate's verdict for paths about to be written; None when allowed or not enforced."""
    root = Path(root)
    items = [str(item) for item in paths if str(item).strip()]
    if not items or not enforced(root):
        return None
    normalized: list[str] = []
    unresolved: list[str] = []
    for item in items:
        norm = None if item.startswith("<") else _normalize(item)
        (normalized if norm else unresolved).append(norm or item)
    if unresolved:
        return _block_from(root, "BLOCKED_UNRESOLVED_TARGET", "the write target is not a plain workspace path", _shown(unresolved))
    real = tuple(dict.fromkeys(normalized))
    script = root / _SCRIPT_REL
    if not script.is_file():
        return _block_from(root, "BLOCKED_GATE", "the implementation gate script is missing", real)
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--proposed", *real],
            cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=60.0, check=False,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return _block_from(root, "BLOCKED_GATE", f"the implementation gate could not run ({type(exc).__name__})", real)
    if result.returncode == 0:
        return None
    text = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
    match = re.search(r"BLOCKED: (BLOCKED_[A-Z_]+)(?:: (.*))?$", text, re.MULTILINE)
    code = match.group(1) if match else "BLOCKED_GATE"
    if match:
        detail = (match.group(2) or "").strip()
    else:
        last = text.splitlines()[-1] if text else "gate failed"
        detail = last.replace("LBE IMPLEMENTATION GATE: BLOCKED:", "").strip()[:200]
    return _block_from(root, code, detail, real)


def record_proposed_intent(root: Path, *, reason: str, paths: tuple[str, ...] | list[str]) -> dict[str, str]:
    """Append one PROPOSED intent block to the ledger the gate file names. Authorizes nothing."""
    root = Path(root)
    data = _gate_data(root)
    if data is None:
        raise ValueError("this workspace has no readable implementation gate; nothing to record against")
    ledger = _ledger_path(root, data)
    if ledger is None:
        raise ValueError("the gate file does not name an existing intent ledger inside this workspace")
    clean_reason = " ".join(str(reason).split())[:_MAX_REASON]
    if len(clean_reason) < 3:
        raise ValueError("an intent needs a reason")
    normalized = [_normalize(item) for item in paths]
    if not normalized or any(p is None or "," in p for p in normalized):
        raise ValueError("an intent needs plain relative workspace paths")
    clean_paths = tuple(dict.fromkeys(p for p in normalized if p))[:_MAX_PATHS]
    raw = ledger.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    stamp = datetime.now(timezone.utc)
    digest = hashlib.sha256((clean_reason + "|" + ",".join(clean_paths)).encode("utf-8")).hexdigest()[:8]
    intent_id = f"LBE-INTENT-PROPOSED-{stamp:%Y%m%d%H%M%S}-{digest}"
    slice_id = str(data.get("active_slice", "")).strip() or "UNDECLARED"
    block = newline.join([
        "",
        f"## INTENT {intent_id}",
        "",
        "STATUS: PROPOSED",
        f"REQUEST: {clean_reason}",
        f"MACHINE_SLICE: {slice_id}",
        f"EXPECTED_PATH_PREFIXES: {','.join(clean_paths)}",
        "AUTHORIZATION: NONE. Recorded from a user answer; it grants no authority. The owner must add "
        "EXISTING_OWNER, set STATUS to AUTHORIZED or ACTIVE, and point active_intent in "
        ".lbe/governance/implementation-gates.json at this id.",
        "RESULT: PENDING_OWNER_DECISION",
        "",
    ])
    if not text.endswith(("\n", "\r")):
        block = newline + block
    handle, temp_name = tempfile.mkstemp(prefix=".lbe-ledger-", dir=str(ledger.parent))
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(raw + block.encode("utf-8"))
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_name, ledger)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return {
        "intent_id": intent_id,
        "status": "PROPOSED",
        "ledger": ledger.relative_to(root.resolve()).as_posix(),
        "paths": ",".join(clean_paths),
    }
