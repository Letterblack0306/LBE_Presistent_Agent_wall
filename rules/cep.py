from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from agent import Context, GovernanceError
from audit_controller import AuditError, RuleResult, register_rule


def _rule(
    ctx: Context,
    params: dict[str, Any],
    rule_id: str,
    logic,
) -> RuleResult:
    try:
        return logic(ctx, params)
    except (GovernanceError, AuditError) as exc:
        return RuleResult(
            rule_id=rule_id,
            status="blocked",
            message=str(exc),
        )
    except Exception as exc:  # pragma: no cover - defensive
        return RuleResult(
            rule_id=rule_id,
            status="failed",
            message=f"{type(exc).__name__}: {exc}",
        )


def rule_cep_manifest_exists(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.manifest_exists"
    requested_roots = set(params.get("roots") or [root.name for root in ctx.roots])
    examined: list[str] = []
    for root in ctx.roots:
        if root.name not in requested_roots:
            continue
        manifest = root.path / "CSXS" / "manifest.xml"
        examined.append(f"{root.name}/CSXS/manifest.xml")
        if not manifest.is_file():
            continue
        try:
            document = ET.parse(manifest)
        except (OSError, UnicodeDecodeError, ET.ParseError) as exc:
            return RuleResult(
                rule_id=rule_id,
                status="blocked",
                message=f"Canonical CEP manifest cannot be parsed: {exc}",
                evidence={"path": f"{root.name}/CSXS/manifest.xml"},
            )
        return RuleResult(
            rule_id=rule_id,
            status="passed",
            message="CEP manifest.xml is present.",
            evidence={
                "path": f"{root.name}/CSXS/manifest.xml",
                "root_element": _local_name(document.getroot().tag),
                "evidence_source": "current_workspace_exact_path",
            },
        )
    return RuleResult(
        rule_id=rule_id,
        status="failed",
        message="CEP manifest.xml is missing.",
        evidence={"examined_paths": examined},
    )


def _selected_roots(ctx: Context, params: dict[str, Any]) -> list[Any]:
    requested = params.get("roots")
    requested_names = set(requested or [])
    selected = [
        root for root in ctx.roots
        if not requested_names or root.name in requested_names
    ]
    found_names = {root.name for root in selected}
    missing = requested_names - found_names
    if missing:
        raise GovernanceError(f"Unknown requested roots: {sorted(missing)}")
    return selected


def _exact_manifests(ctx: Context, params: dict[str, Any]) -> list[tuple[str, Any]]:
    manifests: list[tuple[str, Any]] = []
    for root in _selected_roots(ctx, params):
        path = root.path / "CSXS" / "manifest.xml"
        if path.is_file():
            manifests.append((f"{root.name}/CSXS/manifest.xml", path))
    return manifests


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _parse_manifest(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def _first_descendant_text(root: ET.Element, local_name: str) -> str:
    for element in root.iter():
        if _local_name(element.tag) == local_name:
            return (element.text or "").strip()
    return ""


def _registered_extension_ids(root: ET.Element) -> set[str]:
    registered: set[str] = set()
    for container in root.iter():
        if _local_name(container.tag) != "ExtensionList":
            continue
        for child in container:
            if _local_name(child.tag) != "Extension":
                continue
            extension_id = (child.attrib.get("Id") or "").strip()
            if extension_id:
                registered.add(extension_id)
    return registered


register_rule(
    "cep",
    "cep.manifest_exists",
    lambda ctx, p: _rule(
        ctx,
        p,
        "cep.manifest_exists",
        rule_cep_manifest_exists,
    ),
)


def rule_cep_host_version(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.host_version"

    manifests = _exact_manifests(ctx, params)
    if not manifests:
        return RuleResult(
            rule_id=rule_id,
            status="not_applicable",
            message="manifest.xml not found; cannot verify host version.",
        )

    examined: list[str] = []
    for virtual_path, manifest in manifests:
        try:
            document = _parse_manifest(manifest)
        except (OSError, UnicodeDecodeError, ET.ParseError) as exc:
            return RuleResult(
                rule_id=rule_id,
                status="blocked",
                message=f"Could not read manifest: {exc}",
                evidence={"path": virtual_path},
            )

        examined.append(virtual_path)

        for host in document.iter():
            if _local_name(host.tag) != "Host":
                continue
            host_name = (host.attrib.get("Name") or "").strip()
            version = (host.attrib.get("Version") or host.attrib.get("MinVersion") or "").strip()
            valid_version = re.fullmatch(
                r"(?:\d+(?:\.\d+){1,3}|\[\d+(?:\.\d+){1,3},\s*\d+(?:\.\d+){1,3}\])",
                version,
            )
            if host_name and re.fullmatch(r"[A-Za-z0-9_.-]+", host_name) and valid_version:
                return RuleResult(
                    rule_id=rule_id,
                    status="passed",
                    message="Canonical CEP manifest declares a valid host identity and version.",
                    evidence={
                        "path": virtual_path,
                        "host_name": host_name,
                        "version": version,
                        "evidence_source": "current_workspace_exact_path",
                    },
                )

    return RuleResult(
        rule_id=rule_id,
        status="failed",
        message="Canonical CEP manifest does not declare a valid host identity and version.",
        evidence={"examined_paths": examined},
    )


register_rule(
    "cep",
    "cep.host_version",
    lambda ctx, p: _rule(
        ctx,
        p,
        "cep.host_version",
        rule_cep_host_version,
    ),
)


def rule_cep_debug_mode(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.debug_mode"

    max_hits = 20
    skipped_dirs = {".git", ".lbe", "node_modules", "dist", "build", "coverage", "__pycache__"}
    hits: list[dict[str, Any]] = []
    for root in _selected_roots(ctx, params):
        for path in root.path.rglob("*"):
            if not path.is_file() or any(part in skipped_dirs for part in path.relative_to(root.path).parts):
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "playerdebugmode" not in content.lower():
                continue
            hits.append({
                "path": f"{root.name}/{path.relative_to(root.path).as_posix()}",
                "score": 1,
            })
            if len(hits) >= max_hits:
                break
        if len(hits) >= max_hits:
            break

    if not hits:
        return RuleResult(
            rule_id=rule_id,
            status="blocked",
            message=(
                "PlayerDebugMode reference was not found in the selected "
                "workspace. This does not prove host debug mode is disabled."
            ),
            evidence={
                "roots_checked": [root.name for root in _selected_roots(ctx, params)],
                "evidence_source": "current_workspace_bounded_scan",
            },
            severity="warning",
            required=False,
            fast_fail=False,
        )

    return RuleResult(
        rule_id=rule_id,
        status="passed",
        message="Indexed workspace references PlayerDebugMode.",
        evidence={
            "hits": hits,
            "evidence_source": "current_workspace_bounded_scan",
            "note": (
                "Many PlayerDebugMode references were found."
                if len(hits) >= 10
                else None
            ),
        },
        severity="warning",
        required=False,
        fast_fail=False,
    )


register_rule(
    "cep",
    "cep.debug_mode",
    lambda ctx, p: _rule(
        ctx,
        p,
        "cep.debug_mode",
        rule_cep_debug_mode,
    ),
)


def rule_cep_no_zip_in_repo(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.no_zip_in_repo"

    archive_extensions = {".zxp", ".zip", ".7z", ".rar", ".tar", ".gz"}
    skipped_dirs = {".git", ".lbe", "node_modules", "dist", "build", "coverage", "__pycache__"}
    hits: list[str] = []
    for root in _selected_roots(ctx, params):
        for path in root.path.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in archive_extensions:
                continue
            if any(part in skipped_dirs for part in path.relative_to(root.path).parts):
                continue
            hits.append(f"{root.name}/{path.relative_to(root.path).as_posix()}")
            if len(hits) >= 10:
                break
        if len(hits) >= 10:
            break

    if not hits:
        return RuleResult(
            rule_id=rule_id,
            status="passed",
            message="No packaging archives were found in the selected workspace roots.",
            evidence={"evidence_source": "current_workspace_bounded_scan"},
        )

    return RuleResult(
        rule_id=rule_id,
        status="failed",
        message="Packaging archives were found in the workspace.",
        evidence={
            "hits": hits,
            "evidence_source": "current_workspace_bounded_scan",
        },
    )


register_rule(
    "cep",
    "cep.no_zip_in_repo",
    lambda ctx, p: _rule(
        ctx,
        p,
        "cep.no_zip_in_repo",
        rule_cep_no_zip_in_repo,
    ),
)


def rule_cep_symlink_free(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.symlink_free"

    requested_roots = params.get("roots")

    selected_roots = [
        root
        for root in ctx.roots
        if requested_roots is None
        or root.name in requested_roots
    ]

    requested_root_names = set(requested_roots or [])
    selected_root_names = {
        root.name
        for root in selected_roots
    }

    missing_roots = requested_root_names - selected_root_names

    if missing_roots:
        raise GovernanceError(
            f"Unknown requested roots: {sorted(missing_roots)}"
        )

    skipped_dirs = {
        ".git",
        ".lbe",
        "node_modules",
        "dist",
        "build",
        "coverage",
        "release-public",
        "release-exec",
        "__pycache__",
    }

    symlinks: list[dict[str, str]] = []
    unreadable: list[str] = []

    for root in selected_roots:
        pending = [root.path]

        while pending:
            current = pending.pop()

            try:
                entries = list(current.iterdir())
            except (OSError, PermissionError) as exc:
                unreadable.append(
                    f"{current}: {type(exc).__name__}: {exc}"
                )
                continue

            for entry in entries:
                if entry.name in skipped_dirs:
                    continue

                try:
                    if entry.is_symlink():
                        try:
                            target = str(
                                entry.resolve(strict=False)
                            )
                        except OSError:
                            target = "unresolved"

                        try:
                            relative = entry.relative_to(root.path)
                            display_path = (
                                f"{root.name}/{relative.as_posix()}"
                            )
                        except ValueError:
                            display_path = str(entry)

                        symlinks.append(
                            {
                                "path": display_path,
                                "target": target,
                            }
                        )

                        if len(symlinks) >= 50:
                            break

                    elif entry.is_dir():
                        pending.append(entry)

                except (OSError, PermissionError) as exc:
                    unreadable.append(
                        f"{entry}: {type(exc).__name__}: {exc}"
                    )

            if len(symlinks) >= 50:
                break

        if len(symlinks) >= 50:
            break

    if symlinks:
        return RuleResult(
            rule_id=rule_id,
            status="failed",
            message=f"{len(symlinks)} symbolic link(s) found.",
            evidence={
                "symlinks": symlinks,
                "truncated": len(symlinks) >= 50,
                "unreadable_paths": unreadable[:20],
            },
            severity="error",
            required=True,
            fast_fail=False,
        )

    if unreadable:
        return RuleResult(
            rule_id=rule_id,
            status="blocked",
            message=(
                "No symbolic links were found in readable paths, "
                "but some directories could not be inspected."
            ),
            evidence={
                "unreadable_paths": unreadable[:20],
                "unreadable_count": len(unreadable),
            },
            severity="warning",
            required=False,
            fast_fail=False,
        )

    return RuleResult(
        rule_id=rule_id,
        status="passed",
        message="No symbolic links were found.",
        evidence={
            "roots_checked": [
                root.name
                for root in selected_roots
            ],
        },
        severity="error",
        required=True,
        fast_fail=False,
    )


register_rule(
    "cep",
    "cep.symlink_free",
    lambda ctx, p: _rule(
        ctx,
        p,
        "cep.symlink_free",
        rule_cep_symlink_free,
    ),
)


def rule_cep_menubar_extension(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.menubar_extension"
    supported_ui_types = {"Panel", "Modeless", "ModalDialog"}
    manifests = _exact_manifests(ctx, params)
    if not manifests:
        return RuleResult(rule_id=rule_id, status="not_applicable", message="Canonical CEP manifest is absent.")

    examined: list[str] = []
    for virtual_path, manifest in manifests:
        try:
            document = _parse_manifest(manifest)
        except (OSError, UnicodeDecodeError, ET.ParseError) as exc:
            return RuleResult(rule_id=rule_id, status="blocked", message=f"Could not parse canonical manifest: {exc}", evidence={"path": virtual_path})
        examined.append(virtual_path)
        registered = _registered_extension_ids(document)
        for extension in document.iter():
            if _local_name(extension.tag) != "Extension":
                continue
            extension_id = (extension.attrib.get("Id") or "").strip()
            if extension_id not in registered:
                continue
            for dispatch in extension.iter():
                if _local_name(dispatch.tag) != "DispatchInfo":
                    continue
                ui_type = _first_descendant_text(dispatch, "Type")
                menu = _first_descendant_text(dispatch, "Menu")
                if ui_type in supported_ui_types and menu:
                    return RuleResult(
                        rule_id=rule_id,
                        status="passed",
                        message="Registered CEP extension has a supported UI type and non-empty Menu value.",
                        evidence={
                            "path": virtual_path,
                            "extension_id": extension_id,
                            "ui_type": ui_type,
                            "menu": menu,
                            "evidence_source": "current_workspace_exact_path",
                        },
                    )
    return RuleResult(
        rule_id=rule_id,
        status="failed",
        message="No registered CEP extension has both a supported UI type and a non-empty Menu value.",
        evidence={"examined_paths": examined},
    )


register_rule(
    "cep",
    "cep.menubar_extension",
    lambda ctx, p: _rule(ctx, p, "cep.menubar_extension", rule_cep_menubar_extension),
)
