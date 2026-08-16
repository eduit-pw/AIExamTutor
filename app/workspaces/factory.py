"""WorkspaceFactory — registry + factory for subject workspaces.

Per spec §4.2, this is the single point MainWindow queries to swap the centre
pane. Subclasses register themselves at import time via the `register` class
method. Stubs (v1.1+) still register — they raise NotImplementedError at
construction so the UI can grey them out.
"""

from __future__ import annotations

from typing import Any

from app.core.llm_client import LLMClient
from app.database.db_manager import DBManager
from app.workspaces.base import BaseWorkspace


class WorkspaceNotFoundError(LookupError):
    """Raised when WorkspaceFactory.create is called with an unknown id."""


class _WorkspaceRegistry(dict[str, type[BaseWorkspace]]):
    """Registry that restores built-in bindings after a test reset."""

    def __init__(self) -> None:
        super().__init__()
        self._builtins: dict[str, type[BaseWorkspace]] = {}

    def remember_builtin(
        self, workspace_id: str, workspace_cls: type[BaseWorkspace]
    ) -> None:
        self._builtins[workspace_id] = workspace_cls

    def clear(self) -> None:
        super().clear()
        super().update(self._builtins)

    def restore_builtins(self) -> None:
        """Restore the built-in bindings after an isolated test mutation."""
        super().clear()
        super().update(self._builtins)


class WorkspaceFactory:
    """Static registry mapping workspace_id -> BaseWorkspace subclass."""

    _registry = _WorkspaceRegistry()

    @classmethod
    def register(cls, workspace_id: str, workspace_cls: type[BaseWorkspace]) -> None:
        """Register `workspace_cls` under `workspace_id`.

        Re-registration of the same id replaces the previous binding — useful
        for tests that swap implementations.
        """
        cls._registry[workspace_id] = workspace_cls
        cls._registry.remember_builtin(workspace_id, workspace_cls)

    @classmethod
    def unregister(cls, workspace_id: str) -> None:
        """Remove a binding. No-op if absent. Mostly for tests."""
        cls._registry.pop(workspace_id, None)

    @classmethod
    def reset(cls) -> None:
        """Restore all workspace bindings registered by the application."""
        cls._registry.restore_builtins()

    @classmethod
    def create(
        cls,
        workspace_id: str,
        attempt_id: int,
        db: DBManager,
        llm_client: LLMClient,
    ) -> BaseWorkspace:
        """Instantiate the workspace class registered under `workspace_id`."""
        workspace_cls = cls._registry.get(workspace_id)
        if workspace_cls is None:
            raise WorkspaceNotFoundError(
                f"No workspace registered under id {workspace_id!r}"
            )
        return workspace_cls(attempt_id, db, llm_client)

    @classmethod
    def available(cls) -> list[str]:
        """Return all registered workspace ids in deterministic order."""
        return sorted(cls._registry.keys())

    @classmethod
    def display_name_for(cls, workspace_id: str) -> str:
        """Return the human-readable label for a registered workspace."""
        workspace_cls = cls._registry.get(workspace_id)
        if workspace_cls is None:
            return workspace_id
        return workspace_cls.display_name or workspace_id


def build_context_envelope(workspace: BaseWorkspace, extra: dict[str, Any]) -> dict[str, Any]:
    """Helper for callers that want the merged chat context.

    Wraps the workspace payload with a few well-known keys the LLM client
    always wants (subject + workspace_id), so call sites don't have to repeat
    them.
    """
    payload = workspace.build_context_payload()
    payload.setdefault("workspace_id", workspace.workspace_id)
    payload.setdefault("subject", workspace.workspace_id)
    payload.update(extra)
    return payload