"""STEM photo-first workspace (Math, Physics). [v1.2+ stub]"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from app.core.llm_client import LLMClient
from app.database.db_manager import DBManager
from app.workspaces.base import BaseWorkspace
from app.workspaces.factory import WorkspaceFactory


class STEMWorkspace(BaseWorkspace):
    """Photo-first math/physics. NOT IMPLEMENTED in v1.0."""

    workspace_id = "stem"
    display_name = "Math & Physics — Photo-First [v1.2+]"

    def __init__(self, attempt_id: int, db: DBManager, llm_client: LLMClient) -> None:
        super().__init__(attempt_id, db, llm_client)

    def build_widget(self) -> QWidget:
        raise NotImplementedError(
            "STEMWorkspace lands in v1.2. Requires vision model. See spec §1.2 #2."
        )

    def build_context_payload(self) -> dict[str, Any]:
        raise NotImplementedError

    def grade(self) -> dict[str, Any]:
        raise NotImplementedError


WorkspaceFactory.register(STEMWorkspace.workspace_id, STEMWorkspace)
