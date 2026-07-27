from __future__ import annotations

import hashlib
import re
from pathlib import Path


def canonical_workspace_root(value: str | Path) -> Path:
    candidate = Path(value).expanduser()

    if '..' in candidate.parts:
        raise FileNotFoundError(
            f'Workspace root must not contain parent traversal: {candidate}'
        )

    absolute = candidate.absolute()
    current = Path(absolute.anchor)

    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise FileNotFoundError(
                f'Workspace root must not contain symlinks: {current}'
            )

    try:
        root = absolute.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise FileNotFoundError(
            f'Workspace root does not exist: {absolute}'
        ) from exc

    if not root.is_dir():
        raise FileNotFoundError(
            f'Workspace root is not a directory: {root}'
        )

    return root

def project_workspace_id(
    workspace_root: str | Path,
    requested_id: str | None = None,
) -> str:
    root = canonical_workspace_root(workspace_root)
    canonical = str(root).replace("\\", "/").rstrip("/").casefold()
    fingerprint = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]

    label_source = requested_id or root.name or 'workspace'
    label = re.sub(
        r'[^a-zA-Z0-9_.-]+',
        '-',
        label_source.strip(),
    ).strip('-.').lower()

    if not label:
        label = 'workspace'

    return f'{label}-{fingerprint}'
