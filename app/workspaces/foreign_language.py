"""Foreign-language workspace (English Matura primary subject). [v1.1+ stub]"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from app.core.llm_client import LLMClient
from app.database.db_manager import DBManager
from app.workspaces.base import BaseWorkspace
from app.workspaces.factory import WorkspaceFactory


class ForeignLanguageWorkspace(BaseWorkspace):
    """Written expression + listening comprehension. NOT IMPLEMENTED in v1.0."""

    workspace_id = "foreign_language"
    display_name = "English — Written Expression [v1.1+]"

    def __init__(self, attempt_id: int, db: DBManager, llm_client: LLMClient) -> None:
        super().__init__(attempt_id, db, llm_client)

    def build_widget(self) -> QWidget:
        raise NotImplementedError(
            "ForeignLanguageWorkspace lands in v1.1. See spec §1.2 (subject #1)."
        )

    def build_context_payload(self) -> dict[str, Any]:
        raise NotImplementedError

    def grade(self) -> dict[str, Any]:
        raise NotImplementedError


WorkspaceFactory.register(ForeignLanguageWorkspace.workspace_id, ForeignLanguageWorkspace)
