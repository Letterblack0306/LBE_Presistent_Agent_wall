from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

EXCLUDED_DIR_NAMES = frozenset({
    ".git", ".hg", ".svn", ".lbe", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "vendor", "vendors",
    "dist", "build", "generated", "archive", "archives", "backup",
    "backups", "release", "release-public", "release-exec", "site-packages",
    ".venv", "venv",
})
EXCLUDED_TOP_LEVEL = frozenset({"tests", "test", "examples", "docs"})


@dataclass(frozen=True)
class PackageEvidence:
    package_path: str
    expected_init_path: str
    namespace_package: bool
    module_paths: tuple[str, ...]
    module_hashes: tuple[str, ...]

    def refs(self, workspace_id: str) -> list[str]:
        return [
            f"workspace:{workspace_id}:{path}#sha256:{digest}"
            for path, digest in zip(self.module_paths, self.module_hashes, strict=True)
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "package_path": self.package_path,
            "expected_init_path": self.expected_init_path,
            "namespace_package": self.namespace_package,
            "module_paths": list(self.module_paths),
            "module_hashes": list(self.module_hashes),
        }


def inspect_python_packages(
    root: Path,
    *,
    namespace_packages: set[str],
    excluded_paths: set[str],
) -> list[PackageEvidence]:
    modules: list[Path] = []
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda item: item.name.casefold())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            if is_excluded(entry, root, excluded_paths):
                continue
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    pending.append(entry)
                elif entry.is_file() and entry.suffix.casefold() == ".py" and entry.name != "__init__.py":
                    modules.append(entry)
            except (OSError, PermissionError):
                continue

    package_dirs: set[Path] = set()
    for module in modules:
        current = module.parent
        while current != root:
            if is_excluded(current, root, excluded_paths):
                break
            package_dirs.add(current)
            if current.parent == root:
                break
            current = current.parent

    evidence: list[PackageEvidence] = []
    for package_dir in sorted(package_dirs, key=lambda item: item.relative_to(root).as_posix().casefold()):
        relative = package_dir.relative_to(root).as_posix()
        direct = sorted(
            (child for child in package_dir.iterdir() if child.is_file() and not child.is_symlink()
             and child.suffix.casefold() == ".py" and child.name != "__init__.py"),
            key=lambda item: item.name.casefold(),
        )
        descendants = sorted(
            (module for module in modules if package_dir == module.parent or package_dir in module.parents),
            key=lambda item: item.relative_to(root).as_posix().casefold(),
        )
        selected = direct or descendants
        if not selected:
            continue
        evidence.append(PackageEvidence(
            package_path=relative,
            expected_init_path=f"{relative}/__init__.py",
            namespace_package=relative in namespace_packages,
            module_paths=tuple(item.relative_to(root).as_posix() for item in selected),
            module_hashes=tuple(sha256_file(item) for item in selected),
        ))
    return evidence


def proposal_scope(packages: Sequence[PackageEvidence]) -> list[str]:
    return sorted({item.expected_init_path for item in packages if not item.namespace_package})


def evidence_refs(packages: Sequence[PackageEvidence], workspace_id: str) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for item in packages:
        for ref in item.refs(workspace_id):
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
    return refs


def is_excluded(path: Path, root: Path, explicit: set[str]) -> bool:
    relative = path.relative_to(root).as_posix()
    if relative in explicit or any(relative.startswith(item + "/") for item in explicit if item):
        return True
    parts = path.relative_to(root).parts
    if parts and parts[0].casefold() in EXCLUDED_TOP_LEVEL:
        return True
    return any(part.casefold() in EXCLUDED_DIR_NAMES for part in parts)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
