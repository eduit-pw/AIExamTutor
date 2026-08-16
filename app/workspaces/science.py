"""Science workspace (Chemistry, Biology, Geography). [v1.2+ stub]"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from app.core.llm_client import LLMClient
from app.database.db_manager import DBManager
from app.workspaces.base import BaseWorkspace
from app.workspaces.factory import WorkspaceFactory


class ScienceWorkspace(BaseWorkspace):
    """Formula toolbar + photo OCR. NOT IMPLEMENTED in v1.0."""

    workspace_id = "science"
    display_name = "Biology, Geography, Chemistry [v1.2+]"

    def __init__(self, attempt_id: int, db: DBManager, llm_client: LLMClient) -> None:
        super().__init__(attempt_id, db, llm_client)

    def build_widget(self) -> QWidget:
        raise NotImplementedError(
            "ScienceWorkspace lands in v1.2. Requires vision model. See spec §1.2 #4-5."
        )

    def build_context_payload(self) -> dict[str, Any]:
        raise NotImplementedError

    def grade(self) -> dict[str, Any]:
        raise NotImplementedError


WorkspaceFactory.register(ScienceWorkspace.workspace_id, ScienceWorkspace)
