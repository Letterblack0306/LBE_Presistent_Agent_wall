from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._gatekeeper_common import require_text

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset({
    "a", "all", "allow", "allows", "an", "and", "are", "be", "custom",
    "does", "ensure", "for", "has", "have", "in", "is", "must", "of",
    "proper", "require", "required", "requires", "rule", "rules", "that",
    "the", "to", "validates", "validate", "validation", "with",
})
_NEGATIVE = frozenset({
    "deny", "denied", "disable", "disabled", "disallow", "forbid",
    "forbidden", "missing", "no", "not", "prevent", "prohibit",
    "prohibited", "reject", "without",
})


@dataclass(frozen=True)
class CatalogEntry:
    pack_id: str
    rule_id: str
    trigger: str = ""
    rationale: str = ""
    source_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "rule_id": self.rule_id,
            "trigger": self.trigger,
            "rationale": self.rationale,
            "source_path": self.source_path,
        }


def source_catalog(workspace_root: Path) -> Sequence[CatalogEntry]:
    files: list[Path] = []
    for directory in (workspace_root / "rules", workspace_root / "rule_packs"):
        if directory.is_dir():
            files.extend(path for path in sorted(directory.glob("*.py")) if path.name != "__init__.py")
    entries: list[CatalogEntry] = []
    for source_path in files:
        try:
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        except (OSError, UnicodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "register_rule":
                continue
            if len(node.args) < 2:
                continue
            pack, rule = literal_string(node.args[0]), literal_string(node.args[1])
            if pack and rule:
                entries.append(CatalogEntry(pack, rule, source_path=source_path.relative_to(workspace_root).as_posix()))
    return entries


def normalize_catalog(raw_entries: Sequence[CatalogEntry | Mapping[str, Any]]) -> list[CatalogEntry]:
    normalized: list[CatalogEntry] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_entries:
        if isinstance(raw, CatalogEntry):
            entry = raw
        elif isinstance(raw, Mapping):
            entry = CatalogEntry(
                require_text(raw.get("pack_id"), "catalog.pack_id"),
                require_text(raw.get("rule_id"), "catalog.rule_id"),
                str(raw.get("trigger") or "").strip(),
                str(raw.get("rationale") or "").strip(),
                str(raw.get("source_path")).strip() if raw.get("source_path") else None,
            )
        else:
            raise TypeError(f"Unsupported catalog entry: {type(raw).__name__}")
        key = (entry.pack_id.casefold(), entry.rule_id.casefold())
        if key not in seen:
            seen.add(key)
            normalized.append(entry)
    return sorted(normalized, key=lambda item: (item.pack_id.casefold(), item.rule_id.casefold()))


def check_catalog(catalog: Sequence[CatalogEntry], *, pack_id: str, rule_id: str, trigger: str) -> dict[str, CatalogEntry | None]:
    for item in catalog:
        if item.pack_id.casefold() == pack_id.casefold() and item.rule_id.casefold() == rule_id.casefold():
            return {"equivalent": item, "conflict": None}
    desired = semantic_tokens(f"{rule_id} {trigger}")
    desired_negative = bool(desired & _NEGATIVE)
    equivalent: tuple[float, CatalogEntry] | None = None
    conflict: tuple[float, CatalogEntry] | None = None
    for item in catalog:
        tokens = semantic_tokens(f"{item.rule_id} {item.trigger} {item.rationale}")
        score = jaccard(desired - _NEGATIVE, tokens - _NEGATIVE)
        item_negative = bool(tokens & _NEGATIVE)
        if score >= 0.80 and desired_negative == item_negative and (equivalent is None or score > equivalent[0]):
            equivalent = (score, item)
        elif score >= 0.60 and desired_negative != item_negative and (conflict is None or score > conflict[0]):
            conflict = (score, item)
    return {"equivalent": equivalent[1] if equivalent else None, "conflict": conflict[1] if conflict else None}


def literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.strip() or None
    return None


def semantic_tokens(value: str) -> set[str]:
    normalized: set[str] = set()
    for token in set(_TOKEN_RE.findall(value.casefold())):
        if token in _STOP:
            continue
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        normalized.add(token)
    return normalized


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left and right else 0.0
