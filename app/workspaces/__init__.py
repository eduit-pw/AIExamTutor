"""Subject workspaces — INF.03 implemented in v1.0; others are stubs."""

# Importing each module registers it with WorkspaceFactory as a side effect.
from app.workspaces import (  # noqa: F401
    foreign_language,
    humanities,
    inf03,
    inf04,
    science,
    stem,
)
from app.workspaces.base import BaseWorkspace
from app.workspaces.factory import (
    WorkspaceFactory,
    WorkspaceNotFoundError,
    build_context_envelope,
)
from app.workspaces.inf03 import INF03Workspace

__all__ = [
    "BaseWorkspace",
    "INF03Workspace",
    "WorkspaceFactory",
    "WorkspaceNotFoundError",
    "build_context_envelope",
]
