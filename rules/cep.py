from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from agent import Context, GovernanceError, inspect_file, search_workspace
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



def _parse_host_version(content: str) -> bool:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return False
    for elem in root.iter():
        if elem.tag.endswith('Host'):
            if any(elem.attrib.get(attr) for attr in ('Version', 'MinVersion', 'MaxVersion')):
                return True
    return False


def _parse_menubar_extension(content: str) -> bool:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return False
    for elem in root.iter():
        if elem.tag.endswith('Menu') or elem.tag.endswith('Menubar'):
            if elem.text and elem.text.strip():
                return True
            if len(elem) > 0:
                return True
    return False



def rule_cep_manifest_exists(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.manifest_exists"
    workspace_root = params.get("workspace_root")

    if workspace_root:
        root = Path(workspace_root).expanduser().resolve()
        if root.exists() and root.is_dir():
            for candidate in root.rglob("CSXS/manifest.xml"):
                try:
                    if candidate.is_file():
                        return RuleResult(
                            rule_id=rule_id,
                            status="passed",
                            message="CEP manifest.xml is present.",
                            evidence={
                                "path": str(candidate),
                                "relative_path": candidate.relative_to(root).as_posix(),
                                "preview": candidate.read_text(encoding="utf-8", errors="ignore")[:400],
                            },
                        )
                except (OSError, PermissionError):
                    continue

    result = search_workspace(
        ctx,
        "CSXS/manifest.xml",
        max_results=10,
        extensions=[".xml"],
        roots=params.get("roots"),
    )

    if result.get("outcome") != "matches_found":
        return RuleResult(
            rule_id=rule_id,
            status="failed",
            message="CEP manifest.xml is missing.",
            evidence={
                "searched_roots": result.get("searched_roots"),
            },
        )

    best = result["results"][0]

    try:
        content = inspect_file(
            ctx,
            best["path"],
        ).get("content", "")
    except Exception as exc:
        return RuleResult(
            rule_id=rule_id,
            status="failed",
            message=f"Could not read manifest: {exc}",
        )

    return RuleResult(
        rule_id=rule_id,
        status="passed",
        message="CEP manifest.xml is present.",
        evidence={
            "path": best["path"],
            "preview": content[:400],
        },
    )


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
    workspace_root = params.get("workspace_root")

    if workspace_root:
        root = Path(workspace_root).expanduser().resolve()
        if root.exists() and root.is_dir():
            for candidate in root.rglob("manifest.xml"):
                try:
                    if candidate.is_file():
                        content = candidate.read_text(encoding="utf-8", errors="ignore")
                        if _parse_host_version(content):
                            return RuleResult(
                                rule_id=rule_id,
                                status="passed",
                                message="manifest.xml contains host version metadata.",
                                evidence={
                                    "path": str(candidate),
                                    "relative_path": candidate.relative_to(root).as_posix(),
                                    "preview": content[:500],
                                },
                            )
                except (OSError, PermissionError):
                    continue

    result = search_workspace(
        ctx,
        "manifest.xml",
        max_results=50,
        extensions=[".xml"],
        roots=params.get("roots"),
    )

    if result.get("outcome") != "matches_found":
        return RuleResult(
            rule_id=rule_id,
            status="not_applicable",
            message="manifest.xml not found; cannot verify host version.",
        )

    for item in result.get("results", []):
        try:
            content = inspect_file(
                ctx,
                item["path"],
            ).get("content", "")
        except Exception:
            continue

        if _parse_host_version(content):
            return RuleResult(
                rule_id=rule_id,
                status="passed",
                message="manifest.xml contains host version metadata.",
                evidence={
                    "path": item["path"],
                    "preview": content[:500],
                },
            )

    return RuleResult(
        rule_id=rule_id,
        status="failed",
        message="manifest.xml does not declare host version metadata.",
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

    result = search_workspace(
        ctx,
        "PlayerDebugMode",
        max_results=20,
        roots=params.get("roots"),
    )

    if result.get("outcome") != "matches_found":
        return RuleResult(
            rule_id=rule_id,
            status="blocked",
            message=(
                "PlayerDebugMode reference was not found in the indexed "
                "workspace. This usually means debug mode is not enabled "
                "in host settings or references were not indexed."
            ),
            evidence={
                "searched_roots": result.get("searched_roots"),
            },
            severity="warning",
            required=False,
            fast_fail=False,
        )

    hits = [
        {
            "path": item["path"],
            "score": item["score"],
        }
        for item in result["results"][:5]
    ]

    return RuleResult(
        rule_id=rule_id,
        status="passed",
        message="Indexed workspace references PlayerDebugMode.",
        evidence={
            "hits": hits,
            "note": (
                "Many PlayerDebugMode references were found."
                if len(result.get("results", [])) >= 10
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

    result = search_workspace(
        ctx,
        ".",
        max_results=200,
        extensions=[
            ".zxp",
            ".zip",
            ".7z",
            ".rar",
            ".tar",
            ".gz",
        ],
        roots=params.get("roots"),
    )

    if result.get("outcome") != "matches_found":
        return RuleResult(
            rule_id=rule_id,
            status="passed",
            message="No packaging archives were found in the indexed roots.",
        )

    hits = [
        item["path"]
        for item in result["results"][:10]
    ]

    return RuleResult(
        rule_id=rule_id,
        status="failed",
        message="Packaging archives were found in the workspace.",
        evidence={
            "hits": hits,
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



def rule_cep_menubar_extension(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.menubar_extension"
    workspace_root = params.get("workspace_root")

    if workspace_root:
        root = Path(workspace_root).expanduser().resolve()
        if root.exists() and root.is_dir():
            for candidate in root.rglob("*.xml"):
                try:
                    if candidate.is_file():
                        content = candidate.read_text(encoding="utf-8", errors="ignore")
                        if _parse_menubar_extension(content):
                            return RuleResult(
                                rule_id=rule_id,
                                status="passed",
                                message="Valid menu extension registration found.",
                                evidence={
                                    "path": str(candidate),
                                    "relative_path": candidate.relative_to(root).as_posix(),
                                },
                            )
                except (OSError, PermissionError):
                    continue

    return RuleResult(
        rule_id=rule_id,
        status="not_applicable",
        message="No valid menu extension registration found.",
    )


register_rule(
    "cep",
    "cep.menubar_extension",
    lambda ctx, p: _rule(
        ctx,
        p,
        "cep.menubar_extension",
        rule_cep_menubar_extension,
    ),
)

def rule_cep_symlink_free(
    ctx: Context,
    params: dict[str, Any],
) -> RuleResult:
    rule_id = "cep.symlink_free"
    workspace_root = params.get("workspace_root")

    if workspace_root:
        direct_root = Path(workspace_root).expanduser().absolute()

        if not direct_root.exists() or not direct_root.is_dir():
            raise GovernanceError(
                f"Workspace root does not exist or is not a directory: "
                f"{direct_root}"
            )

        scan_roots = [(direct_root.name, direct_root)]
        # Define selected_rools for workspace_root mode (fallback to empty list if no roots in ctx)
        selected_roots: list[Path] = [direct_root]
    else:
        selected_roots = list(ctx.roots)
        requested_roots = params.get("roots")

        if requested_roots is not None:
            selected_roots = [
                root
                for root in selected_roots
                if root.name in requested_roots
            ]

        requested_root_names = set(requested_roots or [])
        selected_root_names = {root.name for root in selected_roots}
        missing_roots = requested_root_names - selected_root_names

        if missing_roots:
            raise GovernanceError(
                f"Unknown requested roots: {sorted(missing_roots)}"
            )

        scan_roots = [
            (root.name, Path(root.path).expanduser().absolute())
            for root in selected_roots
        ]

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

    for root_name, root_path in scan_roots:
        pending = [root_path]

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
                            relative = entry.relative_to(root_path)
                            display_path = (
                                f"{root_name}/{relative.as_posix()}"
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