"""Canonical project identity and configured-root resolution."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent import Context, GovernanceError, KnowledgeRoot

from .project_profiler import ProjectProfiler


@dataclass(frozen=True)
class WorkspaceIdentity:
    configured_root_id: str
    configured_root: Path
    target_project_root: Path
    workspace_id: str


def resolve_workspace_identity(ctx: Context, workspace_root: str | Path) -> WorkspaceIdentity:
    target = Path(workspace_root).expanduser().resolve()
    if not target.is_dir():
        raise GovernanceError(f"Target project root does not exist or is not a directory: {target}")

    matches: list[KnowledgeRoot] = []
    for root in ctx.roots:
        configured = root.path.expanduser().resolve()
        try:
            target.relative_to(configured)
        except ValueError:
            continue
        matches.append(root)

    if len(matches) != 1:
        if not matches:
            raise GovernanceError(f"Target project root is outside configured roots: {target}")
        raise GovernanceError(f"Target project root resolves ambiguously: {target}")

    configured = matches[0]
    return WorkspaceIdentity(
        configured_root_id=configured.name,
        configured_root=configured.path.expanduser().resolve(),
        target_project_root=target,
        workspace_id=ProjectProfiler.workspace_id(target),
    )


def scoped_context(ctx: Context, identity: WorkspaceIdentity) -> Context:
    """Expose only the selected project to deterministic guards."""
    return Context(
        config=ctx.config,
        governance=ctx.governance,
        roots=(KnowledgeRoot(identity.configured_root_id, identity.target_project_root),),
    )
